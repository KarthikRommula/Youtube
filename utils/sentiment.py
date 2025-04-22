"""
Enhanced Sentiment Analysis Module

This module replaces the previous sentiment analysis implementation with:
1. A streamlined transformer-based model from Hugging Face
2. Emoji sentiment analysis
3. Aspect-based sentiment analysis
4. Batch processing for performance
"""

import re
import string
import emoji
import torch
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from typing import List, Dict, Any, Tuple, Optional
import logging
import nltk
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from nltk.tokenize import word_tokenize
from collections import defaultdict
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    logger.warning(f"Error downloading NLTK data: {e}")

# Define constants
EMOJI_SENTIMENT_MAP = {
    '😊': 1.0, '😃': 1.0, '😄': 1.0, '😁': 1.0, '😆': 1.0, '😍': 1.0, '🥰': 1.0, '😘': 1.0, '👍': 1.0, '❤️': 1.0,
    '🙂': 0.7, '😌': 0.7, '😉': 0.7, '🙃': 0.5, '😐': 0.0, '😑': 0.0, '😶': 0.0, '🤔': 0.0,
    '😕': -0.3, '😟': -0.5, '😔': -0.5, '😞': -0.7, '😒': -0.7, '😣': -0.8, '😖': -0.8,
    '😡': -1.0, '😠': -1.0, '😤': -1.0, '😭': -1.0, '😢': -1.0, '😩': -1.0, '👎': -1.0, '💔': -1.0
}

# Aspects we want to identify in comments
COMMON_ASPECTS = {
    'content': ['video', 'content', 'videos', 'channel', 'episode', 'vlog', 'series'],
    'quality': ['quality', 'resolution', 'hd', '4k', 'footage', 'production', 'editing', 'edited'],
    'audio': ['audio', 'sound', 'volume', 'mic', 'voice', 'music', 'background', 'noise'],
    'presentation': ['presentation', 'speaking', 'talk', 'speech', 'presenter', 'host', 'explained', 'explaining', 'explanation'],
    'information': ['information', 'informative', 'learn', 'learned', 'educational', 'knowledge', 'useful', 'helpful'],
    'length': ['length', 'duration', 'long', 'short', 'longer', 'shorter', 'time']
}

class SentimentAnalyzer:
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english", batch_size: int = 16, cache_size: int = 1024):
        """
        Initialize the sentiment analyzer with a Hugging Face transformer model
        
        Args:
            model_name: Hugging Face model name
            batch_size: Batch size for processing multiple comments
            cache_size: Size of LRU cache for sentiment analysis results
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_size = cache_size
        
        try:
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Initialize sentiment pipeline
            self.sentiment_pipeline = pipeline(
                task="sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=512,
                truncation=True,
                device=0 if torch.cuda.is_available() else -1  # Use GPU if available
            )
            
            # Cache for sentiment results
            self.analyze_text_sentiment = lru_cache(maxsize=cache_size)(self._analyze_text_sentiment)
            
            logger.info(f"Initialized sentiment analyzer with model: {model_name}")
        except Exception as e:
            logger.error(f"Error initializing sentiment model: {e}")
            # Fall back to TextBlob if model fails to load
            logger.warning("Using TextBlob as fallback for sentiment analysis")
            self.model = None
            self.tokenizer = None
            self.sentiment_pipeline = None
    
    def clean_comment_text(self, comment_text: str) -> Tuple[str, List[str]]:
        """
        Clean comment text for sentiment analysis while preserving emojis
        
        Args:
            comment_text: Raw comment text
            
        Returns:
            Tuple of (cleaned_text, extracted_emojis)
        """
        if not isinstance(comment_text, str):
            return "", []
        
        # Extract emojis before cleaning
        extracted_emojis = [c for c in comment_text if c in emoji.EMOJI_DATA]
        
        # Convert to lower case
        comment_text = comment_text.lower()
        
        # Remove URLs
        comment_text = re.sub(r"https?:\/\/\S+", "", comment_text)
        
        # Remove hashtags and mentions (preserve the text without the # or @)
        comment_text = re.sub(r"#(\S+)", r"\1", comment_text)
        comment_text = re.sub(r"@(\S+)", r"\1", comment_text)
        
        # Remove punctuation (except for emojis)
        for p in string.punctuation:
            if p not in emoji.EMOJI_DATA:
                comment_text = comment_text.replace(p, " ")
        
        # Replace multiple spaces with a single space
        comment_text = re.sub(r"\s+", " ", comment_text)
        
        # Trim whitespaces at the start and end of the text
        comment_text = comment_text.strip()
        
        return comment_text, extracted_emojis
    
    def _analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using transformer model
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment label and score
        """
        if not self.sentiment_pipeline or not text.strip():
            # Fallback to simple classification if model isn't loaded
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return {"label": "positive", "score": polarity}
            elif polarity < -0.1:
                return {"label": "negative", "score": polarity}
            else:
                return {"label": "neutral", "score": 0.0}
        
        try:
            result = self.sentiment_pipeline(text)[0]
            
            # Map the model's output labels to our standard format
            label_mapping = {
                "POSITIVE": "positive",
                "NEGATIVE": "negative",
                "NEUTRAL": "neutral",
                "1": "positive",   # For models that output 1 for positive
                "0": "negative"    # For models that output 0 for negative
            }
            
            # Normalize the label
            label = label_mapping.get(result["label"], result["label"]).lower()
            
            # For binary models (like distilbert-sst2), map to three-class
            if label == "positive" and result["score"] < 0.6:
                label = "neutral"
            elif label == "negative" and result["score"] < 0.6:
                label = "neutral"
            
            return {
                "label": label,
                "score": result["score"]
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {"label": "neutral", "score": 0.0}
    
    def analyze_emoji_sentiment(self, emojis: List[str]) -> float:
        """
        Calculate sentiment score based on emojis in the text
        
        Args:
            emojis: List of emoji characters
            
        Returns:
            Sentiment score between -1.0 and 1.0
        """
        if not emojis:
            return 0.0
        
        total_score = 0.0
        counted_emojis = 0
        
        for e in emojis:
            if e in EMOJI_SENTIMENT_MAP:
                total_score += EMOJI_SENTIMENT_MAP[e]
                counted_emojis += 1
        
        # Return average score if we have any recognized emojis
        return total_score / counted_emojis if counted_emojis > 0 else 0.0
    
    def identify_aspects(self, text: str) -> Dict[str, List[str]]:
        """
        Identify which aspects of a video are mentioned in a comment
        
        Args:
            text: Comment text
            
        Returns:
            Dictionary mapping aspect categories to mentioned terms
        """
        text = text.lower()
        mentioned_aspects = defaultdict(list)
        
        words = set(word_tokenize(text))
        
        for aspect, terms in COMMON_ASPECTS.items():
            for term in terms:
                if term in words or term in text:
                    mentioned_aspects[aspect].append(term)
        
        return dict(mentioned_aspects)
    
    def analyze_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive sentiment analysis on a single comment
        
        Args:
            comment: Comment dictionary
            
        Returns:
            Comment with added sentiment analysis
        """
        # Get the comment text
        text = comment.get('text', '')
        
        # Clean the text and extract emojis
        cleaned_text, emojis = self.clean_comment_text(text)
        
        # Get text sentiment
        text_sentiment = self.analyze_text_sentiment(cleaned_text)
        
        # Get emoji sentiment
        emoji_score = self.analyze_emoji_sentiment(emojis)
        
        # Identify aspects
        aspects = self.identify_aspects(cleaned_text)
        
        # Combine text and emoji sentiment
        combined_score = text_sentiment["score"]
        if emojis:
            # Weight emoji sentiment more heavily if there are multiple emojis
            emoji_weight = min(0.5, len(emojis) * 0.1)  
            combined_score = (1 - emoji_weight) * text_sentiment["score"] + emoji_weight * emoji_score
        
        # Determine final sentiment label
        if combined_score > 0.2:
            final_sentiment = "positive"
        elif combined_score < -0.2:
            final_sentiment = "negative"
        else:
            final_sentiment = "neutral"
        
        # Add sentiment data to the comment
        comment['sentiment'] = final_sentiment
        comment['sentiment_data'] = {
            'text_sentiment': text_sentiment,
            'emoji_sentiment': emoji_score,
            'combined_score': combined_score,
            'aspects': aspects
        }
        
        return comment
    
    def analyze_comments_batch(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of comments
        
        Args:
            comments: List of comment dictionaries
            
        Returns:
            List of comments with sentiment analysis added
        """
        logger.info(f"Analyzing sentiment for {len(comments)} comments")
        
        # Process comments in batches for better performance
        result = []
        for i in range(0, len(comments), self.batch_size):
            batch = comments[i:i+self.batch_size]
            
            # Process each comment in the batch
            for comment in batch:
                analyzed_comment = self.analyze_comment(comment)
                result.append(analyzed_comment)
        
        logger.info(f"Completed sentiment analysis for {len(result)} comments")
        return result
    
    def get_aspect_based_sentiment(self, comments: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Aggregate sentiment by different aspects across all comments
        
        Args:
            comments: List of analyzed comment dictionaries
            
        Returns:
            Dictionary mapping aspects to their average sentiment scores
        """
        aspect_sentiments = defaultdict(list)
        
        for comment in comments:
            if 'sentiment_data' not in comment:
                continue
                
            sentiment_score = comment['sentiment_data']['combined_score']
            
            # Add the sentiment score to each aspect mentioned in the comment
            for aspect in comment['sentiment_data']['aspects']:
                aspect_sentiments[aspect].append(sentiment_score)
        
        # Calculate average sentiment for each aspect
        return {
            aspect: {
                'average_score': sum(scores) / len(scores) if scores else 0,
                'positive': sum(1 for s in scores if s > 0.2) / len(scores) if scores else 0,
                'neutral': sum(1 for s in scores if -0.2 <= s <= 0.2) / len(scores) if scores else 0,
                'negative': sum(1 for s in scores if s < -0.2) / len(scores) if scores else 0,
                'mention_count': len(scores)
            }
            for aspect, scores in aspect_sentiments.items()
        }

def analyze_sentiment(text: str) -> str:
    """
    Legacy function for backward compatibility
    
    Args:
        text: Comment text
    
    Returns:
        Sentiment label (positive, neutral, negative)
    """
    # Create a singleton instance if it doesn't exist
    if not hasattr(analyze_sentiment, 'analyzer'):
        analyze_sentiment.analyzer = SentimentAnalyzer()
    
    # Use the analyzer to get sentiment
    sentiment_result = analyze_sentiment.analyzer.analyze_text_sentiment(text)
    return sentiment_result["label"]

def get_sentiment_emoji(sentiment: str) -> str:
    """
    Return an emoji representing the sentiment
    
    Args:
        sentiment: Sentiment classification
    
    Returns:
        str: Emoji representing the sentiment
    """
    sentiment_emojis = {
        'positive': '😊',
        'negative': '😞',
        'neutral': '😐'
    }
    return sentiment_emojis.get(sentiment.lower(), '😐')

def get_sentiment_color(sentiment: str) -> str:
    """
    Return a color representing the sentiment
    
    Args:
        sentiment: Sentiment classification
    
    Returns:
        str: Hex color code
    """
    sentiment_colors = {
        'positive': '#4ade80',  # Green
        'negative': '#f87171',  # Red
        'neutral': '#a3a3a3'    # Gray
    }
    return sentiment_colors.get(sentiment.lower(), '#a3a3a3')