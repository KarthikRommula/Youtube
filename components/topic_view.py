#topic_view.py
import streamlit as st
import plotly.express as px
import pandas as pd
from utils.topic_analysis import extract_keywords

def render_topic_view(dashboard_data):
    """
    Render the topic analysis view with topics, content ideas, and keyword analysis
    
    Args:
        dashboard_data (dict): Dashboard data containing metrics and visualizations
    """
    st.markdown("""
    <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:20px;'>
        <h2 style='color:#3366cc; margin-bottom:0px'>📝 Topic Analysis</h2>
        <p style='color:#666; font-size:14px;'>Discover what your audience is discussing and get content ideas based on your comment analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 Topic Distribution", "💡 Content Recommendations", "📆 Content Planning"])
    
    with tab1:
        # Topic Distribution
        st.markdown("<h3 style='color:#3366cc'>Topic Distribution</h3>", unsafe_allow_html=True)
        
        # Add a brief explanation
        st.markdown("<p style='color:#666; font-size:14px; margin-bottom:20px;'>This chart shows the distribution of topics mentioned in your audience's comments.</p>", 
                    unsafe_allow_html=True)
        
        # Convert topic data to DataFrame
        topic_df = pd.DataFrame(dashboard_data['topic_data'])
        
        # Add percentage column
        total_mentions = topic_df['value'].sum()
        if total_mentions > 0:
            topic_df['percentage'] = (topic_df['value'] / total_mentions * 100).round(1)
            topic_df['label'] = topic_df.apply(lambda x: f"{x['name']} ({x['percentage']}%)", axis=1)
        else:
            topic_df['percentage'] = 0
            topic_df['label'] = topic_df['name']
        
        # Sort by value descending for better visualization
        topic_df = topic_df.sort_values('value', ascending=False)
        
        # Create horizontal bar chart with improved styling
        fig = px.bar(
            topic_df,
            y='name',
            x='value',
            color='name',
            color_discrete_sequence=px.colors.qualitative.Bold,
            labels={'name': 'Topic', 'value': 'Mentions'},
            orientation='h',
            text='percentage',
            hover_data={'percentage': ':.1f%'}
        )
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        
        fig.update_layout(
            xaxis_title='Number of Mentions',
            yaxis_title='',
            showlegend=False,
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='closest',
            hoverlabel=dict(bgcolor="white", font_size=14),
            xaxis=dict(showgrid=True, gridcolor='#eee')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display metrics in a row
        metrics = st.columns(len(topic_df))
        for i, (_, row) in enumerate(topic_df.iterrows()):
            with metrics[i]:
                st.metric(
                    label=row['name'],
                    value=row['value'],
                    delta=f"{row['percentage']:.1f}%" if 'percentage' in row else None
                )
        
        # Topic explanation with improved UI
        with st.expander("📚 What these topics mean"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div style='background-color:#e6f2ff; padding:10px; border-radius:5px; margin-bottom:10px;'>
                    <h4 style='color:#3366cc; margin-top:0;'>Tutorial</h4>
                    <p>Comments asking for how-to guides, step-by-step instructions, or learning resources</p>
                </div>
                
                <div style='background-color:#ffe6e6; padding:10px; border-radius:5px; margin-bottom:10px;'>
                    <h4 style='color:#cc3366; margin-top:0;'>Review</h4>
                    <p>Comments related to opinions, assessments, or thoughts about products or content</p>
                </div>
                
                <div style='background-color:#e6ffe6; padding:10px; border-radius:5px; margin-bottom:10px;'>
                    <h4 style='color:#33cc66; margin-top:0;'>Question</h4>
                    <p>General questions or inquiries from viewers</p>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown("""
                <div style='background-color:#fff2e6; padding:10px; border-radius:5px; margin-bottom:10px;'>
                    <h4 style='color:#ff9933; margin-top:0;'>Suggestion</h4>
                    <p>Recommendations or ideas provided by viewers</p>
                </div>
                
                <div style='background-color:#e6e6ff; padding:10px; border-radius:5px; margin-bottom:10px;'>
                    <h4 style='color:#6633cc; margin-top:0;'>Technical</h4>
                    <p>Comments about technical aspects, hardware, software, settings, or configurations</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        # Content Ideas Section with improved UI
        st.markdown("<h3 style='color:#3366cc'>💡 Content Recommendations</h3>", unsafe_allow_html=True)
        
        if dashboard_data['content_ideas']:
            # Add sorting and filtering options
            sort_col, filter_col = st.columns([1, 2])
            
            with sort_col:
                sort_option = st.selectbox(
                    "Sort by",
                    ["Engagement (High to Low)", "Engagement (Low to High)"]
                )
            
            with filter_col:
                # Calculate the max engagement value with a fallback to avoid the RangeError
                max_engagement = 1  # Default minimum value
                if dashboard_data['content_ideas']:
                    engagement_values = [idea['likes'] for idea in dashboard_data['content_ideas']]
                    if engagement_values:
                        max_value = max(engagement_values)
                        # Ensure max is at least 1 more than min to avoid slider errors
                        max_engagement = max(max_value, 1)
                
                min_engagement = st.slider(
                    "Minimum engagement score",
                    min_value=0,
                    max_value=max_engagement,
                    value=0
                )
            
            # Process the ideas based on sorting and filtering
            ideas_df = pd.DataFrame(dashboard_data['content_ideas'])
            
            # Apply filtering
            filtered_ideas = ideas_df[ideas_df['likes'] >= min_engagement]
            
            # Apply sorting
            if sort_option == "Engagement (High to Low)":
                filtered_ideas = filtered_ideas.sort_values('likes', ascending=False)
            else:
                filtered_ideas = filtered_ideas.sort_values('likes', ascending=True)
            
            # Display ideas in card format with improved styling
            if not filtered_ideas.empty:
                st.markdown("""
                <style>
                .idea-card {
                    background-color: white;
                    border-radius: 10px;
                    padding: 15px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    margin-bottom: 15px;
                    transition: transform 0.3s;
                    height: 100%;
                }
                .idea-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 6px 8px rgba(0,0,0,0.15);
                }
                .idea-header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .idea-star {
                    font-size: 20px;
                    margin-right: 10px;
                    color: #FFD700;
                }
                .idea-title {
                    font-weight: bold;
                    color: #3366cc;
                }
                .idea-text {
                    margin-bottom: 15px;
                    font-size: 16px;
                }
                .idea-engagement {
                    background-color: #f8f9fa;
                    padding: 5px 10px;
                    border-radius: 20px;
                    display: inline-block;
                    font-size: 14px;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Create columns for each idea using st.columns
                for i in range(0, len(filtered_ideas), 2):
                    cols = st.columns(2)
                    
                    # First idea in the row
                    with cols[0]:
                        if i < len(filtered_ideas):
                            idea = filtered_ideas.iloc[i]
                            st.markdown(
                                f"""
                                <div class="idea-card">
                                    <div class="idea-header">
                                        <span class="idea-star">⭐</span>
                                        <span class="idea-title">Content Idea #{i+1}</span>
                                    </div>
                                    <p class="idea-text">{idea['idea']}</p>
                                    <div class="idea-engagement">
                                        <span>👍 {idea['likes']} engagement points</span>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    
                    # Second idea in the row
                    with cols[1]:
                        if i+1 < len(filtered_ideas):
                            idea = filtered_ideas.iloc[i+1]
                            st.markdown(
                                f"""
                                <div class="idea-card">
                                    <div class="idea-header">
                                        <span class="idea-star">⭐</span>
                                        <span class="idea-title">Content Idea #{i+2}</span>
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
                st.warning("No content ideas match your current filters.")
        else:
            st.info("No content recommendations available. This could be due to insufficient comment data.")
            
            # Show placeholder with example
            st.markdown("""
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 10px; text-align: center;">
                <img src="https://via.placeholder.com/100x100?text=💡" style="width: 100px; height: 100px; margin-bottom: 15px;">
                <h3>How recommendations work</h3>
                <p>When you have more comment data, this section will show content ideas based on what your audience is asking for.</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        # Content Planning Assistant with improved UI
        st.markdown("<h3 style='color:#3366cc'>📆 Content Planning</h3>", unsafe_allow_html=True)
        
        # Create columns for planning section
        plan_col1, plan_col2 = st.columns([3, 2])
        
        with plan_col1:
            st.markdown("""
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
                <h4 style="color: #3366cc;">How to Use Topic Analysis for Content Planning</h4>
                <p>Based on the topics your audience is discussing, here are some strategies for planning your content:</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Strategy cards with icons
            strategies = [
                {
                    "icon": "❓", 
                    "title": "Address Common Questions", 
                    "desc": "Look for patterns in the questions being asked and create content that provides clear answers."
                },
                {
                    "icon": "🔄", 
                    "title": "Follow Up on Reviews", 
                    "desc": "If viewers are reviewing certain aspects of your content, consider creating follow-up videos that expand on those topics."
                },
                {
                    "icon": "💭", 
                    "title": "Implement Suggestions", 
                    "desc": "Pay attention to what your audience is asking for - implementing their suggestions can boost engagement."
                },
                {
                    "icon": "📚", 
                    "title": "Create Tutorials", 
                    "desc": "If technical questions dominate your comments, creating tutorial content can be particularly valuable."
                },
                {
                    "icon": "📺", 
                    "title": "Series Planning", 
                    "desc": "Group related topics into a content series to maintain audience interest over multiple videos."
                }
            ]
            
            for strategy in strategies:
                st.markdown(f"""
                <div style="display: flex; margin-bottom: 15px; background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <div style="font-size: 30px; margin-right: 15px;">{strategy['icon']}</div>
                    <div>
                        <h5 style="margin-top: 0; color: #333;">{strategy['title']}</h5>
                        <p style="margin-bottom: 0; color: #666;">{strategy['desc']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.info("Remember that balancing what your audience wants with your own content goals is key to sustainable channel growth.")
            
        with plan_col2:
            st.markdown("<h4 style='color:#3366cc'>Content Calendar Suggestion</h4>", unsafe_allow_html=True)
            
            if dashboard_data['content_ideas'] and len(dashboard_data['content_ideas']) >= 4:
                # Create a styled calendar view
                calendar_data = [
                    {"week": "Week 1", "type": "Tutorial", "idea": dashboard_data['content_ideas'][0]['idea']},
                    {"week": "Week 2", "type": "Review", "idea": dashboard_data['content_ideas'][1]['idea']},
                    {"week": "Week 3", "type": "Q&A", "idea": "Address top questions"},
                    {"week": "Week 4", "type": "Deep Dive", "idea": dashboard_data['content_ideas'][2]['idea']}
                ]
                
                for week_data in calendar_data:
                    st.markdown(f"""
                    <div style="background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #3366cc;">
                        <div style="color: #3366cc; font-weight: bold;">{week_data['week']}</div>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                            <span style="background-color: #e6f2ff; padding: 3px 8px; border-radius: 15px; font-size: 12px;">{week_data['type']}</span>
                        </div>
                        <div style="margin-top: 8px;">{week_data['idea']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Add download calendar button (placeholder functionality)
                st.download_button(
                    label="📥 Export Content Calendar",
                    data="Content calendar data",
                    file_name="content_calendar.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Not enough content ideas to generate a calendar. At least 4 ideas are needed.")
                
    # Add a keyword cloud section at the bottom (new feature) 
    st.markdown("---")
    st.markdown("<h3 style='color:#3366cc'>🔤 Keyword Analysis</h3>", unsafe_allow_html=True)
    
    # Check if keywords are available
    if 'keywords' in dashboard_data and dashboard_data['keywords']:
        # Create columns for keyword visualization
        kw_col1, kw_col2 = st.columns([3, 2])
        
        with kw_col1:
            # Convert keywords to DataFrame
            keywords_df = pd.DataFrame(dashboard_data['keywords'], columns=['word', 'count'])
            
            # Create a bar chart for top keywords
            fig = px.bar(
                keywords_df,
                y='word',
                x='count',
                orientation='h',
                color='count',
                color_continuous_scale='Viridis',
                labels={'word': 'Keyword', 'count': 'Frequency'}
            )
            
            fig.update_layout(
                title="Top Keywords in Comments",
                xaxis_title="Frequency",
                yaxis_title="",
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                coloraxis_showscale=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with kw_col2:
            st.markdown("<h4 style='color:#3366cc'>Keyword Insights</h4>", unsafe_allow_html=True)
            st.markdown("""
            These keywords represent the most frequently mentioned terms in your audience's comments.
            
            **How to use this data:**
            
            * Include these keywords in your video titles and descriptions
            * Create content specifically addressing these topics
            * Use these terms in your scripts to better match viewer interests
            * Consider these terms for SEO optimization
            """)
            
            # Show top 3 keywords as highlighted tags
            st.markdown("<h5>Top Keywords:</h5>", unsafe_allow_html=True)
            
            tag_html = ""
            for _, kw in keywords_df.head(5).iterrows():
                tag_html += f"""<span style="background-color: #3366cc; color: white; padding: 5px 10px; 
                border-radius: 15px; margin-right: 5px; display: inline-block; margin-bottom: 5px;">
                {kw['word']} ({kw['count']})</span>"""
            
            st.markdown(f"""<div style="margin-top: 10px;">{tag_html}</div>""", unsafe_allow_html=True)
    else:
        st.info("Keyword analysis will appear here when more comment data is available.")