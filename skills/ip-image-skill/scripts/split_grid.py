import os
from typing import List, Tuple

from PIL import Image


def grid_to_rows_cols(grid: int) -> Tuple[int, int]:
    n = int(round(grid ** 0.5))
    if n * n != grid:
        raise ValueError(
            f"grid={grid} is not a perfect square. Use explicit rows/cols instead."
        )
    return n, n


def split_image(path: str, rows: int, cols: int) -> List[Image.Image]:
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be >= 1")

    img = Image.open(path)
    width, height = img.size
    tiles: List[Image.Image] = []

    for row in range(rows):
        top = height * row // rows
        bottom = height * (row + 1) // rows if row < rows - 1 else height
        for col in range(cols):
            left = width * col // cols
            right = width * (col + 1) // cols if col < cols - 1 else width
            tiles.append(img.crop((left, top, right, bottom)))
    return tiles


def save_tiles(tiles: List[Image.Image], out_dir: str, stem: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    for index, tile in enumerate(tiles, start=1):
        path = os.path.join(out_dir, f"{stem}_tile_{index:02d}.png")
        tile.save(path)
        paths.append(path)
    return paths

