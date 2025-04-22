#sentiment_view.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.sentiment import get_sentiment_emoji, get_sentiment_color

def render_sentiment_view(dashboard_data, comments):
    """
    Render the sentiment analysis view with detailed sentiment charts and top comments by sentiment
    
    Args:
        dashboard_data (dict): Dashboard data containing metrics and visualizations
        comments (list): List of comment dictionaries
    """
    st.markdown("## 😊 Sentiment Analysis")
    
    # Sentiment Stats
    sentiment_data = dashboard_data['sentiment_data']
    total_comments = dashboard_data['basic_stats']['total_comments']
    
    # Display sentiment metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        positive_count = sentiment_data[0]['value']
        positive_percent = int((positive_count / total_comments * 100) if total_comments else 0)
        st.markdown(
            f"""
            <div class="metric-card positive">
                <h3>{get_sentiment_emoji('positive')} Positive</h3>
                <p class="metric-value">{positive_count}</p>
                <p class="metric-percent">{positive_percent}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        neutral_count = sentiment_data[1]['value']
        neutral_percent = int((neutral_count / total_comments * 100) if total_comments else 0)
        st.markdown(
            f"""
            <div class="metric-card neutral">
                <h3>{get_sentiment_emoji('neutral')} Neutral</h3>
                <p class="metric-value">{neutral_count}</p>
                <p class="metric-percent">{neutral_percent}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        negative_count = sentiment_data[2]['value']
        negative_percent = int((negative_count / total_comments * 100) if total_comments else 0)
        st.markdown(
            f"""
            <div class="metric-card negative">
                <h3>{get_sentiment_emoji('negative')} Negative</h3>
                <p class="metric-value">{negative_count}</p>
                <p class="metric-percent">{negative_percent}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Sentiment Distribution Chart
    st.markdown("### Sentiment Distribution")
    
    # Convert sentiment data to DataFrame
    sentiment_df = pd.DataFrame(dashboard_data['sentiment_data'])
    
    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=sentiment_df['name'],
        values=sentiment_df['value'],
        hole=.4,
        marker_colors=['#4ade80', '#a3a3a3', '#f87171']
    )])
    
    fig.update_layout(
        annotations=[dict(text='Sentiment', x=0.5, y=0.5, font_size=20, showarrow=False)],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Top Comments by Sentiment
    st.markdown("### Top Comments by Sentiment")
    
    # Create tabs for different sentiment categories
    tab1, tab2, tab3 = st.tabs(["Positive Comments", "Neutral Comments", "Negative Comments"])
    
    with tab1:
        positive_comments = [c for c in comments if c['sentiment'] == 'positive']
        if positive_comments:
            display_comments_by_sentiment(positive_comments[:5], 'positive')
        else:
            st.info("No positive comments found.")
    
    with tab2:
        neutral_comments = [c for c in comments if c['sentiment'] == 'neutral']
        if neutral_comments:
            display_comments_by_sentiment(neutral_comments[:5], 'neutral')
        else:
            st.info("No neutral comments found.")
    
    with tab3:
        negative_comments = [c for c in comments if c['sentiment'] == 'negative']
        if negative_comments:
            display_comments_by_sentiment(negative_comments[:5], 'negative')
        else:
            st.info("No negative comments found.")
    
    # Sentiment Analysis Explanation
    with st.expander("How the sentiment analysis works"):
        st.markdown("""
        ### Sentiment Analysis Methodology
        
        This dashboard uses a combination of techniques to analyze the sentiment of YouTube comments:
        
        1. **TextBlob** - A natural language processing library to calculate the polarity of the text
        2. **Keyword Matching** - Detecting positive and negative words
        3. **Preprocessing** - Cleaning the text by removing HTML tags, URLs, and special characters
        
        The sentiment score is calculated based on:
        - **Positive**: Comments with a positive tone expressing satisfaction, appreciation, or enthusiasm
        - **Neutral**: Comments that are neither clearly positive nor negative or contain mixed sentiments
        - **Negative**: Comments expressing dissatisfaction, criticism, or negativity
        
        This analysis helps content creators understand audience reactions and identify potential areas for improvement.
        """)

def display_comments_by_sentiment(comments, sentiment_type):
    """
    Display comments of a specific sentiment type
    
    Args:
        comments (list): List of comment dictionaries
        sentiment_type (str): Sentiment type ('positive', 'neutral', or 'negative')
    """
    # Sort comments by likes
    sorted_comments = sorted(comments, key=lambda x: x.get('likes', 0), reverse=True)
    
    # Display each comment
    for comment in sorted_comments:
        color = get_sentiment_color(sentiment_type)
        emoji = get_sentiment_emoji(sentiment_type)
        
        # Create HTML for the comment card
        comment_html = f"""
        <div class="comment-card" style="border-left: 4px solid {color};">
            <div class="comment-header">
                <span class="comment-author">{comment['author_name']}</span>
                <span class="sentiment-badge" style="background-color: {color}20; color: {color};">
                    {emoji} {sentiment_type.capitalize()}
                </span>
            </div>
            <p class="comment-text">{comment['text']}</p>
            <div class="comment-footer">
                <span>👍 {comment['likes']} likes</span>
                {f"<span>💬 {comment['reply_count']} replies</span>" if comment.get('reply_count', 0) > 0 else ""}
            </div>
        </div>
        """
        
        # Render the HTML safely    
        st.markdown(comment_html, unsafe_allow_html=True)