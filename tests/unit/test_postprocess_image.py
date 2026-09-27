import pytest
from PIL import Image

from gen.postprocess.image import crop_to_aspect, upscale


def _make_image(tmp_path, size):
    path = tmp_path / "photo.png"
    Image.new("RGB", size, color=(10, 20, 30)).save(path)
    return path


def test_upscale_enlarges_small_image(tmp_path):
    path = _make_image(tmp_path, (100, 150))

    upscale(path, min_long_side=1000)

    with Image.open(path) as img:
        assert max(img.size) >= 1000


def test_upscale_skips_already_large_image(tmp_path):
    path = _make_image(tmp_path, (2000, 3000))

    upscale(path, min_long_side=1000)

    with Image.open(path) as img:
        assert img.size == (2000, 3000)


def test_crop_to_aspect_1_1(tmp_path):
    path = _make_image(tmp_path, (400, 600))

    crop_to_aspect(path, "1:1")

    with Image.open(path) as img:
        assert img.width == img.height


def test_crop_to_aspect_9_16(tmp_path):
    path = _make_image(tmp_path, (1000, 1000))

    crop_to_aspect(path, "9:16")

    with Image.open(path) as img:
        assert abs(img.width / img.height - 9 / 16) < 0.01


def test_crop_to_aspect_unknown_raises(tmp_path):
    path = _make_image(tmp_path, (100, 100))

    with pytest.raises(ValueError):
        crop_to_aspect(path, "2:3")
