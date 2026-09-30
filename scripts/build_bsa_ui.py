"""Bakes the Portuguese translation into the simple UI screens bundled
inside GLOBAL.BSA: LOGBOOK.IMG (the Journal screen), and BUYSPELL.IMG /
SPELLMKR.IMG (the Spellbook and Spellmaker screens, which share the exact
same field-label layout). All three are stored uncompressed (raw pixel
bytes) with an embedded palette, on a plain, evenly-lit parchment
background - no artwork to protect, so erasing is a flat fill.

Every piece of text is drawn with its bounding box pinned to the exact
pixel position the original English glyph was measured at (see draw_at),
using each screen's own ink colors sampled from its palette - near-black
for LOGBOOK's plain journal-page style, gold-with-a-dark-outline for the
two spell screens' rune-styled labels - instead of a generic substitute
color, so the translation reads as part of the original art rather than
text pasted over it.

MENU.IMG (the main menu, Huffman-compressed with a decorative border) is
handled separately by build_bsa_menu.py, since it needs art-aware erasure
and re-encoding to a different compression type (no Huffman encoder
exists here).

Reads the pristine copies split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG`, written back to
"GLOBAL_parts/<nome>.IMG" (the same place split_bsa.py extracted it),
which merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_ui.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

MONTSERRAT_BLACK = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Black.otf"
MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
LOGBOOK_INK = (24, 24, 24)  # LOGBOOK.IMG's own plain caption ink
GOLD = (235, 190, 32)  # BUYSPELL/SPELLMKR's own label fill (palette index 215)
OUTLINE = (85, 44, 20)  # BUYSPELL/SPELLMKR's own label outline (palette index 74)
# The rune-styled screen TITLE ("SPELLBOOK"/"SPELLMAKER") uses its own,
# darker orange/brown scheme - distinct from the field labels' gold - and
# was measured (excluding the plain banner background, indices 45/46) to
# occupy exactly x:80-239, y:0-19 (159px wide) on both screens.
TITLE_FILL = (174, 101, 0)  # sampled palette index 147
TITLE_OUTLINE = (77, 40, 16)  # sampled palette index 73
TITLE_LEFT = 80
TITLE_TOP = 0
TITLE_WIDTH = 159
# The field labels start around y=16 (e.g. "Saldo:" at y=16); keep the
# title's rendered height short enough to clear them with a small gap.
TITLE_HEIGHT = 14
BG_INDEX = 46

Box = tuple[int, int, int, int]


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def draw_at(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
) -> None:
    """Draws text with its bounding box's top-left corner pinned exactly
    at (x0, y0) - i.e. exactly where the original glyph was measured to
    start - optionally with a single-pixel drop-shadow behind the fill,
    matching a screen's own two-tone label ink instead of a plain single
    color. A full 8-direction ring outline was tried first but made the
    small label/button text look much thicker and bigger than the
    original's thin glyphs; one corner offset reads as a thin edge without
    that extra bulk."""
    bbox = draw.textbbox((0, 0), text, font=font)
    x, y = x0 - bbox[0], y0 - bbox[1]
    if outline is not None:
        draw.text((x + 1, y + 1), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def draw_title(
    rgb: Image.Image,
    x0: int,
    y0: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    target_width: int,
    target_height: int,
) -> None:
    """Renders the rune-styled screen title at a large, crisp size then
    scales it to exactly (target_width, target_height) - matching the
    original glyphs' measured width while keeping the height short enough
    to stay clear of the field labels just below it - before pasting with
    its top-left pinned at (x0, y0)."""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    pad = 4
    tmp = Image.new("RGBA", (bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tmp)
    ox, oy = pad - bbox[0], pad - bbox[1]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                tdraw.text((ox + dx, oy + dy), text, font=font, fill=(*outline, 255))
    tdraw.text((ox, oy), text, font=font, fill=(*fill, 255))

    crop_box = tmp.getbbox()
    tmp = tmp.crop(crop_box)
    tmp = tmp.resize((target_width, target_height), Image.LANCZOS)
    rgb.paste(tmp, (x0, y0), tmp)


def draw_fitted(
    draw: ImageDraw.ImageDraw,
    x0: int,
    x1: int,
    y0: int,
    text: str,
    font_path: str,
    base_size: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None,
    min_size: int = 6,
    overflow: float = 1.1,
) -> None:
    """Shrinks the font (down to min_size) until the text's natural,
    undistorted width fits within (x1-x0)*overflow, then draws it centered
    on the original glyphs' own measured midpoint - same center point as
    the original label/button, without squeezing letterforms the way a
    horizontal stretch/squeeze would. A first attempt stretched every
    word's width to match x0/x1 exactly, but that squashed longer
    Portuguese phrases (e.g. "Comprar Feitiço" into "Buy Spell"'s narrow
    slot) into illegibly thin glyphs - shrinking the font and allowing a
    little overflow instead keeps the letters readable."""
    target_width = x1 - x0
    size = base_size
    font = ImageFont.truetype(font_path, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while size > min_size and bbox[2] - bbox[0] > target_width * overflow:
        size -= 1
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)

    center = (x0 + x1) / 2
    x = round(center - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = y0 - bbox[1]
    if outline is not None:
        draw.text((x + 1, y + 1), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


# Each entry: (x, y, text, font_size). x, y is the exact top-left corner
# the original English glyph was measured at.
LOGBOOK = {
    "erase": [(115, 2, 190, 22), (38, 181, 78, 193), (262, 182, 296, 194)],
    "items": [
        (128, 3, "Diário", 15, LOGBOOK_INK, None),
        (38, 183, "imprimir", 12, LOGBOOK_INK, None),
        (270, 184, "sair", 12, LOGBOOK_INK, None),
    ],
}

SPELLSCREEN_ERASE = [
    (5, 0, 245, 20),
    (6, 15, 200, 31), (6, 30, 200, 42), (6, 45, 200, 57), (6, 56, 200, 68), (6, 68, 200, 80),
    (200, 13, 316, 31), (200, 30, 316, 43), (200, 45, 316, 56), (200, 56, 316, 68),
    (0, 179, 320, 200),
]
# Each entry: (x0, x1, y0, text) - x0/x1/y0 are the exact left edge,
# right edge and top the ORIGINAL English glyphs were measured at (per
# column-scan of the pristine BUYSPELL.IMG/SPELLMKR.IMG, identical on both
# screens). draw_fitted renders each label at LABEL_FONT_SIZE (matching
# the original's own ~7-9px cap height) then stretches/squeezes only its
# width so it starts and ends at that exact x0/x1 - occupying precisely
# the same horizontal space the original label did, whatever the
# Portuguese word's natural length.
LABEL_FONT_SIZE = 9
SPELLSCREEN_LABELS = [
    (18, 43, 22, "Nome:"),
    (18, 44, 32, "Nível:"),
    (18, 67, 47, "Feitiço:"),
    (18, 48, 58, "Alvo:"),
    (18, 52, 70, "Efeitos:"),
    (203, 238, 22, "Saldo:"),
    (203, 248, 32, "Custo:"),
    (203, 242, 47, "Resist.:"),
    (203, 258, 58, "Conjuração:"),
]

BUTTON_FONT_SIZE = 9
BUYSPELL_BUTTONS = [
    (5, 100, 189, "Escolher Outro Feitiço"),
    (120, 185, 189, "Comprar Feitiço"),
    (287, 305, 189, "Sair"),
]
SPELLMKR_BUTTONS = [
    (5, 62, 189, "Novo Feitiço"),
    (200, 240, 189, "Comprar Feitiço"),
    (287, 305, 189, "Sair"),
]

# (text, base_font_size) - base_font_size is picked to match the original
# title's ~20px cap height; draw_title then stretches the rendered glyphs
# to TITLE_WIDTH so every title also matches the original's exact width.
BUYSPELL = {
    "erase": SPELLSCREEN_ERASE,
    "title": ("GRIMÓRIO", 20),
    "fitted_items": [
        *[(x0, x1, y0, t, LABEL_FONT_SIZE, GOLD, OUTLINE) for x0, x1, y0, t in SPELLSCREEN_LABELS],
        *[(x0, x1, y0, t, BUTTON_FONT_SIZE, GOLD, OUTLINE) for x0, x1, y0, t in BUYSPELL_BUTTONS],
    ],
}

SPELLMKR = {
    "erase": SPELLSCREEN_ERASE,
    "title": ("CRIA-FEITIÇOS", 20),
    "fitted_items": [
        *[(x0, x1, y0, t, LABEL_FONT_SIZE, GOLD, OUTLINE) for x0, x1, y0, t in SPELLSCREEN_LABELS],
        *[(x0, x1, y0, t, BUTTON_FONT_SIZE, GOLD, OUTLINE) for x0, x1, y0, t in SPELLMKR_BUTTONS],
    ],
}


def build(name: str, spec: dict) -> None:
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    pixels = filedata[12:12 + width * height]
    palette_flat_raw = filedata[12 + length:12 + length + 768]

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in palette_flat_raw]

    px = bytearray(pixels)
    for box in spec["erase"]:
        erase_flat(px, width, box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for x, y, text, size, fill, outline in spec.get("items", []):
        font = ImageFont.truetype(MONTSERRAT_BLACK, size)
        draw_at(draw, x, y, text, font, fill, outline)

    for x0, x1, y0, text, size, fill, outline in spec.get("fitted_items", []):
        draw_fitted(draw, x0, x1, y0, text, MONTSERRAT_BOLD, size, fill, outline)

    if "title" in spec:
        text, base_size = spec["title"]
        font = ImageFont.truetype(MONTSERRAT_BLACK, base_size)
        draw_title(rgb, TITLE_LEFT, TITLE_TOP, text, font, TITLE_FILL, TITLE_OUTLINE, TITLE_WIDTH, TITLE_HEIGHT)

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
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / f"{name.replace('.', '_')}_traduzido.png"
    )


def main() -> None:
    print("Building translated UI screens (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build("LOGBOOK.IMG", LOGBOOK)
    build("BUYSPELL.IMG", BUYSPELL)
    build("SPELLMKR.IMG", SPELLMKR)
    print("Done.")


if __name__ == "__main__":
    main()
