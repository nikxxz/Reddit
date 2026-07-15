# React Migration Frontend

This directory contains a parallel React + Vite frontend for the Reddit Media Downloader migration.

The current production frontend remains unchanged in `frontend/` and continues to be served by FastAPI at http://127.0.0.1:8000. This React app is only a development workspace for staged migration work and is not served by FastAPI yet.

## Requirements

- Node.js
- npm
- Python dependencies from the repository root

## Install

```powershell
cd frontend-react
npm install
```

## Run Both Applications

Start FastAPI from the repository root:

```powershell
python run.py
```

Start Vite from this directory:

```powershell
cd frontend-react
npm run dev
```

Development URLs:

- Existing frontend: http://127.0.0.1:8000
- React workspace: http://127.0.0.1:5173

## API Proxy

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000` and preserves the `/api` path. React API modules use relative paths such as `/api/health`; they do not call Reddit directly and do not hardcode the FastAPI origin.

## Build

Create a production React build with:

```powershell
npm run build
```

The build output is written to `frontend-react/dist/`. FastAPI does not serve this build yet.
