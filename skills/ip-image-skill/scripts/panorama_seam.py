"""Make a wide environment image horizontally seamless (left/right edges wrap).

Text-to-image models do not actually guarantee a tileable equirectangular seam,
even when the prompt asks for one. This post-process feathers the left and right
edge bands toward a shared per-row seam color so the panorama can wrap-tile for
360 camera planning. Pure Pillow, no extra dependencies.
"""

from PIL import Image


def make_horizontally_seamless(path: str, blend_ratio: float = 0.08, out_path: str = None) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    b = max(2, int(w * blend_ratio))
    if b * 2 >= w:
        b = max(1, w // 4)

    # Per-row seam color: the average of the leftmost and rightmost columns.
    left_edge = im.crop((0, 0, 1, h))
    right_edge = im.crop((w - 1, 0, w, h))
    seam_col = Image.blend(left_edge, right_edge, 0.5)
    seam_band = seam_col.resize((b, h))

    # Ramp mask over the band: 0 (use seam color) at the seam side, 255 (use
    # original content) b pixels inward. Image.composite picks image1 where mask=255.
    ramp = Image.new("L", (b, 1))
    ramp.putdata([int(255 * x / b) for x in range(b)])
    ramp = ramp.resize((b, h))
    ramp_r = ramp.transpose(Image.FLIP_LEFT_RIGHT)

    left_band = im.crop((0, 0, b, h))
    im.paste(Image.composite(left_band, seam_band, ramp), (0, 0))

    right_band = im.crop((w - b, 0, w, h))
    im.paste(Image.composite(right_band, seam_band, ramp_r), (w - b, 0))

    target = out_path or path
    im.save(target, quality=95)
    return target
