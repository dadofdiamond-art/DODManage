"""Daily SQLite backup utility for Dad Of Diamond (local snapshot + private Google Drive)."""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

from database import get_db_path
from drive_uploader import get_drive_status, upload_backup_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BACKUP_DIR = os.path.join(BASE_DIR, "backups")

load_dotenv(os.path.join(BASE_DIR, ".env"))


def create_local_backup(db_path: str | None = None, backup_dir: str | None = None) -> str:
    """Create a consistent SQLite hot backup snapshot in backups/."""
    source_path = get_db_path(db_path)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Database file not found at '{source_path}'.")

    target_dir = backup_dir or DEFAULT_BACKUP_DIR
    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(target_dir, f"orders_backup_{timestamp}.db")

    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(dest_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    return dest_path


def run_backup(upload_to_drive: bool = True) -> dict[str, str | None]:
    """Run local SQLite backup and optionally upload it to a private Drive folder."""
    local_backup = create_local_backup()
    result: dict[str, str | None] = {
        "local_backup_path": local_backup,
        "drive_file_id": None,
        "drive_view_link": None,
    }

    if upload_to_drive:
        status = get_drive_status()
        if status.get("configured"):
            uploaded = upload_backup_file(local_backup)
            result["drive_file_id"] = uploaded["drive_file_id"]
            result["drive_view_link"] = uploaded["drive_view_link"]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up orders.db locally and to Google Drive.")
    parser.add_argument("--local-only", action="store_true", help="Skip Google Drive upload.")
    args = parser.parse_args()

    outcome = run_backup(upload_to_drive=not args.local_only)
    print(f"Local backup created: {outcome['local_backup_path']}")
    if outcome["drive_file_id"]:
        print(f"Uploaded to private Drive folder (file ID: {outcome['drive_file_id']})")
    elif not args.local_only:
        print("Google Drive not configured; skipped remote upload.")


if __name__ == "__main__":
    main()
