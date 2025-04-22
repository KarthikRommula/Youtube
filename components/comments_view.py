#comments_view.py
import streamlit as st
import pandas as pd
import math
from utils.sentiment import get_sentiment_emoji, get_sentiment_color

def render_comments_view(dashboard_data, comments):
    """
    Render the comments analysis view showing top comments and statistics
    
    Args:
        dashboard_data (dict): Dashboard data containing metrics and visualizations
        comments (list): List of comment dictionaries
    """
    st.markdown("## 💬 Comments Analysis")
    
    # Comments statistics in a more visually appealing card layout
    st.markdown("""
        <style>
        .stat-card {
            padding: 1.2rem;
            border-radius: 8px;
            background-color: #f8f9fa;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
            height: 100%;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 0.3rem;
        }
        .stat-label {
            font-size: 0.9rem;
            color: #555;
        }
        .comment-card {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 6px;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid;
        }
        .comment-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .comment-author {
            font-weight: bold;
            font-size: 1rem;
        }
        .comment-details {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .comment-date {
            color: #777;
            font-size: 0.8rem;
        }
        .sentiment-badge {
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .comment-text {
            margin: 0.6rem 0;
            line-height: 1.4;
        }
        .comment-footer {
            display: flex;
            gap: 12px;
            font-size: 0.9rem;
            color: #555;
        }
        .filter-section {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        .pagination-nav {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin: 20px 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### Comment Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Enhanced statistics display
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{dashboard_data['basic_stats']['total_comments']}</div>
                <div class="stat-label">Total Comments</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{dashboard_data['basic_stats']['total_likes']}</div>
                <div class="stat-label">Total Likes</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{dashboard_data['basic_stats']['total_replies']}</div>
                <div class="stat-label">Total Replies</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_likes = round(dashboard_data['basic_stats']['total_likes'] / 
                       dashboard_data['basic_stats']['total_comments'], 1) if dashboard_data['basic_stats']['total_comments'] else 0
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{avg_likes}</div>
                <div class="stat-label">Avg. Likes per Comment</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Improved filter section with better visual organization
    st.markdown("### Filter & Search")
    
    # Wrap filters in a container with background
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        sentiment_filter = st.multiselect(
            "Filter by sentiment",
            ["Positive", "Neutral", "Negative"],
            default=["Positive", "Neutral", "Negative"]
        )

        # Add a search box to filter comments
        search_term = st.text_input("Search comments", "", placeholder="Type to search...")
    
    with filter_col2:
        sort_option = st.selectbox(
            "Sort comments by",
            ["Most Likes", "Most Recent", "Most Replies"]
        )
        
        # Comments per page selector
        comments_per_page = st.select_slider(
            "Comments per page",
            options=[10, 20, 50, 100],
            value=20
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Convert filter options to lowercase for matching
    sentiment_filter = [s.lower() for s in sentiment_filter]
    
    # Filter comments based on selected sentiments
    filtered_comments = [c for c in comments if c['sentiment'] in sentiment_filter]
    
    # Apply search filter if provided
    if search_term:
        filtered_comments = [c for c in filtered_comments if search_term.lower() in c['text'].lower()]
        st.markdown(f"Found **{len(filtered_comments)}** comments containing '**{search_term}**'")
    
    # Sort comments based on selected option
    if sort_option == "Most Likes":
        filtered_comments = sorted(filtered_comments, key=lambda x: x.get('likes', 0), reverse=True)
    elif sort_option == "Most Recent":
        filtered_comments = sorted(filtered_comments, key=lambda x: x.get('date', ''), reverse=True)
    elif sort_option == "Most Replies":
        filtered_comments = sorted(filtered_comments, key=lambda x: x.get('reply_count', 0), reverse=True)
    
    # Show number of comments found
    total_filtered = len(filtered_comments)
    st.markdown(f"### Showing {total_filtered} comments")
    
    # Improved pagination controls
    total_pages = math.ceil(total_filtered / comments_per_page)
    
    # Initialize session state for pagination if not already done
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 1
    
    # If we have more than one page of comments, show pagination controls
    if total_pages > 1:
        # Simple page buttons
        cols = st.columns([3, 1, 1, 1, 3])
        
        # Previous button
        if cols[1].button("◀ Prev", use_container_width=True, disabled=st.session_state.page_number <= 1):
            st.session_state.page_number -= 1
            st.rerun()
        
        # Page indicator
        cols[2].markdown(f"<div style='text-align:center; padding:10px 0; font-weight:bold;'>{st.session_state.page_number}/{total_pages}</div>", unsafe_allow_html=True)
        
        # Next button
        if cols[3].button("Next ▶", use_container_width=True, disabled=st.session_state.page_number >= total_pages):
            st.session_state.page_number += 1
            st.rerun()
        
        # Calculate start and end indices for current page
        start_idx = (st.session_state.page_number - 1) * comments_per_page
        end_idx = min(start_idx + comments_per_page, total_filtered)
        
        # Get comments for current page
        page_comments = filtered_comments[start_idx:end_idx]
        
        st.markdown(f"<div style='text-align: center; color: #666; margin: 0.5rem 0 1.5rem 0;'>Showing comments {start_idx+1}-{end_idx} of {total_filtered}</div>", unsafe_allow_html=True)
    else:
        # If only one page, show all comments
        page_comments = filtered_comments
        st.session_state.page_number = 1
    
    # Display comments for current page with enhanced styling and fixed HTML structure
    if page_comments:
        for comment in page_comments:
            color = get_sentiment_color(comment['sentiment'])
            emoji = get_sentiment_emoji(comment['sentiment'])
            
            # Format the comment date and name for better readability
            author_name = comment['author_name']
            comment_date = comment['date']
            
            # Create a unified comment component with fixed HTML structure
            comment_html = f"""
                <div class="comment-card" style="border-left-color: {color};">
                    <div class="comment-header">
                        <span class="comment-author">@{author_name}</span>
                        <div class="comment-details">
                            <span class="comment-date">{comment_date}</span>
                            <span class="sentiment-badge" style="background-color: {color}20; color: {color};">
                                {emoji} {comment['sentiment'].capitalize()}
                            </span>
                        </div>
                    </div>
                    <p class="comment-text">{comment['text']}</p>
                    <div class="comment-footer">
                        <span>👍 {comment['likes']} likes</span>
                        {f"<span>💬 {comment['reply_count']} replies</span>" if comment.get('reply_count', 0) > 0 else ""}
                    </div>
                </div>
            """
                
            # Render the comment
            st.markdown(comment_html, unsafe_allow_html=True)
    else:
        st.info("No comments found matching your criteria.")