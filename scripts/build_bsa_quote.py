"""Bakes the Portuguese translation into QUOTE.IMG - a loading-screen
flavor quote (fictional "Blademaster" epigraph) shown on a plain black
background. Found via the "varredura_img_bruta.py" bulk scan (see
docs/inventario-arquivos.md, seção 4).

Type 8 (Huffman) compressed, WITH its own embedded palette. Background
is flat black (palette index 0) with no artwork, so erasing is a plain
flat fill - the simplest case in this project. Ink is anti-aliased
near-white/gray; a single representative light-gray fill is used for
the redrawn text instead of trying to reproduce the anti-aliasing.

"Gaiden Shinji" is left untranslated (an in-universe proper name, like
every other Elder Scrolls character name in this project - ver
docs/traducao-estilo.md); "Blademaster" and "First Era" are titles/era
terms, translated like any other flavor text.

Reads and overwrites the pristine copy split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (recompressed as
LZSS "type 4", since there's no Huffman encoder here).

Usage: python3 scripts/build_bsa_quote.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from huffman_codec import decode_type08

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"
INK = (225, 225, 225)
BG_INDEX = 0

Box = tuple[int, int, int, int]


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def draw_centered_lines(draw: ImageDraw.ImageDraw, center_x: float, top: float, lines: list[str], size: int, line_height: int) -> None:
    font = ImageFont.truetype(NOTO_SERIF_ITALIC, size)
    y = top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
        draw.text((x, y - bbox[1]), line, font=font, fill=INK)
        y += line_height


QUOTE_LINES = ["As melhores técnicas são passadas adiante", "pelos sobreviventes..."]
ATTRIBUTION_LINES = ["-Gaiden Shinji, Mestre-Espadachim", "Primeira Era, 947"]


def build() -> None:
    filedata = (PARTS_DIR / "QUOTE.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 8, "QUOTE.IMG is expected to be type-8 (Huffman) compressed"
    assert (flags & 0x100) != 0, "QUOTE.IMG is expected to have an embedded palette"

    pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)
    pal_region = filedata[12 + length:12 + length + 768]

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in pal_region]

    px = bytearray(pixels)
    erase_flat(px, width, (0, 34, width, 88))
    erase_flat(px, width, (0, 114, width, 172))

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    draw_centered_lines(draw, width / 2, 38, QUOTE_LINES, 15, 21)
    draw_centered_lines(draw, width / 2, 120, ATTRIBUTION_LINES, 15, 21)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "QUOTE.png")
    print(f"  QUOTE.IMG: wrote legivel/QUOTE.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "QUOTE_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated QUOTE.IMG (GLOBAL_parts/legivel/)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
