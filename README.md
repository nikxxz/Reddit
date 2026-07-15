# Reddit Media Downloader

A localhost FastAPI web app for searching Reddit media through a read-only PRAW client. Downloading is intentionally not implemented yet.

## Project Structure

```text
backend/
  api/                 FastAPI dependencies, safe error types, shared response text
  models/              Pydantic models split by common and Reddit-specific domains
  routes/              Thin HTTP route handlers
  services/reddit/     Reddit client, connection checks, search, detection, normalization
  tests/               Backend unit tests and mocked Reddit submission fixtures
  utils/               Shared HTML, URL, and logging helpers
frontend/
  index.html           Application shell and page containers
  js/                  ES module frontend application code
  styles/              CSS split by layout, sidebar, search, filters, cards, states, responsive
  assets/              Static frontend assets
downloads/            Reserved local output folder
```

Future downloader work should go into reserved domain modules such as:

- `backend/services/downloads/`
- `backend/routes/downloads.py`
- `backend/models/downloads.py`

Do not add `yt-dlp`, FFmpeg, or download queue behavior outside those future downloader modules.

## Backend Responsibilities

- `backend/main.py`: creates the FastAPI app, registers routers, and mounts static frontend assets.
- `backend/config.py`: reads environment configuration and validates required Reddit values.
- `backend/routes/reddit.py`: validates HTTP parameters, calls Reddit services, and translates known domain errors into safe HTTP responses.
- `backend/services/reddit/client.py`: creates and reuses the read-only PRAW client.
- `backend/services/reddit/connection.py`: checks Reddit connectivity without exposing credentials.
- `backend/services/reddit/search.py`: executes Reddit searches, paginates where possible, filters normalized media, and returns response models.
- `backend/services/reddit/media_detector.py`: contains media-type constants and detection rules.
- `backend/services/reddit/normalizer.py`: converts PRAW submission-like objects into stable `RedditMediaItem` models.

## Frontend Responsibilities

- `frontend/js/app.js`: small bootstrap that initializes state, pages, sidebar behavior, app config, and connection checks.
- `frontend/js/state.js`: shared UI state.
- `frontend/js/api/`: all frontend `fetch` calls.
- `frontend/js/data/sampleMedia.js`: sample cards used only before a real search.
- `frontend/js/handlers/`: event binding and coordination.
- `frontend/js/renderers/`: DOM rendering for cards, grids, states, and connection status.
- `frontend/js/pages/`: page controllers for search, connections, and placeholder pages.
- `frontend/js/utils/`: URL, date, text, and DOM helpers.

The frontend uses browser-native ES modules and has no build step.

## Setup

Requirements:

- Python 3.11 or newer
- A Reddit app with a client ID, client secret, and user agent

Install dependencies:

```powershell
pip install -r requirements.txt
```

Copy the example environment file and fill in the Reddit values:

```powershell
Copy-Item .env.example .env
```

Expected `.env` keys:

```dotenv
APP_HOST=127.0.0.1
APP_PORT=8000
APP_NAME=Reddit Media Downloader
DOWNLOAD_DIR=downloads
DEBUG=true

REDDIT_USERNAME=your_username
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=windows:your-app-name:v0.1.0 (by /u/your_username)
```

Keep `.env` private. It is ignored by git and should not be committed or shared.

## Run

```powershell
python run.py
```

Open:

- Web app: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/api/health
- Public app config: http://127.0.0.1:8000/api/app-config
- Reddit connection test: http://127.0.0.1:8000/api/reddit/test
- Reddit search: http://127.0.0.1:8000/api/reddit/search?q=mountain&limit=3

## Reddit Search API

`GET /api/reddit/search`

Supported query parameters:

- `q` required
- `subreddit` optional, without `r/`
- `media_type`: `all`, `image`, `video`, `gif`, `gallery`
- `sort`: `relevance`, `hot`, `top`, `new`, `comments`
- `time_filter`: `hour`, `day`, `week`, `month`, `year`, `all`
- `limit`: 1 to 50
- `after`: optional Reddit listing cursor

The response returns normalized media items only and never exposes raw PRAW objects or credentials.

## Tests

Run backend unit tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests
```

Run an import/syntax check:

```powershell
.\.venv\Scripts\python.exe -m compileall backend run.py
```

## Troubleshooting

- `Missing Reddit configuration values`: check `.env` and all `REDDIT_*` keys.
- `Reddit API connection failed`: verify credentials, user agent, network access, and Reddit availability.
- Port already in use: change `APP_PORT` in `.env`, then restart the app.
- Browser module 404s: ensure `python run.py` is serving the current FastAPI app so `/js/...` and `/styles/...` mounts are active.
