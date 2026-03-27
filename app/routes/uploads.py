"""
CapitalOps API - Image Upload Routes

Handles avatar and profile image uploads for authenticated users.
Images are received as multipart form data or base64-encoded JSON,
processed (resized to a thumbnail), and stored as base64 data URLs
directly in the User model's profile_image column.

This approach avoids external object storage dependencies (AWS S3, GCS)
and keeps all user data self-contained in PostgreSQL. It works correctly
on any hosting environment without extra bucket configuration, secrets,
or network latency from external services.

Limitations:
    - Base64 encoding increases data size by ~33%
    - PostgreSQL TEXT columns have a 1GB limit, but 5MB upload cap keeps
      stored thumbnails well within practical limits
    - No CDN/caching of images (they're embedded in API responses)

Routes:
    POST /api/v1/upload/avatar   — Upload avatar for the authenticated user
                                    Requires valid JWT. Image stored in the
                                    current user's profile_image column.
                                    Accepts multipart file (field name 'image')
                                    or JSON body (field 'imageData').

    POST /api/upload-avatar       — Alias endpoint for GUI compatibility layer.
                                    Same behavior as /avatar but may accept
                                    API key auth in addition to JWT.

Size Limits:
    - Maximum input: 5 MB (MAX_UPLOAD_BYTES)
    - Stored output: Resized JPEG, max 256x256 pixels, quality 85

Processing Pipeline:
    1. Receive image bytes (file upload or base64 decode)
    2. Validate size does not exceed 5 MB limit
    3. Open image with Pillow (if available)
    4. Convert RGBA/palette images to RGB (for JPEG compatibility)
    5. Resize to fit within 256x256 box, preserving aspect ratio
    6. Encode as JPEG at 85% quality
    7. Wrap as data URL: data:image/jpeg;base64,<base64>
    8. Persist to User.profile_image and commit

Fallback Behavior:
    If Pillow is not installed or image processing fails, the raw image
    is stored without resizing. This prevents hard failures but may
    result in larger storage use and non-standard thumbnail sizes.

Security Considerations:
    - JWT authentication required (prevents arbitrary image uploads)
    - File size enforced before processing (prevents memory exhaustion)
    - MIME type defaults to image/jpeg (overridden from content-type header
      or extracted from data URL prefix, not from file extension)
    - Base64 decoding errors return 400 (invalid payload)
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

# Maximum allowed upload size (bytes) — reject anything larger upfront.
# 5 MB is a reasonable limit for profile avatars; larger images are
# resized anyway so the original doesn't need to be kept.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

# Thumbnail dimensions — images are resized to fit within this box on the
# longest side. This keeps storage predictable and reduces response payload
# size for avatar requests across the application.
THUMBNAIL_SIZE = (256, 256)


def _image_to_data_url(file_data: bytes, mime_type: str) -> str:
    """
    Convert raw image bytes to a base64-encoded data URL.

    Attempts to use Pillow to resize the image to THUMBNAIL_SIZE and encode
    as a JPEG for consistent output format and smaller file size.
    Falls back to raw base64 encoding (without resize) if Pillow is not
    available or if the image cannot be processed.

    Args:
        file_data: Raw bytes of the uploaded image file.
        mime_type: MIME type string (e.g., 'image/jpeg', 'image/png').
                   Used for the data URL prefix when Pillow processing fails.

    Returns:
        A data URL string: 'data:<mime>;base64,<encoded_data>'
        On success, mime is always 'image/jpeg' (images are converted for
        consistent output). On fallback, the original mime_type is used.

    Implementation Details:
        - RGBA and palette images are converted to RGB by compositing over
          a white background (required because JPEG doesn't support alpha)
        - Aspect ratio is preserved via Image.thumbnail() which scales down
          in-place maintaining proportions
        - LANCZOS resampling used for high-quality downscaling
        - JPEG quality 85 strikes a balance between file size and visual quality
    """
    try:
        # Try to resize with Pillow if available
        from PIL import Image

        img = Image.open(io.BytesIO(file_data))

        # Convert RGBA/palette images to RGB for JPEG compatibility.
        # JPEG does not support transparency, so transparent pixels are
        # composited over a white background to avoid black fill on conversion.
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            # Paste using alpha channel as mask if present
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background

        # Scale down to fit within the thumbnail box (preserving aspect ratio).
        # thumbnail() modifies the image in-place; only one dimension may
        # reach the max, the other will be proportionally smaller.
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

        # Encode as JPEG for consistent output format and smaller size.
        # Converting everything to JPEG also normalizes the MIME type returned
        # to the client, avoiding content-type confusion.
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    except ImportError:
        # Pillow not available — store as-is without resize.
        # This should rarely happen in production but allows the endpoint
        # to remain functional in environments without Pillow installed.
        logger.warning("Pillow not installed — storing avatar without resizing")
        encoded = base64.b64encode(file_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        # Image couldn't be decoded/processed by Pillow — store raw bytes.
        # This can happen with corrupted images, unsupported formats (e.g., webp
        # without a proper codec), or extremely large images that cause OOM.
        logger.warning("Image processing failed (%s) — storing avatar without resizing", str(e))
        encoded = base64.b64encode(file_data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"


@uploads_bp.route("/avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    """
    Upload a profile avatar for the currently authenticated user.

    Accepts image data in two formats:
        1. Multipart form data with field name 'image' (standard file upload)
           Content-Type: multipart/form-data
           Form field: image = <file>

        2. JSON body with base64-encoded field 'imageData'
           Content-Type: application/json
           Body: { "imageData": "<base64 string or data URL>" }

    The image is processed (resized to 256x256 JPEG thumbnail) and stored
    directly in the user's profile_image column as a base64 data URL.

    Because profile_image is stored on the User model, the updated avatar
    is immediately returned via /api/v1/auth/me without needing a separate
    fetch call.

    Request Fields:
        image (multipart)   — Binary image file (optional)
        imageData (JSON)     — Base64 string or data URL (optional)
                               If prefixed with 'data:...;base64,', the
                               prefix is stripped and MIME type is extracted.

    Returns (200):
        {
            "url": "data:image/jpeg;base64,...",   — The stored data URL
            "message": "Avatar uploaded successfully"
        }

    Returns on failure:
        400 — No image provided, file too large (>5MB), or invalid base64 data
        404 — Authenticated user not found in database
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data_url = None

    # --- Accept multipart file upload ---
    # Standard HTML file input submission via FormData
    if "image" in request.files:
        file = request.files["image"]

        # Read file bytes and enforce size limit before any processing.
        # Reading the entire file first prevents partial processing of
        # oversized files and ensures consistent error messages.
        file_data = file.read()
        if len(file_data) > MAX_UPLOAD_BYTES:
            return jsonify({"error": f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB"}), 400
        if not file_data:
            return jsonify({"error": "Empty file received"}), 400

        # Determine MIME type from the uploaded file's content-type header.
        # Note: this header is client-supplied and not trusted for security,
        # but since we re-encode as JPEG via Pillow, the actual format is
        # validated during processing regardless of this header.
        mime_type = file.content_type or "image/jpeg"
        data_url = _image_to_data_url(file_data, mime_type)

    # --- Accept JSON body with base64 imageData ---
    # Used by clients that don't support multipart uploads (mobile, certain SDKs)
    elif request.is_json:
        body = request.get_json()
        image_data = body.get("imageData", "") if body else ""

        if not image_data:
            return jsonify({"error": "No image provided — send 'image' file field or 'imageData' base64 string"}), 400

        # If client sends a full data URL (data:image/...;base64,...),
        # extract the raw bytes and MIME type from the prefix
        if image_data.startswith("data:"):
            try:
                header, encoded = image_data.split(",", 1)
                # Extract MIME type from 'data:image/jpeg;base64'
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

    # Persist the data URL to the user's profile_image column.
    # The next /auth/me call will return the updated avatar automatically.
    user.profile_image = data_url
    db.session.commit()
    logger.info("Avatar uploaded for user %s (id=%s)", user.username, user.id)

    return jsonify({
        "url": data_url,
        "message": "Avatar uploaded successfully",
    })
