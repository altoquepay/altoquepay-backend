"""What a product image may be. The type is read from the file's bytes, not from its name."""

from app.shared.domain.errors import BusinessError

MAXIMUM_IMAGE_BYTES = 2 * 1024 * 1024

# The first bytes of each accepted format and the extension it is saved with.
SIGNATURES = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
]

# The media type each extension is served with.
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def image_extension(content: bytes) -> str:
    """Return the extension of a valid image, or raise if it is too large or not an image."""
    if len(content) > MAXIMUM_IMAGE_BYTES:
        raise BusinessError(
            "IMAGE_TOO_LARGE",
            f"The image must weigh at most {MAXIMUM_IMAGE_BYTES // (1024 * 1024)} MB.",
            field="image",
        )
    for signature, extension in SIGNATURES:
        if content.startswith(signature):
            return extension
    # WebP is a RIFF container: RIFF, the size in 4 bytes, then WEBP.
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    raise BusinessError(
        "UNSUPPORTED_IMAGE_TYPE", "The image must be a JPEG, PNG or WebP file.", field="image"
    )
