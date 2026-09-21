"""Convert source-prepped.png into a monochrome ASCII SVG that types itself in row by row.

Two modes, picked from the prepped image:
* cutout (image has alpha, from prep_photo.py --rembg): the subject is drawn as a positive on the
  dark card - bright pixels print dense glyphs - and the removed background prints nothing.
* scene (plain grayscale): dark pixels print dense glyphs, bright areas wash out to spaces.
"""
import os
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

from ascii_icons import icon_block

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "ascii-portrait.svg"
STATIC = os.environ.get("STATIC") == "1"

RAMP = " .`:-=+*cs#%@"  # sparse -> dense; leading space is the background
W, H = 404, 662  # fixed card size so the README table row stays aligned with the info card
PAD = 16
CHAR_W, LINE_H = 5.0, 8.75  # glyph cell in SVG units; ~0.57 aspect of a monospace glyph
COLS, ROWS = int((W - 2 * PAD) / CHAR_W), int((H - 2 * PAD) / LINE_H)
FG, BG, CURSOR = "#c9d1d9", "#0d1117", "#39d353"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
ROW_DELAY, ROW_DUR = 0.045, 0.22
SCENE_LEVELS = (0.15, 0.80)  # black/white points: bright walls go blank, only real shadows print dense
ALPHA_MIN = 100  # cutout pixels below this alpha count as background
LABEL = "#8b949e"
ICON_W, ICON_H = int(os.environ.get("ICON_W", 15)), int(os.environ.get("ICON_H", 9))
UI_UX = [
    r" _   _  ___",
    r"| | | ||_ _|",
    r"| |_| | | |",
    r" \___/ |___|",
    r" _   ___  __",
    r"| | | \ \/ /",
    r"| |_| |>  <",
    r" \___//_/\_\ ",
]
PAPER_PLANE = [
    r"            /|",
    r"         _/' |",
    r"      _/'  / |",
    r"   _/'   /   |",
    r"_/'    /  _-'",
    r"`-._ /  _-'",
    r"    `/-'",
]
# (svg name in scripts/icons or literal ASCII art, side, preferred top row, color,
#  per-subpath colors for an svg / per-row colors for art, label)
ICONS = [
    ("python", "L", 2, "#ffd43b", ["#3776ab"] * 2 + ["#ffd43b"] * 2, "python"),
    ("git", "R", 2, "#f05032", None, "git"),
    ("vscode", "L", 29, "#3fa9f5", None, "vscode"),
    ("csharp", "R", 29, "#a179dc", None, "c#"),
    (UI_UX, "L", 57, "#ff7262", ["#a259ff"] * 4 + ["#ff7262"] * 4, "design"),
    (PAPER_PLANE, "R", 57, "#79c0ff", None, "aviação"),
]


def fit(size: tuple[int, int], max_cols: int, max_rows: int) -> tuple[int, int]:
    """Largest (cols, rows) grid that keeps the image aspect inside max_cols x max_rows."""
    w, h = size
    aspect = (h / w) * (CHAR_W / LINE_H)  # rows per column
    cols = max_cols
    rows = round(cols * aspect)
    if rows > max_rows:
        rows = max_rows
        cols = round(rows / aspect)
    return cols, rows


def cutout_grid(img: Image.Image) -> np.ndarray:
    gray, alpha = img.getchannel("L"), img.getchannel("A")
    cols, rows = fit(img.size, COLS, ROWS - 2)
    g = np.asarray(gray.resize((cols, rows), Image.LANCZOS), dtype=np.float32)
    a = np.asarray(alpha.resize((cols, rows), Image.LANCZOS))
    subject = a >= ALPHA_MIN
    lo, hi = np.percentile(g[subject], (3, 97))
    b = np.clip((g - lo) / max(hi - lo, 1), 0, 1)
    # Subject never drops to the space glyph, so dark hair / glasses keep their outline.
    idx = np.where(subject, 1 + (b * (len(RAMP) - 2)).round(), 0).astype(int)
    grid = np.zeros((ROWS, COLS), dtype=int)
    top, left = (ROWS - rows) // 2, (COLS - cols) // 2
    grid[top:top + rows, left:left + cols] = idx
    return grid


def scene_grid(img: Image.Image) -> np.ndarray:
    cols, rows = fit(img.size, COLS, ROWS)
    arr = np.asarray(img.convert("L").resize((cols, rows), Image.LANCZOS), dtype=np.float32) / 255.0
    lo, hi = SCENE_LEVELS
    arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    return ((1.0 - arr) * (len(RAMP) - 1)).round().astype(int)


def place_icons(chars: list[list[str]], colors: list[list[str | None]], busy: np.ndarray) -> None:
    """Stamp each icon (plus its label) onto the grid on its side, sliding down past the figure."""
    rows, cols = busy.shape
    for source, side, pref, color, sub_colors, label in ICONS:
        if isinstance(source, str):
            block, block_colors = icon_block(source, ICON_W, ICON_H, RAMP, color, sub_colors)
        else:  # literal art, centered in the icon box
            pad_top = (ICON_H - len(source)) // 2
            pad_left = (ICON_W - max(map(len, source))) // 2
            block = [""] * pad_top + [" " * pad_left + line for line in source]
            row_colors = [None] * pad_top + (sub_colors or [color] * len(source))
            block_colors = [[row_colors[r]] * len(line) for r, line in enumerate(block)]
        col = 0 if side == "L" else cols - ICON_W
        h = ICON_H + 2  # icon, blank row, label
        for top in range(pref, rows - h + 1):
            if not busy[top:top + h, col:col + ICON_W].any():
                break
        else:
            raise SystemExit(f"no room for the {name} icon on side {side}")
        for r, line in enumerate(block):
            for c, ch in enumerate(line):
                if ch != " ":
                    chars[top + r][col + c], colors[top + r][col + c] = ch, block_colors[r][c]
        lc = col + (ICON_W - len(label)) // 2
        for c, ch in enumerate(label):
            chars[top + h - 1][lc + c], colors[top + h - 1][lc + c] = ch, LABEL
        busy[top:top + h, col:col + ICON_W] = True
        print(f"  {label:7s} rows {top}-{top + h - 1}, cols {col}-{col + ICON_W - 1}")


def styled(chars: list[str], colors: list[str | None]) -> str:
    """Row text with a <tspan> per run of colored glyphs; uncolored glyphs inherit the figure color."""
    out, i = [], 0
    while i < len(chars):
        j = i
        while j < len(chars) and colors[j] == colors[i]:
            j += 1
        run = escape("".join(chars[i:j]))
        out.append(f'<tspan fill="{colors[i]}">{run}</tspan>' if colors[i] else run)
        i = j
    return "".join(out)


def main() -> None:
    img = Image.open(SRC)
    cutout = "A" in img.getbands()
    grid = cutout_grid(img.convert("LA")) if cutout else scene_grid(img)
    chars = [[RAMP[i] for i in row] + [" "] * (COLS - len(row)) for row in grid]
    colors: list[list[str | None]] = [[None] * COLS for _ in grid]
    if cutout:
        # Keep a 2-column / 1-row gutter around the figure free of icons.
        busy = np.pad(grid > 0, ((0, 0), (0, COLS - grid.shape[1])))
        busy = busy | np.roll(busy, 1, 0) | np.roll(busy, -1, 0)
        for s in (1, 2):
            busy = busy | np.roll(busy, s, 1) | np.roll(busy, -s, 1)
        place_icons(chars, colors, busy)
    lines = ["".join(row).rstrip() for row in chars]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-label="Retrato em ASCII">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="#30363d"/>',
    ]
    rows = []  # (row index, first col, last col) of every non-empty line, in print order
    for i, line in enumerate(lines):
        if line.strip():
            rows.append((i, len(line) - len(line.lstrip()), len(line)))

    if not STATIC:
        out.append("<defs>")
        for n, (i, c0, c1) in enumerate(rows):
            x0, span = PAD + c0 * CHAR_W, (c1 - c0) * CHAR_W
            out.append(
                f'<clipPath id="r{i}"><rect x="{x0:.1f}" y="{PAD + i * LINE_H:.1f}" width="0" height="{LINE_H + 1}">'
                f'<animate attributeName="width" from="0" to="{span:.1f}" begin="{n * ROW_DELAY:.3f}s" '
                f'dur="{ROW_DUR}s" fill="freeze"/></rect></clipPath>'
            )
        out.append("</defs>")

    font_size = round(CHAR_W / 0.6, 2)
    out.append(f'<g font-family="{FONT}" font-size="{font_size}" fill="{FG}">')
    for i, _, c1 in rows:
        y = PAD + i * LINE_H + LINE_H * 0.8
        clip = "" if STATIC else f' clip-path="url(#r{i})"'
        out.append(
            f'<text x="{PAD}" y="{y:.1f}" xml:space="preserve" textLength="{c1 * CHAR_W:.1f}" '
            f'lengthAdjust="spacingAndGlyphs"{clip}>{styled(chars[i][:c1], colors[i][:c1])}</text>'
        )
    out.append("</g>")

    if not STATIC and rows:
        # A block cursor rides the wipe edge of each row and disappears after the last one.
        out.append(f'<rect width="{CHAR_W}" height="{LINE_H - 1}" fill="{CURSOR}" opacity="0">')
        for n, (i, c0, c1) in enumerate(rows):
            b = n * ROW_DELAY
            out.append(
                f'<set attributeName="y" to="{PAD + i * LINE_H:.1f}" begin="{b:.3f}s"/>'
                f'<animate attributeName="x" from="{PAD + c0 * CHAR_W:.1f}" to="{PAD + c1 * CHAR_W:.1f}" '
                f'begin="{b:.3f}s" dur="{ROW_DUR}s" fill="freeze"/>'
            )
        end = (len(rows) - 1) * ROW_DELAY + ROW_DUR
        out.append('<set attributeName="opacity" to="0.9" begin="0s"/>')
        out.append(f'<set attributeName="opacity" to="0" begin="{end:.3f}s"/>')
        out.append("</rect>")

    out.append("</svg>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} rows on a {COLS}x{ROWS} grid)")


if __name__ == "__main__":
    main()
