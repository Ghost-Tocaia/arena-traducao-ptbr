"""Bakes the Portuguese translation into 5 small standalone UI labels
found via the "varredura_img_bruta.py" bulk scan (see
docs/inventario-arquivos.md, seção 4): BONUS.IMG ("Bonus Pts:"),
EQUIPB.IMG ("Equipment" header), GOLD.IMG ("Gold"), PAGE2.IMG
("Next Page" button) and SPELLBK.IMG ("Spell Book" banner).

All five have NO embedded palette. BONUS/GOLD/PAGE2/SPELLBK use PAL.COL,
confirmed correct via the bulk scan's default-palette render (each
one's text was clearly legible in plausible colors there - no per-file
trial needed for those four). EQUIPB.IMG is the exception: the bulk
scan's PAL.COL guess also looked "plausible" (a reddish background) but
was wrong - trying CHARSHT.COL side by side showed a proper dark
stone/teal background matching EQUIP.IMG's own screen (see
build_bsa_equip.py), which makes much more sense for what's presumably
the same equipment-screen family. Same lesson as SCROLL01/02.IMG and
EQUIP.IMG: "renders something legible" isn't the same as "confirmed
correct" - always compare candidates before accepting one.

BONUS/EQUIPB/GOLD/PAGE2 share the exact same ink color (palette index
253, RGB (191,115,0)) as CHARSTAT.IMG/NEWEQUIP.IMG/EQUIP.IMG - the same
in-game text-overlay palette region, and that index happens to map to
the same RGB under both PAL.COL and CHARSHT.COL, so only the palette
FILE loaded for EQUIPB.IMG needed to change. SPELLBK.IMG is a different
asset (a wood/stone plaque with flanking gauntlet icons) with its own
green ink (palette index 31, RGB (108,140,0)).

Reads and overwrites the pristine copies split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first). Saves the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/" - compile_images.py later
compiles that PNG into the actual game-format `.IMG`.

Usage: python3 scripts/build_bsa_labels2.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from huffman_codec import decode_type08
from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"

Box = tuple[int, int, int, int]

INK_LAVA = (191, 115, 0)
INK_LAVA_INDEX = 253
INK_SPELLBK = (108, 140, 0)
INK_SPELLBK_INDEX = 31


def _region_is_clean(pristine: bytes, width: int, height: int, box: Box, exclude: list[Box], ink_index: int) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        return False
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pristine[y * width + x] == ink_index:
                return False
            if any(bx0 <= x < bx1 and by0 <= y < by1 for bx0, by0, bx1, by1 in exclude):
                return False
    return True


def erase_box(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box], ink_index: int, bg_index: int) -> None:
    """Same clone-a-real-texture-patch-first, fall-back-to-local-mode
    technique used for CHARSTAT.IMG/YESNO.IMG - these small labels sit
    on the same kind of high-contrast marbled/plaque background."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    offsets = [
        (w, 0), (-w, 0), (2 * w, 0), (-2 * w, 0),
        (0, h), (0, -h), (0, 2 * h), (0, -2 * h),
    ]
    for dx, dy in offsets:
        candidate = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        if _region_is_clean(pristine, width, height, candidate, exclude, ink_index):
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
            if pristine[yy * width + xx] != ink_index
            and not (x0 <= xx < x1 and y0 <= yy < y1)
            and not any(bx0 <= xx < bx1 and by0 <= yy < by1 for bx0, by0, bx1, by1 in exclude)
        ]
        r += 4
    fill = Counter(samples).most_common(1)[0][0] if samples else bg_index
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = fill


def draw_fitted_centered(
    draw: ImageDraw.ImageDraw, center_x: float, center_y: float, text: str,
    base_size: int, fill: tuple[int, int, int], min_size: int = 5, max_width: float | None = None,
) -> None:
    size = base_size
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    if max_width is not None:
        while size > min_size and bbox[2] - bbox[0] > max_width:
            size -= 1
            font = ImageFont.truetype(MONTSERRAT_BOLD, size)
            bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(center_y - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


# (erase_box, text, base_size, max_width, center_x, center_y, ink, ink_index, bg_index, palette_file)
LabelSpec = tuple[Box, str, int, float, float, float, tuple[int, int, int], int, int, str]
LABELS: dict[str, LabelSpec] = {
    "BONUS.IMG": ((0, 4, 48, 12), "BONUS:", 7, 46, 24, 7.5, INK_LAVA, INK_LAVA_INDEX, 250, "PAL.COL"),
    # "EQUIPAMENTO" (11 letras) never fits legibly in this 41x9px label -
    # tried at every size down to the minimum, letters merge into an
    # unreadable blob (confirmed visually, not assumed). "ITENS" is the
    # user-approved substitute: reads clearly at the label's max size.
    "EQUIPB.IMG": ((0, 0, 41, 9), "ITENS", 9, 40, 20.5, 4.5, INK_LAVA, INK_LAVA_INDEX, 250, "CHARSHT.COL"),
    "GOLD.IMG": ((0, 0, 18, 8), "OURO", 6, 17, 9, 4, INK_LAVA, INK_LAVA_INDEX, 250, "PAL.COL"),
    # Same family as EQUIPB.IMG/NEWEQUIP.IMG (dungeon loot screen
    # pagination) - CHARSHT.COL confirmed correct by side-by-side
    # comparison, not PAL.COL's orange/lava theme.
    "PAGE2.IMG": ((2, 3, 46, 12), "Próxima", 7, 43, 24, 7.5, INK_LAVA, INK_LAVA_INDEX, 250, "CHARSHT.COL"),
    "SPELLBK.IMG": ((12, 0, 54, 9), "GRIMÓRIO", 7, 41, 33, 4.5, INK_SPELLBK, INK_SPELLBK_INDEX, 87, "PAL.COL"),
}


def build(name: str) -> None:
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    comp_type = flags & 0xFF
    assert (flags & 0x100) == 0, f"{name} is expected to have no embedded palette"

    if comp_type == 4:
        pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    elif comp_type == 8:
        pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)
    else:
        raise ValueError(f"{name}: unexpected comp_type {comp_type}")
    pixels = bytes(pixels)

    box, text, base_size, max_width, cx, cy, ink, ink_index, bg_index, pal_name = LABELS[name]
    col_raw = (ORIG_DIR / pal_name).read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    px = bytearray(pixels)
    erase_box(px, pixels, width, height, box, [box], ink_index, bg_index)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)
    draw_fitted_centered(draw, cx, cy, text, base_size, ink, max_width=max_width)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    stem = name.rsplit(".", 1)[0]
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / f"{stem}.png")
    print(f"  {name}: wrote legivel/{stem}.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 6, height * 6), Image.NEAREST).save(
        PREVIEW_DIR / f"{name.replace('.', '_')}_traduzido.png"
    )


def main() -> None:
    print("Building translated small labels (GLOBAL_parts/legivel/)...")
    for name in LABELS:
        build(name)
    print("Done.")


if __name__ == "__main__":
    main()
