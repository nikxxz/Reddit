# Reddit Media Downloader

A simple localhost web app for inspecting Reddit posts and preparing media downloads.

## Technology stack

- Frontend: Vanilla HTML, CSS, and JavaScript
- Backend: Python 3.11+
- API framework: FastAPI
- Server: Uvicorn
- Media downloads: yt-dlp

## Project structure

```text
reddit-media-downloader/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py
│   └── services/
│       └── __init__.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── downloads/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

## Python virtual environment

### Windows PowerShell

```powershell
cd E:\Dev\Python\Reddit
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
cd /path/to/Reddit
python3.11 -m venv .venv
source .venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure environment

Copy the example environment file:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### macOS/Linux

```bash
cp .env.example .env
```

## Run the app

```bash
python run.py
```

Open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/api/health
