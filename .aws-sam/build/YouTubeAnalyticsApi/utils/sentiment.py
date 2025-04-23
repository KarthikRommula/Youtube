#sentiment.py
"""
Simplified Sentiment Analysis Module

This module implements a simplified version of sentiment analysis
using TextBlob as a fallback when transformers aren't available.
"""

import re
import string
import logging
from textblob import TextBlob
import nltk
from typing import Dict, Any, List
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
except Exception as e:
    logger.warning(f"Error downloading NLTK data: {e}")

# Define emoji maps for sentiment representation
SENTIMENT_EMOJIS = {
    'positive': '😊',
    'negative': '😞',
    'neutral': '😐'
}

SENTIMENT_COLORS = {
    'positive': '#4ade80',  # Green
    'negative': '#f87171',  # Red
    'neutral': '#a3a3a3'    # Gray
}

# Sentiment analysis function with caching for better performance
@lru_cache(maxsize=1024)
def analyze_sentiment(text: str) -> str:
    """
    Analyze sentiment of text using TextBlob
    
    Args:
        text: Text to analyze
        
    Returns:
        String with sentiment label: 'positive', 'neutral', or 'negative'
    """
    if not text or not isinstance(text, str):
        return "neutral"
    
    # Clean the text
    text = clean_text(text)
    
    try:
        # Use TextBlob for sentiment analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classify based on polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        return "neutral"

def clean_text(text: str) -> str:
    """
    Clean text for sentiment analysis
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r"https?:\/\/\S+", "", text)
    
    # Remove hashtags and mentions (preserve the text without the # or @)
    text = re.sub(r"#(\S+)", r"\1", text)
    text = re.sub(r"@(\S+)", r"\1", text)
    
    # Remove punctuation (except for emojis)
    for p in string.punctuation:
        text = text.replace(p, " ")
    
    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)
    
    # Trim whitespaces at the start and end of the text
    text = text.strip()
    
    return text

def get_sentiment_emoji(sentiment: str) -> str:
    """
    Return an emoji representing the sentiment
    
    Args:
        sentiment: Sentiment classification
    
    Returns:
        str: Emoji representing the sentiment
    """
    return SENTIMENT_EMOJIS.get(sentiment.lower(), SENTIMENT_EMOJIS['neutral'])

def get_sentiment_color(sentiment: str) -> str:
    """
    Return a color representing the sentiment
    
    Args:
        sentiment: Sentiment classification
    
    Returns:
        str: Hex color code
    """
    return SENTIMENT_COLORS.get(sentiment.lower(), SENTIMENT_COLORS['neutral'])

def batch_analyze_sentiments(texts: List[str]) -> List[str]:
    """
    Analyze sentiment for a batch of texts
    
    Args:
        texts: List of texts to analyze
        
    Returns:
        List of sentiment labels
    """
    return [analyze_sentiment(text) for text in texts]