"""Bakes the Portuguese translation into NEWEQUIP.IMG - the dungeon loot
screen shown when looting a container, with a "Level: N" indicator and
a "Drop / Spellbook / Exit" button bar.

Unlike every other translated screen so far, this one is already LZSS
"type 4" compressed in the original (no Huffman-to-LZSS recompression
needed - just decode, edit, re-encode). No embedded palette. **Not
PAL.COL**: an earlier pass accepted PAL.COL by trial ("rendered
something legible" - a muddy dark red/orange mess with barely-readable
text) without comparing alternatives, the same mistake made and later
corrected for EQUIP.IMG/EQUIPB.IMG and SCROLL01/02.IMG (see
docs/pipeline-imagens.md). Side-by-side comparison against all 4
candidate `.COL` files confirms **CHARSHT.COL** is correct: a clean
teal/stone dungeon-loot look matching EQUIP.IMG's own (already-fixed)
screen family, with legible gold text throughout - not the orange/lava
theme PAL.COL produces. Ink color is palette index 253, RGB
(191,115,0) - happens to map to the same RGB under both palettes (like
EQUIP.IMG), so only the palette FILE loaded needed to change here.

The background here is a busy, high-contrast lava/marble texture (very
different from POPUP3/4's smooth low-contrast marble), so this file
uses the texture-clone erase technique from CHARSTAT.IMG/YESNO.IMG
rather than POPUP3/4's local-average fill - a flat fill would stand out
as a visible rectangle against this much noisier backdrop.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (per
img_manifest.py, still LZSS "type 4" like the original), written back
to "GLOBAL_parts/NEWEQUIP.IMG" (the same place split_bsa.py extracted
it), which merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_newequip.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (191, 115, 0)  # sampled palette index 253
INK_INDEX = 253
BG_INDEX = 250

Box = tuple[int, int, int, int]


def _region_is_clean(pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        return False
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pristine[y * width + x] == INK_INDEX:
                return False
            if any(bx0 <= x < bx1 and by0 <= y < by1 for bx0, by0, bx1, by1 in exclude):
                return False
    return True


def erase_box(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    offsets = [
        (w, 0), (-w, 0), (2 * w, 0), (-2 * w, 0),
        (0, h), (0, -h), (0, 2 * h), (0, -2 * h),
    ]
    for dx, dy in offsets:
        candidate = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        if _region_is_clean(pristine, width, height, candidate, exclude):
            cx0, cy0, cx1, _ = candidate
            for row in range(h):
                src_row = (cy0 + row) * width
                dst_row = (y0 + row) * width
                px[dst_row + x0:dst_row + x1] = pristine[src_row + cx0:src_row + cx1]
            return

    r = 4
    samples: list[int] = []
    while len(samples) < 15 and r <= 30:
        samples = [
            pristine[yy * width + xx]
            for yy in range(max(0, y0 - r), min(height, y1 + r))
            for xx in range(max(0, x0 - r), min(width, x1 + r))
            if pristine[yy * width + xx] != INK_INDEX
            and not (x0 <= xx < x1 and y0 <= yy < y1)
            and not any(bx0 <= xx < bx1 and by0 <= yy < by1 for bx0, by0, bx1, by1 in exclude)
        ]
        r += 4
    fill = Counter(samples).most_common(1)[0][0] if samples else BG_INDEX
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = fill


def draw_centered(draw: ImageDraw.ImageDraw, center_x: float, center_y: float, text: str, size: int) -> None:
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(center_y - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=INK)


# (erase_box, text, size, center_x, center_y) - measured against the
# pristine ink pixels: LEVEL x105-125 y23-29; DROP x16-30 y192-198;
# SPELLBOOK x67-101 y192-198; EXIT x138-152 y191-197. Button centers
# use the button bar's own interior (dividers at x≈45 and x≈122), not
# just the text bbox.
LABELS: list[tuple[Box, str, int, float, float]] = [
    ((98, 19, 132, 32), "Nivel:", 7, 115, 29),
    ((10, 188, 36, 200), "LARGAR", 6, 23, 195),
    ((60, 188, 108, 200), "GRIMORIO", 7, 83, 195),
    ((132, 187, 158, 200), "SAIR", 8, 145, 195),
]


def build() -> None:
    filedata = (PARTS_DIR / "NEWEQUIP.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 4, "NEWEQUIP.IMG is expected to be type-4 (LZSS) compressed"
    assert (flags & 0x100) == 0, "NEWEQUIP.IMG is expected to have no embedded palette"

    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    pixels = bytes(pixels)

    col_raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    all_boxes = [box for box, _, _, _, _ in LABELS]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_box(px, pixels, width, height, box, all_boxes)

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
    im_out.save(LEGIVEL_DIR / "NEWEQUIP.png")
    print(f"  NEWEQUIP.IMG: wrote legivel/NEWEQUIP.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 3, height * 3), Image.NEAREST).save(
        PREVIEW_DIR / "NEWEQUIP_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated NEWEQUIP.IMG (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build()
    print("Done.")


if __name__ == "__main__":
    main()
