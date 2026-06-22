import os
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from split_grid import grid_to_rows_cols, save_tiles, split_image  # noqa: E402


def _make_img(width, height, path):
    Image.new("RGB", (width, height), (123, 200, 50)).save(path)


def test_grid_to_rows_cols():
    assert grid_to_rows_cols(4) == (2, 2)
    assert grid_to_rows_cols(9) == (3, 3)
    assert grid_to_rows_cols(16) == (4, 4)


def test_non_square_raises():
    for bad in (3, 5, 8):
        try:
            grid_to_rows_cols(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"grid={bad} should fail")


def test_split_counts():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "g.png")
        _make_img(400, 400, path)
        assert len(split_image(path, 2, 2)) == 4
        assert len(split_image(path, 3, 3)) == 9
        assert len(split_image(path, 4, 4)) == 16


def test_no_pixel_loss():
    with tempfile.TemporaryDirectory() as d:
        for width, height in [(400, 400), (401, 403), (1000, 600)]:
            path = os.path.join(d, f"g_{width}x{height}.png")
            _make_img(width, height, path)
            tiles = split_image(path, 3, 3)
            total = sum(tile.size[0] * tile.size[1] for tile in tiles)
            assert total == width * height


def test_original_untouched():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "g.png")
        _make_img(400, 400, path)
        before = os.path.getsize(path)
        split_image(path, 2, 2)
        assert os.path.getsize(path) == before


def test_save_tiles_naming():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "hero.png")
        _make_img(400, 400, path)
        tiles = split_image(path, 2, 2)
        paths = save_tiles(tiles, os.path.join(d, "out"), "hero")
        assert paths[0].endswith("hero_tile_01.png")
        assert all(os.path.exists(item) for item in paths)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
