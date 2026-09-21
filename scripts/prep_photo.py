"""Prep a photo for ASCII conversion: crop, (optionally) remove background, boost local contrast.

usage: python scripts/prep_photo.py source-photo.png [--crop x0,y0,x1,y1] [--rembg] [--clahe 2.5]
writes source-prepped.png (grayscale)
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
    ap.add_argument("--rembg", action="store_true", help="isolate the subject (needs `pip install rembg`)")
    ap.add_argument("--clahe", type=float, default=0, help="CLAHE clip limit; helps flat-lit faces, adds noise on textured scenes")
    args = ap.parse_args()

    img = Image.open(args.photo).convert("RGBA")
    if args.crop:
        img = img.crop(tuple(int(v) for v in args.crop.split(",")))
    if args.rembg:
        from rembg import remove  # heavy dependency, only imported when asked for

        img = remove(img)

    # Composite onto white so any removed background maps to the blank end of the ramp.
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    gray = np.array(Image.alpha_composite(white, img).convert("L"))

    if args.clahe:  # gives flat regions real highlights and shadows
        gray = cv2.createCLAHE(clipLimit=args.clahe, tileGridSize=(4, 4)).apply(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)  # soften fine texture so it doesn't print as noise

    Image.fromarray(gray).save(OUT)
    print(f"wrote {OUT} {gray.shape[1]}x{gray.shape[0]}")


if __name__ == "__main__":
    main()
