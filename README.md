# Dad Of Diamond — Order Entry & Workshop Job Sheet System

A local-first Flask + SQLite web application for managing custom jewelry orders, uploading reference media to Google Drive, and generating A4 workshop/karigar PDF job sheets.

## Features

- **Order Entry Form** — capture customer details, product specs, stone details, engraving, and reference media (images + videos)
- **Google Drive Upload** — automatically upload order media to a shared Google Drive folder with shareable links
- **PDF Job Sheets** — generate print-ready A4 workshop sheets with product specs, embedded image previews, and QR codes for video links
- **Order History** — search, view, and delete past orders
- **Daily DB Backup** — scheduled SQLite backup to local disk and optionally to a private Google Drive folder

## Project Structure

```
├── app.py                  # Flask server and REST API
├── database.py             # SQLite schema and CRUD operations
├── drive_uploader.py       # Google Drive API v3 uploader
├── pdf_generator.py        # A4 PDF generator (Playwright + Jinja2 + QR)
├── backup_db.py            # Daily SQLite hot backup script
├── templates/              # index.html, orders.html, pdf_template.html
├── static/                 # CSS and JavaScript
├── tests/                  # Automated test suite
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
└── README.md
```

## Prerequisites

- **Python 3.11+**
- **Google Chrome** or **Microsoft Edge** (for PDF generation via Playwright)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/dadofdiamond-art/DODManage.git
cd DODManage
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your own values:
- `FLASK_SECRET_KEY` — change to a random secret string
- `GOOGLE_DRIVE_ROOT_FOLDER_ID` — your Google Drive folder ID (optional, see below)

### 5. Run the application

```bash
python app.py
```

Open in your browser:
- **Order Entry Form:** http://127.0.0.1:5000/
- **Orders History & Search:** http://127.0.0.1:5000/orders

## Google Drive Setup (Optional)

Google Drive integration is optional. Without it, the app operates in **Local Storage Mode** — you can still create orders and generate PDFs.

### To enable Drive uploads:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Drive API**.
3. Create **OAuth 2.0 Client ID** (Desktop App) credentials.
4. Download the JSON and save it as `credentials.json` in the project root.
5. Set `GOOGLE_DRIVE_ROOT_FOLDER_ID` in `.env` to your target folder ID.
6. Authenticate once:
   ```bash
   python drive_uploader.py --auth
   ```

> **Note:** `credentials.json`, `token.json`, and `.env` are excluded from git via `.gitignore`. Never commit these files.

## Daily Database Backup

Run a one-click backup anytime:
```bash
python backup_db.py
```

Or register a daily scheduled task (Windows Task Scheduler):
```powershell
schtasks /Create /SC DAILY /TN "DOD_Order_DB_Backup" /TR "python backup_db.py" /ST 21:00 /F
```

## Running Tests

```bash
python -m pytest -v
```

## Security Notes

The following files contain secrets and are **excluded from git** via `.gitignore`:

| File | Contains |
|---|---|
| `.env` | Flask secret key, Drive folder IDs |
| `credentials.json` | Google OAuth client ID and client secret |
| `token.json` | Google OAuth access/refresh token |
| `service_account.json` | Google service account private key |
| `orders.db` | Customer data (names, contacts, addresses) |

> ⚠️ **Never commit these files.** If you accidentally push secrets, revoke them immediately in [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

## License

Private — Dad Of Diamond internal tooling.
