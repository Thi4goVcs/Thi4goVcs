"""Render data/contributions.json as an animated 53x7 heatmap SVG (contrib-heatmap.svg)."""
import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"
STATIC = os.environ.get("STATIC") == "1"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 = the single best day)
MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
WEEKDAYS = {1: "seg", 3: "qua", 5: "sex"}

W, GAP, TOP = 860, 3, 62
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    days = data["days"]
    best = data["best_day"]

    first = date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7  # GitHub columns start on Sunday
    cells, month_labels = [], []
    for i, d in enumerate(days):
        col, row = divmod(i + offset, 7)
        dt = date.fromisoformat(d["date"])
        if row == 0 and dt.day <= 7 and col < 52:  # first Sunday of a month starts its label
            month_labels.append((col, MONTHS[dt.month - 1]))
        level = d["level"]
        if d["count"] and d["date"] == best["date"]:
            level = 5
        cells.append((col, row, level, d))

    n_cols = cells[-1][0] + 1
    step = min(15, (W - 90) // n_cols)
    cell = step - GAP
    grid_w = n_cols * step - GAP
    left = (W - grid_w) // 2 + 10  # nudge right to leave room for weekday labels
    grid_h = 7 * step - GAP
    legend_y = TOP + grid_h + 22
    stats_y = legend_y + 28
    H = stats_y + 22

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{fmt_int(data["total"])} contribuições no último ano">'
    ]
    if not STATIC:
        out.append(
            "<style>"
            ".c{opacity:0;transform-box:fill-box;transform-origin:center;"
            "animation:drop .45s cubic-bezier(.2,.8,.2,1) forwards}"
            "@keyframes drop{from{opacity:0;transform:translateY(-8px) scale(.4)}"
            "to{opacity:1;transform:none}}"
            ".f{opacity:0;animation:fade .6s ease-out forwards}"
            "@keyframes fade{to{opacity:1}}"
            "</style>"
        )
    out.append(f'<rect width="{W}" height="{H}" rx="10" fill="#0d1117" stroke="#30363d"/>')
    # title bar
    out.append(
        f'<g font-family="{FONT}" font-size="13">'
        f'<circle cx="20" cy="20" r="5" fill="#ff5f56"/><circle cx="36" cy="20" r="5" fill="#ffbd2e"/>'
        f'<circle cx="52" cy="20" r="5" fill="#27c93f"/>'
        f'<text x="{W / 2}" y="24" fill="#8b949e" text-anchor="middle">contribuições — {data["username"]}</text>'
        "</g>"
    )
    out.append(f'<g font-family="{FONT}" font-size="10" fill="#8b949e">')
    for col, name in month_labels:
        out.append(f'<text x="{left + col * step}" y="{TOP - 8}">{name}</text>')
    for row, name in WEEKDAYS.items():
        out.append(f'<text x="{left - 8}" y="{TOP + row * step + 9}" text-anchor="end">{name}</text>')
    out.append("</g>")

    for col, row, level, d in cells:
        x, y = left + col * step, TOP + row * step
        delay = "" if STATIC else f' style="animation-delay:{(col + row) * 0.025:.3f}s"'
        n = d["count"]
        label = f'{n} contribuiç{"ão" if n == 1 else "ões"} em {fmt_date(d["date"])}'
        out.append(
            f'<rect class="c" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" '
            f'fill="{PALETTE[level]}"{delay}><title>{label}</title></rect>'
        )

    end = (52 + 7) * 0.025 + 0.3
    fade = "" if STATIC else f' class="f" style="animation-delay:{end:.2f}s"'
    lx = left + grid_w - 6 * step - 30
    out.append(f'<g font-family="{FONT}" font-size="11" fill="#8b949e"{fade}>')
    out.append(f'<text x="{lx - 8}" y="{legend_y + 10}" text-anchor="end">menos</text>')
    for i, color in enumerate(PALETTE):
        out.append(f'<rect x="{lx + i * step}" y="{legend_y}" width="{cell}" height="{cell}" rx="2.5" fill="{color}"/>')
    out.append(f'<text x="{lx + 6 * step + 5}" y="{legend_y + 10}">mais</text>')
    stats = (
        f'<tspan fill="#39d353" font-weight="bold">{fmt_int(data["total"])}</tspan> contribuições no último ano'
        f'  ·  sequência atual <tspan fill="#c9d1d9">{data["current_streak"]}d</tspan>'
        f'  ·  recorde <tspan fill="#c9d1d9">{data["longest_streak"]}d</tspan>'
    )
    if best["count"]:
        stats += f'  ·  melhor dia <tspan fill="#c9d1d9">{fmt_date(best["date"])} ({best["count"]})</tspan>'
    out.append(f'<text x="{left}" y="{stats_y}" font-size="12">{stats}</text>')
    out.append("</g></svg>")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
