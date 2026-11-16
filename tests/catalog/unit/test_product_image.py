"""Tests for the rules of a product image."""

import pytest

from app.catalog.domain.services.product_image import MAXIMUM_IMAGE_BYTES, image_extension
from app.shared.domain.errors import BusinessError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 8


@pytest.mark.parametrize(("content", "extension"), [(PNG, "png"), (JPEG, "jpg"), (WEBP, "webp")])
def test_type_is_read_from_the_bytes(content, extension):
    assert image_extension(content) == extension


@pytest.mark.parametrize("content", [b"GIF89a" + b"\x00" * 10, b"%PDF-1.7", b""])
def test_other_files_are_rejected(content):
    with pytest.raises(BusinessError) as error:
        image_extension(content)
    assert (error.value.code, error.value.field) == ("UNSUPPORTED_IMAGE_TYPE", "image")


def test_images_over_2_mb_are_rejected():
    with pytest.raises(BusinessError) as error:
        image_extension(PNG + b"\x00" * MAXIMUM_IMAGE_BYTES)
    assert error.value.code == "IMAGE_TOO_LARGE"
