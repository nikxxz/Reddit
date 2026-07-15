# Reddit Media Downloader

A local FastAPI and React application for browsing Reddit media and saving selected files to the host computer. The app supports anonymous Reddit browsing where Reddit allows it, OAuth-authenticated access, keyword search, subreddit-only browsing, media filters, NSFW filtering, responsive media cards, gallery previews, background download jobs, progress polling, and cancellation.

The current authoritative frontend is `frontend-react/`, built with React, Vite, and Mantine. FastAPI serves the production React build from `frontend-react/dist`. The older `frontend/` browser-module frontend remains in the repository as legacy code and should not be removed without a separate parity check and explicit approval.

## Features

- Reddit OAuth sign-in, session restore, and disconnect
- Anonymous and authenticated Reddit access
- Keyword search and subreddit-only browsing
- Media-type filters for images, GIFs, videos, external media, and galleries
- NSFW filtering
- Responsive media grid with preview modal and gallery carousel
- Downloads for images, GIFs, videos, supported external media, and galleries
- Background download jobs with progress, result files, failures, and cancellation
- SQLite-backed persistent download history with portable relative file paths
- Local thumbnails for downloaded history items with dummy fallback
- Safe diagnostics endpoint at `GET /api/system/status`

## Project Structure

```text
backend/
  api/
  models/
  routes/
  services/
    downloads/
    reddit/
  tests/
  utils/

frontend-react/
  src/
    api/
    components/
    hooks/
    pages/
    styles/
  package.json
  package-lock.json
  vite.config.js

frontend/
  Legacy browser-module frontend retained for reference.

downloads/
  images/
  videos/
  gifs/
  galleries/
  external/

app-data/
  database/
  thumbnails/generated/
  sessions/
  backups/
  logs/
  settings/
```

## Requirements

- Python 3.10 or newer. This repository is currently validated on Python 3.10.
- Node.js and npm for the React frontend.
- `yt-dlp` is required for video and supported external-media downloads.
- FFmpeg is recommended for media that requires audio/video merging. The app starts without FFmpeg; diagnostics report it as missing, image downloads still work, and affected video merges fail with a clear download error.

## Setup On Windows PowerShell

Backend:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Frontend development server:

```powershell
cd frontend-react
npm ci
npm run dev
```

Frontend production build:

```powershell
cd frontend-react
npm ci
npm run build
```

FastAPI runs at `http://127.0.0.1:8000` by default. Vite runs at its printed development URL, usually `http://127.0.0.1:5173`. For LAN access, set `APP_HOST=0.0.0.0` and open `http://<host-computer-lan-ip>:8000` from another device.

FastAPI serves `frontend-react/dist/index.html` and `/assets/*` after `npm run build`. If the React build is missing, the backend returns a 503 page telling you to run the frontend development server or build the React app.

Reddit OAuth redirect URIs are exact. If `REDDIT_REDIRECT_URI` is configured for `127.0.0.1`, OAuth callback completion is intended for the host computer, not another LAN device. Add and configure a matching LAN callback URI in the Reddit app settings before expecting OAuth login to complete from a phone or tablet.

## Configuration

Copy `.env.example` to `.env` and fill in the Reddit credentials. Do not commit `.env`.

Important settings:

- `APP_HOST`, `APP_PORT`, `APP_NAME`, `DEBUG`
- `APP_DATA_DIR`, `DATABASE_FILENAME`, `THUMBNAIL_FORMAT`, `THUMBNAIL_MAX_WIDTH`, `THUMBNAIL_MAX_HEIGHT`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `REDDIT_REDIRECT_URI`, `SESSION_FILE`
- `SEARCH_LIMIT`, `SEARCH_FETCH_MULTIPLIER`, `SEARCH_SYNTAX`, `MAX_API_RETRIES`
- `DOWNLOAD_DIR`, `MAX_CONCURRENT_DOWNLOADS`, `MAX_DOWNLOAD_SIZE_MB`
- `DOWNLOAD_JOB_RETENTION_HOURS`, `FAILED_JOB_RETENTION_HOURS`, `PART_FILE_MAX_AGE_HOURS`, `MIN_FREE_DISK_GB`
- `DATABASE_BACKUP_RETENTION`, `DATABASE_BACKUP_INTERVAL_HOURS`, `LIBRARY_RECONCILE_ON_STARTUP`, `GENERATE_MISSING_THUMBNAILS_ON_STARTUP`

## Download Behavior

Downloaded files are saved on the host computer running FastAPI, not on the browser device. Opening the UI from a phone starts downloads on the host computer; it does not transfer the resulting files to the phone.

Default folders:

```text
downloads/images/
downloads/videos/
downloads/gifs/
downloads/galleries/
downloads/external/
```

Filename format:

```text
<subreddit>_<username>_<filename>.<extension>
```

Gallery item format:

```text
<subreddit>_<username>_<filename>_01.<extension>
```

Gallery downloads may produce multiple files. Duplicate target filenames receive suffixes so existing files are not overwritten. Temporary `.part` files are used while direct downloads stream to disk; stale `.part` files under the configured download root are cleaned up on startup after the configured age threshold.

## Portable Media Library

The persistent library database lives at `app-data/database/reddit_media_library.sqlite3`.

Downloaded media remains as normal files under `downloads/`; the database stores history, file metadata, checksums, relative paths, and thumbnail records. It does not store OAuth tokens, Reddit secrets, browser cookies, raw PRAW objects, absolute installation paths, or the media files themselves.

For a full portable restore:

1. Stop the application.
2. Copy `app-data/`.
3. Copy `downloads/`.
4. Copy `.env` only when appropriate for that machine.
5. Start the application from the new location.
6. The app opens the database and reconciles history against the moved `downloads/` folder.

Copying only `app-data/` restores the history database, but downloaded files may appear missing until the matching `downloads/` tree is restored. Missing files do not erase history; records keep their completed, failed, or cancelled status and update a separate availability field.

Generated thumbnails live under `app-data/thumbnails/generated/`. The backend prefers generated local thumbnails, then downloaded local media, then a dummy thumbnail. Video thumbnails use FFmpeg when available. Image and GIF thumbnail generation uses Pillow when installed; without it, the app falls back to local files or the dummy thumbnail.

## Database Backups

Routine SQLite backups are written to `app-data/backups/`.

The app uses SQLite's backup API, creates pre-migration backups before applying pending migrations to an existing database, and retains the newest `DATABASE_BACKUP_RETENTION` routine backups. It only prunes backup files matching this application's backup naming pattern.

Manual restore:

1. Stop the application.
2. Back up the current `app-data/` directory.
3. Replace `app-data/database/reddit_media_library.sqlite3` with the selected backup.
4. Start the application.
5. Let startup reconciliation update file and thumbnail availability.

## Reliability And Diagnostics

Active download jobs are in memory. Historical completed, failed, and cancelled downloads are persisted in SQLite. Cleanup removes only history records, never downloaded media.

Retained jobs are available at `GET /api/downloads`. The response returns safe job summaries ordered by active jobs first, then queued, failed, completed, and cancelled jobs, newest first within each group. Failed and cancelled jobs can be retried with `POST /api/downloads/{job_id}/retry`; the retry creates a new job ID and keeps the old terminal job unchanged. Terminal metadata can be cleared with `DELETE /api/downloads/terminal` without deleting downloaded files.

Before starting a new download, the backend checks free disk space under the configured download filesystem. If available space is below `MIN_FREE_DISK_GB`, the job is rejected with:

```text
Not enough free disk space to start this download.
```

Safe diagnostics are available at:

```text
GET /api/system/status
```

The response reports FFmpeg availability, yt-dlp availability, download-directory readiness, writable status, free space, configured minimum free space, active download count, queued download count, database readiness, schema version, backup availability, library counts, and thumbnail-directory readiness. It does not expose absolute filesystem paths, environment values, OAuth tokens, secrets, usernames, command lines, or internal IP addresses.

The React app currently has no real settings or connections page beyond sidebar/status components, so diagnostics are backend-only for now. A future UI block should live on a real settings or connections page, not on the search page.

## Development Workflow

Run backend tests without live Reddit or media-host requests:

```powershell
python -m compileall backend
pytest
```

Run the backend:

```powershell
python run.py
```

Useful local checks:

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/api/reddit/test
http://127.0.0.1:8000/api/system/status
```

Run the React production build:

```powershell
cd frontend-react
npm ci
npm run build
```

## Security Cautions

This is a local personal tool. Treat it as host-machine access to downloads and OAuth state:

- Do not expose it directly to the public internet.
- Do not commit `.env`, app-data session files, SQLite databases, generated thumbnails, backups, or downloaded media.
- Do not share logs that might contain post metadata you consider private.
- Use LAN access only on networks you trust.
- Keep `yt-dlp` and FFmpeg installed from trusted sources.

## Current Limitations

- Automatic orphan-file import is not implemented.
- Gallery "download missing items" is detected as partial history but queued as a full retry in this milestone.
- The diagnostics endpoint is backend-only until a real settings or connections page exists.
- The legacy `frontend/` tree has not been removed.
- OAuth redirect behavior across LAN devices depends on matching Reddit app callback configuration.
- Supported external-media downloads depend on yt-dlp and the remote host.
