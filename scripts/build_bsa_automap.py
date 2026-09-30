"""Bakes the Portuguese translation into AUTOMAP.IMG - the automap
parchment background: a compass rose (N/S/E/W) and an "Exit" label at
the bottom. Found via the "varredura_img_bruta.py" bulk scan (see
docs/inventario-arquivos.md, seção 4).

Uncompressed (type 0), with its OWN embedded palette (unlike most of
the recently-found screens) - no palette guessing needed. The
background is a plain, evenly-lit parchment scroll with no artwork to
protect (same style as LOGBOOK.IMG/BUYSPELL.IMG), so erasing is a flat
fill with the dominant parchment tone (palette index 5). The compass
letters/the "Exit" label are hand-drawn brown ink with soft
anti-aliasing (several close brown shades, not one flat color) -
sampled a representative mid-tone for the redrawn text instead of
trying to reproduce that anti-aliasing.

N and S stay as-is (Norte/Sul share the same initial in Portuguese);
E -> L (Leste) and W -> O (Oeste).

Reads and overwrites the pristine copy split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG`.

Usage: python3 scripts/build_bsa_automap.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"
INK = (90, 55, 25)
BG_INDEX = 5

Box = tuple[int, int, int, int]


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def draw_centered(draw: ImageDraw.ImageDraw, center_x: float, center_y: float, text: str, size: int) -> None:
    font = ImageFont.truetype(NOTO_SERIF_ITALIC, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(center_y - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=INK)


# (erase_box, text, size, center_x, center_y) - measured against the
# pristine ink pixels of each compass letter and the "Exit" label.
# N's box top was originally 16, overlapping the top border's own
# drop-shadow gradient band (a uniform-per-row texture from y=14 to
# y=20, confirmed against Originais/GLOBAL.BSA directly - GLOBAL_parts/
# had gone stale with an earlier erase baked back in via a later
# compile_images.py run, which is what made this look "already fine"
# on a first pass). Flat-filling into that band left a visible seam
# where the gradient abruptly cut off. The real "N" ink only starts
# around y=25, so the box top moved down to right where the shadow
# band's own uniform texture ends (y=21) - still comfortable margin
# above the glyph, without touching the border's shadow at all.
# Re-measured the compass cross itself directly (isolating its strong
# ink color per arm - value 11 vertical, 10 horizontal - from the
# surrounding parchment noise and the small diagonal tick decorations,
# which share ink shades with the letters and were throwing off a
# naive "any non-background pixel" scan): true center (271.5, 48),
# tip positions N=39, S=57, W=258, E=285. Every label below now sits a
# consistent ~3px off its own tip, centered on the cross's actual axis
# (271.5 for N/S, 48 for O/L) rather than the old ad hoc centers.
LABELS: list[tuple[Box, str, int, float, float]] = [
    # Bottom stays 36 (3px above the north tip at 39); top stays 21
    # (the top border's own drop-shadow band ends there - see below).
    ((260, 21, 283, 36), "N", 16, 271.5, 28.5),
    ((260, 60, 283, 75), "S", 16, 271.5, 67.5),
    # Right edge widened back to 258: the pristine "W" ink actually
    # reaches x=257 (1px short of the bar's own tip at 258), so 255
    # left a sliver of the original English letter showing.
    ((238, 40, 258, 56), "O", 14, 248, 48),
    # Left edge moved back to 287: the pristine "E" ink's topmost
    # stroke reaches x=287 (1px short of the bar's own tip at 285),
    # same class of leftover-sliver issue as O/"W" above.
    ((287, 40, 300, 56), "L", 14, 293.5, 48),
    ((240, 156, 285, 179), "Sair", 15, 262, 167),
]
# N's box top was originally 16, overlapping the top border's own
# drop-shadow gradient band (a uniform-per-row texture from y=14 to
# y=20, confirmed against Originais/GLOBAL.BSA directly - GLOBAL_parts/
# had gone stale with an earlier erase baked back in via a later
# compile_images.py run, which is what made this look "already fine"
# on a first pass). Flat-filling into that band left a visible seam
# where the gradient abruptly cut off. The real "N" ink only starts
# around y=25, so the box top moved down to right where the shadow
# band's own uniform texture ends (y=21).
#
# S's box originally started at 56, 4px into the cross's own bottom
# tip (ends at y=57 - see the fresh measurement above); "S" itself
# only starts around y=62.
#
# O/L originally left/right too much empty space around the compass
# (not visibly wrong, just far from the arrow tips) and weren't
# centered on the horizontal arm's actual y=48 center.


def build() -> None:
    filedata = (PARTS_DIR / "AUTOMAP.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 0, "AUTOMAP.IMG is expected to be uncompressed"
    assert (flags & 0x100) != 0, "AUTOMAP.IMG is expected to have an embedded palette"

    pixels = filedata[12:12 + width * height]
    pal_region = filedata[12 + length:12 + length + 768]

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in pal_region]

    all_boxes = [box for box, _, _, _, _ in LABELS]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_flat(px, width, box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for box, text, size, cx, cy in LABELS:
        draw_centered(draw, cx, cy, text, size)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "AUTOMAP.png")
    print(f"  AUTOMAP.IMG: wrote legivel/AUTOMAP.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "AUTOMAP_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated AUTOMAP.IMG (GLOBAL_parts/legivel/)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
