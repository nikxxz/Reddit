# Reddit Media Downloader

A localhost FastAPI web app for searching Reddit media through a read-only PRAW client. Search uses Reddit only for discovery and metadata; media transfer is handled by direct URLs or `yt-dlp` service modules.

## Project Structure

```text
backend/
  api/                 FastAPI dependencies, safe error types, shared response text
  models/              Pydantic models split by common and Reddit-specific domains
  routes/              Thin HTTP route handlers
  services/downloads/  Direct download, yt-dlp, filename, resolver, and safety helpers
  services/reddit/     Reddit clients, OAuth/session, connection checks, search, detection, normalization
  tests/               Backend unit tests and mocked Reddit submission fixtures
  utils/               Shared HTML, URL, and logging helpers
frontend/
  index.html           Application shell and page containers
  js/                  ES module frontend application code
  styles/              CSS split by layout, sidebar, search, filters, cards, states, responsive
  assets/              Static frontend assets
downloads/            Reserved local output folder
```

Download queue and history are intentionally still future work. Additional downloader behavior should stay in domain modules such as:

- `backend/services/downloads/`
- `backend/routes/downloads.py`
- `backend/models/downloads.py`

Do not add FFmpeg orchestration or download queue behavior outside those future downloader modules.

## Backend Responsibilities

- `backend/main.py`: creates the FastAPI app, registers routers, and mounts static frontend assets.
- `backend/config.py`: reads environment configuration and validates required Reddit values.
- `backend/routes/reddit.py`: validates HTTP parameters, calls Reddit services, and translates known domain errors into safe HTTP responses.
- `backend/routes/auth.py`: handles Reddit OAuth login, callback, status, and logout.
- `backend/services/reddit/client.py`: creates and reuses the anonymous PRAW client, or returns the authenticated user client when connected.
- `backend/services/reddit/oauth.py`: creates OAuth URLs, exchanges callback codes, restores sessions, and logs out.
- `backend/services/reddit/session.py`: persists the refresh token and username locally.
- `backend/services/reddit/connection.py`: checks Reddit connectivity without exposing credentials.
- `backend/services/reddit/search.py`: executes Reddit searches, paginates where possible, filters normalized media, and returns response models.
- `backend/services/reddit/media_detector.py`: contains media-type constants and detection rules.
- `backend/services/reddit/normalizer.py`: converts PRAW submission-like objects into stable `RedditMediaItem` models.
- `backend/services/downloads/`: validates URLs, streams direct media to `.part` files, chooses download strategy, and wraps `yt-dlp`.

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

## Frontend Migration Status

- `frontend/` contains the current production frontend.
- `frontend-react/` contains the parallel React migration workspace.
- FastAPI continues to serve `frontend/`.
- Do not remove `frontend/` until React feature parity is verified.

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
SESSION_FILE=backend/data/session.json
DEBUG=true
REDDIT_CONNECT_TIMEOUT=10
REDDIT_READ_TIMEOUT=20
MEDIA_CONNECT_TIMEOUT=10
MEDIA_READ_TIMEOUT=60
DOWNLOAD_TOTAL_TIMEOUT=300
MAX_API_RETRIES=2
MAX_DOWNLOAD_RETRIES=2
SEARCH_LIMIT=24
SEARCH_FETCH_MULTIPLIER=3
MAX_CONCURRENT_DOWNLOADS=2

REDDIT_USERNAME=your_username
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=windows:your-app-name:v0.1.0 (by /u/your_username)
REDDIT_REDIRECT_URI=http://127.0.0.1:8000/api/reddit/auth/callback
```

Keep `.env` private. It is ignored by git and should not be committed or shared.

Configure the same redirect URI in your Reddit app settings:

```text
http://127.0.0.1:8000/api/reddit/auth/callback
```

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

## Reddit Account OAuth

The app can run anonymously with the configured Reddit app credentials, or with an optional connected Reddit user session.

- Click `Connect Reddit` in the sidebar.
- Reddit opens in a popup and asks for `identity` and `read` scopes only.
- After approval, Reddit redirects to `/api/reddit/auth/callback`.
- The backend stores only the refresh token and username in `backend/data/session.json`.
- Access tokens are not persisted; PRAW regenerates them from the refresh token.
- Click `Disconnect` to delete the local session and return to anonymous mode.

The session file is ignored by git. On startup, the backend attempts to restore the saved refresh token; if it is invalid, the file is deleted and the app falls back to anonymous search.

## Reddit Search API

`GET /api/reddit/search`

Supported query parameters:

- `q` required
- `subreddit` optional, without `r/`
- `media_type`: `all`, `image`, `video`, `gif`, `gallery`, `external`
- `sort`: `relevance`, `hot`, `top`, `new`
- `time_filter`: `hour`, `day`, `week`, `month`, `year`, `all`
- `limit`: 1 to 50
- `after`: optional Reddit listing cursor
- `include_nsfw`: `false` by default; `true` includes NSFW posts Reddit normally returns to this API client

The response returns normalized media items only and never exposes raw PRAW objects or credentials. Search normalization uses already-loaded listing fields and does not intentionally access comment trees or hydrate each submission.

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
