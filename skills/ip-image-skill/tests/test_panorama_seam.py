import os
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from panorama_seam import make_horizontally_seamless  # noqa: E402


def _edge_mae(im):
    w, h = im.size
    px = im.load()
    total = 0
    for y in range(h):
        left = px[0, y]
        right = px[w - 1, y]
        total += sum(abs(a - b) for a, b in zip(left, right))
    return total / (h * 3)


def test_seam_blend_makes_edges_match():
    # Horizontal gradient: left edge is black, right edge is white -> worst-case seam.
    w, h = 256, 64
    im = Image.new("RGB", (w, h))
    im.putdata([(int(255 * x / (w - 1)),) * 3 for _ in range(h) for x in range(w)])

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pano.png")
        im.save(path)
        before = _edge_mae(Image.open(path))
        make_horizontally_seamless(path, blend_ratio=0.1)
        after = _edge_mae(Image.open(path))

    assert before > 200  # gradient edges are far apart
    assert after < 1.0   # blended edges now wrap-match


def test_seam_blend_preserves_image_center():
    w, h = 256, 64
    im = Image.new("RGB", (w, h), (120, 60, 30))
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pano.png")
        im.save(path)
        make_horizontally_seamless(path, blend_ratio=0.08)
        out = Image.open(path)
        assert out.size == (w, h)
        assert out.getpixel((w // 2, h // 2)) == (120, 60, 30)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
