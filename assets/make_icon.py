#!/usr/bin/env python3
"""
assets/make_icon.py — genera assets/icona.ico (e .png) per FileAI.

Disegno minimale coerente con assets/icona.svg: cartella + scintilla AI,
palette Tokyo Night. Render in super-sampling per bordi netti.

USO:
    pip install Pillow
    python assets/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent
SS = 4               # super-sampling factor
S = 1024 * SS        # canvas ad alta risoluzione

BG = (26, 27, 38, 255)        # #1a1b26
BLUE = (122, 162, 247, 255)   # #7aa2f7
CYAN = (125, 207, 255, 255)   # #7dcfff
PURPLE = (187, 154, 247, 255) # #bb9af7
WHITE = (255, 255, 255, 255)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


def vgrad(draw, box, top, bottom):
    x0, y0, x1, y1 = box
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, (y1 - y0))
        draw.line([(x0, y), (x1, y)], fill=lerp(top, bottom, t))


def spark(cx, cy, r, color):
    """Stella a 4 punte (scintilla AI) come poligono con lati concavi."""
    k = 0.18  # quanto i lati rientrano verso il centro
    pts = []
    # 4 punte (su, dx, giù, sx) alternate ai punti interni
    tips = [(0, -r), (r, 0), (0, r), (-r, 0)]
    inner = r * k
    diag = [(inner, -inner), (inner, inner), (-inner, inner), (-inner, -inner)]
    for i in range(4):
        pts.append((cx + tips[i][0], cy + tips[i][1]))
        pts.append((cx + diag[i][0], cy + diag[i][1]))
    return pts, color


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def render():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # sfondo scuro arrotondato
    rounded(d, (0, 0, S, S), 224 * SS, BG)

    u = SS  # scala per coordinate prese dall'SVG (viewBox 1024)

    # linguetta cartella
    d.polygon([
        (232 * u, 300 * u), (468 * u, 300 * u), (532 * u, 384 * u),
        (232 * u, 384 * u),
    ], fill=BLUE)

    # corpo cartella con gradiente cyan→blu (su rettangolo arrotondato)
    body = (208 * u, 372 * u, 816 * u, 764 * u)
    # disegno gradiente clippato dentro la forma arrotondata
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    vgrad(gd, body, CYAN, BLUE)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle(body, radius=44 * u, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # scintilla grande
    pts, col = spark(620 * u, 510 * u, 118 * u, WHITE)
    # gradiente fittizio: bianco verso viola -> uso colore medio brillante
    d.polygon(pts, fill=lerp(WHITE, PURPLE, 0.35))
    # scintilla piccola
    pts2, col2 = spark(732 * u, 652 * u, 54 * u, WHITE)
    d.polygon(pts2, fill=WHITE)

    # downscale ad alta qualità
    base = img.resize((1024, 1024), Image.LANCZOS)

    png = ASSETS / "icona.png"
    base.save(png)

    ico = ASSETS / "icona.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base.save(ico, sizes=[(s, s) for s in sizes])

    print(f"OK  ->  {png.name}, {ico.name}  (sizes: {sizes})")


if __name__ == "__main__":
    render()
