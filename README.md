# Dad Of Diamond — Order Entry & Workshop Job Sheet System

A local-first Flask + SQLite web application for managing custom jewelry orders, uploading reference media to Google Drive, and generating PII-free A4 workshop/karigar PDF job sheets.

## Project Structure

- `app.py` — Flask server and REST API (`/`, `/orders`, `/api/orders`, `/api/check-order-id/<id>`, `/orders/<id>/pdf`)
- `database.py` — SQLite schema (`orders`, `order_items`, `order_media`) and CRUD operations (`orders.db`)
- `drive_uploader.py` — Standalone & integrated Google Drive API v3 uploader and private DB backup helper
- `pdf_generator.py` — A4 Workshop PDF generator (Playwright + Jinja2 + QR codes for video links)
- `backup_db.py` — Daily SQLite hot backup script (saves to `backups/` and private Google Drive folder)
- `templates/` — `index.html`, `orders.html`, and `pdf_template.html`
- `static/` — Minimalist white/grey/`#3F070C` maroon styling and dynamic order form / history JS
- `tests/` — Automated test suite covering database, Drive mocking, PII exclusion, and edge cases

## Quick Start (Windows PowerShell)

1. Activate or use the virtual environment Python directly:
   ```powershell
   .\venv\Scripts\python.exe app.py
   ```
2. Open in your browser:
   - Order Entry Form: `http://127.0.0.1:5000/`
   - Orders History & Search: `http://127.0.0.1:5000/orders`

## Google Drive Setup (Optional for Local Testing, Required for Cloud Media Links)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the **Google Drive API**.
2. Create **OAuth 2.0 Client ID (Desktop App)** credentials, download the JSON, and save it as `credentials.json` in `D:\ORDER project\` (or place a Service Account key at `service_account.json`).
3. Copy `.env.example` to `.env` and optionally set `GOOGLE_DRIVE_ROOT_FOLDER_ID` to your `DOD_Order_Media` folder ID.
4. Authenticate once from PowerShell:
   ```powershell
   .\venv\Scripts\python.exe drive_uploader.py --auth
   ```
   Until `credentials.json` is added, the app operates in **Local Storage Mode** so you can still create orders and generate PDFs immediately.

## Daily Database Backup (Windows Task Scheduler)

Run a one-click backup anytime:
```powershell
.\venv\Scripts\python.exe backup_db.py
```

Or register a daily 9:00 PM Windows Scheduled Task:
```powershell
schtasks /Create /SC DAILY /TN "DOD_Order_DB_Backup" /TR "\"D:\ORDER project\venv\Scripts\python.exe\" \"D:\ORDER project\backup_db.py\"" /ST 21:00 /F
```

## Running Tests

```powershell
.\venv\Scripts\python.exe -m pytest -v
```
