"""
CapitalOps API - Image Upload Routes

Handles avatar/profile image uploads without requiring external object storage
like AWS S3. Images are received as multipart form data or base64-encoded JSON,
resized to a reasonable max, and stored as base64 data URLs in the user's
profile_image column in the database.

This approach keeps all data self-contained in the PostgreSQL database and works
correctly on any hosting environment without extra configuration.

Routes:
    POST /api/v1/upload/avatar   — Upload avatar for the authenticated user (JWT required)
    POST /api/upload-avatar      — Same, but for GUI compat layer (API key optional)

Size limit: 5 MB input; output stored as base64 JPEG thumbnail (max 256x256).
"""

import base64
import io
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app import db
from app.auth_utils import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

uploads_bp = Blueprint("uploads", __name__)

# Maximum allowed upload size (bytes) — reject anything larger upfront
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

# Thumbnail dimensions — images are resized to fit within this box
THUMBNAIL_SIZE = (256, 256)


def _image_to_data_url(file_data: bytes, mime_type: str) -> str:
    """Convert raw image bytes to a base64-encoded data URL.

    Attempts to use Pillow to resize the image to THUMBNAIL_SIZE.
    Falls back to raw base64 if Pillow is not available or if the image
    cannot be processed (to avoid hard failures on unexpected formats).

    Args:
        file_data: Raw bytes of the uploaded image.
        mime_type: MIME type string (e.g., 'image/jpeg', 'image/png').

    Returns:
        A data URL string: 'data:<mime>;base64,<encoded_data>'
    """
    try:
        # Try to resize with Pillow if available
        from PIL import Image

        img = Image.open(io.BytesIO(file_data))

        # Convert RGBA/palette images to RGB for JPEG compatibility
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background

        # Scale down to fit within the thumbnail box (preserving aspect ratio)
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

        # Encode as JPEG for consistent output and smaller size
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    except ImportError:
        # Pillow not available — store as-is (no resize)
        logger.warning("Pillow not installed — storing avatar without resizing")
        encoded = base64.b64encode(file_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        # Image couldn't be processed — store raw
        logger.warning("Image processing failed (%s) — storing avatar without resizing", str(e))
        encoded = base64.b64encode(file_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"


@uploads_bp.route("/avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    """Upload a profile avatar for the currently authenticated user.

    Accepts either:
        1. Multipart form data with field name 'image' (file upload)
        2. JSON body with field 'imageData' (base64 data URL string)

    The image is stored directly in the user's profile_image column as a
    base64 data URL, making it immediately accessible via the /api/v1/auth/me
    response without any additional storage configuration.

    Returns (200):
        { "url": "<data_url>", "message": "Avatar uploaded successfully" }

    Returns on failure:
        400 — No image provided, or file too large
        404 — Authenticated user not found
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data_url = None

    # --- Accept multipart file upload ---
    if "image" in request.files:
        file = request.files["image"]

        # Read file bytes and enforce size limit
        file_data = file.read()
        if len(file_data) > MAX_UPLOAD_BYTES:
            return jsonify({"error": f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB"}), 400
        if not file_data:
            return jsonify({"error": "Empty file received"}), 400

        # Determine MIME type from the uploaded file's content-type header
        mime_type = file.content_type or "image/jpeg"
        data_url = _image_to_data_url(file_data, mime_type)

    # --- Accept JSON body with base64 imageData ---
    elif request.is_json:
        body = request.get_json()
        image_data = body.get("imageData", "") if body else ""

        if not image_data:
            return jsonify({"error": "No image provided — send 'image' file field or 'imageData' base64 string"}), 400

        # If client sends a full data URL (data:image/...;base64,...), extract the bytes
        if image_data.startswith("data:"):
            try:
                header, encoded = image_data.split(",", 1)
                mime_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
                file_data = base64.b64decode(encoded)
            except Exception:
                return jsonify({"error": "Invalid base64 image data"}), 400
        else:
            # Plain base64 string without data URL prefix
            try:
                file_data = base64.b64decode(image_data)
                mime_type = "image/jpeg"
            except Exception:
                return jsonify({"error": "Invalid base64 image data"}), 400

        if len(file_data) > MAX_UPLOAD_BYTES:
            return jsonify({"error": f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB"}), 400

        data_url = _image_to_data_url(file_data, mime_type)

    else:
        return jsonify({"error": "No image provided — send 'image' file field or JSON with 'imageData'"}), 400

    # Persist the data URL to the user's profile_image column
    user.profile_image = data_url
    db.session.commit()
    logger.info("Avatar uploaded for user %s (id=%s)", user.username, user.id)

    return jsonify({
        "url": data_url,
        "message": "Avatar uploaded successfully",
    })
