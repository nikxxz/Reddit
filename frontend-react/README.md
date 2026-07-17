# React Frontend

`frontend-react/` is the authoritative frontend for Reddit Media Downloader. It is built with React, Vite, and Mantine.

FastAPI serves the production build from `frontend-react/dist/` at `http://127.0.0.1:8000`. The archived browser-module frontend lives under `legacy/frontend/` and is no longer served.

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

## Universal Search

The Universal Search page searches Reddit and Tumblr through provider-neutral backend models. Tumblr appears as available when `TUMBLR_CONSUMER_KEY` is configured and as configuration-required otherwise. Pinterest and Instagram remain planned.

Tumblr options appear only when Tumblr is selected. Tags mode is the default; Blog mode accepts a public Tumblr blog name or URL and can include an optional tag. Tumblr results use the shared preview modal and download actions for supported image, GIF, video, and gallery assets. Unsupported Tumblr media keeps the safe source link visible without showing a broken download action.

The existing Search page remains the stable Reddit-specific experience.

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
- `src/components/`: UI components
- `src/hooks/`: stateful React hooks
- `src/pages/`: top-level app views
- `src/styles/`: app CSS
- `src/test/`: Vitest and Testing Library setup helpers
