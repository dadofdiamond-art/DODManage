"""SQLite-backed authentication and admin user management helpers."""

from __future__ import annotations

import os
import sqlite3
from functools import wraps
from typing import Any

from flask import abort, current_app, has_app_context, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_path


def _resolve_db_path(db_path: str | None = None) -> str:
    """Resolve SQLite database path from explicit arg, Flask config, or default."""
    if db_path:
        return db_path
    if has_app_context() and current_app.config.get("DB_PATH"):
        return str(current_app.config["DB_PATH"])
    return get_db_path()


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory enabled."""
    resolved = _resolve_db_path(db_path)
    parent = os.path.dirname(resolved)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(resolved, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_auth_tables(db_path: str | None = None) -> None:
    """Create the users table and bootstrap a default admin account if none exists."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        admin_username = os.environ.get("ADMIN_USERNAME", "dodadmin").strip()
        admin_password = os.environ.get("ADMIN_PASSWORD", "Dod@130726")

        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()

        if not existing_admin and admin_username and admin_password:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                (admin_username, generate_password_hash(admin_password)),
            )
        conn.commit()


def verify_user(username: str, password: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Verify username and password; return user dict on success or None."""
    clean_username = (username or "").strip()
    if not clean_username or not password:
        return None
    with get_db_connection(db_path) as conn:
        user = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (clean_username,),
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            return dict(user)
    return None


def create_standard_user(
    username: str, password: str, db_path: str | None = None
) -> tuple[bool, str]:
    """Create a new standard user account (role='user')."""
    clean_username = (username or "").strip()
    if len(clean_username) < 3 or len(password or "") < 6:
        return False, "Username must be at least 3 characters and password at least 6 characters."

    try:
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
                (clean_username, generate_password_hash(password)),
            )
            conn.commit()
        return True, f"User '{clean_username}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{clean_username}' already exists."


def list_users(db_path: str | None = None) -> list[dict[str, Any]]:
    """Return all user accounts ordered by ID."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def login_required(view_func):
    """Redirect unauthenticated visitors to the login page."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    """Require an authenticated user with role == 'admin' (403 otherwise)."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped
