"""Convert source-prepped.png into a monochrome ASCII SVG that types itself in row by row."""
import os
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "ascii-portrait.svg"
STATIC = os.environ.get("STATIC") == "1"

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense); leading space clears the background
COLS = int(os.environ.get("COLS", 62))
CHAR_W, LINE_H = 6.0, 10.5  # glyph cell in SVG units; ~0.57 aspect of a monospace glyph
PAD = 16
FG, BG, CURSOR = "#c9d1d9", "#0d1117", "#39d353"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
ROW_DELAY, ROW_DUR = 0.055, 0.28
LEVELS = (0.15, 0.80)  # black/white points: bright walls go blank, only real shadows print dense


def to_rows(img: Image.Image) -> list[str]:
    w, h = img.size
    rows = round(COLS * (h / w) * (CHAR_W / LINE_H))
    arr = np.asarray(img.resize((COLS, rows), Image.LANCZOS), dtype=np.float32) / 255.0
    lo, hi = LEVELS
    arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    idx = ((1.0 - arr) * (len(RAMP) - 1)).round().astype(int)
    lines = ["".join(RAMP[i] for i in row).rstrip() for row in idx]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def main() -> None:
    lines = to_rows(Image.open(SRC).convert("L"))
    text_w = COLS * CHAR_W
    W = round(text_w + 2 * PAD)
    H = round(len(lines) * LINE_H + 2 * PAD)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-label="Retrato em ASCII">',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="#30363d"/>',
    ]
    if not STATIC:
        out.append("<defs>")
        for i in range(len(lines)):
            y = PAD + i * LINE_H
            begin = f"{i * ROW_DELAY:.3f}s"
            out.append(
                f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="0" height="{LINE_H + 1}">'
                f'<animate attributeName="width" from="0" to="{text_w}" begin="{begin}" dur="{ROW_DUR}s" fill="freeze"/>'
                "</rect></clipPath>"
            )
        out.append("</defs>")

    out.append(f'<g font-family="{FONT}" font-size="10" fill="{FG}" xml:space="preserve">')
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = PAD + i * LINE_H + LINE_H * 0.8
        clip = "" if STATIC else f' clip-path="url(#r{i})"'
        length = len(line) * CHAR_W
        out.append(
            f'<text x="{PAD}" y="{y:.1f}" xml:space="preserve" textLength="{length:.1f}" lengthAdjust="spacingAndGlyphs"{clip}>'
            f"{escape(line)}</text>"
        )
    out.append("</g>")

    if not STATIC:
        # A block cursor rides the wipe edge of each row, then parks blinking after the last one.
        out.append(f'<rect width="{CHAR_W}" height="{LINE_H - 1}" fill="{CURSOR}" opacity="0">')
        for i in range(len(lines)):
            y = PAD + i * LINE_H
            b = i * ROW_DELAY
            out.append(
                f'<set attributeName="y" to="{y:.1f}" begin="{b:.3f}s"/>'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + text_w}" begin="{b:.3f}s" dur="{ROW_DUR}s" fill="freeze"/>'
            )
        end = (len(lines) - 1) * ROW_DELAY + ROW_DUR
        out.append(f'<set attributeName="opacity" to="0.9" begin="0s"/>')
        out.append(f'<set attributeName="opacity" to="0" begin="{end:.3f}s"/>')
        out.append("</rect>")

    out.append("</svg>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT} ({COLS}x{len(lines)}, {W}x{H})")


if __name__ == "__main__":
    main()
