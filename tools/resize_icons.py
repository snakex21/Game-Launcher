"""Zmniejsza ikony z icons/ do faktycznego rozmiaru (domyślnie 16x16 RGBA).

Źródłowe PNG miały 1024x1024 px (~1 MB każdy) i jasne tło "udające"
przezroczystość. Skrypt:
  1. usuwa jasne, szare tło połączone z krawędzią obrazka (flood fill),
  2. przycina do zawartości z marginesem i skaluje do --size,
  3. zapisuje zoptymalizowany PNG w miejscu (albo do --out).

Użycie: python tools/resize_icons.py [--size 16] [--out icons]
"""
import argparse
import glob
import os
from collections import deque

from PIL import Image


def _is_background(rgb):
    r, g, b = rgb[:3]
    return min(r, g, b) >= 200 and max(r, g, b) - min(r, g, b) <= 24


def remove_light_background(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    if img.getextrema()[3][0] < 255:
        return img  # ma już prawdziwą przezroczystość
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    queue = deque()
    for x in range(w):
        queue.append((x, 0)); queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y)); queue.append((w - 1, y))
    while queue:
        x, y = queue.popleft()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        if not _is_background(px[x, y]):
            continue
        px[x, y] = (0, 0, 0, 0)
        if x > 0: queue.append((x - 1, y))
        if x < w - 1: queue.append((x + 1, y))
        if y > 0: queue.append((x, y - 1))
        if y < h - 1: queue.append((x, y + 1))
    return img


def shrink(path: str, size: int, out_dir: str) -> tuple:
    before = os.path.getsize(path)
    with Image.open(path) as src:
        img = remove_light_background(src)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    side = max(img.size)
    pad = int(side * 0.06)
    canvas = Image.new("RGBA", (side + 2 * pad, side + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2))
    # Skalowanie w dwóch krokach daje ostrzejszy wynik dla pixel-artu.
    mid = canvas.resize((size * 4, size * 4), Image.Resampling.LANCZOS)
    small = mid.resize((size, size), Image.Resampling.LANCZOS)
    target = os.path.join(out_dir, os.path.basename(path))
    small.save(target, optimize=True)
    return before, os.path.getsize(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=16)
    parser.add_argument("--src", default=os.path.join(os.path.dirname(__file__), "..", "icons"))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    out_dir = args.out or args.src
    os.makedirs(out_dir, exist_ok=True)
    total_before = total_after = 0
    for path in sorted(glob.glob(os.path.join(args.src, "*.png"))):
        before, after = shrink(path, args.size, out_dir)
        total_before += before
        total_after += after
        print(f"{os.path.basename(path):24s} {before/1024:9.1f} KB -> {after/1024:6.2f} KB")
    print(f"RAZEM {total_before/1024/1024:.2f} MB -> {total_after/1024:.1f} KB")


if __name__ == "__main__":
    main()
