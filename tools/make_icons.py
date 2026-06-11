"""Generate the DeveloperOS app icons (slice 12, D-0029).

Stdlib-only (zlib + struct) so icon regeneration needs no image library —
consistent with the project's zero-dependency rule. The mark is the brand
spec from D-0029: a terminal-prompt glyph (">_") in the dashboard accent
color on the dashboard panel color, drawn from rectangle/diagonal primitives
so no font is required and it renders identically at every size.

Run from the repo root:  python tools/make_icons.py
Output (committed, vendored): devos/api/static/icons/*.png
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

BG = (0x0F, 0x11, 0x17, 0xFF)        # --bg / manifest theme color
ACCENT = (0x6E, 0xA8, 0xFE, 0xFF)    # --accent
TRANSPARENT = (0, 0, 0, 0)

OUT_DIR = Path(__file__).resolve().parents[1] / "devos" / "api" / "static" / "icons"


def png_bytes(size: int, pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in pixels)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def write_png(path: Path, size: int, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    path.write_bytes(png_bytes(size, pixels))


def write_ico(path: Path, sizes: tuple[int, ...]) -> None:
    """Multi-size Windows .ico with PNG-format entries (valid since Vista).

    ICONDIR + one ICONDIRENTRY per image + the raw PNG blobs — stdlib struct
    only, same zero-dependency rule as the PNG writer (D-0031).
    """
    images = [png_bytes(s, render(s, maskable=False)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    entries = b""
    offset = len(header) + 16 * len(sizes)
    for size, blob in zip(sizes, images):
        dim = 0 if size >= 256 else size  # 0 encodes 256 in ICO entries
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(images))


def render(size: int, *, maskable: bool) -> list[list[tuple[int, int, int, int]]]:
    """Rounded-square icon, or full-bleed background with a safe-zone mark (maskable)."""
    s = float(size)
    radius = 0.0 if maskable else 0.22 * s
    # Maskable icons must keep the mark inside the central ~60% safe zone.
    shrink = 0.78 if maskable else 1.0

    def inside_bg(x: float, y: float) -> bool:
        if maskable:
            return True
        # Rounded-rect test: distance from the clamped "core rectangle" point.
        r = radius
        cx = min(max(x, r), s - r)
        cy = min(max(y, r), s - r)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

    # Glyph geometry (fractions of the canvas, centered then shrunk for maskable).
    def g(v: float) -> float:
        return s / 2 + (v - 0.5) * s * shrink

    stroke = 0.075 * s * shrink
    chev_x, chev_top, chev_mid, chev_bot = g(0.24), g(0.32), g(0.50), g(0.68)
    under_x0, under_x1 = g(0.52), g(0.78)
    under_y0, under_y1 = g(0.625), g(0.68 + 0.005)

    def on_chevron(x: float, y: float) -> bool:
        # Two diagonal strokes:  \  (top->mid) then  /  (mid->bottom), forming ">".
        if chev_top <= y <= chev_mid:
            t = (y - chev_top) / (chev_mid - chev_top)
        elif chev_mid < y <= chev_bot:
            t = (chev_bot - y) / (chev_bot - chev_mid)
        else:
            return False
        cx = chev_x + t * (chev_mid - chev_top)  # 45-degree slope
        return abs(x - cx) <= stroke / 2

    def on_underscore(x: float, y: float) -> bool:
        return under_x0 <= x <= under_x1 and under_y0 <= y <= under_y1

    rows = []
    for j in range(size):
        row = []
        y = j + 0.5
        for i in range(size):
            x = i + 0.5
            if not inside_bg(x, y):
                row.append(TRANSPARENT)
            elif on_chevron(x, y) or on_underscore(x, y):
                row.append(ACCENT)
            else:
                row.append(BG)
        rows.append(row)
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-192.png", 192, True),
        ("icon-maskable-512.png", 512, True),
        ("apple-touch-icon.png", 180, False),
    ]
    for name, size, maskable in targets:
        write_png(OUT_DIR / name, size, render(size, maskable=maskable))
        print(f"wrote {OUT_DIR / name} ({size}x{size}{', maskable' if maskable else ''})")
    ico_path = Path(__file__).resolve().parents[1] / "packaging" / "devos.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    write_ico(ico_path, (16, 32, 48, 256))
    print(f"wrote {ico_path} (16/32/48/256, PNG entries)")


if __name__ == "__main__":
    main()
