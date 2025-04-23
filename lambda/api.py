# api.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import re
import logging
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from mangum import Mangum

# Import the utility functions
from utils.youtube_api import fetch_comments, extract_video_statistics
from utils.sentiment import analyze_sentiment, get_sentiment_emoji
from utils.topic_analysis import extract_topics, generate_content_ideas, extract_keywords

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Analytics API",
    description="API for analyzing YouTube videos and comments",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Enable CORS to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Lambda handler
handler = Mangum(app)

# Function to extract YouTube video ID
def extract_video_id(url: str) -> Optional[str]:
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
def fetch_all_comments(video_id: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all comments from a YouTube video using pagination
    
    Args:
        video_id (str): YouTube video ID
        max_results (int, optional): Maximum number of comments to fetch. If None, fetches all.
            
    Returns:
        list: List of comment dictionaries
        
    Raises:
        HTTPException: If there's an error fetching comments
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
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """API Root endpoint with documentation"""
    # Check if API key is configured
    api_key = os.getenv('YOUTUBE_API_KEY')
    api_configured = api_key and api_key != 'YOUR_API_KEY'
    
    api_status = {
        'status': 'ready' if api_configured else 'not configured',
        'message': 'API is ready to use' if api_configured else 'YouTube API key not configured. Set YOUTUBE_API_KEY environment variable.'
    }
    
    return {
        'name': 'YouTube Analytics API',
        'version': '1.0.0',
        'description': 'API for analyzing YouTube videos and comments',
        'api_status': api_status,
        'endpoints': {
            '/api/health': 'Health check endpoint',
            '/api/video-info': 'Get basic video information',
            '/api/comments': 'Get comments for a video',
            '/api/analyze': 'Full analysis of video comments',
            '/api/sentiment': 'Analysis of comment sentiment',
            '/api/topics': 'Analysis of comment topics',
            '/api/comments/search': 'Search for specific comments'
        },
        'requirements': 'Valid YouTube Data API key required for all endpoints',
        'usage': 'Use ?url=YOUTUBE_VIDEO_URL parameter for most endpoints'
    }

@app.get("/api/video-info")
async def get_video_info(
    url: str = Query(..., description="YouTube video URL or ID")
):
    """Get basic information about a YouTube video"""
    # Check if API key is configured
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key or api_key == 'YOUR_API_KEY':
        raise HTTPException(
            status_code=503,
            detail="YouTube API key not configured. Please set YOUTUBE_API_KEY environment variable."
        )
    
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        video_stats = extract_video_statistics(video_id)
        if not video_stats:
            raise HTTPException(status_code=404, detail="Could not retrieve video information")
        
        # Add thumbnail URL to response
        video_stats['thumbnail_url'] = f"https://img.youtube.com/vi/{video_id}/0.jpg"
        
        return {
            'success': True,
            'video_id': video_id,
            'video_info': video_stats
        }
    
    except ValueError as ve:
        # Handle specific API key related errors
        if "API key not found" in str(ve):
            raise HTTPException(status_code=503, detail="YouTube API key not configured or invalid")
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/comments")
async def get_comments(
    url: str = Query(..., description="YouTube video URL or ID"),
    max_comments: Optional[int] = Query(None, description="Maximum number of comments to fetch")
):
    """Get comments for a YouTube video"""
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return {
                'success': True,
                'video_id': video_id,
                'comments': [],
                'message': 'No comments found for this video.'
            }
        
        # Normalize comment structure
        for comment in comments:
            # Ensure required fields exist
            if 'likes' not in comment:
                comment['likes'] = 0
            if 'reply_count' not in comment:
                comment['reply_count'] = 0
            
        return {
            'success': True,
            'video_id': video_id,
            'comments': comments,
            'comment_count': len(comments)
        }
    
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analyze")
async def analyze_video(
    url: str = Query(..., description="YouTube video URL or ID"),
    max_comments: Optional[int] = Query(None, description="Maximum number of comments to analyze")
):
    """Comprehensive analysis of a YouTube video's comments"""
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        # First try to get video statistics
        video_stats = extract_video_statistics(video_id)
        if video_stats:
            # Add thumbnail URL to response
            video_stats['thumbnail_url'] = f"https://img.youtube.com/vi/{video_id}/0.jpg"
        
        # Fetch comments - either all or limited number
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return {
                'success': True,
                'video_id': video_id,
                'video_info': video_stats,
                'error_message': 'No comments found for this video.',
                'analysis': None
            }
        
        # Analyze sentiment for each comment
        for comment in comments:
            comment['sentiment'] = analyze_sentiment(comment['text'])
            # Add sentiment emoji for frontend use
            comment['sentiment_emoji'] = get_sentiment_emoji(comment['sentiment'])
        
        # Make sure likes is always a valid number
        for comment in comments:
            if 'likes' not in comment:
                comment['likes'] = 0
            elif not isinstance(comment['likes'], (int, float)):
                try:
                    comment['likes'] = int(comment['likes'])
                except (ValueError, TypeError):
                    comment['likes'] = 0
            
            # Make sure reply_count is always a valid number
            if 'reply_count' not in comment:
                comment['reply_count'] = 0
            elif not isinstance(comment['reply_count'], (int, float)):
                try:
                    comment['reply_count'] = int(comment['reply_count'])
                except (ValueError, TypeError):
                    comment['reply_count'] = 0
        
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
                    {'name': 'Positive', 'value': sentiment_counts['positive'], 'percentage': sentiment_percentages['positive'], 'emoji': get_sentiment_emoji('positive')},
                    {'name': 'Neutral', 'value': sentiment_counts['neutral'], 'percentage': sentiment_percentages['neutral'], 'emoji': get_sentiment_emoji('neutral')},
                    {'name': 'Negative', 'value': sentiment_counts['negative'], 'percentage': sentiment_percentages['negative'], 'emoji': get_sentiment_emoji('negative')}
                ]
            },
            'topic_data': topic_data,
            'content_ideas': content_ideas,
            'keywords': keywords,
            'top_comments': sorted(comments, key=lambda x: x.get('likes', 0), reverse=True)[:5],
            'recent_comments': sorted(comments, key=lambda x: x.get('date', ''), reverse=True)[:5]
        }
        
        # Add timestamp for analysis
        analysis_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            'success': True,
            'video_id': video_id,
            'video_info': video_stats,
            'analysis': analysis_data,
            'analysis_timestamp': analysis_timestamp,
            'comments_analyzed': total_comments
        }
    
    except Exception as e:
        logger.error(f"Error analyzing video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sentiment")
async def analyze_sentiment_only(
    url: str = Query(..., description="YouTube video URL or ID"),
    max_comments: Optional[int] = Query(None, description="Maximum number of comments to analyze")
):
    """Analyze only the sentiment of a YouTube video's comments"""
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        # Fetch comments
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return {
                'success': True,
                'video_id': video_id,
                'error_message': 'No comments found for this video.',
                'sentiment_analysis': None
            }
        
        # Analyze sentiment for each comment
        for comment in comments:
            comment['sentiment'] = analyze_sentiment(comment['text'])
            comment['sentiment_emoji'] = get_sentiment_emoji(comment['sentiment'])
        
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
        
        # Get sentiment emojis
        sentiment_emojis = {
            'positive': get_sentiment_emoji('positive'),
            'neutral': get_sentiment_emoji('neutral'),
            'negative': get_sentiment_emoji('negative')
        }
        
        return {
            'success': True,
            'video_id': video_id,
            'sentiment_analysis': {
                'counts': sentiment_counts,
                'percentages': sentiment_percentages,
                'emojis': sentiment_emojis,
                'formatted': [
                    {'name': 'Positive', 'value': sentiment_counts['positive'], 'percentage': sentiment_percentages['positive'], 'emoji': sentiment_emojis['positive']},
                    {'name': 'Neutral', 'value': sentiment_counts['neutral'], 'percentage': sentiment_percentages['neutral'], 'emoji': sentiment_emojis['neutral']},
                    {'name': 'Negative', 'value': sentiment_counts['negative'], 'percentage': sentiment_percentages['negative'], 'emoji': sentiment_emojis['negative']}
                ]
            },
            'comments_analyzed': len(comments),
            'comments_with_sentiment': comments
        }
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/topics")
async def analyze_topics_only(
    url: str = Query(..., description="YouTube video URL or ID"),
    max_comments: Optional[int] = Query(None, description="Maximum number of comments to analyze")
):
    """Analyze only the topics of a YouTube video's comments"""
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        # Fetch comments
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return {
                'success': True,
                'video_id': video_id,
                'error_message': 'No comments found for this video.',
                'topic_analysis': None
            }
        
        # Extract topics and content ideas
        topic_data = extract_topics(comments)
        content_ideas = generate_content_ideas(comments)
        keywords = extract_keywords(comments, top_n=20)
        
        return {
            'success': True,
            'video_id': video_id,
            'topic_analysis': {
                'topic_data': topic_data,
                'content_ideas': content_ideas,
                'keywords': keywords
            },
            'comments_analyzed': len(comments)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing topics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/comments/search")
async def search_comments(
    url: str = Query(..., description="YouTube video URL or ID"),
    q: str = Query(..., description="Search term"),
    max_comments: Optional[int] = Query(None, description="Maximum number of comments to search"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, neutral, negative)")
):
    """Search for comments containing specific terms"""
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid YouTube URL or video ID."
        )
    
    try:
        # Fetch all comments first
        comments = fetch_all_comments(video_id, max_results=max_comments)
        
        if not comments:
            return {
                'success': True,
                'video_id': video_id,
                'error_message': 'No comments found for this video.',
                'search_results': []
            }
        
        # Add sentiment to comments
        for comment in comments:
            comment['sentiment'] = analyze_sentiment(comment['text'])
        
        # Filter based on search term
        search_term = q.lower()
        search_results = [c for c in comments if search_term in c['text'].lower()]
        
        # Apply sentiment filter if provided
        if sentiment and sentiment in ['positive', 'neutral', 'negative']:
            search_results = [c for c in search_results if c.get('sentiment') == sentiment]
        
        return {
            'success': True,
            'video_id': video_id,
            'search_term': q,
            'sentiment_filter': sentiment,
            'search_results': search_results,
            'result_count': len(search_results),
            'total_comments_searched': len(comments)
        }
    
    except Exception as e:
        logger.error(f"Error searching comments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    api_configured = api_key and api_key != 'YOUR_API_KEY'
    
    if not api_configured:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'error',
                'service': 'youtube-analytics-api',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'error': 'YouTube API key not configured. Please set YOUTUBE_API_KEY environment variable.',
                'version': '1.0.0'
            }
        )
    
    return {
        'status': 'ok',
        'service': 'youtube-analytics-api',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'api_configured': True,
        'version': '1.0.0'
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# For local development
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)