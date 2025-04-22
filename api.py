from flask import Flask, request, jsonify
import re
import logging
import pandas as pd
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Import the same utility functions
from utils.youtube_api import fetch_comments, extract_video_statistics
from utils.sentiment import analyze_sentiment
from utils.topic_analysis import extract_topics, generate_content_ideas, extract_keywords

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Function to extract YouTube video ID
def extract_video_id(url):
    """Extract the YouTube video ID from various URL formats"""
    if not url:
        return None
        
    patterns = [
        r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Check if the input is directly a video ID (11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
        
    return None

# Function to fetch all comments with pagination
def fetch_all_comments(video_id, max_results=None):
    """
    Fetch all comments from a YouTube video using pagination
    """
    all_comments = []
    page_token = None
    page_num = 1
    
    try:
        while True:
            logger.info(f"Fetching page {page_num} of comments...")
            
            # Fetch a page of comments (100 is the max per page)
            result = fetch_comments(
                video_id=video_id,
                max_results=100,
                page_token=page_token
            )
            
            # Extract comments and next page token
            page_comments = result["comments"]
            next_page_token = result["metadata"]["nextPageToken"]
            
            # If no comments were found, exit the loop
            if not page_comments or len(page_comments) == 0:
                break
            
            all_comments.extend(page_comments)
            
            # Check if we need to stop based on max_results
            if max_results is not None and len(all_comments) >= max_results:
                logger.info(f"Reached requested maximum of {max_results} comments")
                all_comments = all_comments[:max_results]  # Trim to exact count
                break
            
            # If no next page token, we're done
            if not next_page_token:
                logger.info("No more comment pages available")
                break
                
            # Set the token for the next iteration
            page_token = next_page_token
            page_num += 1
            
            # Add a small delay to avoid hitting API rate limits
            time.sleep(0.5)
        
        logger.info(f"Successfully retrieved {len(all_comments)} comments!")
        return all_comments
        
    except Exception as e:
        logger.error(f"Error fetching all comments: {str(e)}")
        # Return any comments we managed to fetch before the error
        if all_comments:
            logger.warning(f"Only retrieved {len(all_comments)} comments due to an error.")
            return all_comments
        else:
            raise

@app.route('/api/video-info', methods=['GET'])
def get_video_info():
    """Get basic information about a YouTube video"""
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube URL or video ID.'}), 400
    
    try:
        video_stats = extract_video_statistics(video_id)
        if not video_stats:
            return jsonify({'error': 'Could not retrieve video information'}), 404
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_info': video_stats
        })
    
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/comments', methods=['GET'])
def get_comments():
    """Get comments for a YouTube video"""
    video_url = request.args.get('url')
    max_comments = request.args.get('max_comments')
    
    if max_comments:
        try:
            max_comments = int(max_comments)
        except ValueError:
            return jsonify({'error': 'max_comments must be a number'}), 400
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube URL or video ID.'}), 400
    
    try:
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'comments': [],
                'message': 'No comments found for this video.'
            })
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'comments': comments,
            'comment_count': len(comments)
        })
    
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['GET'])
def analyze_video():
    """Comprehensive analysis of a YouTube video's comments"""
    video_url = request.args.get('url')
    max_comments = request.args.get('max_comments')
    
    if max_comments:
        try:
            max_comments = int(max_comments)
        except ValueError:
            return jsonify({'error': 'max_comments must be a number'}), 400
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube URL or video ID.'}), 400
    
    try:
        # First try to get video statistics
        video_stats = extract_video_statistics(video_id)
        
        # Fetch comments - either all or limited number
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'video_info': video_stats,
                'error_message': 'No comments found for this video.',
                'analysis': None
            })
        
        # Analyze sentiment for each comment
        for comment in comments:
            comment['sentiment'] = analyze_sentiment(comment['text'])
        
        # Make sure likes is always a valid number
        for comment in comments:
            if 'likes' not in comment:
                comment['likes'] = 0
            elif not isinstance(comment['likes'], (int, float)):
                try:
                    comment['likes'] = int(comment['likes'])
                except (ValueError, TypeError):
                    comment['likes'] = 0
        
        # Analyze comments
        total_comments = len(comments)
        total_likes = sum(comment.get('likes', 0) for comment in comments)
        total_replies = sum(comment.get('reply_count', 0) for comment in comments)
        
        # Calculate sentiment counts
        sentiment_counts = {
            'positive': len([c for c in comments if c.get('sentiment') == 'positive']),
            'neutral': len([c for c in comments if c.get('sentiment') == 'neutral']),
            'negative': len([c for c in comments if c.get('sentiment') == 'negative'])
        }
        
        # Get total sentiment percentage
        total_sentiments = sum(sentiment_counts.values())
        sentiment_percentages = {
            k: round((v / total_sentiments) * 100) if total_sentiments else 0 
            for k, v in sentiment_counts.items()
        }
        
        # Extract topics and content ideas
        topic_data = extract_topics(comments)
        content_ideas = generate_content_ideas(comments)
        
        # Extract keywords
        keywords = extract_keywords(comments, top_n=20)
        
        # Create dashboard data structure
        analysis_data = {
            'basic_stats': {
                'total_comments': total_comments,
                'total_likes': total_likes,
                'total_replies': total_replies,
                'engagement_rate': round(total_likes / total_comments, 1) if total_comments else 0
            },
            'sentiment_data': {
                'counts': sentiment_counts,
                'percentages': sentiment_percentages,
                'formatted': [
                    {'name': 'Positive', 'value': sentiment_counts['positive'], 'percentage': sentiment_percentages['positive']},
                    {'name': 'Neutral', 'value': sentiment_counts['neutral'], 'percentage': sentiment_percentages['neutral']},
                    {'name': 'Negative', 'value': sentiment_counts['negative'], 'percentage': sentiment_percentages['negative']}
                ]
            },
            'topic_data': topic_data,
            'content_ideas': content_ideas,
            'keywords': keywords,
            'top_comments': sorted(comments, key=lambda x: x.get('likes', 0), reverse=True)[:5],
            'recent_comments': sorted(comments, key=lambda x: x.get('date', ''), reverse=True)[:5]
        }
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_info': video_stats,
            'analysis': analysis_data,
            'analysis_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'comments_analyzed': total_comments
        })
    
    except Exception as e:
        logger.error(f"Error analyzing video: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sentiment', methods=['GET'])
def analyze_sentiment_only():
    """Analyze only the sentiment of a YouTube video's comments"""
    video_url = request.args.get('url')
    max_comments = request.args.get('max_comments')
    
    if max_comments:
        try:
            max_comments = int(max_comments)
        except ValueError:
            return jsonify({'error': 'max_comments must be a number'}), 400
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube URL or video ID.'}), 400
    
    try:
        # Fetch comments
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'error_message': 'No comments found for this video.',
                'sentiment_analysis': None
            })
        
        # Analyze sentiment for each comment
        for comment in comments:
            comment['sentiment'] = analyze_sentiment(comment['text'])
        
        # Calculate sentiment counts
        sentiment_counts = {
            'positive': len([c for c in comments if c.get('sentiment') == 'positive']),
            'neutral': len([c for c in comments if c.get('sentiment') == 'neutral']),
            'negative': len([c for c in comments if c.get('sentiment') == 'negative'])
        }
        
        # Get total sentiment percentage
        total_sentiments = sum(sentiment_counts.values())
        sentiment_percentages = {
            k: round((v / total_sentiments) * 100) if total_sentiments else 0 
            for k, v in sentiment_counts.items()
        }
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'sentiment_analysis': {
                'counts': sentiment_counts,
                'percentages': sentiment_percentages,
                'formatted': [
                    {'name': 'Positive', 'value': sentiment_counts['positive'], 'percentage': sentiment_percentages['positive']},
                    {'name': 'Neutral', 'value': sentiment_counts['neutral'], 'percentage': sentiment_percentages['neutral']},
                    {'name': 'Negative', 'value': sentiment_counts['negative'], 'percentage': sentiment_percentages['negative']}
                ]
            },
            'comments_analyzed': len(comments)
        })
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics', methods=['GET'])
def analyze_topics_only():
    """Analyze only the topics of a YouTube video's comments"""
    video_url = request.args.get('url')
    max_comments = request.args.get('max_comments')
    
    if max_comments:
        try:
            max_comments = int(max_comments)
        except ValueError:
            return jsonify({'error': 'max_comments must be a number'}), 400
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube URL or video ID.'}), 400
    
    try:
        # Fetch comments
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'error_message': 'No comments found for this video.',
                'topic_analysis': None
            })
        
        # Extract topics and content ideas
        topic_data = extract_topics(comments)
        content_ideas = generate_content_ideas(comments)
        keywords = extract_keywords(comments, top_n=20)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'topic_analysis': {
                'topic_data': topic_data,
                'content_ideas': content_ideas,
                'keywords': keywords
            },
            'comments_analyzed': len(comments)
        })
    
    except Exception as e:
        logger.error(f"Error analyzing topics: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    api_configured = api_key and api_key != 'YOUR_API_KEY'
    
    return jsonify({
        'status': 'ok',
        'service': 'youtube-analytics-api',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'api_configured': api_configured
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)