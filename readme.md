### API Documentation

``Base URL``
The API will be available at http://localhost:5000 by default (or the server where you deploy it).
Endpoints

``test url:-  http://127.0.0.1:5000/api/analyze?url=https://youtu.be/GMjFY02ToCo?si=dZakjf3cNteXJcgP&max_comments=100``
### 1. Health Check ###
``GET /api/health``
Checks if the API is running and if the YouTube API key is configured.
### 2. Video Information
GET /api/video-info?url={youtube_url}
Fetches basic information about a YouTube video.
Parameters:

url: YouTube video URL or ID (required)

### 3. Comments
``GET /api/comments?url={youtube_url}&max_comments={number}``
Fetches comments from a YouTube video.
Parameters:

url: YouTube video URL or ID (required)
``max_comments: Maximum number of comments to fetch (optional)``

### 4. Full Analysis
``GET /api/analyze?url={youtube_url}&max_comments={number}``
Performs comprehensive analysis of a YouTube video's comments, including sentiment, topics, keywords, and content ideas.
Parameters:

url: YouTube video URL or ID (required)
max_comments: Maximum number of comments to analyze (optional)

### 5. Sentiment Analysis
``GET /api/sentiment?url={youtube_url}&max_comments={number}``
Analyzes only the sentiment of a YouTube video's comments.
Parameters:

url: YouTube video URL or ID (required)
max_comments: Maximum number of comments to analyze (optional)

### 6. Topic Analysis
``GET /api/topics?url={youtube_url}&max_comments={number}``
Analyzes only the topics and keywords of a YouTube video's comments.
Parameters:

url: YouTube video URL or ID (required)
max_comments: Maximum number of comments to analyze (optional)