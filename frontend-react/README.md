# React Frontend

`frontend-react/` is the authoritative frontend for Reddit Media Downloader. It is built with React, Vite, and Mantine.

FastAPI serves the production build from `frontend-react/dist/` at `http://127.0.0.1:8000`. The archived browser-module frontend lives under `legacy/frontend/` and is no longer served.

## App Navigation

The sidebar contains four primary entries:

- Search
- Subreddits / Users
- Downloads
- Settings

`Subreddits / Users` opens `/browse`, where a combined search field finds Reddit communities and users. Selecting a result opens `/browse/subreddit/:name` or `/browse/user/:username`. The entity media browser persists normalized filters in the URL query string, reuses the shared media grid, preview modal, gallery carousel, and download controls, and only renders normalized media posts returned by the backend.

Subreddit feeds support Hot, New, Top, and Rising. User feeds support New and Top. Time ranges apply only to Top. Invalid URL filter values are normalized to safe defaults, and private or unavailable entities render safe app messages. User search support is limited by Reddit/PRAW capabilities. When broad user search is unavailable, the backend falls back to exact username lookup.

## Development

Install dependencies:

```powershell
npm.cmd ci
```

Start Vite:

```powershell
npm.cmd run dev
```

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`, preserving the `/api` path. React API modules use relative paths and do not call Reddit directly.

## Production Build

```powershell
npm.cmd run build
```

The output is written to `frontend-react/dist/`. If the build is missing, FastAPI returns a `503 React frontend not built` page for `/`.

## Quality Commands

```powershell
npm.cmd run lint
npm.cmd run test:run
npm.cmd run build
```

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1` with an execution-policy error.

## Structure

- `src/api/`: FastAPI API clients
- `src/components/`: UI components, including entity search cards and shared media cards
- `src/hooks/`: stateful React hooks
- `src/pages/`: top-level app views
- `src/styles/`: app CSS
- `src/test/`: Vitest and Testing Library setup helpers
