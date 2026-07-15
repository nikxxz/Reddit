# React Frontend

This directory contains the current React + Vite frontend for Reddit Media Downloader.

FastAPI serves the production build from `frontend-react/dist/` at http://127.0.0.1:8000. The older `frontend/` directory remains in the repository as a legacy reference.

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
npm.cmd run dev
```

Development URLs:

- FastAPI backend and production build: http://127.0.0.1:8000
- Vite development server: http://127.0.0.1:5173

## API Proxy

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000` and preserves the `/api` path. React API modules use relative paths such as `/api/health`; they do not call Reddit directly and do not hardcode the FastAPI origin.

## Build

Create a production React build with:

```powershell
npm.cmd run build
```

The build output is written to `frontend-react/dist/`. FastAPI serves this build at `/`; if the directory is missing, `/` returns `503 React frontend not built`.

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1` with an execution policy error.
