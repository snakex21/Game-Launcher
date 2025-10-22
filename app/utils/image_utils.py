"""Helpers for working with images."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def create_default_cover(game_name: str, size: Tuple[int, int] = (300, 420)) -> Image.Image:
    image = Image.new("RGB", size, color="#1e293b")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()

    text = game_name[:22] + ("..." if len(game_name) > 22 else "")
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = 100, 40

    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    draw.text(position, text, fill="white", font=font)
    return image


def load_image(path: str | Path, size: Tuple[int, int] = (300, 420)) -> Image.Image:
    path = Path(path)
    if not path.exists():
        return create_default_cover(path.stem if path.stem else "Gra", size)

    image = Image.open(path)
    return image.resize(size, Image.Resampling.LANCZOS)
