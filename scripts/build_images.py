"""Bakes the Portuguese translation into the game's image-based screens
(SCROLL03.IMG, CHARSPEL.IMG, TITLE.IMG, TAMRIEL.MNU), which carry their
text as pixel art rather than as editable strings.

Reads the pristine files from "Originais/" and writes the translated
result as a readable PNG (mode "P", palette embedded) to
"Minha tradução/legivel/", so re-running this script always reproduces
the same output from scratch (no cumulative edits). compile_images.py
later compiles that PNG into the actual game-format `.IMG`, written to
"Minha tradução/<nome>.IMG" per img_manifest.py's rule for each file -
see that script; this one never writes a compiled `.IMG` itself.

Usage: run from the repo root or from the "scripts" folder:
    python3 scripts/build_images.py
"""
import struct
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
DEST_DIR = ROOT_DIR / "Minha tradução"
LEGIVEL_DIR = DEST_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SANS_BOLD = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"
MONTSERRAT_BLACK = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Black.otf"


def s6(v: int) -> int:
    """Scale a 6-bit VGA DAC color channel (0-63) up to 8-bit (0-255)."""
    return (v << 2) | (v >> 4)


def read_header(data: bytes) -> tuple[int, int, int, int, int, int]:
    return struct.unpack_from("<HHHHHH", data, 0)


def palette_from(pal_region: bytes) -> list[int]:
    flat = []
    for i in range(256):
        flat += [s6(pal_region[i * 3]), s6(pal_region[i * 3 + 1]), s6(pal_region[i * 3 + 2])]
    return flat


def quantize_to_palette(rgb_image: Image.Image, palette_flat: list[int]) -> bytes:
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb_image.quantize(palette=pal_img, dither=Image.Dither.NONE)
    return bytes(quantized.getdata())


def write_verified(
    name: str,
    xoff: int, yoff: int, width: int, height: int, flags: int,
    new_pixels: bytes, pal_region: bytes, compressed: bool,
    preview_name: str, palette_flat: list[int],
) -> None:
    """Saves the translated result as a readable PNG in "legivel/" -
    mode "P" with the resolved palette embedded in the PNG itself, so it
    opens with correct colors in any image viewer/editor. The actual
    game-format `.IMG` (header, compression, optional embedded palette
    region) is assembled later by compile_images.py, per
    img_manifest.py's rule for this filename - never here. xoff/yoff/
    flags/pal_region are accepted for call-site compatibility but no
    longer used to write a binary file."""
    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    stem = name.rsplit(".", 1)[0]
    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(new_pixels)
    im.save(LEGIVEL_DIR / f"{stem}.png")
    print(f"  {name}: wrote legivel/{stem}.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    preview = Image.new("P", (width, height))
    preview.putpalette(palette_flat)
    preview.putdata(new_pixels)
    preview.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / preview_name
    )


def build_scroll03() -> None:
    name = "SCROLL03.IMG"
    data = (ORIG_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = read_header(data)
    pixels, _ = decode_type04(data, 12, 12 + length, width * height)
    pal_region = data[12 + length:12 + length + 768]
    palette_flat = palette_from(pal_region)

    BG_INDEX = 3  # dominant parchment tone sampled from the scroll's blank area
    px = bytearray(pixels)
    for y in range(18, 72):
        for x in range(10, 310):
            px[y * width + x] = BG_INDEX

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    font = ImageFont.truetype(NOTO_SERIF_ITALIC, 13)
    ink = (48, 12, 12)  # darkest ink shade sampled from the original scroll
    lines = [
        "Diz-se que a esperança voa nas asas da morte.",
        "Prepare-se então, pois como os Elder Scrolls",
        "profetizaram, é aqui que sua aventura começa...",
    ]
    for text, y in zip(lines, (19, 37, 55)):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2 - bbox[0]
        draw.text((x, y), text, font=font, fill=ink)

    new_pixels = quantize_to_palette(rgb, palette_flat)
    write_verified(
        name, xoff, yoff, width, height, flags, new_pixels, pal_region,
        compressed=True, preview_name="SCROLL03_traduzido.png", palette_flat=palette_flat,
    )


def build_charspel() -> None:
    name = "CHARSPEL.IMG"
    data = (ORIG_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = read_header(data)
    assert (flags & 0xFF) == 0, "expected uncompressed type 0"
    pixels = data[12:12 + width * height]
    pal_region = data[12 + width * height:12 + width * height + 768]
    palette_flat = palette_from(pal_region)

    random.seed(7)
    bg_choices = (
        [46] * 12537 + [45] * 8854 + [44] * 516 + [84] * 425
        + [42] * 28 + [82] * 18 + [83] * 10 + [81] * 7
    )
    px = bytearray(pixels)

    def erase(x0, y0, x1, y1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[y * width + x] = random.choice(bg_choices)

    for box in (
        (25, 0, 295, 19),     # title
        (10, 19, 195, 31),    # Name:
        (10, 29, 195, 41),    # Level:
        (197, 19, 300, 31),   # Balance:
        (197, 29, 300, 41),   # Spell Cost:
        (10, 45, 195, 57),    # Spell Name:
        (10, 56, 195, 68),    # Target:
        (197, 45, 300, 57),   # Save Vs.:
        (197, 56, 300, 68),   # Casting Cost:
        (10, 68, 195, 80),    # Effects:
        (0, 184, 320, 200),   # buttons row
    ):
        erase(*box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    gold = (235, 190, 32)
    gold_shadow = (85, 44, 20)
    # sampled from the original "SPELLBOOK" title ink (burnt-orange fill,
    # near-black outline) - a different color scheme than the field labels.
    title_fill = (174, 101, 0)
    title_shadow = (0, 0, 0)
    label_font = ImageFont.truetype(NOTO_SANS_BOLD, 9)
    title_font = ImageFont.truetype(MONTSERRAT_BLACK, 15)

    def draw_text(text, x, y, font, shadow=True, fill=gold, shadow_fill=gold_shadow):
        if shadow:
            draw.text((x + 1, y + 1), text, font=font, fill=shadow_fill)
        draw.text((x, y), text, font=font, fill=fill)

    def centered_x(text, font, box_x0, box_x1):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        return box_x0 + ((box_x1 - box_x0) - w) // 2 - bbox[0]

    def centered_on(text, font, center):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        return center - w / 2 - bbox[0]

    draw_text(
        "GRIMÓRIO", centered_x("GRIMÓRIO", title_font, 25, 295), 1, title_font,
        fill=title_fill, shadow_fill=title_shadow,
    )

    for text, y in (("Nome:", 21), ("Nível:", 31), ("Feitiço:", 47), ("Alvo:", 58), ("Efeitos:", 70)):
        draw_text(text, 17, y, label_font)

    for text, y in (("Saldo:", 21), ("Custo:", 31), ("Resist.:", 47), ("Conjuração:", 58)):
        draw_text(text, 202, y, label_font)

    # buttons: centered on the ORIGINAL English button's exact pixel center
    # (measured from CHARSPEL.IMG's gold-ink bounding box), since the game's
    # click regions are fixed to those original coordinates.
    for text, center in (
        ("Próximo", 36.0), ("Anterior", 130.5), ("Excluir", 231.0), ("Sair", 296.0),
    ):
        x = centered_on(text, label_font, center)
        draw_text(text, x, 188, label_font)

    new_pixels = quantize_to_palette(rgb, palette_flat)
    write_verified(
        name, xoff, yoff, width, height, flags, new_pixels, pal_region,
        compressed=False, preview_name="CHARSPEL_traduzido.png", palette_flat=palette_flat,
    )


def build_tamriel() -> None:
    """The "choose your home province" map (character creation). Only
    "Empire of" (banner) and "EXIT" (bottom-right button) get translated
    - "Tamriel" itself and all 9 province names (High Rock, Skyrim,
    Morrowind, ...) are proper nouns left untouched, per this project's
    own rule (see docs/pipeline-acd-exe.md's "nomes de provincia" note).
    Found via manual review of varredura_imagens/, not the original bulk
    scan (it's a loose file, not inside GLOBAL.BSA)."""
    name = "TAMRIEL.MNU"
    data = (ORIG_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = read_header(data)
    pixels, _ = decode_type04(data, 12, 12 + length, width * height)
    pal_region = data[12 + length:12 + length + 768]
    palette_flat = palette_from(pal_region)

    px = bytearray(pixels)
    # dominant ribbon/parchment tan, sampled from the erased regions.
    BG_INDEX = 35

    def erase(x0, y0, x1, y1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[y * width + x] = BG_INDEX

    erase(35, 2, 136, 16)     # "Empire of" (banner ribbon, left half)
    erase(283, 187, 318, 198)  # "EXIT" (bottom-right corner)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    # sampled from the erased regions' own darkest engraved-letter tone.
    ink = (93, 52, 24)

    banner_font = ImageFont.truetype(NOTO_SERIF_ITALIC, 12)
    bbox = draw.textbbox((0, 0), "Império de", font=banner_font)
    # centered on the original "Empire of" span.
    bx = 85 - (bbox[2] - bbox[0]) // 2 - bbox[0]
    draw.text((bx, 3), "Império de", font=banner_font, fill=ink)

    exit_font = ImageFont.truetype(NOTO_SANS_BOLD, 9)
    bbox = draw.textbbox((0, 0), "SAIR", font=exit_font)
    # centered on the original "EXIT" span.
    ex = 300 - (bbox[2] - bbox[0]) // 2 - bbox[0]
    draw.text((ex, 189), "SAIR", font=exit_font, fill=ink)

    new_pixels = quantize_to_palette(rgb, palette_flat)
    write_verified(
        name, xoff, yoff, width, height, flags, new_pixels, pal_region,
        compressed=True, preview_name="TAMRIEL_traduzido.png", palette_flat=palette_flat,
    )


def build_title() -> None:
    name = "TITLE.IMG"
    data = (ORIG_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = read_header(data)
    pixels, _ = decode_type04(data, 12, 12 + length, width * height)
    pal_region = data[12 + length:12 + length + 768]
    palette_flat = palette_from(pal_region)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(pixels)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    font = ImageFont.truetype(NOTO_SANS_BOLD, 8)
    # sampled from "The Elder Scrolls" title ink: bright yellow highlight.
    fill = (255, 231, 73)

    lines = ["Traduzido por:", "Ghost Tocaia"]
    coliseum_center_x = 213  # measured center of the coliseum tower's cylinder
    y = 126  # right under "Chapter One: The Arena", inside the tower silhouette
    line_height = 10
    for i, text in enumerate(lines):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = coliseum_center_x - text_w // 2 - bbox[0]
        draw.text((x, y + i * line_height), text, font=font, fill=fill)

    new_pixels = quantize_to_palette(rgb, palette_flat)
    write_verified(
        name, xoff, yoff, width, height, flags, new_pixels, pal_region,
        compressed=True, preview_name="TITLE_creditos.png", palette_flat=palette_flat,
    )


def main() -> None:
    print("Building translated images...")
    build_scroll03()
    build_charspel()
    build_tamriel()
    build_title()
    print("Done.")


if __name__ == "__main__":
    main()
