"""Bakes the Portuguese translation into HISTORY.IMG - the backstory
paragraph shown before the vision panels. Unlike the INTRO panels, this is
a single flowing paragraph wrapped around an illuminated drop-cap "T"
(left untouched: "Talin" starts with T in Portuguese too, so the cap
still matches the first line's initial letter).

The first 3 lines are narrower (they run alongside the drop cap); the
rest use the full text width below it.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first), and saves both an
erased-only ("empty") PNG into
"Minha tradução/GLOBAL_parts/legivel/empty/" and the final translated
PNG into "Minha tradução/GLOBAL_parts/legivel/", following the same
split/blank/draw pattern as the INTRO panels. compile_images.py later
compiles the translated PNG into the actual game-format `.IMG`, written
back to "GLOBAL_parts/HISTORY.IMG" (the same place split_bsa.py
extracted it), which merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_history.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
EMPTY_DIR = LEGIVEL_DIR / "empty"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

Box = tuple[int, int, int, int]

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"
FONT_SIZE = 13
LINE_HEIGHT = 16
INK = (58, 30, 12)
# The parchment here is plain and evenly lit (no shadow gradient like some
# INTRO panels), so a flat fill is the safe, correct choice - matches the
# background sampled next to every one of the erased lines.
BG_INDEX = 3


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX

# The illuminated drop-cap "T" - decorative art, never erased or drawn over.
DROP_CAP = (5, 20, 66, 76)

# Original English line boxes, measured against the pristine panel - used
# only to erase every pixel of the old text. The first 3 sit beside the
# drop cap; the rest span the full text width below it.
ORIGINAL_LINES = [
    (65, 22, 285, 42),
    (65, 42, 296, 62),
    (65, 62, 303, 79),
    (10, 79, 293, 96),
    (10, 96, 312, 113),
    (10, 113, 301, 130),
    (10, 130, 314, 147),
    (10, 147, 276, 165),
    (10, 165, 298, 180),
]

TEXT = (
    "alin Warhaft, líder da Guarda Imperial e seu guardião, pede que em "
    "seu décimo sétimo aniversário você parta pelas terras, e retorne "
    "como membro pleno da corte real. Você já viajou pelas oito "
    "províncias e viu muitas coisas, decidindo por fim voltar para casa. "
    "Seus sonhos, porém, são interrompidos por imagens aterrorizantes. "
    "Elas falam de uma coisa só.  Alta Traição..."
)

NARROW_LEFT, NARROW_WIDTH = 68, 210
FULL_LEFT, FULL_WIDTH = 18, 294
NARROW_LINE_BUDGET = 3


def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def wrap_two_phase(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> list[tuple[str, int]]:
    """Wraps text to NARROW_WIDTH for up to NARROW_LINE_BUDGET lines (the
    rows beside the drop cap), then continues wrapping whatever's left to
    FULL_WIDTH. Returns (line, left_x) pairs."""
    words = text.split()
    lines: list[tuple[str, int]] = []
    cur: list[str] = []
    i = 0
    while i < len(words):
        narrow = len(lines) < NARROW_LINE_BUDGET
        width = NARROW_WIDTH if narrow else FULL_WIDTH
        left = NARROW_LEFT if narrow else FULL_LEFT
        trial = " ".join(cur + [words[i]])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= width or not cur:
            cur.append(words[i])
            i += 1
        else:
            lines.append((" ".join(cur), NARROW_LEFT if len(lines) < NARROW_LINE_BUDGET else FULL_LEFT))
            cur = []
    if cur:
        lines.append((" ".join(cur), NARROW_LEFT if len(lines) < NARROW_LINE_BUDGET else FULL_LEFT))
    return lines


def render(pixels: bytes, width: int, height: int, palette_flat: list[int]) -> bytes:
    px = bytearray(pixels)
    for box in ORIGINAL_LINES:
        erase_flat(px, width, box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    font = ImageFont.truetype(NOTO_SERIF_ITALIC, FONT_SIZE)
    lines = wrap_two_phase(draw, TEXT, font)
    y = ORIGINAL_LINES[0][1]
    for line, x0 in lines:
        draw.text((x0, y), line, font=font, fill=INK)
        y += LINE_HEIGHT

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    return bytes(quantized.getdata())


def erase_only(pixels: bytes, width: int, height: int) -> bytes:
    px = bytearray(pixels)
    for box in ORIGINAL_LINES:
        erase_flat(px, width, box)
    return bytes(px)


def main() -> None:
    print("Building translated HISTORY.IMG (GLOBAL_parts/legivel/)...")
    EMPTY_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(exist_ok=True)

    filedata = (PARTS_DIR / "HISTORY.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    palette_flat_raw = filedata[12 + length:12 + length + 768]

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in palette_flat_raw]

    # empty/ copy, for review
    blanked = erase_only(pixels, width, height)
    im_empty = Image.new("P", (width, height))
    im_empty.putpalette(palette_flat)
    im_empty.putdata(blanked)
    im_empty.save(EMPTY_DIR / "HISTORY.png")

    # translated, final copy
    new_pixels = render(pixels, width, height, palette_flat)
    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(new_pixels)
    im.save(LEGIVEL_DIR / "HISTORY.png")
    print(f"  HISTORY.IMG: wrote legivel/HISTORY.png ({width}x{height})")

    im.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "HISTORY_IMG_traduzido.png"
    )
    print("Done.")


if __name__ == "__main__":
    main()
