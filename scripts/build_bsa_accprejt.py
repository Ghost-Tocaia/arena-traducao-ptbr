"""Bakes the Portuguese translation into ACCPREJT.IMG - the "Accept /
Reject" button bar (a negotiation/offer response prompt).

Found manually by the user going through varredura_imagens/ (not part
of the earlier 26-screen batch) - see docs/inventario-arquivos.md
seção 4.

Same shape as NEWMENU.IMG/YESNO.IMG: type 8 (Huffman) compressed, no
embedded palette, real palette found by trial (all 4 candidates
compared side by side, only PAL.COL renders legible letters instead of
noise) as PAL.COL. Ink color also happens to be the exact same sampled
tone as NEWMENU.IMG's (palette index 192, RGB (215,159,7)) - both
button bars share this palette file, so this isn't a coincidence, just
worth re-verifying per file per this project's own rule (see that
script's own comment) rather than assumed.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (per
img_manifest.py, recompressed as LZSS "type 4" since there's no type-8
encoder), written back to "GLOBAL_parts/ACCPREJT.IMG" (the same place
split_bsa.py extracted it), which merge_bsa.py then packs into a full
GLOBAL.BSA.

Usage: python3 scripts/build_bsa_accprejt.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from huffman_codec import decode_type08

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (215, 159, 7)  # sampled palette index 192 - same as NEWMENU.IMG's
INK_INDEX = 192
BG_INDEX = 201  # fallback dominant stone/wood tone, (42,37,32)

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


def draw_centered(draw: ImageDraw.ImageDraw, center_x: float, box: Box, text: str, size: int) -> None:
    x0, y0, x1, y1 = box
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round((y0 + y1) / 2 - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=INK)


# (erase_box, text, size, button_center_x) - measured against the
# pristine text bounding boxes (ACCEPT x10-33 y3-9, REJECT x106-129
# y3-10, found via ink-color column profiling), padded a few px on
# every side. center_x kept at the original glyph run's own center
# (button "slots" have plenty of spare width either side before the
# divider/frame, confirmed visually) since the Portuguese words are
# longer than the English ones. Font size dropped to 7 (from NEWMENU's
# 8) so "REJEITAR" (8 letters, vs. REJECT's 6) still clears the
# vertical divider around x=55-65.
BUTTONS: list[tuple[Box, str, int, float]] = [
    ((5, 1, 40, 12), "ACEITAR", 7, 21.5),
    ((100, 1, 135, 12), "REJEITAR", 7, 117.5),
]


def build() -> None:
    filedata = (PARTS_DIR / "ACCPREJT.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 8, "ACCPREJT.IMG is expected to be type-8 (Huffman) compressed"
    assert (flags & 0x100) == 0, "ACCPREJT.IMG is expected to have no embedded palette"

    pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)

    col_raw = (ORIG_DIR / "PAL.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    all_boxes = [box for box, _, _, _ in BUTTONS]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_box(px, pixels, width, height, box, all_boxes)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for box, text, size, center_x in BUTTONS:
        draw_centered(draw, center_x, box, text, size)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "ACCPREJT.png")
    print(f"  ACCPREJT.IMG: wrote legivel/ACCPREJT.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 6, height * 6), Image.NEAREST).save(
        PREVIEW_DIR / "ACCPREJT_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated ACCPREJT.IMG (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build()
    print("Done.")


if __name__ == "__main__":
    main()
