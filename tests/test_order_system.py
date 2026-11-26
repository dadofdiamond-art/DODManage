"""Comprehensive test suite for Dad Of Diamond Order & Workshop Sheet System."""

from __future__ import annotations

import io
import json
import os
import sqlite3
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app import create_app
from backup_db import create_local_backup
from database import (
    delete_order,
    get_order_by_id,
    get_workshop_order_by_id,
    init_db,
    list_all_orders,
    order_exists,
    save_order,
)
from drive_uploader import upload_order_media
from pdf_generator import render_workshop_html


def _make_png_bytes(color: tuple[int, int, int] = (63, 7, 12)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (320, 240), color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.get_drive_status", lambda: {"configured": False, "mode": "local_only"})
    db_path = str(tmp_path / "test_orders.db")
    upload_dir = str(tmp_path / "uploads")
    pdf_dir = str(tmp_path / "generated_pdfs")
    app = create_app(
        {
            "TESTING": True,
            "DB_PATH": db_path,
            "UPLOAD_DIR": upload_dir,
            "PDF_DIR": pdf_dir,
            "MAX_VIDEO_SIZE_MB": 5,
        }
    )
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"
        yield client, app, db_path, pdf_dir


def test_database_crud_and_pii_boundary(tmp_path):
    db_path = str(tmp_path / "orders.db")
    init_db(db_path)

    save_order(
        order_data={
            "order_id": "DOD1001",
            "customer_name": "Ananya Sharma",
            "mobile_number": None,  # Missing optional mobile number
            "email": "ananya@example.com",
            "living_address": "42 Marine Drive, Mumbai",
            "dispatch_date": "2026-12-10",
        },
        item_data={
            "product_type": "Ring",
            "product_sku": "DOD-SOL-01",
            "quantity": 1,
            "metal_option": "18K Solid Gold",
            "metal_tone": "Yellow",
            "size_or_closure": "US 6.25",
            "engraving": "A ♥ R & Forever <3",
            "special_requirements": "Hidden halo with cathedral prongs",
            "stone_details": [
                {
                    "stone_type": "Lab Diamond",
                    "shape": "Oval",
                    "size_mm": "9.5 x 6.8",
                    "carat_weight": "2.20 ct",
                    "color": "E",
                }
            ],
        },
        media_list=[],
        db_path=db_path,
    )

    assert order_exists("DOD1001", db_path=db_path) is True
    assert order_exists("dod1001", db_path=db_path) is True

    full = get_order_by_id("DOD1001", db_path=db_path)
    assert full is not None
    assert full["customer_name"] == "Ananya Sharma"
    assert full["mobile_number"] is None
    assert len(full["item"]["stone_details"]) == 1

    workshop = get_workshop_order_by_id("DOD1001", db_path=db_path)
    assert workshop is not None
    for pii_key in ("mobile_number", "email", "living_address"):
        assert pii_key not in workshop

    html = render_workshop_html(workshop)
    assert "DOD1001" in html
    assert "DOD-SOL-01" in html
    assert "2026-12-10" in html
    assert "Ananya Sharma" in html
    assert "ananya@example.com" not in html
    assert "42 Marine Drive, Mumbai" not in html
    assert "Clarity / Cert" not in html
    assert "A ♥ R &amp; Forever &lt;3" in html


def test_create_order_zero_media_and_missing_mobile_generates_pdf(app_client):
    client, _app, _db_path, pdf_dir = app_client

    resp = client.post(
        "/api/orders",
        data={
            "order_id": "DOD2026ZERO",
            "customer_name": "Rohan Kapoor",
            "mobile_number": "",
            "email": "rohan@private.test",
            "living_address": "18 Park Street, Kolkata",
            "dispatch_date": "2026-12-15",
            "product_type": "Earrings",
            "product_sku": "DOD-EAR-99",
            "quantity": "2",
            "metal_option": "14K Solid Gold",
            "metal_tone": "Rose",
            "size_or_closure": "La Poussette",
            "engraving": "",
            "special_requirements": "Mirror polish",
            "stone_details_json": json.dumps([]),
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 201
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["order_id"] == "DOD2026ZERO"

    expected_pdf = os.path.join(pdf_dir, "DOD2026ZERO_job_sheet.pdf")
    assert os.path.isfile(expected_pdf)
    with open(expected_pdf, "rb") as fh:
        assert fh.read(5) == b"%PDF-"

    dl_resp = client.get("/orders/DOD2026ZERO/pdf")
    assert dl_resp.status_code == 200
    assert dl_resp.mimetype == "application/pdf"


def test_create_order_ten_images_and_two_videos_multipage_pdf(app_client, monkeypatch):
    client, _app, db_path, pdf_dir = app_client

    # Simulate configured Google Drive returning shareable links for 10 images + 2 videos
    monkeypatch.setattr(
        "app.get_drive_status",
        lambda: {"configured": True, "mode": "oauth2"},
    )

    def fake_upload_order_media(order_id, entries, **_kwargs):
        return [
            {
                "media_type": e["media_type"],
                "local_temp_path": e["local_temp_path"],
                "drive_file_id": f"drv_{idx}",
                "drive_view_link": f"https://drive.google.com/file/d/drv_{idx}/view",
            }
            for idx, e in enumerate(entries, start=1)
        ]

    monkeypatch.setattr("app.upload_order_media", fake_upload_order_media)

    png_bytes = _make_png_bytes()
    images = [(io.BytesIO(png_bytes), f"ref_{i}.png") for i in range(1, 11)]
    videos = [
        (io.BytesIO(b"\x00\x00\x00\x18ftypmp42" + b"0" * 1024), "spin_1.mp4"),
        (io.BytesIO(b"\x00\x00\x00\x18ftypqt  " + b"0" * 1024), "hand_2.mov"),
    ]

    stones = [
        {
            "stone_type": "Lab Diamond",
            "shape": "Oval",
            "size_mm": "10.0 x 7.0",
            "carat_weight": "2.50 ct",
            "color": "D",
            "clarity_cert": "VVS1 / IGI",
        },
        {
            "stone_type": "Natural",
            "shape": "Round",
            "size_mm": "1.2",
            "carat_weight": "0.35 ct total",
            "color": "E-F",
            "quantity": "24",
        },
    ]

    data = {
        "order_id": "DOD10IMG2VID",
        "customer_name": "Secret VIP Client",
        "mobile_number": "+919999988888",
        "email": "vip@secret.example",
        "living_address": "999 Confidential Villa",
        "dispatch_date": "2026-12-20",
        "product_type": "Ring",
        "product_sku": "DOD-HALO-10",
        "quantity": "1",
        "metal_option": "950 Platinum",
        "metal_tone": "White",
        "size_or_closure": "US 6.75",
        "engraving": 'Dad Of Diamond "2026" & ♥',
        "special_requirements": "Low profile basket; pave 3/4 eternity",
        "stone_details_json": json.dumps(stones),
        "images": images,
        "videos": videos,
    }

    resp = client.post("/api/orders", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    payload = resp.get_json()
    assert payload["drive_uploaded"] is True

    saved = get_order_by_id("DOD10IMG2VID", db_path=db_path)
    assert len(saved["images"]) == 10
    assert len(saved["videos"]) == 2
    assert all(img["drive_view_link"].startswith("https://drive.google.com/") for img in saved["images"])
    assert all(vid["drive_view_link"].startswith("https://drive.google.com/") for vid in saved["videos"])

    workshop = get_workshop_order_by_id("DOD10IMG2VID", db_path=db_path)
    html = render_workshop_html(workshop)
    assert "DOD10IMG2VID" in html
    assert "DOD-HALO-10" in html
    assert "2026-12-20" in html
    assert "Secret VIP Client" in html
    assert "+919999988888" not in html
    assert "vip@secret.example" not in html
    assert "999 Confidential Villa" not in html
    assert "data:image/png;base64," in html  # QR codes + embedded image previews
    assert "<td>24</td>" in html  # Optional diamond quantity rendered when provided

    pdf_path = os.path.join(pdf_dir, "DOD10IMG2VID_job_sheet.pdf")
    assert os.path.isfile(pdf_path)
    assert os.path.getsize(pdf_path) > 15000


def test_validation_rejects_duplicates_and_excess_media(app_client):
    client, _app, _db_path, _pdf_dir = app_client

    # Seed an order
    client.post(
        "/api/orders",
        data={
            "order_id": "DODDUP1",
            "customer_name": "First Customer",
            "product_type": "Pendant",
            "product_sku": "SKU-1",
            "quantity": "1",
            "metal_option": "10K Solid Gold",
            "metal_tone": "Gold",
            "size_or_closure": '18" Chain',
        },
        content_type="multipart/form-data",
    )

    # Check duplicate endpoint
    chk = client.get("/api/check-order-id/doddup1").get_json()
    assert chk["available"] is False
    assert chk["exists"] is True

    # Reject duplicate, >15 char ID, 11 images, 3 videos
    png_bytes = _make_png_bytes()
    resp = client.post(
        "/api/orders",
        data={
            "order_id": "DODDUP1",
            "customer_name": "Second Customer",
            "product_type": "Ring",
            "product_sku": "SKU-2",
            "quantity": "1",
            "metal_option": "14K Solid Gold",
            "metal_tone": "White",
            "size_or_closure": "US 7",
            "images": [(io.BytesIO(png_bytes), f"i{i}.png") for i in range(11)],
            "videos": [(io.BytesIO(b"vid"), f"v{i}.mp4") for i in range(3)],
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    errs = " ".join(resp.get_json()["errors"])
    assert "already exists" in errs
    assert "Maximum 10 images" in errs
    assert "Maximum 2 videos" in errs

    # Reject non-alphanumeric or >15 char order ID
    bad_id = client.get("/api/check-order-id/INVALID-ID-TOO-LONG").get_json()
    assert bad_id["valid_format"] is False
    assert bad_id["available"] is False


def test_search_orders_by_id_sku_and_customer(app_client):
    client, _app, _db_path, _pdf_dir = app_client

    for oid, cname, sku in [
        ("DODSRCH1", "Meera Patel", "RG-OVAL-101"),
        ("DODSRCH2", "Kabir Mehta", "BR-TENNIS-202"),
    ]:
        resp = client.post(
            "/api/orders",
            data={
                "order_id": oid,
                "customer_name": cname,
                "product_type": "Ring",
                "product_sku": sku,
                "quantity": "1",
                "metal_option": "18K Solid Gold",
                "metal_tone": "White",
                "size_or_closure": "US 6",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201

    assert client.get("/api/orders?q=DODSRCH1").get_json()["count"] == 1
    assert client.get("/api/orders?q=TENNIS").get_json()["count"] == 1
    assert client.get("/api/orders?q=Meera").get_json()["count"] == 1
    assert client.get("/api/orders?q=").get_json()["count"] == 2


def test_shape_options_and_delete_order_cleanup(app_client):
    client, app, db_path, pdf_dir = app_client

    home_html = client.get("/").get_data(as_text=True)
    for shape in (
        "Marquise",
        "Round",
        "Pear",
        "Oval",
        "Emerald",
        "Radiant",
        "Heart",
        "Asscher",
        "Cushion",
        "Custom shape",
    ):
        assert shape in home_html
    assert "Vermeil" in home_html
    assert "Custom Metal" in home_html
    assert "Clarity / Cert" not in home_html

    png_bytes = _make_png_bytes()
    create_resp = client.post(
        "/api/orders",
        data={
            "order_id": "DODDEL99",
            "customer_name": "Delete Me",
            "product_type": "Engagement Ring",
            "product_sku": "RG-DEL-99",
            "quantity": "1",
            "metal_option": "14K Solid Gold",
            "metal_tone": "Yellow",
            "size_or_closure": "US 6.5",
            "stone_details_json": json.dumps(
                [
                    {
                        "stone_type": "Lab Diamond",
                        "shape": "Asscher",
                        "size_mm": "7.0 x 7.0",
                        "carat_weight": "1.80 ct",
                        "color": "F",
                    }
                ]
            ),
            "images": [(io.BytesIO(png_bytes), "ring.png")],
        },
        content_type="multipart/form-data",
    )
    assert create_resp.status_code == 201
    assert order_exists("DODDEL99", db_path=db_path) is True

    pdf_file = os.path.join(pdf_dir, "DODDEL99_job_sheet.pdf")
    upload_dir = os.path.join(app.config["UPLOAD_DIR"], "DODDEL99")
    assert os.path.isfile(pdf_file)
    assert os.path.isdir(upload_dir)

    del_resp = client.delete("/api/orders/DODDEL99")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["ok"] is True
    assert order_exists("DODDEL99", db_path=db_path) is False
    assert not os.path.isfile(pdf_file)
    assert not os.path.isdir(upload_dir)

    missing_del = client.delete("/api/orders/DODDEL99")
    assert missing_del.status_code == 404

    # Bulk delete stored entries
    for oid in ("DODBULK1", "DODBULK2"):
        r = client.post(
            "/api/orders",
            data={
                "order_id": oid,
                "customer_name": f"Client {oid}",
                "product_type": "Bracelet",
                "product_sku": f"SKU-{oid}",
                "quantity": "1",
                "metal_option": "Vermeil",
                "metal_tone": "Yellow",
                "size_or_closure": '7"',
            },
            content_type="multipart/form-data",
        )
        assert r.status_code == 201

    bulk_resp = client.post(
        "/api/orders/bulk-delete",
        json={"order_ids": ["DODBULK1", "DODBULK2"]},
    )
    assert bulk_resp.status_code == 200
    assert bulk_resp.get_json()["count"] == 2
    assert order_exists("DODBULK1", db_path=db_path) is False
    assert order_exists("DODBULK2", db_path=db_path) is False


def test_drive_uploader_creates_subfolder_and_public_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", raising=False)
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(_make_png_bytes())

    mock_service = MagicMock()
    files_api = mock_service.files.return_value
    perms_api = mock_service.permissions.return_value

    # Root folder lookup -> missing; subfolder lookup -> missing
    files_api.list.return_value.execute.side_effect = [{"files": []}, {"files": []}]
    # Create root folder, create order subfolder, upload file
    files_api.create.return_value.execute.side_effect = [
        {"id": "root_folder_123"},
        {"id": "order_folder_456"},
        {"id": "file_789", "name": "sample.png", "webViewLink": "https://drive.google.com/file/d/file_789/view"},
    ]
    files_api.get.return_value.execute.return_value = {
        "id": "file_789",
        "webViewLink": "https://drive.google.com/file/d/file_789/view",
    }

    results = upload_order_media(
        order_id="DODDRV1",
        file_entries=[
            {
                "media_type": "image",
                "local_temp_path": str(img_path),
                "filename": "sample.png",
            }
        ],
        service=mock_service,
    )

    assert len(results) == 1
    assert results[0]["drive_file_id"] == "file_789"
    assert results[0]["drive_view_link"] == "https://drive.google.com/file/d/file_789/view"
    perms_api.create.assert_called_once_with(
        fileId="file_789",
        body={"type": "anyone", "role": "reader"},
        supportsAllDrives=True,
    )


def test_local_database_backup(tmp_path):
    db_path = str(tmp_path / "orders.db")
    init_db(db_path)
    save_order(
        order_data={"order_id": "DODBAK1", "customer_name": "Backup Test"},
        item_data={
            "product_type": "Pendant",
            "product_sku": "PEN-01",
            "quantity": 1,
            "metal_option": "925 Sterling Silver",
            "metal_tone": "White",
            "size_or_closure": "Pendant Only",
        },
        db_path=db_path,
    )

    backup_dir = str(tmp_path / "backups")
    backup_file = create_local_backup(db_path=db_path, backup_dir=backup_dir)
    assert os.path.isfile(backup_file)

    conn = sqlite3.connect(backup_file)
    count = conn.execute("SELECT COUNT(*) FROM orders WHERE order_id = 'DODBAK1'").fetchone()[0]
    conn.close()
    assert count == 1


def test_auth_login_and_admin_only_user_management(tmp_path, monkeypatch):
    monkeypatch.setattr("app.get_drive_status", lambda: {"configured": False, "mode": "local_only"})
    monkeypatch.setenv("ADMIN_USERNAME", "bossadmin")
    monkeypatch.setenv("ADMIN_PASSWORD", "SecretAdmin123!")

    db_path = str(tmp_path / "auth_orders.db")
    upload_dir = str(tmp_path / "uploads")
    pdf_dir = str(tmp_path / "pdfs")

    app = create_app(
        {
            "TESTING": True,
            "DB_PATH": db_path,
            "UPLOAD_DIR": upload_dir,
            "PDF_DIR": pdf_dir,
        }
    )

    with app.test_client() as client:
        # Unauthenticated visitors are redirected to /login
        for protected_path in ("/", "/orders", "/admin/users"):
            resp = client.get(protected_path)
            assert resp.status_code == 302
            assert "/login" in resp.headers["Location"]

        # Admin login succeeds
        login_resp = client.post(
            "/login",
            data={"username": "bossadmin", "password": "SecretAdmin123!"},
            follow_redirects=True,
        )
        assert login_resp.status_code == 200
        home_html = login_resp.get_data(as_text=True)
        assert "Add Users" in home_html

        # Admin creates a standard user
        create_resp = client.post(
            "/admin/users",
            data={"username": "karigar1", "password": "UserPass123!"},
            follow_redirects=True,
        )
        assert create_resp.status_code == 200
        admin_html = create_resp.get_data(as_text=True)
        assert "karigar1" in admin_html
        assert "created successfully" in admin_html

        # Logout and sign in as standard user
        client.get("/logout")
        user_login = client.post(
            "/login",
            data={"username": "karigar1", "password": "UserPass123!"},
            follow_redirects=True,
        )
        assert user_login.status_code == 200
        user_home = user_login.get_data(as_text=True)
        assert "Add Users" not in user_home

        # Regular user gets 403 Forbidden on /admin/users
        assert client.get("/admin/users").status_code == 403
        assert client.post("/admin/users", data={"username": "x", "password": "y"}).status_code == 403

    # Persistence across app restart
    app_restarted = create_app(
        {
            "TESTING": True,
            "DB_PATH": db_path,
            "UPLOAD_DIR": upload_dir,
            "PDF_DIR": pdf_dir,
        }
    )
    with app_restarted.test_client() as client2:
        r1 = client2.post("/login", data={"username": "bossadmin", "password": "SecretAdmin123!"})
        assert r1.status_code == 302
        client2.get("/logout")
        r2 = client2.post("/login", data={"username": "karigar1", "password": "UserPass123!"})
        assert r2.status_code == 302
