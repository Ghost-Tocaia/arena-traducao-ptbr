"""Bakes the Portuguese translation into POPUP3.IMG and POPUP4.IMG - the
inventory-list header bars shown when browsing weapons ("NAME / HANDS /
WEIGHT / COST") and armor ("NAME / PROTECTS / WEIGHT / COST").

Both files are uncompressed (flags & 0xFF == 0, comp type 0) with no
embedded palette - the real palette (found by trial, like every other
screen here) is PAL.COL. Being uncompressed means there's no
encode/decode round trip to worry about: the pixel buffer is written
back exactly the same length, in place of the original.

The header text is a genuinely tiny bitmap font baked into the original
(each word's ink - palette index 96, RGB (231,215,0) - occupies only
~6px of height), so this is closer in scale to CHARSTAT.IMG's labels
than to a banner title. Both files share the exact same header layout
(measured from the pristine pixels): every word sits at y 20-25 with
NAME left-aligned starting at x=42, and HANDS/PROTECTS, WEIGHT, COST
each right-aligned to their own column edge (211 / 245 / 281) - the
same right-align-by-column pattern established in CHARSTAT.IMG, since
these are headers over what will be right-aligned numeric/short values.

Reads the pristine copies split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (still
uncompressed, per img_manifest.py), written back to
"GLOBAL_parts/<nome>.IMG" (the same place split_bsa.py extracted it),
which merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_popup.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (231, 215, 0)  # sampled palette index 96
INK_INDEX = 96

Box = tuple[int, int, int, int]

# (erase_box, text, size, column_right_x) for right-aligned words;
# NAME is handled separately since it's left-aligned.
NAME_BOX: Box = (40, 18, 62, 27)
NAME_TEXT = "NOME"
NAME_LEFT_X = 42
NAME_SIZE = 6

RowSpec = tuple[Box, str, int, int]


def _region_is_clean(pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 18 or y0 < 14 or x1 > 300 or y1 > 108:
        return False
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pristine[y * width + x] == INK_INDEX:
                return False
            if any(bx0 <= x < bx1 and by0 <= y < by1 for bx0, by0, bx1, by1 in exclude):
                return False
    return True


def erase_box(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> None:
    """This panel's marble texture is subtle/low-contrast but drifts in
    average brightness across its width (a soft cloudy patch), so a
    hard clone of a same-size patch from elsewhere (the technique used
    for CHARSTAT.IMG/YESNO.IMG's high-contrast stone) leaves a visible
    seam here. A local ring-sampled fill (INTRO-panel style) blends in
    far better for this smoother texture, so this file skips cloning
    entirely and always fills from the immediate surrounding pixels."""
    x0, y0, x1, y1 = box
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
    fill = Counter(samples).most_common(1)[0][0] if samples else 111
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = fill


def draw_right_aligned(draw: ImageDraw.ImageDraw, anchor_x1: float, anchor_ybottom: float, text: str, size: int) -> None:
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(anchor_x1 - (bbox[2] - bbox[0])) - bbox[0]
    y = round(anchor_ybottom - bbox[3])
    draw.text((x, y), text, font=font, fill=INK)


def draw_left_aligned(draw: ImageDraw.ImageDraw, anchor_x0: float, anchor_ybottom: float, text: str, size: int) -> None:
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(anchor_x0) - bbox[0]
    y = round(anchor_ybottom - bbox[3])
    draw.text((x, y), text, font=font, fill=INK)


# per-file right-aligned rows: (erase_box, text, size, column_right_x)
ROWS: dict[str, list[RowSpec]] = {
    "POPUP3.IMG": [
        ((188, 18, 214, 27), "MAOS", 6, 211),
        ((217, 18, 248, 27), "PESO", 6, 245),
        ((263, 18, 284, 27), "CUSTO", 6, 281),
    ],
    "POPUP4.IMG": [
        ((177, 18, 214, 27), "PROTEGE", 6, 211),
        ((217, 18, 248, 27), "PESO", 6, 245),
        ((263, 18, 284, 27), "CUSTO", 6, 281),
    ],
}

ROW_YBOTTOM = 26  # original glyphs' tight bottom edge (y=25) + 1


def build(name: str) -> None:
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 0, f"{name} is expected to be uncompressed"
    assert (flags & 0x100) == 0, f"{name} is expected to have no embedded palette"

    pixels = filedata[12:12 + width * height]

    col_raw = (ORIG_DIR / "PAL.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    rows = ROWS[name]
    all_boxes = [NAME_BOX] + [box for box, _, _, _ in rows]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_box(px, pixels, width, height, box, all_boxes)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    draw_left_aligned(draw, NAME_LEFT_X, ROW_YBOTTOM, NAME_TEXT, NAME_SIZE)
    for box, text, size, right_x in rows:
        draw_right_aligned(draw, right_x, ROW_YBOTTOM, text, size)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    assert len(new_pixels) == length, f"{name}: pixel buffer size changed unexpectedly"

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    stem = name.rsplit(".", 1)[0]
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / f"{stem}.png")
    print(f"  {name}: wrote legivel/{stem}.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 4, height * 4), Image.NEAREST).save(
        PREVIEW_DIR / f"{name.replace('.', '_')}_traduzido.png"
    )


def main() -> None:
    print("Building translated POPUP3.IMG/POPUP4.IMG (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build("POPUP3.IMG")
    build("POPUP4.IMG")
    print("Done.")


if __name__ == "__main__":
    main()
