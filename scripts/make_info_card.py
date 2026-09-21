"""Hand-authored neofetch-style info card (info-card.svg). Edit INFO below and re-run."""
import os
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"
STATIC = os.environ.get("STATIC") == "1"

USER, HOST = "thiago", "github"
INFO = [
    ("Nome", "Thiago Vinicius"),
    ("Foco", "Dev & Dados — Python, SQL, APIs"),
    ("Agora", "Estudando todo dia e documentando o processo aqui"),
    ("OS", "Windows 11 + WSL2"),
    ("Stack", "Python · FastAPI · SQLite · SQL · JavaScript · HTML/CSS · OpenCV · OpenFOAM"),
    (None, None),
    ("Projetos", ""),
    ("›", "Aerodynamic Simulation — GUI que automatiza CFD de perfis NACA com OpenFOAM"),
    ("›", "todo-api — API REST (CRUD) com FastAPI + SQLite"),
    ("›", "mottu-dashboard — dashboard de dados em Python"),
    ("›", "organizador-arquivos — organiza pastas por tipo de arquivo"),
    ("›", "lista-tarefas-web — to-do em JS puro, salvo no navegador"),
    (None, None),
    ("Perfil", "github.com/Thi4goVcs"),
]

W, H = 490, 606  # height matches the portrait column (370/404 * 662) so the table rows line up
PAD, LINE_H, CHAR_W = 22, 21, 7.8
WRAP = int((W - 2 * PAD) / CHAR_W)
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
KEY, VAL, DIM, ACCENT = "#39d353", "#c9d1d9", "#8b949e", "#58a6ff"
BLOCKS = ["#484f58", "#ff7b72", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#f0f6fc"]
DELAY = 0.12


def build_lines() -> list[str]:
    """Return SVG <tspan> contents for each visual line."""
    lines = [
        f'<tspan fill="{KEY}" font-weight="bold">{USER}</tspan><tspan fill="{VAL}">@</tspan>'
        f'<tspan fill="{KEY}" font-weight="bold">{HOST}</tspan>',
        f'<tspan fill="{DIM}">{"-" * (len(USER) + len(HOST) + 1)}</tspan>',
    ]
    for key, val in INFO:
        if key is None:
            lines.append("")
            continue
        if key == "›":
            name, _, desc = val.partition(" — ")
            wrapped = textwrap.wrap(f"{name} — {desc}", WRAP - 4)
            first = wrapped[0][len(name):]
            lines.append(
                f'  <tspan fill="{ACCENT}">›</tspan> <tspan fill="{VAL}" font-weight="bold">{escape(name)}</tspan>'
                f'<tspan fill="{DIM}">{escape(first)}</tspan>'
            )
            lines += [f'    <tspan fill="{DIM}">{escape(w)}</tspan>' for w in wrapped[1:]]
            continue
        prefix = f"{key}: "
        wrapped = textwrap.wrap(val, WRAP - len(prefix)) or [""]
        lines.append(f'<tspan fill="{KEY}" font-weight="bold">{escape(key)}</tspan><tspan fill="{VAL}">: {escape(wrapped[0])}</tspan>')
        lines += [f'{" " * len(prefix)}<tspan fill="{VAL}">{escape(w)}</tspan>' for w in wrapped[1:]]
    return lines


def main() -> None:
    lines = build_lines()
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-label="Thiago Vinicius — informações">'
    ]
    if not STATIC:
        out.append(
            "<style>.l{opacity:0;animation:in .4s ease-out forwards}"
            "@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}</style>"
        )
    out.append(f'<rect width="{W}" height="{H}" rx="10" fill="#0d1117" stroke="#30363d"/>')
    out.append(
        '<circle cx="20" cy="20" r="5" fill="#ff5f56"/><circle cx="36" cy="20" r="5" fill="#ffbd2e"/>'
        '<circle cx="52" cy="20" r="5" fill="#27c93f"/>'
        f'<text x="{W / 2}" y="24" font-family="{FONT}" font-size="13" fill="{DIM}" text-anchor="middle">'
        "~ neofetch</text>"
        f'<line x1="0" y1="40" x2="{W}" y2="40" stroke="#21262d"/>'
    )

    y0 = 72
    out.append(f'<g font-family="{FONT}" font-size="13">')
    n = 0
    for i, content in enumerate(lines):
        if not content:
            continue
        anim = "" if STATIC else f' class="l" style="animation-delay:{0.3 + n * DELAY:.2f}s"'
        out.append(f'<text x="{PAD}" y="{y0 + i * LINE_H}" xml:space="preserve"{anim}>{content}</text>')
        n += 1
    by = y0 + (len(lines) + 1) * LINE_H - 10
    anim = "" if STATIC else f' class="l" style="animation-delay:{0.3 + n * DELAY:.2f}s"'
    out.append(f"<g{anim}>")
    for j, color in enumerate(BLOCKS):
        out.append(f'<rect x="{PAD + j * 26}" y="{by}" width="24" height="14" rx="2" fill="{color}"/>')
    out.append("</g>")
    end = 0.3 + (n + 1) * DELAY + 0.4
    blink = "" if STATIC else (
        f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.01;0.5;0.51;1" dur="1.1s" '
        f'begin="{end:.2f}s" repeatCount="indefinite"/>'
    )
    hidden = "" if STATIC else ' opacity="0"'
    anim = "" if STATIC else f' class="l" style="animation-delay:{0.3 + (n + 1) * DELAY:.2f}s"'
    out.append(
        f'<text x="{PAD}" y="{by + 44}"{anim}><tspan fill="{KEY}">{USER}@{HOST}</tspan>'
        f'<tspan fill="{DIM}"> ~ $ </tspan></text>'
        f'<rect x="{PAD + 7.8 * (len(USER) + len(HOST) + 6)}" y="{by + 32}" width="8" height="15" fill="{VAL}"'
        f'{hidden}>{blink}</rect>'
    )
    out.append("</g></svg>")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT} ({len(lines)} lines, last y={by + 44})")


if __name__ == "__main__":
    main()
