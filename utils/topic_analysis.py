#topic_analysis.py
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pandas as pd
import logging
from typing import List, Dict, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Try to download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    logger.warning(f"NLTK download failed: {str(e)}")

# Define topic keywords
TOPIC_KEYWORDS = {
    'tutorial': ['how to', 'tutorial', 'guide', 'learn', 'step by step', 'techniques'],
    'review': ['review', 'opinion', 'thoughts on', 'what I think', 'assessment'],
    'question': ['question', 'wondering', 'can you', 'how do you', '?'],
    'suggestion': ['suggestion', 'recommend', 'should make', 'would like to see', 'please make'],
    'technical': ['technical', 'software', 'hardware', 'settings', 'configuration', 'setup']
}

def extract_topics(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract common topics from comments using predefined categories
    
    Args:
        comments (list): List of comment dictionaries
    
    Returns:
        list: List of topic dictionaries with name and value
    """
    if not comments:
        return [{'name': 'No Data', 'value': 1}]
        
    topics = {
        'tutorial': 0,
        'review': 0,
        'question': 0,
        'suggestion': 0,
        'technical': 0
    }
    
    for comment in comments:
        # Extract text and handle case where text might be missing
        text = comment.get('text', '')
        if not isinstance(text, str):
            continue
            
        text = text.lower()
        
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                topics[topic] += 1
    
    # Check if all values are zero
    all_zeros = all(value == 0 for value in topics.values())
    
    # If all values are zero, set at least one topic to 1 to avoid RangeError
    if all_zeros and comments:
        topics['other'] = 1
    
    # Convert to list format for visualization
    return [{'name': key, 'value': value} for key, value in topics.items()]

def generate_content_ideas(comments: List[Dict[str, Any]], max_ideas: int = 10) -> List[Dict[str, Any]]:
    """
    Generate content ideas based on user comments
    
    Args:
        comments (list): List of comment dictionaries
        max_ideas (int): Maximum number of ideas to generate
    
    Returns:
        list: List of content idea dictionaries
    """
    # Check for empty comments
    if not comments:
        return [{'idea': 'No comments available for content ideas', 'likes': 0, 'source': ''}]
        
    # Debug the structure of a comment to ensure 'likes' is present
    if comments and len(comments) > 0:
        logger.info(f"Sample comment structure in generate_content_ideas: {list(comments[0].keys())}")
    
    request_patterns = [
        'can you make',
        'would like to see',
        'please make',
        'should do',
        'next video',
        'tutorial on',
        'comparison',
        'review of'
    ]
    
    content_ideas = []
    
    for comment in comments:
        # Ensure 'text' is present and a string
        if 'text' not in comment or not isinstance(comment.get('text', ''), str):
            continue
            
        text = comment.get('text', '').lower()
        
        # Get likes with a default value of 0
        likes = comment.get('likes', 0)
        
        # Ensure likes is an integer
        if not isinstance(likes, (int, float)):
            try:
                likes = int(likes)
            except (ValueError, TypeError):
                likes = 0
        
        for pattern in request_patterns:
            if pattern in text:
                # Find where the pattern occurs
                index = text.find(pattern) + len(pattern)
                
                # Extract the suggestion text after the pattern
                suggestion = text[index:].strip()
                
                # Clean up the suggestion by removing everything after the first punctuation
                suggestion = re.sub(r'[.!?].*$', '', suggestion).strip()
                
                # Only include suggestions that are meaningful
                if len(suggestion) > 3 and len(suggestion.split()) >= 2:
                    # Capitalize the first letter
                    suggestion = suggestion[0].upper() + suggestion[1:]
                    
                    # Add to content ideas with engagement metrics
                    content_ideas.append({
                        'idea': suggestion,
                        'likes': likes,
                        'source': comment.get('id', '')
                    })
    
    try:
        # Check if content_ideas is empty
        if not content_ideas:
            logger.warning("No content ideas generated from comments")
            # Return a default idea to prevent empty visualizations
            return [{'idea': 'No content ideas found in comments', 'likes': 0, 'source': ''}]
            
        # Convert to DataFrame for processing
        ideas_df = pd.DataFrame(content_ideas)
        
        # Debug the DataFrame structure
        logger.info(f"Content ideas DataFrame columns: {ideas_df.columns.tolist()}")
        
        # Check if 'likes' column exists
        if 'likes' not in ideas_df.columns:
            logger.warning("'likes' column not found in content ideas DataFrame")
            # Add a default 'likes' column if missing
            ideas_df['likes'] = 0
        
        # Sort, remove duplicates, and limit to max_ideas
        result = (
            ideas_df
            .sort_values('likes', ascending=False)
            .drop_duplicates(subset=['idea'])
            .head(max_ideas)
            .to_dict('records')
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing content ideas: {str(e)}", exc_info=True)
        # Return a default idea to prevent empty visualizations
        return [{'idea': 'Error processing content ideas', 'likes': 0, 'source': ''}]

def extract_keywords(comments: List[Dict[str, Any]], top_n: int = 10) -> List[Tuple[str, int]]:
    """
    Extract most common keywords from comments
    
    Args:
        comments (list): List of comment dictionaries
        top_n (int): Number of top keywords to return
    
    Returns:
        list: List of (keyword, count) tuples
    """
    # Check for empty comments
    if not comments:
        return [('nodata', 1)]
        
    try:
        # Get English stopwords
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            # NLTK data might not be downloaded
            logger.warning("NLTK stopwords not found. Using minimal stopword list.")
            stop_words = {"the", "and", "is", "in", "it", "to", "that", "of", "for", "with", "on", "at", "this", "be", "are", "was"}
        
        # Add custom stopwords specific to YouTube comments
        custom_stopwords = {
            'video', 'youtube', 'channel', 'subscribe', 'like', 'comment',
            'watch', 'watching', 'watched', 'thanks', 'thank', 'please',
            'great', 'good', 'best', 'love', 'really', 'just', 'make',
            'made', 'making', 'now', 'get', 'one', 'would', 'could'
        }
        
        stop_words.update(custom_stopwords)
        
        # Combine all comment texts
        all_text = ' '.join([comment.get('text', '') for comment in comments if isinstance(comment.get('text', ''), str)])
        
        if not all_text.strip():
            return [('nodata', 1)]
            
        try:
            # Tokenize and filter words
            tokens = word_tokenize(all_text.lower())
            
            # Remove stopwords, punctuation, and short words
            filtered_tokens = [
                word for word in tokens 
                if word.isalpha() and word not in stop_words and len(word) > 2
            ]
            
            # Count word frequencies
            word_freq = Counter(filtered_tokens)
            
            # Return top N keywords or a default if none found
            results = word_freq.most_common(top_n)
            
            # If no keywords were found, return a default to prevent visualization errors
            if not results and comments:
                return [('nodata', 1)]
                
            return results
        except Exception as e:
            logger.error(f"Error in tokenization: {str(e)}")
            return [('error', 1)]
            
    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}")
        return [('error', 1)]  # Return a default to prevent visualization errors