"""SQLite database layer for Dad Of Diamond order management."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "orders.db")


def get_db_path(db_path: str | None = None) -> str:
    """Resolve the active SQLite database path."""
    if db_path:
        return db_path
    return os.environ.get("DOD_DB_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(get_db_path(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_columns(conn: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    """Safely add missing columns to an existing SQLite table."""
    existing = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for col_name, col_type in columns.items():
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")


def init_db(db_path: str | None = None) -> str:
    """Initialize orders.db with the three relational tables and indexes."""
    resolved_path = get_db_path(db_path)
    parent = os.path.dirname(resolved_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with get_connection(resolved_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY CHECK(length(order_id) <= 15),
                customer_name TEXT NOT NULL,
                mobile_number TEXT,
                email TEXT,
                living_address TEXT,
                dispatch_date DATE,
                order_placing_date DATE,
                factory_receiving_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                product_type TEXT NOT NULL,
                product_sku TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                metal_option TEXT NOT NULL,
                metal_tone TEXT NOT NULL,
                band_tone TEXT,
                prong_tone TEXT,
                basket_tone TEXT,
                cad_image_no TEXT,
                size_or_closure TEXT NOT NULL,
                engraving TEXT,
                side_engraving TEXT,
                special_requirements TEXT,
                stone_details_json TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS order_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                media_type TEXT NOT NULL CHECK(media_type IN ('image', 'video')),
                local_temp_path TEXT,
                drive_file_id TEXT,
                drive_view_link TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_sku ON order_items(product_sku);
            CREATE INDEX IF NOT EXISTS idx_order_media_order_id ON order_media(order_id);
            CREATE INDEX IF NOT EXISTS idx_orders_customer_name ON orders(customer_name);
            """
        )
        _ensure_columns(
            conn,
            "orders",
            {
                "order_placing_date": "DATE",
                "factory_receiving_date": "DATE",
            },
        )
        _ensure_columns(
            conn,
            "order_items",
            {
                "band_tone": "TEXT",
                "prong_tone": "TEXT",
                "basket_tone": "TEXT",
                "cad_image_no": "TEXT",
                "side_engraving": "TEXT",
            },
        )
    return resolved_path


def order_exists(order_id: str, db_path: str | None = None) -> bool:
    """Return True if an order with the given Order ID (case-insensitive) exists."""
    cleaned = (order_id or "").strip()
    if not cleaned:
        return False
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM orders WHERE LOWER(order_id) = LOWER(?) LIMIT 1",
            (cleaned,),
        ).fetchone()
        return row is not None


def save_order(
    order_data: dict[str, Any],
    item_data: dict[str, Any],
    media_list: list[dict[str, Any]] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Save a complete order, its item specs, and its media records atomically."""
    init_db(db_path)
    media_list = media_list or []

    stones = item_data.get("stone_details", [])
    if isinstance(stones, str):
        stone_details_json = stones
    else:
        stone_details_json = json.dumps(stones, ensure_ascii=False)

    order_id = str(order_data["order_id"]).strip()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO orders (
                order_id, customer_name, mobile_number, email, living_address,
                dispatch_date, order_placing_date, factory_receiving_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                str(order_data["customer_name"]).strip(),
                (order_data.get("mobile_number") or "").strip() or None,
                (order_data.get("email") or "").strip() or None,
                (order_data.get("living_address") or "").strip() or None,
                (order_data.get("dispatch_date") or "").strip() or None,
                (order_data.get("order_placing_date") or "").strip() or None,
                (order_data.get("factory_receiving_date") or "").strip() or None,
            ),
        )

        conn.execute(
            """
            INSERT INTO order_items (
                order_id, product_type, product_sku, quantity,
                metal_option, metal_tone, band_tone, prong_tone, basket_tone, cad_image_no,
                size_or_closure, engraving, side_engraving, special_requirements, stone_details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                str(item_data["product_type"]).strip(),
                str(item_data["product_sku"]).strip(),
                int(item_data.get("quantity", 1)),
                str(item_data["metal_option"]).strip(),
                str(item_data["metal_tone"]).strip(),
                (item_data.get("band_tone") or "").strip() or None,
                (item_data.get("prong_tone") or "").strip() or None,
                (item_data.get("basket_tone") or "").strip() or None,
                (item_data.get("cad_image_no") or "").strip() or None,
                str(item_data["size_or_closure"]).strip(),
                (item_data.get("engraving") or "").strip() or None,
                (item_data.get("side_engraving") or "").strip() or None,
                (item_data.get("special_requirements") or "").strip() or None,
                stone_details_json,
            ),
        )

        for media in media_list:
            conn.execute(
                """
                INSERT INTO order_media (
                    order_id, media_type, local_temp_path, drive_file_id, drive_view_link
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    media["media_type"],
                    media.get("local_temp_path"),
                    media.get("drive_file_id"),
                    media.get("drive_view_link"),
                ),
            )

    saved = get_order_by_id(order_id, db_path=db_path)
    if saved is None:
        raise RuntimeError(f"Failed to retrieve newly saved order '{order_id}'.")
    return saved


def _parse_stones(raw_json: str | None) -> list[dict[str, Any]]:
    """Safely parse stone_details_json into a list of stone dictionaries."""
    if not raw_json:
        return []
    try:
        parsed = json.loads(raw_json)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def get_order_by_id(order_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Retrieve full order record (including local customer details, items, and media)."""
    cleaned = (order_id or "").strip()
    if not cleaned:
        return None

    with get_connection(db_path) as conn:
        order_row = conn.execute(
            """
            SELECT order_id, customer_name, mobile_number, email, living_address,
                   dispatch_date, order_placing_date, factory_receiving_date, created_at
            FROM orders
            WHERE LOWER(order_id) = LOWER(?)
            LIMIT 1
            """,
            (cleaned,),
        ).fetchone()
        if order_row is None:
            return None

        canonical_id = order_row["order_id"]

        item_rows = conn.execute(
            """
            SELECT id, order_id, product_type, product_sku, quantity,
                   metal_option, metal_tone, band_tone, prong_tone, basket_tone, cad_image_no,
                   size_or_closure, engraving, side_engraving, special_requirements, stone_details_json
            FROM order_items
            WHERE order_id = ?
            ORDER BY id ASC
            """,
            (canonical_id,),
        ).fetchall()

        media_rows = conn.execute(
            """
            SELECT id, order_id, media_type, local_temp_path, drive_file_id, drive_view_link
            FROM order_media
            WHERE order_id = ?
            ORDER BY id ASC
            """,
            (canonical_id,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in item_rows:
        item_dict = dict(row)
        item_dict["stone_details"] = _parse_stones(item_dict.get("stone_details_json"))
        items.append(item_dict)

    media = [dict(row) for row in media_rows]
    images = [m for m in media if m["media_type"] == "image"]
    videos = [m for m in media if m["media_type"] == "video"]

    result = dict(order_row)
    result["created_at"] = str(result["created_at"]) if result.get("created_at") else None
    result["dispatch_date"] = str(result["dispatch_date"]) if result.get("dispatch_date") else None
    result["order_placing_date"] = (
        str(result["order_placing_date"]) if result.get("order_placing_date") else None
    )
    result["factory_receiving_date"] = (
        str(result["factory_receiving_date"]) if result.get("factory_receiving_date") else None
    )
    result["items"] = items
    result["item"] = items[0] if items else None
    result["media"] = media
    result["images"] = images
    result["videos"] = videos
    return result


def get_workshop_order_by_id(order_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Return strictly non-PII order fields for workshop/karigar PDF generation."""
    full_order = get_order_by_id(order_id, db_path=db_path)
    if full_order is None:
        return None

    return {
        "order_id": full_order["order_id"],
        "customer_name": full_order["customer_name"],
        "dispatch_date": full_order["dispatch_date"],
        "order_placing_date": full_order["order_placing_date"],
        "factory_receiving_date": full_order["factory_receiving_date"],
        "product_sku": full_order["item"].get("product_sku", ""),
        "created_at": full_order["created_at"],
        "items": full_order["items"],
        "item": full_order["item"],
        "media": full_order["media"],
        "images": full_order["images"],
        "videos": full_order["videos"],
    }


def update_order(
    order_id: str,
    order_data: dict[str, Any],
    item_data: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any] | None:
    """Update an existing order and its primary item specification atomically."""
    existing = get_order_by_id(order_id, db_path=db_path)
    if existing is None:
        return None

    canonical_id = existing["order_id"]
    stones = item_data.get("stone_details", [])
    if isinstance(stones, str):
        stone_details_json = stones
    else:
        stone_details_json = json.dumps(stones, ensure_ascii=False)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE orders
            SET customer_name = ?,
                mobile_number = ?,
                email = ?,
                living_address = ?,
                dispatch_date = ?,
                order_placing_date = ?,
                factory_receiving_date = ?
            WHERE order_id = ?
            """,
            (
                str(order_data["customer_name"]).strip(),
                (order_data.get("mobile_number") or "").strip() or None,
                (order_data.get("email") or "").strip() or None,
                (order_data.get("living_address") or "").strip() or None,
                (order_data.get("dispatch_date") or "").strip() or None,
                (order_data.get("order_placing_date") or "").strip() or None,
                (order_data.get("factory_receiving_date") or "").strip() or None,
                canonical_id,
            ),
        )

        conn.execute(
            """
            UPDATE order_items
            SET product_type = ?,
                product_sku = ?,
                quantity = ?,
                metal_option = ?,
                metal_tone = ?,
                band_tone = ?,
                prong_tone = ?,
                basket_tone = ?,
                cad_image_no = ?,
                size_or_closure = ?,
                engraving = ?,
                side_engraving = ?,
                special_requirements = ?,
                stone_details_json = ?
            WHERE order_id = ?
            """,
            (
                str(item_data["product_type"]).strip(),
                str(item_data["product_sku"]).strip(),
                int(item_data.get("quantity", 1)),
                str(item_data["metal_option"]).strip(),
                str(item_data["metal_tone"]).strip(),
                (item_data.get("band_tone") or "").strip() or None,
                (item_data.get("prong_tone") or "").strip() or None,
                (item_data.get("basket_tone") or "").strip() or None,
                (item_data.get("cad_image_no") or "").strip() or None,
                str(item_data["size_or_closure"]).strip(),
                (item_data.get("engraving") or "").strip() or None,
                (item_data.get("side_engraving") or "").strip() or None,
                (item_data.get("special_requirements") or "").strip() or None,
                stone_details_json,
                canonical_id,
            ),
        )

    return get_order_by_id(canonical_id, db_path=db_path)


def list_all_orders(search_query: str | None = None, db_path: str | None = None) -> list[dict[str, Any]]:
    """List orders for the history dashboard, optionally filtering by Order ID, SKU, or Customer Name."""
    init_db(db_path)
    query = (search_query or "").strip()

    base_sql = """
        SELECT
            o.order_id,
            o.customer_name,
            o.mobile_number,
            o.email,
            o.living_address,
            o.dispatch_date,
            o.order_placing_date,
            o.factory_receiving_date,
            o.created_at,
            oi.product_type,
            oi.product_sku,
            oi.quantity,
            oi.metal_option,
            oi.metal_tone,
            oi.band_tone,
            oi.prong_tone,
            oi.basket_tone,
            oi.cad_image_no,
            oi.size_or_closure,
            oi.engraving,
            oi.side_engraving,
            oi.special_requirements,
            oi.stone_details_json,
            COALESCE(SUM(CASE WHEN om.media_type = 'image' THEN 1 ELSE 0 END), 0) AS image_count,
            COALESCE(SUM(CASE WHEN om.media_type = 'video' THEN 1 ELSE 0 END), 0) AS video_count
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        LEFT JOIN order_media om ON om.order_id = o.order_id
    """

    params: tuple[Any, ...] = ()
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like_term = f"%{escaped}%"
        base_sql += """
            WHERE (
                o.order_id LIKE ? ESCAPE '\\'
                OR o.customer_name LIKE ? ESCAPE '\\'
                OR COALESCE(oi.product_sku, '') LIKE ? ESCAPE '\\'
            )
        """
        params = (like_term, like_term, like_term)

    base_sql += """
        GROUP BY o.order_id, oi.id
        ORDER BY o.created_at DESC, o.rowid DESC
    """

    with get_connection(db_path) as conn:
        rows = conn.execute(base_sql, params).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        record["created_at"] = str(record["created_at"]) if record.get("created_at") else None
        record["dispatch_date"] = str(record["dispatch_date"]) if record.get("dispatch_date") else None
        record["stone_details"] = _parse_stones(record.get("stone_details_json"))
        results.append(record)
    return results


def delete_order(order_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Delete an order (and cascading items/media) by Order ID; return deleted record or None."""
    existing = get_order_by_id(order_id, db_path=db_path)
    if existing is None:
        return None

    with get_connection(db_path) as conn:
        conn.execute(
            "DELETE FROM orders WHERE order_id = ?",
            (existing["order_id"],),
        )
    return existing
