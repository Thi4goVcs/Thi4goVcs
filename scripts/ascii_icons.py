"""Rasterize small SVG logos (scripts/icons/*.svg) into colored ASCII glyph blocks.

Each path is filled with even-odd at high resolution, then downsampled so each character cell's
coverage picks a glyph from the ramp (soft edges print lighter glyphs) and its dominant path
picks the color.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from svgelements import SVG, Path as SvgPath

ICONS = Path(__file__).resolve().parent / "icons"
RES = 480  # raster size of the icon's longer side before downsampling
MIN_LUMA = 0.45  # brand colors darker than this get lifted so they read on the dark card


def _lift(hex_color: str) -> str:
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255
    luma = rgb @ [0.2126, 0.7152, 0.0722]
    if luma < MIN_LUMA:
        rgb = rgb + (1 - rgb) * (MIN_LUMA - luma) / (1 - luma)
    return "#" + "".join(f"{round(c * 255):02x}" for c in rgb)


def _path_masks(name: str, sub_colors: list[str] | None) -> list[tuple[np.ndarray, str | None]]:
    """One even-odd mask per color. sub_colors optionally recolors subpaths in document order
    (e.g. the Python logo is a single path; its first snake + eye are blue, the second yellow)."""
    svg = SVG.parse(str(ICONS / f"{name}.svg"), width=RES, height=RES)
    groups: dict[str | None, Image.Image] = {}
    i = 0
    for el in svg.elements():
        if not isinstance(el, SvgPath) or len(el) == 0:
            continue
        fill = el.values.get("fill")  # raw attribute; svgelements defaults unset fills to black
        fill = el.fill.hexrgb if fill and fill.startswith("#") else None
        for sub in el.as_subpaths():
            sub = SvgPath(sub)
            color = sub_colors[i] if sub_colors else fill
            i += 1
            n = max(int(sub.length(error=1e-2) / 2), 8)
            pts = [tuple(p) for p in sub.npoint(np.linspace(0, 1, n))]
            layer = Image.new("1", (RES, RES), 0)
            ImageDraw.Draw(layer).polygon(pts, fill=1)
            mask = groups.get(color, Image.new("1", (RES, RES), 0))
            groups[color] = ImageChops.logical_xor(mask, layer)  # even-odd: nested subpaths cut holes
    return [(np.asarray(m, dtype=np.float32), c) for c, m in groups.items()]


def icon_block(name: str, cols: int, rows: int, ramp: str, color: str,
               sub_colors: list[str] | None = None) -> tuple[list[str], list[list[str | None]]]:
    """Return (lines, colors) for an icon fitted into cols x rows character cells."""
    masks = _path_masks(name, sub_colors)
    union = np.clip(sum(m for m, _ in masks), 0, 1)
    ys, xs = np.where(union > 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    side = max(y1 - y0, x1 - x0)
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2

    def cells(a: np.ndarray) -> np.ndarray:
        # Square crop around the icon, then area-average into the (non-square) character grid.
        canvas = np.zeros((side, side), dtype=np.float32)
        oy, ox = int(side / 2 - (cy - y0)), int(side / 2 - (cx - x0))
        canvas[oy:oy + (y1 - y0), ox:ox + (x1 - x0)] = a[y0:y1, x0:x1]
        return np.asarray(Image.fromarray(canvas).resize((cols, rows), Image.BOX))

    cov = [cells(m) for m, _ in masks]
    total = np.clip(sum(cov), 0, 1)
    idx = np.where(total > 0.08, 1 + (total * (len(ramp) - 2)).round(), 0).astype(int)
    owner = np.argmax(np.stack(cov), axis=0)
    lines = ["".join(ramp[i] for i in row) for row in idx]
    colors = [
        [(_lift(masks[owner[r, c]][1] or color) if idx[r, c] else None) for c in range(cols)]
        for r in range(rows)
    ]
    return lines, colors
