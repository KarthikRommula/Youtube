import os
import requests
import time
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def fetch_comments(video_id, max_results=100, page_token=None):
    """
    Fetch comments from a YouTube video using the API key
    
    Args:
        video_id (str): YouTube video ID
        max_results (int): Maximum number of comments to fetch
        page_token (str, optional): Token for pagination
        
    Returns:
        dict: Dictionary with comments and metadata
    """
    # Get API key directly from environment variables
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    # Validate API key
    if not api_key or api_key == 'YOUR_API_KEY':
        error_msg = "YouTube API key not found or not set. Please add it to your .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Initialize empty list for comments
    comments = []
    
    # Build the parameters for the API request - API key is included in the params
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_results, 100),  # API max is 100 per request
        "key": api_key,
        "textFormat": "plainText"  # Get plain text rather than HTML
    }
    
    # Add page token if provided (for pagination)
    if page_token:
        params["pageToken"] = page_token
    
    try:
        # Log the API request (without exposing the key)
        logger.info(f"Making YouTube API request for comments with video ID: {video_id}")
        
        # Make the API request using only the key in params (no URL)
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            params=params,
            timeout=15
        )
        
        # Handle response errors
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Process the comments
        if "items" in data and len(data["items"]) > 0:
            logger.info(f"Successfully retrieved {len(data['items'])} comments")
            
            for item in data["items"]:
                comment_snippet = item["snippet"]["topLevelComment"]["snippet"]
                
                # Parse the date
                date_str = comment_snippet.get("publishedAt", "")
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_date = date_str
                    logger.warning(f"Could not parse date: {date_str}")
                
                # Clean up text from HTML if needed
                text = comment_snippet.get("textDisplay", "")
                text = text.replace("<br>", "\n").replace("&nbsp;", " ")
                
                # Create the comment object
                try:
                    like_count = int(comment_snippet.get("likeCount", 0))
                except (ValueError, TypeError):
                    like_count = 0
                    
                comment = {
                    "id": item["id"],
                    "author_name": comment_snippet.get("authorDisplayName", "Anonymous"),
                    "author_channel_url": comment_snippet.get("authorChannelUrl", ""),
                    "author_profile_image": comment_snippet.get("authorProfileImageUrl", ""),
                    "text": text,
                    "likes": like_count,
                    "date": formatted_date,
                    "reply_count": item["snippet"].get("totalReplyCount", 0)
                }
                
                comments.append(comment)
            
            # Return comments and metadata
            return {
                "comments": comments,
                "metadata": {
                    "nextPageToken": data.get("nextPageToken"),
                    "totalResults": data.get("pageInfo", {}).get("totalResults", 0)
                }
            }
        else:
            # No comments found
            logger.info("No comments found for this video.")
            return {
                "comments": [],
                "metadata": {
                    "nextPageToken": None,
                    "totalResults": 0
                }
            }
            
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        raise ValueError(f"Error accessing YouTube API: {str(e)}")

def fetch_all_comments(video_id, max_results=None):
    """
    Fetch all comments from a YouTube video with pagination
    
    Args:
        video_id (str): YouTube video ID
        max_results (int, optional): Maximum number of comments to fetch. If None, fetches all.
        
    Returns:
        list: List of comment dictionaries
    """
    # Initialize empty list for all comments
    all_comments = []
    
    # Track pagination
    next_page_token = None
    page_num = 1
    
    # Set up Streamlit progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(f"Starting to fetch comments...")
    
    try:
        # Loop until we have all comments or reach max_results
        while True:
            # Update status
            status_text.text(f"Fetching page {page_num} of comments...")
            
            # Fetch a page of comments (100 is max per page)
            result = fetch_comments(
                video_id=video_id,
                max_results=100,
                page_token=next_page_token
            )
            
            # Get comments and metadata from result
            page_comments = result["comments"]
            metadata = result.get("metadata", {})
            
            # Check if we got any comments
            if not page_comments or len(page_comments) == 0:
                logger.info(f"No comments found on page {page_num}")
                break
                
            # Add this page's comments to our total
            all_comments.extend(page_comments)
            
            # Update progress
            status_text.text(f"Retrieved {len(all_comments)} comments so far...")
            
            # Show progress
            progress_value = min(0.95, page_num * 0.1)  # Never quite reaches 100% until done
            progress_bar.progress(progress_value)
            
            # Check if we need to stop based on max_results
            if max_results is not None and len(all_comments) >= max_results:
                logger.info(f"Reached requested maximum of {max_results} comments")
                all_comments = all_comments[:max_results]  # Trim to exact count
                break
                
            # Get the next page token
            next_page_token = metadata.get("nextPageToken")
            
            # If no more pages, we're done
            if not next_page_token:
                logger.info("No more comment pages available")
                break
                
            # Sleep briefly to avoid API rate limits
            time.sleep(0.5)
            
            # Increment page counter
            page_num += 1
        
        # Complete the progress bar
        progress_bar.progress(1.0)
        status_text.text(f"Successfully retrieved {len(all_comments)} comments!")
        
        logger.info(f"Successfully retrieved a total of {len(all_comments)} comments")
        return all_comments
        
    except Exception as e:
        logger.error(f"Error in fetch_all_comments: {str(e)}")
        progress_bar.progress(1.0)
        status_text.text(f"Error: {str(e)}")
        raise ValueError(f"Error fetching comments: {str(e)}")

def extract_video_statistics(video_id):
    """
    Fetch basic statistics for a YouTube video
    
    Args:
        video_id (str): YouTube video ID
        
    Returns:
        dict: Video statistics
    """
    # Get API key directly from environment variable
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key or api_key == 'YOUR_API_KEY':
        error_msg = "YouTube API key not found or not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Build the parameters for the API request
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    
    try:
        logger.info(f"Making YouTube API request for video statistics with video ID: {video_id}")
        
        # Make the API request using only the key
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("items"):
            logger.warning(f"No video found with ID {video_id}")
            raise ValueError(f"No video found with ID {video_id}")
        
        video_data = data["items"][0]
        snippet = video_data.get("snippet", {})
        statistics = video_data.get("statistics", {})
        
        # Parse the date
        date_str = snippet.get("publishedAt", "")
        try:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = date_str
        
        return {
            "title": snippet.get("title", "Unknown Title"),
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "views": int(statistics.get("viewCount", 0)),
            "likes": int(statistics.get("likeCount", 0)),   
            "comments": int(statistics.get("commentCount", 0)),
            "published_at": formatted_date,
            "description": snippet.get("description", "No description available")
        }
        
    except Exception as e:
        logger.error(f"Error fetching video statistics: {e}")
        raise ValueError(f"Error accessing YouTube API: {str(e)}")