# Reddit Media Downloader

A localhost FastAPI web app for checking a Reddit API connection and preparing Reddit media download workflows.

## What is included

- `backend/`: FastAPI app, routes, config, and Reddit service code.
- `frontend/`: static HTML, CSS, and JavaScript served by FastAPI.
- `downloads/`: local output folder for downloaded media.
- `run.py`: local development server entry point.
- `.env.example`: template for local configuration.

## Requirements

- Python 3.11 or newer
- A Reddit app with a client ID, client secret, and user agent

Install dependencies from `requirements.txt`:

```powershell
pip install -r requirements.txt
```

## Setup

From the project directory:

```powershell
cd E:\Dev\Python\Reddit
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux:

```bash
cd /path/to/Reddit
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the example file and fill in your Reddit app values:

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
`APP_NAME` controls the browser/app title and `REDDIT_USERNAME` is displayed under the app title in the sidebar.

## Run the App

With the virtual environment activated:

```powershell
python run.py
```

Then open:

- Web app: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/api/health
- Public app config: http://127.0.0.1:8000/api/app-config
- Reddit connection test: http://127.0.0.1:8000/api/reddit/test

When `DEBUG=true`, Uvicorn runs with reload enabled. That is useful for development, but use `DEBUG=false` if you want a single stable server process.

## Test the Package

Run a Python syntax/import check:

```powershell
.\.venv\Scripts\python.exe -m compileall backend run.py
```

Test local configuration without printing secrets:

```powershell
.\.venv\Scripts\python.exe -c "from backend.config import settings; settings.validate_reddit_settings(); print('Reddit config values are present')"
```

Test the Reddit API connection directly:

```powershell
.\.venv\Scripts\python.exe -c "from backend.services.reddit_service import RedditService; print(RedditService().test_connection())"
```

Expected successful result:

```python
{'connected': True, 'read_only': True, 'authenticated_user': None}
```

You can also test through the running HTTP server:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/reddit/test
```

## API Behavior

The current Reddit test uses a read-only PRAW client and fetches one item from `r/python` with `limit=1`. The frontend calls `/api/reddit/test` once on page load, so normal use should not generate repeated Reddit API calls.

## Troubleshooting

- `Missing Reddit configuration values`: check that `.env` exists and all `REDDIT_*` keys are filled in.
- `Reddit API connection failed`: verify the client ID, client secret, user agent, and network access.
- Port already in use: change `APP_PORT` in `.env`, then restart the app.
