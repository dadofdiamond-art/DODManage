"""Workshop / Karigar PDF generator using Jinja2, QRCode, and Playwright."""

from __future__ import annotations

import base64
import io
import mimetypes
import os
from typing import Any

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DEFAULT_PDF_DIR = os.path.join(BASE_DIR, "generated_pdfs")


def make_qr_data_uri(url: str) -> str:
    """Generate a crisp PNG data URI QR code for a video or reference URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#3F070C", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def file_to_data_uri(file_path: str) -> str | None:
    """Read a local image file and encode it as an inline data URI for PDF rendering."""
    if not file_path or not os.path.isfile(file_path):
        return None
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg"
    with open(file_path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_workshop_context(workshop_order: dict[str, Any]) -> dict[str, Any]:
    """Build sanitized template context strictly free of customer PII."""
    item = workshop_order.get("item") or {}
    images_ctx: list[dict[str, Any]] = []
    for idx, img in enumerate(workshop_order.get("images", []), start=1):
        local_path = img.get("local_temp_path") or ""
        data_uri = file_to_data_uri(local_path)
        drive_link = img.get("drive_view_link") or ""
        if data_uri or drive_link:
            images_ctx.append(
                {
                    "index": idx,
                    "filename": os.path.basename(local_path) if local_path else f"Image {idx}",
                    "src": data_uri or drive_link,
                    "drive_view_link": drive_link,
                }
            )

    videos_ctx: list[dict[str, Any]] = []
    for idx, vid in enumerate(workshop_order.get("videos", []), start=1):
        local_path = vid.get("local_temp_path") or ""
        drive_link = vid.get("drive_view_link") or ""
        qr_target = drive_link or (f"file:///{local_path.replace(os.sep, '/')}" if local_path else "")
        videos_ctx.append(
            {
                "index": idx,
                "filename": os.path.basename(local_path) if local_path else f"Video {idx}",
                "drive_view_link": drive_link,
                "is_drive_link": bool(drive_link),
                "qr_data_uri": make_qr_data_uri(qr_target) if qr_target else None,
            }
        )

    return {
        "brand_name": "Dad Of Diamond",
        "order_id": workshop_order.get("order_id", ""),
        "product_sku": workshop_order.get("product_sku", "") or item.get("product_sku", ""),
        "customer_name": workshop_order.get("customer_name", ""),
        "dispatch_date": workshop_order.get("dispatch_date", ""),
        "product_type": item.get("product_type", ""),
        "quantity": item.get("quantity", 1),
        "metal_option": item.get("metal_option", ""),
        "metal_tone": item.get("metal_tone", ""),
        "size_or_closure": item.get("size_or_closure", ""),
        "engraving": item.get("engraving") or "",
        "special_requirements": item.get("special_requirements") or "",
        "stones": item.get("stone_details") or [],
        "images": images_ctx,
        "videos": videos_ctx,
    }


def render_workshop_html(workshop_order: dict[str, Any]) -> str:
    """Render the workshop/karigar job sheet HTML string without any customer PII."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("pdf_template.html")
    context = build_workshop_context(workshop_order)
    return template.render(**context)


def _launch_chromium(playwright: Any):
    """Launch headless Chromium using Playwright's browser or system Chrome/Edge on Windows."""
    last_error: Exception | None = None
    for launch_kwargs in (
        {"headless": True},
        {"headless": True, "channel": "chrome"},
        {"headless": True, "channel": "msedge"},
    ):
        try:
            return playwright.chromium.launch(**launch_kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(
        "Unable to launch a Chromium/Chrome/Edge browser for PDF generation. "
        "Run 'playwright install chromium' or ensure Chrome/Edge is installed."
    ) from last_error


def generate_order_pdf(
    workshop_order: dict[str, Any],
    output_dir: str | None = None,
) -> str:
    """Render workshop_order to an A4 PDF file in output_dir and return the file path."""
    target_dir = output_dir or os.environ.get("DOD_PDF_DIR", DEFAULT_PDF_DIR)
    os.makedirs(target_dir, exist_ok=True)
    safe_order_id = "".join(c for c in workshop_order["order_id"] if c.isalnum() or c in ("-", "_"))
    pdf_path = os.path.join(target_dir, f"{safe_order_id}DOD.pdf")

    html_content = render_workshop_html(workshop_order)

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        try:
            page = browser.new_page()
            page.set_content(html_content, wait_until="load")
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "12mm", "right": "12mm", "bottom": "12mm", "left": "12mm"},
            )
        finally:
            browser.close()

    return pdf_path
