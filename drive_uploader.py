"""Google Drive API uploader and backup helper for Dad Of Diamond."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from typing import Any

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
SCOPES = ["https://www.googleapis.com/auth/drive"]

DEFAULT_CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
DEFAULT_SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "service_account.json")
DEFAULT_TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


def _resolve_credential_paths(
    credentials_path: str | None = None,
    token_path: str | None = None,
    service_account_path: str | None = None,
) -> tuple[str, str, str]:
    """Return resolved paths for OAuth credentials, token, and service account JSON."""
    cred_path = credentials_path or os.environ.get("GOOGLE_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH)
    tok_path = token_path or os.environ.get("GOOGLE_TOKEN_PATH", DEFAULT_TOKEN_PATH)
    sa_path = service_account_path or os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH", DEFAULT_SERVICE_ACCOUNT_PATH)
    return cred_path, tok_path, sa_path


def _is_service_account_file(path: str) -> bool:
    """Detect whether a JSON credential file is a Google Service Account key."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("type") == "service_account"
    except (OSError, json.JSONDecodeError):
        return False


def get_drive_status(
    credentials_path: str | None = None,
    token_path: str | None = None,
    service_account_path: str | None = None,
) -> dict[str, Any]:
    """Return diagnostic status about whether Google Drive credentials are present."""
    cred_path, tok_path, sa_path = _resolve_credential_paths(
        credentials_path, token_path, service_account_path
    )
    if os.path.isfile(sa_path) and _is_service_account_file(sa_path):
        return {"configured": True, "mode": "service_account", "credential_file": sa_path}
    if os.path.isfile(cred_path):
        mode = "service_account" if _is_service_account_file(cred_path) else "oauth2"
        return {
            "configured": True,
            "mode": mode,
            "credential_file": cred_path,
            "token_cached": os.path.isfile(tok_path),
        }
    return {
        "configured": False,
        "mode": "local_only",
        "message": "credentials.json or service_account.json not found. Media will be stored locally until Google Drive is configured.",
    }


def get_drive_service(
    credentials_path: str | None = None,
    token_path: str | None = None,
    service_account_path: str | None = None,
):
    """Build an authenticated Google Drive v3 service client."""
    cred_path, tok_path, sa_path = _resolve_credential_paths(
        credentials_path, token_path, service_account_path
    )

    if os.path.isfile(sa_path) and _is_service_account_file(sa_path):
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    if os.path.isfile(cred_path) and _is_service_account_file(cred_path):
        creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    if not os.path.isfile(cred_path):
        raise FileNotFoundError(
            f"Google Drive credentials not found at '{cred_path}'. "
            "Place your OAuth 2.0 credentials.json or service_account.json in the project root."
        )

    creds: Credentials | None = None
    if os.path.isfile(tok_path):
        creds = Credentials.from_authorized_user_file(tok_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(tok_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def get_or_create_folder(service: Any, folder_name: str, parent_id: str | None = None) -> str:
    """Find an existing non-trashed folder by name or create it, returning its Drive ID."""
    escaped_name = _escape_drive_query(folder_name)
    query_parts = [
        f"name = '{escaped_name}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
    ]
    if parent_id:
        query_parts.append(f"'{_escape_drive_query(parent_id)}' in parents")

    response = (
        service.files()
        .list(
            q=" and ".join(query_parts),
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = response.get("files", [])
    if files:
        return files[0]["id"]

    metadata: dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    created = (
        service.files()
        .create(body=metadata, fields="id", supportsAllDrives=True)
        .execute()
    )
    return created["id"]


MIME_OVERRIDES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}


def upload_file_to_folder(
    service: Any,
    local_path: str,
    folder_id: str,
    filename: str | None = None,
    make_public: bool = True,
) -> dict[str, str]:
    """Upload a single file into a Drive folder and optionally set public read permission."""
    target_name = filename or os.path.basename(local_path)
    ext = os.path.splitext(target_name)[1].lower()
    mime_type = MIME_OVERRIDES.get(ext) or mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    metadata = {"name": target_name, "parents": [folder_id]}

    uploaded = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    file_id = uploaded["id"]

    if make_public:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        ).execute()
        refreshed = (
            service.files()
            .get(fileId=file_id, fields="id, webViewLink, webContentLink", supportsAllDrives=True)
            .execute()
        )
        web_view_link = refreshed.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
    else:
        web_view_link = uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"

    return {
        "drive_file_id": file_id,
        "drive_view_link": web_view_link,
    }


def upload_order_media(
    order_id: str,
    file_entries: list[dict[str, str]],
    root_folder_id: str | None = None,
    root_folder_name: str | None = None,
    service: Any | None = None,
) -> list[dict[str, Any]]:
    """Create an Order ID subfolder in Drive, upload media, and return shareable view links."""
    if not file_entries:
        return []

    drive_service = service or get_drive_service()
    effective_root_id = root_folder_id or os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID") or None
    effective_root_name = root_folder_name or os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_NAME", "DOD_Order_Media")

    if not effective_root_id:
        effective_root_id = get_or_create_folder(drive_service, effective_root_name)

    order_folder_id = get_or_create_folder(drive_service, order_id, parent_id=effective_root_id)

    uploaded_results: list[dict[str, Any]] = []
    for entry in file_entries:
        local_path = entry["local_temp_path"]
        media_type = entry["media_type"]
        filename = entry.get("filename") or os.path.basename(local_path)
        upload_info = upload_file_to_folder(
            drive_service,
            local_path=local_path,
            folder_id=order_folder_id,
            filename=filename,
            make_public=True,
        )
        uploaded_results.append(
            {
                "media_type": media_type,
                "local_temp_path": local_path,
                "drive_file_id": upload_info["drive_file_id"],
                "drive_view_link": upload_info["drive_view_link"],
            }
        )

    return uploaded_results


def upload_backup_file(
    local_db_path: str,
    backup_filename: str | None = None,
    backup_folder_id: str | None = None,
    backup_folder_name: str = "DOD_DB_Backups",
    service: Any | None = None,
) -> dict[str, str]:
    """Upload orders.db backup to a private Google Drive folder (never public)."""
    drive_service = service or get_drive_service()
    target_folder_id = backup_folder_id or os.environ.get("GOOGLE_DRIVE_BACKUP_FOLDER_ID") or None
    if not target_folder_id:
        target_folder_id = get_or_create_folder(drive_service, backup_folder_name)

    return upload_file_to_folder(
        drive_service,
        local_path=local_db_path,
        folder_id=target_folder_id,
        filename=backup_filename or os.path.basename(local_db_path),
        make_public=False,
    )


def _collect_media_entries(paths: list[str]) -> list[dict[str, str]]:
    """Build upload entries from a list of local file paths."""
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    entries: list[dict[str, str]] = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        entries.append(
            {
                "local_temp_path": os.path.abspath(path),
                "media_type": "image" if ext in image_exts else "video",
                "filename": os.path.basename(path),
            }
        )
    return entries


def _interactive_upload() -> None:
    """Interactive prompt workflow for standalone `python drive_uploader.py`."""
    print("\n===== DOD GOOGLE DRIVE UPLOADER =====\n")
    service = get_drive_service()
    order_id = input("Enter Order ID: ").strip()
    if not order_id:
        print("ERROR: Order ID is required.")
        return

    media_folder = input("Enter the full path of your media folder: ").strip().strip('"')
    if not os.path.isdir(media_folder):
        print("ERROR: Media folder not found.")
        return

    file_paths = [
        os.path.join(media_folder, name)
        for name in sorted(os.listdir(media_folder))
        if os.path.isfile(os.path.join(media_folder, name))
    ]
    entries = _collect_media_entries(file_paths)
    if not entries:
        print("ERROR: No files found inside the media folder.")
        return

    results = upload_order_media(order_id, entries, service=service)
    print("\n===== UPLOAD COMPLETE =====\n")
    print("Order ID:", order_id)
    print("\nUploaded file links:")
    for item in results:
        print(item["drive_view_link"])
    print("\nDone!")


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Dad Of Diamond Google Drive Uploader CLI")
    parser.add_argument("--auth", action="store_true", help="Authenticate and cache token.json")
    parser.add_argument("--order-id", help="Order ID subfolder name")
    parser.add_argument("--files", nargs="*", default=[], help="Paths to image/video files to upload")
    parser.add_argument("--root-folder-id", help="Optional target Google Drive root folder ID")
    args = parser.parse_args()

    if args.auth:
        get_drive_service()
        print("Google Drive authentication succeeded.")
        return

    if not args.order_id and not args.files:
        _interactive_upload()
        return

    if not args.order_id or not args.files:
        parser.error("Provide --auth, run with no arguments for interactive mode, or pass both --order-id and --files.")

    entries = _collect_media_entries(args.files)
    results = upload_order_media(args.order_id, entries, root_folder_id=args.root_folder_id)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    _cli()
