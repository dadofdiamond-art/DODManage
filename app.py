"""Flask web application for Dad Of Diamond Order & Workshop Sheet Management."""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from auth_setup import (
    admin_required,
    create_standard_user,
    delete_user,
    init_auth_tables,
    list_users,
    login_required,
    update_user,
    verify_user,
)
from database import (
    delete_order,
    get_order_by_id,
    get_workshop_order_by_id,
    init_db,
    list_all_orders,
    order_exists,
    save_order,
    update_order,
)
from drive_uploader import get_drive_status, upload_order_media
from pdf_generator import generate_both_order_pdfs, generate_order_pdf, get_pdf_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
MAX_IMAGES = 10
MAX_VIDEOS = 2
DEFAULT_MAX_VIDEO_MB = 200

ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{1,15}$")

METAL_OPTIONS = [
    "925 Sterling Silver",
    "Vermeil",
    "10K Solid Gold",
    "14K Solid Gold",
    "18K Solid Gold",
    "950 Platinum",
    "Custom Metal",
]

SIDE_ENGRAVING_MAP = {
    "925 Sterling Silver": "DOD 925S",
    "10K Solid Gold": "DOD 10KT",
    "14K Solid Gold": "DOD 14KT",
    "18K Solid Gold": "DOD 18KT",
    "950 Platinum": "DOD 950P",
}


def resolve_side_engraving(metal_option: str, explicit_value: str | None = None) -> str:
    """Return the fixed DOD + metal hallmark side engraving."""
    cleaned = (explicit_value or "").strip()
    if cleaned:
        return cleaned
    return SIDE_ENGRAVING_MAP.get((metal_option or "").strip(), "DOD")


def clean_stones_payload(stones: list[Any]) -> list[dict[str, str]]:
    """Normalize stone detail entries including category, clarity, IGI cert, and remarks."""
    cleaned: list[dict[str, str]] = []
    fields = (
        "stone_category",
        "stone_type",
        "shape",
        "size_mm",
        "carat_weight",
        "color",
        "clarity",
        "igi_certificate",
        "quantity",
        "other_remark",
    )
    for s in stones:
        if not isinstance(s, dict):
            continue
        if not any(str(s.get(k) or "").strip() for k in fields[1:]):
            continue
        category = str(s.get("stone_category") or "Center Stone").strip()
        if category not in ("Center Stone", "Side Stone"):
            category = "Center Stone"
        entry = {k: str(s.get(k) or "").strip() for k in fields}
        entry["stone_category"] = category
        cleaned.append(entry)
    return cleaned

METAL_TONES = ["White", "Yellow", "Rose", "Two-Tone"]

PRODUCT_TYPES = [
    "Engagement Ring",
    "Wedding Band",
    "Bracelet",
    "Pendant / Necklace",
    "Earrings",
    "Other (Brooch, Nose Pin, etc.)",
]

STONE_TYPES = ["Lab Diamond", "Moissanite", "Natural", "Gemstone", "Colored Stone"]

STONE_SHAPES = [
    "Marquise",
    "Round",
    "Pear",
    "Oval",
    "Emerald",
    "Radiant",
    "Heart",
    "Asscher",
    "Cushion",
    "E. Cushion",
    "Princess",
    "Baguette",
    "Triangle",
    "Trillion",
    "Tapper",
    "Custom shape",
]


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or "dod-local-workshop-secret"
    )
    app.config["DB_PATH"] = os.environ.get("DOD_DB_PATH", os.path.join(BASE_DIR, "orders.db"))
    app.config["UPLOAD_DIR"] = os.environ.get("DOD_UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    app.config["PDF_DIR"] = os.path.join(BASE_DIR, "generated_pdfs") if not os.environ.get("DOD_PDF_DIR") else os.environ.get("DOD_PDF_DIR")
    app.config["MAX_VIDEO_SIZE_MB"] = int(os.environ.get("MAX_VIDEO_SIZE_MB", DEFAULT_MAX_VIDEO_MB))

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["PDF_DIR"], exist_ok=True)
    init_db(app.config["DB_PATH"])
    init_auth_tables(app.config["DB_PATH"])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            user = verify_user(username, password, db_path=app.config["DB_PATH"])
            if user:
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                return redirect(url_for("index"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/admin/users", methods=["GET", "POST"])
    @admin_required
    def admin_users():
        if request.method == "POST":
            new_username = request.form.get("username", "")
            new_password = request.form.get("password", "")
            ok, message = create_standard_user(
                new_username, new_password, db_path=app.config["DB_PATH"]
            )
            flash(message, "success" if ok else "error")
            return redirect(url_for("admin_users"))

        users = list_users(db_path=app.config["DB_PATH"])
        return render_template(
            "admin_users.html",
            users=users,
            current_user=session.get("username"),
            current_user_id=session.get("user_id"),
        )

    @app.route("/admin/users/<int:user_id>/edit", methods=["POST"])
    @admin_required
    def admin_edit_user(user_id: int):
        new_username = request.form.get("username", "")
        new_password = request.form.get("password", "")
        ok, message = update_user(
            user_id, new_username, new_password, db_path=app.config["DB_PATH"]
        )
        if ok and user_id == session.get("user_id"):
            session["username"] = new_username.strip()
        flash(message, "success" if ok else "error")
        return redirect(url_for("admin_users"))

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_user(user_id: int):
        ok, message = delete_user(
            user_id,
            acting_user_id=session.get("user_id"),
            db_path=app.config["DB_PATH"],
        )
        flash(message, "success" if ok else "error")
        return redirect(url_for("admin_users"))

    @app.route("/", methods=["GET"])
    @login_required
    def index():
        return render_template(
            "index.html",
            drive_status=get_drive_status(),
            metal_options=METAL_OPTIONS,
            metal_tones=METAL_TONES,
            product_types=PRODUCT_TYPES,
            stone_types=STONE_TYPES,
            stone_shapes=STONE_SHAPES,
            max_images=MAX_IMAGES,
            max_videos=MAX_VIDEOS,
            max_video_mb=app.config["MAX_VIDEO_SIZE_MB"],
        )

    @app.route("/orders", methods=["GET"])
    @login_required
    def orders_page():
        query = request.args.get("q", "").strip()
        orders = list_all_orders(search_query=query, db_path=app.config["DB_PATH"])
        return render_template(
            "orders.html",
            orders=orders,
            search_query=query,
            drive_status=get_drive_status(),
        )

    @app.route("/api/drive-status", methods=["GET"])
    @login_required
    def api_drive_status():
        return jsonify(get_drive_status())

    @app.route("/api/check-order-id/<order_id>", methods=["GET"])
    @login_required
    def api_check_order_id(order_id: str):
        cleaned = (order_id or "").strip()
        valid_format = bool(ORDER_ID_PATTERN.match(cleaned))
        exists = order_exists(cleaned, db_path=app.config["DB_PATH"]) if valid_format else False
        return jsonify(
            {
                "order_id": cleaned,
                "valid_format": valid_format,
                "exists": exists,
                "available": valid_format and not exists,
            }
        )

    @app.route("/api/orders", methods=["GET"])
    @login_required
    def api_list_orders():
        query = request.args.get("q", "").strip()
        orders = list_all_orders(search_query=query, db_path=app.config["DB_PATH"])
        return jsonify({"orders": orders, "count": len(orders)})

    @app.route("/api/orders/<order_id>", methods=["GET"])
    @login_required
    def api_get_order(order_id: str):
        order = get_order_by_id(order_id, db_path=app.config["DB_PATH"])
        if order is None:
            return jsonify({"error": f"Order '{order_id}' not found."}), 404
        return jsonify({"order": order})

    @app.route("/api/orders/<order_id>", methods=["PUT"])
    @login_required
    def api_update_order(order_id: str):
        existing = get_order_by_id(order_id, db_path=app.config["DB_PATH"])
        if existing is None:
            return jsonify({"ok": False, "error": f"Order '{order_id}' not found."}), 404

        payload = request.get_json(silent=True) or {}
        customer_name = str(payload.get("customer_name") or "").strip()
        product_type = str(payload.get("product_type") or "").strip()
        product_sku = str(payload.get("product_sku") or "").strip()
        metal_option = str(payload.get("metal_option") or "").strip()
        metal_tone = str(payload.get("metal_tone") or "").strip()
        size_or_closure = str(payload.get("size_or_closure") or "").strip()

        errors: list[str] = []
        if not customer_name:
            errors.append("Customer Name is required.")
        if not product_type:
            errors.append("Product Type is required.")
        if not product_sku:
            errors.append("Product SKU is required.")
        if not metal_option:
            errors.append("Metal Option is required.")
        if not metal_tone:
            errors.append("Metal Tone is required.")
        if not size_or_closure:
            errors.append("Size / Closure is required.")

        try:
            quantity = int(payload.get("quantity", 1))
            if quantity < 1:
                errors.append("Quantity must be at least 1.")
        except (TypeError, ValueError):
            quantity = 1
            errors.append("Quantity must be a valid integer.")

        raw_stones = payload.get("stone_details")
        if raw_stones is None:
            raw_stones = (existing.get("item") or {}).get("stone_details") or []
        if not isinstance(raw_stones, list):
            errors.append("Invalid stone_details payload.")
            raw_stones = []

        if errors:
            return jsonify({"ok": False, "errors": errors}), 400

        updated = update_order(
            order_id,
            order_data={
                "customer_name": customer_name,
                "mobile_number": payload.get("mobile_number"),
                "email": payload.get("email"),
                "living_address": payload.get("living_address"),
                "dispatch_date": payload.get("dispatch_date"),
                "order_placing_date": payload.get("order_placing_date"),
                "factory_receiving_date": payload.get("factory_receiving_date"),
            },
            item_data={
                "product_type": product_type,
                "product_sku": product_sku,
                "quantity": quantity,
                "metal_option": metal_option,
                "metal_tone": metal_tone,
                "band_tone": payload.get("band_tone"),
                "prong_tone": payload.get("prong_tone"),
                "basket_tone": payload.get("basket_tone"),
                "cad_image_no": payload.get("cad_image_no"),
                "size_or_closure": size_or_closure,
                "engraving": payload.get("engraving"),
                "side_engraving": resolve_side_engraving(metal_option, payload.get("side_engraving")),
                "special_requirements": payload.get("special_requirements"),
                "stone_details": clean_stones_payload(raw_stones),
            },
            db_path=app.config["DB_PATH"],
        )

        if updated is not None:
            generate_both_order_pdfs(updated, output_dir=app.config["PDF_DIR"])

        return jsonify(
            {
                "ok": True,
                "order": updated,
                "workpdf_url": f"/orders/{order_id}/workpdf",
                "ourpdf_url": f"/orders/{order_id}/ourpdf",
            }
        )

    def _delete_order_and_files(order_id: str) -> str | None:
        deleted = delete_order(order_id, db_path=app.config["DB_PATH"])
        if deleted is None:
            return None

        canonical_id = deleted["order_id"]
        safe_order_id = "".join(c for c in canonical_id if c.isalnum() or c in ("-", "_"))

        upload_subdir = os.path.join(app.config["UPLOAD_DIR"], canonical_id)
        if os.path.isdir(upload_subdir):
            shutil.rmtree(upload_subdir, ignore_errors=True)

        for fname in (
            get_pdf_filename(canonical_id, "work"),
            get_pdf_filename(canonical_id, "our"),
            f"{safe_order_id}DOD.pdf",
        ):
            pdf_file = os.path.join(app.config["PDF_DIR"], fname)
            if os.path.isfile(pdf_file):
                try:
                    os.remove(pdf_file)
                except OSError:
                    pass
        return canonical_id

    @app.route("/api/orders/<order_id>", methods=["DELETE"])
    @login_required
    def api_delete_order(order_id: str):
        canonical_id = _delete_order_and_files(order_id)
        if canonical_id is None:
            return jsonify({"ok": False, "error": f"Order '{order_id}' not found."}), 404
        return jsonify({"ok": True, "deleted_order_id": canonical_id})

    @app.route("/api/orders/bulk-delete", methods=["POST"])
    @login_required
    def api_bulk_delete_orders():
        payload = request.get_json(silent=True) or {}
        raw_ids = payload.get("order_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"ok": False, "error": "Select at least one order to delete."}), 400

        deleted_ids: list[str] = []
        for oid in raw_ids:
            canonical_id = _delete_order_and_files(str(oid))
            if canonical_id:
                deleted_ids.append(canonical_id)

        return jsonify({"ok": True, "deleted_order_ids": deleted_ids, "count": len(deleted_ids)})

    @app.route("/api/orders", methods=["POST"])
    @login_required
    def api_create_order():
        form = request.form

        order_id = (form.get("order_id") or "").strip()
        customer_name = (form.get("customer_name") or "").strip()
        mobile_number = (form.get("mobile_number") or "").strip() or None
        email = (form.get("email") or "").strip() or None
        living_address = (form.get("living_address") or "").strip() or None
        dispatch_date = (form.get("dispatch_date") or "").strip() or None
        order_placing_date = (form.get("order_placing_date") or "").strip() or None
        factory_receiving_date = (form.get("factory_receiving_date") or "").strip() or None

        product_type = (form.get("product_type") or "").strip()
        product_sku = (form.get("product_sku") or "").strip()
        quantity_raw = (form.get("quantity") or "1").strip()
        metal_option = (form.get("metal_option") or "").strip()
        metal_tone = (form.get("metal_tone") or "").strip()
        band_tone = (form.get("band_tone") or "").strip() or None
        prong_tone = (form.get("prong_tone") or "").strip() or None
        basket_tone = (form.get("basket_tone") or "").strip() or None
        cad_image_no = (form.get("cad_image_no") or "").strip() or None
        size_or_closure = (form.get("size_or_closure") or "").strip()
        engraving = (form.get("engraving") or "").strip() or None
        side_engraving = resolve_side_engraving(metal_option, form.get("side_engraving"))
        special_requirements = (form.get("special_requirements") or "").strip() or None
        stones_raw = form.get("stone_details_json") or "[]"

        # Basic field validation
        errors: list[str] = []
        if not ORDER_ID_PATTERN.match(order_id):
            errors.append("Order ID is required, must be alphanumeric, and at most 15 characters.")
        elif order_exists(order_id, db_path=app.config["DB_PATH"]):
            errors.append(f"Order ID '{order_id}' already exists. Please enter a unique Order ID.")

        if not customer_name:
            errors.append("Customer Name is required.")
        if not product_type:
            errors.append("Product Type is required.")
        if not product_sku:
            errors.append("Product SKU is required.")
        if not metal_option:
            errors.append("Metal Option is required.")
        if not metal_tone:
            errors.append("Metal Tone is required.")
        if not size_or_closure:
            errors.append("Size / Closure is required.")

        try:
            quantity = int(quantity_raw)
            if quantity < 1:
                errors.append("Quantity must be at least 1.")
        except ValueError:
            quantity = 1
            errors.append("Quantity must be a valid integer.")

        try:
            stones = json.loads(stones_raw)
            if not isinstance(stones, list):
                raise ValueError("stone_details_json must be a list")
        except (json.JSONDecodeError, ValueError):
            stones = []
            errors.append("Invalid stone details payload.")

        # Validate uploaded files
        image_files = [f for f in request.files.getlist("images") if f and f.filename]
        video_files = [f for f in request.files.getlist("videos") if f and f.filename]

        if len(image_files) > MAX_IMAGES:
            errors.append(f"Maximum {MAX_IMAGES} images allowed (received {len(image_files)}).")
        if len(video_files) > MAX_VIDEOS:
            errors.append(f"Maximum {MAX_VIDEOS} videos allowed (received {len(video_files)}).")

        for img in image_files:
            ext = os.path.splitext(img.filename)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append(f"Unsupported image format for '{img.filename}'. Allowed: .jpg, .jpeg, .png, .webp.")

        max_video_bytes = app.config["MAX_VIDEO_SIZE_MB"] * 1024 * 1024
        for vid in video_files:
            ext = os.path.splitext(vid.filename)[1].lower()
            if ext not in ALLOWED_VIDEO_EXTENSIONS:
                errors.append(f"Unsupported video format for '{vid.filename}'. Allowed: .mp4, .mov.")
            vid.stream.seek(0, os.SEEK_END)
            size_bytes = vid.stream.tell()
            vid.stream.seek(0)
            if size_bytes > max_video_bytes:
                errors.append(
                    f"Video '{vid.filename}' exceeds the {app.config['MAX_VIDEO_SIZE_MB']} MB limit."
                )

        if errors:
            return jsonify({"ok": False, "errors": errors}), 400

        # Persist media locally first so PDF generation always has crisp local images
        order_upload_dir = os.path.join(app.config["UPLOAD_DIR"], order_id)
        os.makedirs(order_upload_dir, exist_ok=True)

        local_entries: list[dict[str, str]] = []
        for idx, img in enumerate(image_files, start=1):
            safe_name = secure_filename(img.filename) or f"image_{idx}.jpg"
            dest_name = f"img_{idx:02d}_{safe_name}"
            dest_path = os.path.join(order_upload_dir, dest_name)
            img.save(dest_path)
            local_entries.append(
                {
                    "media_type": "image",
                    "local_temp_path": dest_path,
                    "filename": dest_name,
                }
            )

        for idx, vid in enumerate(video_files, start=1):
            safe_name = secure_filename(vid.filename) or f"video_{idx}.mp4"
            dest_name = f"vid_{idx:02d}_{safe_name}"
            dest_path = os.path.join(order_upload_dir, dest_name)
            vid.save(dest_path)
            local_entries.append(
                {
                    "media_type": "video",
                    "local_temp_path": dest_path,
                    "filename": dest_name,
                }
            )

        warnings: list[str] = []
        drive_uploaded = False
        media_records: list[dict[str, Any]] = []

        if local_entries:
            drive_status = get_drive_status()
            if drive_status.get("configured"):
                try:
                    media_records = upload_order_media(order_id, local_entries)
                    drive_uploaded = True
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"Google Drive upload failed ({exc}); media saved locally.")
                    media_records = [
                        {
                            "media_type": entry["media_type"],
                            "local_temp_path": entry["local_temp_path"],
                            "drive_file_id": None,
                            "drive_view_link": None,
                        }
                        for entry in local_entries
                    ]
            else:
                warnings.append(
                    "Google Drive credentials are not configured yet; media saved locally."
                )
                media_records = [
                    {
                        "media_type": entry["media_type"],
                        "local_temp_path": entry["local_temp_path"],
                        "drive_file_id": None,
                        "drive_view_link": None,
                    }
                    for entry in local_entries
                ]

        clean_stones = clean_stones_payload(stones)

        save_order(
            order_data={
                "order_id": order_id,
                "customer_name": customer_name,
                "mobile_number": mobile_number,
                "email": email,
                "living_address": living_address,
                "dispatch_date": dispatch_date,
                "order_placing_date": order_placing_date,
                "factory_receiving_date": factory_receiving_date,
            },
            item_data={
                "product_type": product_type,
                "product_sku": product_sku,
                "quantity": quantity,
                "metal_option": metal_option,
                "metal_tone": metal_tone,
                "band_tone": band_tone,
                "prong_tone": prong_tone,
                "basket_tone": basket_tone,
                "cad_image_no": cad_image_no,
                "size_or_closure": size_or_closure,
                "engraving": engraving,
                "side_engraving": side_engraving,
                "special_requirements": special_requirements,
                "stone_details": clean_stones,
            },
            media_list=media_records,
            db_path=app.config["DB_PATH"],
        )

        saved_order = get_order_by_id(order_id, db_path=app.config["DB_PATH"])
        if saved_order is None:
            return jsonify({"ok": False, "errors": ["Failed to load order for PDF generation."]}), 500

        pdfs = generate_both_order_pdfs(saved_order, output_dir=app.config["PDF_DIR"])

        return jsonify(
            {
                "ok": True,
                "order_id": order_id,
                "pdf_url": f"/orders/{order_id}/workpdf",
                "pdf_filename": os.path.basename(pdfs["workpdf_path"]),
                "workpdf_url": f"/orders/{order_id}/workpdf",
                "workpdf_filename": os.path.basename(pdfs["workpdf_path"]),
                "ourpdf_url": f"/orders/{order_id}/ourpdf",
                "ourpdf_filename": os.path.basename(pdfs["ourpdf_path"]),
                "drive_uploaded": drive_uploaded,
                "warnings": warnings,
            }
        ), 201

    def _serve_order_pdf(order_id: str, pdf_type: str):
        full_order = get_order_by_id(order_id, db_path=app.config["DB_PATH"])
        if full_order is None:
            return jsonify({"error": f"Order '{order_id}' not found."}), 404

        canonical_id = full_order["order_id"]
        filename = get_pdf_filename(canonical_id, pdf_type=pdf_type)
        expected_pdf = os.path.join(app.config["PDF_DIR"], filename)
        force_regen = request.args.get("regenerate") == "1"

        if force_regen or not os.path.isfile(expected_pdf):
            expected_pdf = generate_order_pdf(
                full_order, output_dir=app.config["PDF_DIR"], pdf_type=pdf_type
            )

        return send_file(
            expected_pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/orders/<order_id>/workpdf", methods=["GET"])
    @login_required
    def download_work_pdf(order_id: str):
        return _serve_order_pdf(order_id, "work")

    @app.route("/orders/<order_id>/ourpdf", methods=["GET"])
    @login_required
    def download_our_pdf(order_id: str):
        return _serve_order_pdf(order_id, "our")

    @app.route("/orders/<order_id>/pdf", methods=["GET"])
    @login_required
    def download_order_pdf(order_id: str):
        pdf_type = "our" if request.args.get("type") == "our" else "work"
        return _serve_order_pdf(order_id, pdf_type)

    @app.route("/uploads/<order_id>/<filename>", methods=["GET"])
    @login_required
    def serve_local_upload(order_id: str, filename: str):
        safe_id = secure_filename(order_id)
        safe_name = secure_filename(filename)
        file_path = os.path.join(app.config["UPLOAD_DIR"], safe_id, safe_name)
        if not os.path.isfile(file_path):
            return jsonify({"error": "File not found."}), 404
        return send_file(file_path)

    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
