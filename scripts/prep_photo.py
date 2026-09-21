"""Prep a photo for ASCII conversion: crop, upscale, (optionally) cut out the subject, boost contrast.

usage: python scripts/prep_photo.py source-photo.png [--crop x0,y0,x1,y1] [--upscale 4] [--rembg] [--clahe 2.5]
writes source-prepped.png: grayscale, or grayscale+alpha tightly cropped to the subject with --rembg
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--crop", help="x0,y0,x1,y1 in source pixels")
    ap.add_argument("--upscale", type=int, default=1, help="enlarge before processing (helps small subjects)")
    ap.add_argument("--rembg", action="store_true", help="cut out the subject (needs `pip install rembg`)")
    ap.add_argument("--clahe", type=float, default=0, help="CLAHE clip limit; helps flat-lit faces, adds noise on textured scenes")
    args = ap.parse_args()

    img = Image.open(args.photo).convert("RGB")
    if args.crop:
        img = img.crop(tuple(int(v) for v in args.crop.split(",")))
    if args.upscale > 1:
        img = img.resize((img.width * args.upscale, img.height * args.upscale), Image.LANCZOS)

    alpha = None
    if args.rembg:
        from rembg import remove  # heavy dependency, only imported when asked for

        alpha = np.array(remove(img).getchannel("A"))

    gray = np.array(img.convert("L"))
    if args.clahe:  # gives flat regions real highlights and shadows
        gray = cv2.createCLAHE(clipLimit=args.clahe, tileGridSize=(4, 4)).apply(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)  # soften fine texture so it doesn't print as noise

    if alpha is None:
        out = Image.fromarray(gray)
    else:
        ys, xs = np.where(alpha > 40)
        box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        out = Image.merge("LA", (Image.fromarray(gray), Image.fromarray(alpha))).crop(box)
    out.save(OUT)
    print(f"wrote {OUT} {out.width}x{out.height} ({out.mode})")


if __name__ == "__main__":
    main()
