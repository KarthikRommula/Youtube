# YouTube Analytics Dashboard

An interactive analytics tool that fetches a YouTube video's comments via the YouTube Data API v3 and turns them into actionable insights — sentiment breakdowns, topic categorization, trending keywords, and audience-driven content ideas.

The project ships in two flavors that share the same analysis engine:

- A **Streamlit web dashboard** (`app.py`) with interactive visualizations.
- A **Flask REST API** (`api.py`) that exposes the same analysis as JSON endpoints for integration with other frontends or services.

## Features

- **Comment fetching** — Pulls comments from any public YouTube video using the YouTube Data API v3, with automatic pagination (100 per page) and an optional cap on the total number analyzed (100–500 or "all").
- **Sentiment analysis** — Classifies each comment as positive, neutral, or negative using TextBlob polarity scoring (cached for performance), with emoji and color mappings for display.
- **Topic detection** — Buckets comments into predefined categories (tutorial, review, question, suggestion, technical) based on keyword matching.
- **Keyword extraction** — Surfaces the most frequent meaningful terms using NLTK tokenization and stopword filtering (including a custom YouTube-specific stopword list).
- **Content ideas** — Mines request-style comments (e.g. "can you make…", "please make…", "tutorial on…") to suggest content the audience is asking for, ranked by likes.
- **Video statistics** — Retrieves title, channel, view/like/comment counts, publish date, description, and thumbnail.
- **Engagement metrics** — Aggregates total comments, likes, replies, and a computed engagement rate.
- **Dashboard views** — Overview, sentiment analysis, topic analysis, and a searchable/filterable comments explorer.
- **REST API** — Health check, video info, comments, full analysis, sentiment-only, topics-only, and comment search endpoints (CORS enabled).

## Tech Stack

- **Language:** Python
- **Web UI:** [Streamlit](https://streamlit.io/)
- **REST API:** [Flask](https://flask.palletsprojects.com/) with Flask-CORS
- **Data source:** [YouTube Data API v3](https://developers.google.com/youtube/v3) (accessed via `requests`)
- **NLP / sentiment:** [TextBlob](https://textblob.readthedocs.io/), [NLTK](https://www.nltk.org/)
- **Data handling:** pandas, NumPy
- **Visualization:** Plotly
- **Config:** python-dotenv

> Note: `requirements.txt` also pins a number of heavier ML libraries (e.g. `torch`, `transformers`, `huggingface-hub`). The current sentiment module uses TextBlob as its active implementation — these are not required to run the core features.

## How It Works

1. A YouTube URL (or raw 11-character video ID) is submitted via the dashboard form or an API query parameter.
2. `extract_video_id()` normalizes the input, supporting standard watch URLs, `youtu.be` short links, Shorts, and Live URLs.
3. `utils/youtube_api.py` calls the YouTube Data API:
   - `extract_video_statistics()` → video metadata and stats.
   - `fetch_comments()` → a page of comment threads; the app paginates until the requested count (or all comments) is reached.
4. Each comment is run through the analysis utilities:
   - `utils/sentiment.py` → per-comment sentiment label.
   - `utils/topic_analysis.py` → topic counts, keyword frequencies, and content ideas.
5. Results are aggregated into a dashboard data structure and either rendered by the Streamlit `components/` views or returned as JSON by the Flask API.

## Project Structure

```
Youtube/
├── app.py                     # Streamlit dashboard entry point
├── api.py                     # Flask REST API entry point
├── requirements.txt           # Python dependencies
├── assets/
│   └── style.css              # Custom dashboard styling
├── components/                # Streamlit UI views
│   ├── dashboard.py           # Overview view
│   ├── sentiment_view.py      # Sentiment analysis view
│   ├── topic_view.py          # Topic & keyword view
│   └── comments_view.py       # Searchable comments explorer
└── utils/                     # Analysis engine (shared by app.py & api.py)
    ├── youtube_api.py         # YouTube Data API client
    ├── sentiment.py           # TextBlob-based sentiment analysis
    └── topic_analysis.py      # Topics, keywords, content ideas
```

## Prerequisites

- Python 3.9+ recommended
- A **YouTube Data API v3** key ([Google Cloud Console](https://console.cloud.google.com/) → enable YouTube Data API v3 → create an API key)

## Installation

```bash
# Clone the repository
git clone https://github.com/KarthikRommula/Youtube.git
cd Youtube

# (Recommended) create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root (it is git-ignored) and add your API key:

```env
YOUTUBE_API_KEY=your_api_key_here
```

Supported environment variables:

| Variable          | Used by         | Description                                                        | Default |
| ----------------- | --------------- | ------------------------------------------------------------------ | ------- |
| `YOUTUBE_API_KEY` | app.py / api.py | YouTube Data API v3 key (required to fetch any real data).         | —       |
| `PORT`            | api.py          | Port the Flask API listens on.                                     | `5000`  |
| `FLASK_DEBUG`     | api.py          | Set to `true` to run Flask in debug mode.                          | `false` |

> The API key is read from the environment at request time. Without a valid key, the API endpoints return `503` and the dashboard shows a configuration warning.

## Usage

### Streamlit dashboard

```bash
streamlit run app.py
```

Open the provided local URL (default `http://localhost:8501`), paste a YouTube video URL, choose how many comments to analyze, and click **Analyze Video**. Use the sidebar to switch between the Overview, Sentiment, Topics, and Comments views.

### Flask REST API

```bash
python api.py
```

The API runs at `http://localhost:5000` by default.

#### Endpoints

| Method | Endpoint               | Description                                            |
| ------ | ---------------------- | ------------------------------------------------------ |
| `GET`  | `/`                    | API metadata and endpoint listing.                     |
| `GET`  | `/api/health`          | Health check; reports whether the API key is set.      |
| `GET`  | `/api/video-info`      | Basic video information.                               |
| `GET`  | `/api/comments`        | Fetch comments for a video.                            |
| `GET`  | `/api/analyze`         | Full analysis (sentiment, topics, keywords, ideas).    |
| `GET`  | `/api/sentiment`       | Sentiment analysis only.                               |
| `GET`  | `/api/topics`          | Topic and keyword analysis only.                       |
| `GET`  | `/api/comments/search` | Search comments by term, optionally filter by sentiment.|

Common query parameters:

- `url` *(required for most endpoints)* — YouTube video URL or 11-character video ID.
- `max_comments` *(optional)* — Maximum number of comments to fetch/analyze.
- `q` *(required for search)* — Search term.
- `sentiment` *(optional, search only)* — `positive` | `neutral` | `negative`.

Example:

```bash
curl "http://localhost:5000/api/analyze?url=https://youtu.be/GMjFY02ToCo&max_comments=100"
```

## Notes on API Quota

The YouTube Data API uses a quota system (10,000 units/day by default). Reading comments consumes quota in batches of up to 100, so analyzing videos with very large comment counts can use a significant portion of the daily allowance. Limit `max_comments` when working with popular videos.
