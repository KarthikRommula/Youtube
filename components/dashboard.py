#dashboard.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_dashboard(dashboard_data):
    """
    Render the main dashboard overview with key metrics and visualizations
    
    Args:
        dashboard_data (dict): Dashboard data containing metrics and visualizations
    """
    st.markdown("## 📊 Dashboard Overview")
    
    # Display key metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <div class="metric-card positive">
                <h3>💬 Total Comments</h3>
                <p class="metric-value">{}</p>
            </div>
            """.format(dashboard_data['basic_stats']['total_comments']),
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            """
            <div class="metric-card neutral">
                <h3>👍 Total Likes</h3>
                <p class="metric-value">{}</p>
            </div>
            """.format(dashboard_data['basic_stats']['total_likes']),
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            """
            <div class="metric-card accent">
                <h3>📈 Engagement Rate</h3>
                <p class="metric-value">{}</p>
            </div>
            """.format(dashboard_data['basic_stats']['engagement_rate']),
            unsafe_allow_html=True
        )
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Sentiment Overview")
        
        # Convert sentiment data to DataFrame
        sentiment_df = pd.DataFrame(dashboard_data['sentiment_data'])
        
        # Create pie chart
        fig = px.pie(
            sentiment_df, 
            values='value', 
            names='name',
            color='name',
            color_discrete_map={
                'Positive': '#4ade80',
                'Neutral': '#a3a3a3',
                'Negative': '#f87171'
            },
            hole=0.4
        )
        
        fig.update_layout(
            legend_title_text='Sentiment',
            legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Topic Distribution")
        
        # Convert topic data to DataFrame
        topic_df = pd.DataFrame(dashboard_data['topic_data'])
        
        # Create bar chart
        fig = px.bar(
            topic_df,
            x='name',
            y='value',
            color='name',
            color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={'name': 'Topic', 'value': 'Count'}
        )
        
        fig.update_layout(
            xaxis_title='',
            yaxis_title='Count',
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Content Recommendations
    st.markdown("### 🌟 Top Content Recommendations")
    
    if dashboard_data['content_ideas']:
        # Display content ideas in a grid of cards
        idea_cols = st.columns(3)
        
        for i, idea in enumerate(dashboard_data['content_ideas'][:3]):
            with idea_cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="idea-card">
                        <div class="idea-header">
                            <span class="idea-star">⭐</span>
                            <span class="idea-title">Trending Idea #{i+1}</span>
                        </div>
                        <p class="idea-text">{idea['idea']}</p>
                        <div class="idea-engagement">
                            <span>👍 {idea['likes']} engagement points</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No content recommendations available. This could be due to insufficient comment data.")
    
    # Recent Comments Preview
    st.markdown("### 💬 Recent Comments")
    
    if dashboard_data['recent_comments']:
        for comment in dashboard_data['recent_comments'][:3]:
            st.markdown(
                f"""
                <div class="comment-card">
                    <div class="comment-header">
                        <span class="comment-author">{comment['author_name']}</span>
                        <span class="comment-date">{comment['date']}</span>
                    </div>
                    <p class="comment-text">{comment['text']}</p>
                    <div class="comment-footer">
                        <span>👍 {comment['likes']} likes</span>
                        {f"<span>💬 {comment['reply_count']} replies</span>" if comment['reply_count'] > 0 else ""}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No comments available to display.")