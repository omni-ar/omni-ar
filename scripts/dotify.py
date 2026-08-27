#!/usr/bin/env python3
"""
dotify.py — turns a photo into a dot-matrix SVG portrait.

Usage:
    python dotify.py photo.png -o assets/portrait --cols 100 --equalize --detail 0.5 --color
    python dotify.py photo.png -o assets/portrait --cols 88 --equalize --mode mono --accent 00D9FF

Requires: Pillow (pip install pillow --break-system-packages)
"""
import argparse
from PIL import Image, ImageOps
import sys


def load_image(path):
    img = Image.open(path).convert("RGBA")
    return img


def equalize_luma(gray_img):
    """Stretch tonal range against the subject's own histogram so shadow
    detail (hair, jaw shadow) survives being bucketed into ~10 dot sizes."""
    return ImageOps.equalize(gray_img)


def unsharp_detail(gray_img, amount):
    """Adds back local structure (cheekbones, nose bridge) that a global
    equalize flattens. amount above ~1.0 starts reading as noise."""
    if amount <= 0:
        return gray_img
    from PIL import ImageFilter
    blurred = gray_img.filter(ImageFilter.GaussianBlur(radius=2))
    sharpened = Image.blend(gray_img, blurred, -amount)
    return sharpened


def sample_grid(img, cols, focus=None):
    w, h = img.size
    aspect = h / w
    rows = max(1, round(cols * aspect))
    return cols, rows


def build_svg(img, cols, rows, cell=10, mode="color", accent="00D9FF",
              equalize=True, detail=0.5, invert=False, circle_mask=False):
    # Process luminance at FULL resolution first — equalizing or sharpening
    # after downsampling amplifies resize ringing into noise (verified bug:
    # see test images). Order matters: equalize/sharpen full-res, then resize.
    gray_full = ImageOps.grayscale(img)
    if equalize:
        gray_full = equalize_luma(gray_full)
    gray_full = unsharp_detail(gray_full, detail)
    if invert:
        gray_full = ImageOps.invert(gray_full)

    gray_small = gray_full.resize((cols, rows), Image.LANCZOS)
    rgba_small = img.convert("RGBA").resize((cols, rows), Image.LANCZOS)

    px_rgba = rgba_small.load()
    px_gray = gray_small.load()

    width = cols * cell
    height = rows * cell
    cx, cy = width / 2, height / 2
    max_r = min(width, height) / 2

    parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="none"/>',
    ]

    for y in range(rows):
        for x in range(cols):
            alpha = px_rgba[x, y][3]
            if alpha < 16:
                continue
            lum = px_gray[x, y] / 255.0  # 0 dark .. 1 bright
            # brighter pixel -> smaller dot. Max radius must exceed cell/sqrt(2)
            # (~0.71*cell) to fully cover a cell's corners -- otherwise dark
            # regions render as a visible dot grid instead of solid ink.
            radius = (1 - lum) * (cell * 0.8) + (cell * 0.04)
            ccx = x * cell + cell / 2
            ccy = y * cell + cell / 2
            if circle_mask:
                if ((ccx - cx) ** 2 + (ccy - cy) ** 2) ** 0.5 > max_r:
                    continue
            if mode == "color":
                r, g, b, _ = px_rgba[x, y]
                fill = f"rgb({r},{g},{b})"
            else:
                fill = f"#{accent}"
            parts.append(
                f'<circle cx="{ccx:.0f}" cy="{ccy:.0f}" r="{radius:.1f}" fill="{fill}"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("-o", "--out", default="assets/portrait")
    ap.add_argument("--cols", type=int, default=96)
    ap.add_argument("--cell", type=int, default=10)
    ap.add_argument("--equalize", action="store_true")
    ap.add_argument("--detail", type=float, default=0.5)
    ap.add_argument("--mode", choices=["color", "mono"], default="color")
    ap.add_argument("--accent", default="00D9FF", help="hex without #, used in mono mode")
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--circle", action="store_true")
    args = ap.parse_args()

    img = load_image(args.image)
    cols, rows = sample_grid(img, args.cols)
    svg = build_svg(
        img, cols, rows, cell=args.cell, mode=args.mode, accent=args.accent,
        equalize=args.equalize, detail=args.detail, invert=args.invert,
        circle_mask=args.circle,
    )

    out_path = f"{args.out}.svg"
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"wrote {out_path} ({cols}x{rows} dots)")


if __name__ == "__main__":
    main()
