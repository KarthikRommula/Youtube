#app.py
import streamlit as st
import re
import logging
import pandas as pd
from datetime import datetime
from utils.youtube_api import fetch_comments, extract_video_statistics
from utils.sentiment import analyze_sentiment, get_sentiment_emoji
from utils.topic_analysis import extract_topics, generate_content_ideas, extract_keywords
from components.dashboard import render_dashboard
from components.sentiment_view import render_sentiment_view
from components.topic_view import render_topic_view
from components.comments_view import render_comments_view
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Try to load custom CSS
try:
    with open("assets/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    logger.warning("CSS file not found. Using default styling.")
    # Add minimal default styling
    st.markdown("""
        <style>
        .header {background: linear-gradient(to right, #4f46e5, #7c3aed); color: white; padding: 2rem 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem; text-align: center;}
        .header h1 {font-size: 2.25rem; font-weight: 700; margin-bottom: 0.5rem;}
        .welcome-container {text-align: center; padding: 3rem; background-color: #f8fafc; border-radius: 0.75rem; border: 1px solid #e2e8f0; margin: 2rem 0;}
        footer {background-color: #1f2937; color: #e5e7eb; padding: 2rem 1rem; margin-top: 3rem; border-radius: 0.5rem;}
        </style>
    """, unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'comments' not in st.session_state:
    st.session_state.comments = []
if 'dashboard_data' not in st.session_state:
    st.session_state.dashboard_data = None
if 'video_id' not in st.session_state:
    st.session_state.video_id = ""
if 'video_stats' not in st.session_state:
    st.session_state.video_stats = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = "overview"
if 'analysis_timestamp' not in st.session_state:
    st.session_state.analysis_timestamp = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

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

# Function to reset session state
def reset_analysis():
    """Reset all analysis-related session state variables"""
    st.session_state.comments = []
    st.session_state.dashboard_data = None
    st.session_state.video_stats = None
    st.session_state.analysis_timestamp = None
    st.session_state.error_message = None

# Function to fetch all comments with pagination
# Function to fetch all comments with pagination
def fetch_all_comments(video_id, max_results=None):
    """
    Fetch all comments from a YouTube video using pagination
    
    Args:
        video_id (str): YouTube video ID
        max_results (int, optional): Maximum number of comments to fetch. If None, fetches all.
            
    Returns:
        list: List of comment dictionaries
    """
    all_comments = []
    page_token = None
    page_num = 1
    
    with st.spinner("Fetching comments..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            while True:
                status_text.text(f"Fetching page {page_num} of comments...")
                
                # Fetch a page of comments (100 is the max per page)
                result = fetch_comments(
                    video_id=video_id,
                    max_results=100,
                    page_token=page_token
                )
                
                # Now fetch_comments always returns a dictionary with 'comments' and 'metadata'
                page_comments = result["comments"]
                next_page_token = result["metadata"]["nextPageToken"]
                
                # If no comments were found, exit the loop
                if not page_comments or len(page_comments) == 0:
                    break
                
                all_comments.extend(page_comments)
                
                # Update progress
                status_text.text(f"Retrieved {len(all_comments)} comments so far...")
                
                # Show incremental progress
                progress_value = min(0.95, page_num * 0.1)  # Never quite reaches 100% until done
                progress_bar.progress(progress_value)
                
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
            
            # Finalize progress
            progress_bar.progress(1.0)
            status_text.text(f"Successfully retrieved {len(all_comments)} comments!")
            
            return all_comments
            
        except Exception as e:
            logger.error(f"Error fetching all comments: {str(e)}")
            status_text.text(f"Error: {str(e)}")
            
            # Return any comments we managed to fetch before the error
            if all_comments:
                st.warning(f"Only retrieved {len(all_comments)} comments due to an error.")
                return all_comments
            else:
                raise

# Application header
st.markdown("""
    <div class="header">
        <h1>📊 YouTube Analytics Dashboard</h1>
        <p>Analyze your video's performance and get actionable insights from comments</p>
    </div>
""", unsafe_allow_html=True)

# Create tabs for main content
main_tab, about_tab, settings_tab = st.tabs(["Dashboard", "About", "Settings"])

with main_tab:
    # Video URL input form
    with st.form(key='url_form'):
        col1, col2 = st.columns([4, 1])
        with col1:
            video_url = st.text_input(
                "Enter YouTube video URL", 
                placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                help="Paste a YouTube video URL or video ID to analyze its comments"
            )
        with col2:
            # Add option for "All Comments"
            comment_options = ["100 comments", "200 comments", "300 comments", "400 comments", "500 comments", "All comments"]
            comment_selection = st.selectbox(
                "Comments to analyze",
                options=comment_options,
                index=0,
                help="Select how many comments to analyze. 'All comments' may take longer and use more API quota."
            )
            
            # Parse the selection to get the number
            if comment_selection == "All comments":
                max_comments = None  # Special value for all comments
            else:
                max_comments = int(comment_selection.split()[0])
            
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            submit_button = st.form_submit_button("🔍 Analyze Video", use_container_width=True)
        with col3:
            reset_button = st.form_submit_button("🔄 Reset", use_container_width=True)
            
        if reset_button:
            reset_analysis()
            st.experimental_rerun()
        
        if submit_button and video_url:
            video_id = extract_video_id(video_url)
            if video_id:
                st.session_state.video_id = video_id
                
    
                
                # Show loading indicator
                with st.spinner('Fetching and analyzing YouTube comments...'):
                    try:
                        # First try to get video statistics
                        video_stats = extract_video_statistics(video_id)
                        if video_stats:
                            st.session_state.video_stats = video_stats
                        
                        # Fetch comments - either all or limited number
                        if max_comments is None:
                            # Use our new function to fetch all comments
                            comments = fetch_all_comments(video_id)
                        else:
                            # Use existing function with max_results
                            comments = fetch_all_comments(video_id, max_results=max_comments)
                        
                        if not comments:
                            st.warning("No comments found for this video. This could be because comments are disabled or the video doesn't have any comments yet.")
                            st.session_state.error_message = "No comments found for this video."
                        else:
                            # Show progress for sentiment analysis
                            sentiment_progress_bar = st.progress(0)
                            sentiment_status = st.empty()
                            sentiment_status.text("Analyzing sentiment of comments...")
                            
                            # Analyze sentiment for each comment
                            for i, comment in enumerate(comments):
                                comment['sentiment'] = analyze_sentiment(comment['text'])
                                # Update progress periodically
                                if i % 10 == 0 or i == len(comments) - 1:
                                    progress = min(1.0, (i + 1) / len(comments))
                                    sentiment_progress_bar.progress(progress)
                                    sentiment_status.text(f"Analyzing sentiment: {i+1}/{len(comments)} comments")
                            
                            # Clear sentiment analysis progress indicators
                            sentiment_status.empty()
                            
                            # Log a sample comment to debug
                            if comments:
                                logger.info(f"Sample comment structure: {comments[0].keys()}")
                            
                            # Store in session state
                            st.session_state.comments = comments
                            st.session_state.analysis_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Make sure likes is always a valid number
                            for comment in comments:
                                if 'likes' not in comment:
                                    comment['likes'] = 0
                                elif not isinstance(comment['likes'], (int, float)):
                                    try:
                                        comment['likes'] = int(comment['likes'])
                                    except (ValueError, TypeError):
                                        comment['likes'] = 0
                            
                            # Analyze comments for dashboard
                            total_comments = len(comments)
                            # Use safe get() method with default 0 for likes
                            total_likes = sum(comment.get('likes', 0) for comment in comments)
                            # Use safe get() method with default 0 for reply_count
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
                            st.session_state.dashboard_data = {
                                'basic_stats': {
                                    'total_comments': total_comments,
                                    'total_likes': total_likes,
                                    'total_replies': total_replies,
                                    'engagement_rate': round(total_likes / total_comments, 1) if total_comments else 0
                                },
                                'sentiment_data': [
                                    {'name': 'Positive', 'value': sentiment_counts['positive'], 'percentage': sentiment_percentages['positive']},
                                    {'name': 'Neutral', 'value': sentiment_counts['neutral'], 'percentage': sentiment_percentages['neutral']},
                                    {'name': 'Negative', 'value': sentiment_counts['negative'], 'percentage': sentiment_percentages['negative']}
                                ],
                                'topic_data': topic_data,
                                'content_ideas': content_ideas,
                                'keywords': keywords,
                                'top_comments': sorted(comments, key=lambda x: x.get('likes', 0), reverse=True)[:5],
                                'recent_comments': sorted(comments, key=lambda x: x.get('date', ''), reverse=True)[:5]
                            }
                            
                            # Success message
                            st.success(f"Successfully analyzed {total_comments} comments!")
                            
                    except Exception as e:
                        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
                        st.error(f"Error analyzing video: {str(e)}")
                        st.session_state.error_message = str(e)
            else:
                st.error("Invalid YouTube URL. Please enter a valid YouTube URL or video ID.")
                st.session_state.error_message = "Invalid YouTube URL format."
    
    # If there's an error, provide helpful information
    if st.session_state.error_message and not st.session_state.dashboard_data:
        st.error(st.session_state.error_message)
        
        if "API key not found" in st.session_state.error_message:
            st.info("""
            ### YouTube API Key Required
            
            To analyze real YouTube videos, you need to set up a YouTube Data API key:
            
            1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project
            3. Enable the YouTube Data API v3
            4. Create API credentials (API Key)
            5. Add the key to your environment or .env file:
            ```
            YOUTUBE_API_KEY=your_api_key_here
            ```
            
            Alternatively, check "Use sample data" to see how the dashboard works with mock data.
            """)
            
        elif "quota exceeded" in st.session_state.error_message.lower():
            st.info("""
            ### API Quota Exceeded
            
            Your YouTube API quota has been exceeded for today. Options:
            
            1. Try again tomorrow when your quota resets
            2. Create a new project in Google Cloud Console with a new API key
            3. Check "Use sample data" to see how the dashboard works with mock data
            """)

# Sidebar navigation
with st.sidebar:
    # Display video info and thumbnail if available
    if st.session_state.video_id and st.session_state.video_stats:
        stats = st.session_state.video_stats
        
        st.markdown("### Video Information")
        st.image(
            f"https://img.youtube.com/vi/{st.session_state.video_id}/0.jpg",
            use_column_width=True
        )
        
        st.markdown(f"**{stats['title']}**")
        st.markdown(f"Channel: {stats['channel']}")
        
        col1, col2 = st.columns(2)
        col1.metric("Views", f"{stats['views']:,}")
        col2.metric("Likes", f"{stats['likes']:,}")
        
        st.caption(f"Published: {stats['published_at']}")
        
        # Add an expander for description
        with st.expander("Video Description"):
            st.text(stats.get('description', 'No description available'))
    
    # Only show navigation if we have data
    if st.session_state.dashboard_data:
        st.markdown("---")
        st.title("Navigation")
        
        # Navigation options
        views = {
            "overview": "📊 Overview",
            "sentiment": "😊 Sentiment Analysis",
            "topics": "📝 Topic Analysis",
            "comments": "💬 Comments Explorer"
        }
        
        selected_view = st.radio("Select a view:", list(views.values()))
        
        # Map the selected view back to its key
        for key, value in views.items():
            if value == selected_view:
                st.session_state.current_view = key
        
        st.markdown("---")
        
        # Display metrics in sidebar
        stats = st.session_state.dashboard_data['basic_stats']
        sentiment_data = st.session_state.dashboard_data['sentiment_data']
        
        st.markdown("### Key Metrics")
        
        # Comments count with indicator
        st.metric("Total Comments Analyzed", stats['total_comments'])
        
        # Sentiment summary
        st.markdown("### Sentiment Summary")
        
        # Calculate total sentiments for percentage
        total = sum(item['value'] for item in sentiment_data)
        
        # Display each sentiment with emoji, progress bar and percentage
        for item in sentiment_data:
            sentiment_name = item['name'].lower()
            percentage = item.get('percentage', 0)
            emoji = get_sentiment_emoji(sentiment_name)
            
            st.markdown(f"{emoji} **{item['name']}**: {item['value']} comments ({percentage}%)")
            st.progress(percentage/100)
        
        # Analysis details
        if st.session_state.analysis_timestamp:
            st.markdown("---")
            st.caption(f"Analysis performed: {st.session_state.analysis_timestamp}")
            if os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true':
                st.caption("*Using sample data (mock mode)*")

# Content area - show appropriate view based on selection
if st.session_state.dashboard_data:
    with main_tab:
        if st.session_state.current_view == "overview":
            render_dashboard(st.session_state.dashboard_data)
        elif st.session_state.current_view == "sentiment":
            render_sentiment_view(st.session_state.dashboard_data, st.session_state.comments)
        elif st.session_state.current_view == "topics":
            render_topic_view(st.session_state.dashboard_data)
        elif st.session_state.current_view == "comments":
            render_comments_view(st.session_state.dashboard_data, st.session_state.comments)
else:
    with main_tab:
        # Welcome message when no data is loaded
        st.markdown("""
            <div class="welcome-container">
                <div class="welcome-icon">🎬</div>
                <h2>Welcome to YouTube Analytics Dashboard</h2>
                <p>Enter a YouTube video URL above to analyze comments and get valuable insights about your content.</p>
                <p style="margin-top: 20px; font-size: 0.9rem; color: #6b7280;">The dashboard analyzes YouTube comments to help you understand audience sentiment, identify popular topics, and discover content ideas.</p>
            </div>
        """, unsafe_allow_html=True)

# About tab content
with about_tab:
    st.markdown("""
    # About YouTube Analytics Dashboard
    
    This dashboard is designed to help content creators and marketers analyze YouTube comments to gain insights about audience sentiment, identify trending topics, and discover content ideas.
    
    ## Features
    
    - **Comment Analysis**: Fetch and analyze comments from any YouTube video
    - **Sentiment Analysis**: Classify comments as positive, neutral, or negative
    - **Topic Detection**: Identify common themes and topics in the comments
    - **Content Recommendations**: Generate content ideas based on audience feedback
    - **Comment Explorer**: Search, filter, and sort through comments
    
    ## How to Use
    
    1. Enter a YouTube video URL in the input field
    2. Click "Analyze Video" to fetch and analyze the comments
    3. Navigate through different views using the sidebar
    
    ## Technical Information
    
    This application is built with:
    
    - **Streamlit**: Web application framework
    - **YouTube Data API**: For fetching video comments
    - **TextBlob**: For sentiment analysis
    - **Plotly**: For interactive visualizations
    
    ## Privacy
    
    This application does not store any data. All analysis is performed in memory and is lost when you close the browser tab.
    """)

# Settings tab content
with settings_tab:
    st.markdown("## Application Settings")
    
    with st.expander("API Configuration"):
        st.markdown("""
        ### YouTube API Key
        
        The application requires a YouTube Data API key to fetch comments. You can configure it in multiple ways:
        
        1. **Environment Variable**: Set `YOUTUBE_API_KEY` in your system environment
        2. **.env File**: Create a `.env` file in the project root with:
        ```
        YOUTUBE_API_KEY=your_api_key_here
        ```
        3. **Streamlit Secrets**: For deployment, you can use Streamlit's secrets management
        
        If you don't have an API key, you can still use the application with sample data by checking the "Use sample data" option.
        """)
        
        # Display current API status
        api_key = os.getenv('YOUTUBE_API_KEY')
        if api_key and api_key != 'YOUR_API_KEY':
            st.success("✅ YouTube API key is configured")
        else:
            st.warning("⚠️ YouTube API key is not configured")
    
    with st.expander("Cache & Data Settings"):
        if st.button("Clear Session Data"):
            reset_analysis()
            st.success("Session data cleared successfully!")
            
        st.info("Note: YouTube API has a quota limit. Fetching all comments from popular videos may consume a significant portion of your daily quota.")
        
        st.markdown("""
        ### About YouTube API Quotas
        
        The YouTube Data API uses a quota system:
        
        - Each API project gets 10,000 units per day by default
        - Reading comments costs 1 unit per comment (in batches up to 100)
        - For videos with thousands of comments, you may hit quota limits
        
        If you need to analyze videos with many comments, consider:
        
        1. Limiting the number of comments analyzed
        2. Applying for increased quota from Google
        3. Spreading analysis across multiple days
        """)
    
    with st.expander("Display Settings"):
        theme = st.selectbox(
            "Color Theme",
            ["Default", "Purple & Indigo", "Blue & Teal", "Green & Emerald"],
            disabled=True
        )
        st.info("Custom themes will be available in future updates.")
        
        show_author_images = st.checkbox("Show author profile images", value=False, disabled=True)
        st.info("Additional display settings will be available in future updates.")