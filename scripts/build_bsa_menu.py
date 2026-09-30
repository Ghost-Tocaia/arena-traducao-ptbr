"""Bakes the Portuguese translation into MENU.IMG - the main menu scroll
("Load Saved Game" / "Start New Game" / "Exit") bundled inside GLOBAL.BSA.

Unlike every other GLOBAL.BSA image handled so far, MENU.IMG is stored
with compression "type 8" (adaptive Huffman + LZ77, see
huffman_codec.py) instead of type 4 (LZSS). There is no type-8 encoder,
so after editing the pixels this script recompresses the result as type
4 instead (encode_type04, already used everywhere else) and rewrites the
flags byte accordingly - the game reads type 4 just as well, and nothing
else about the file format changes.

The three menu items sit on a plain, gently mottled parchment scroll
inside an ornate border with swirling corner flourishes drawn in the
SAME ink color as the text - so the erase boxes here were measured by
eye against a zoomed, grid-ruled render (not by a generic ink-color
scan, which would also "detect" the corner flourishes as text and risk
eating into them). Each box is kept a few pixels clear of where a
flourish tendril reaches closest to the text line above/below it.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (per
img_manifest.py, MENU.IMG is always recompressed as LZSS "type 4" since
there's no type-8 encoder), written back to "GLOBAL_parts/MENU.IMG"
(the same place split_bsa.py extracted it), which merge_bsa.py then
packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_menu.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from huffman_codec import decode_type08

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SERIF_BLACK = "/usr/share/fonts/google-noto/NotoSerif-Black.ttf"
# Sampled directly from MENU.IMG's own palette: index 192 is the dark
# maroon/near-black body ink, index 249 is the bright red used only for
# each menu item's decorative drop-cap first letter.
INK = (48, 12, 12)
INK_RED = (158, 28, 20)
BG_INDEX = 46

Box = tuple[int, int, int, int]


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def draw_two_tone(
    draw: ImageDraw.ImageDraw,
    box: Box,
    text: str,
    font_path: str,
    base_size: int,
    draw_center: tuple[float, float],
    min_size: int = 10,
    overflow: float = 1.05,
) -> None:
    """Shrinks the font until the text's natural, undistorted width fits
    within the box (with a small overflow allowance), then draws it
    centered on draw_center = (x, y) - the ORIGINAL English text's own
    measured center point, not the erase box's geometric center (see
    below) - with the first character in red (matching the original's
    decorative drop-cap first letter) and the rest in the body ink
    color. Mirrors draw_fitted's shrink-and-center approach in
    build_bsa_ui.py: squeezing the text to an exact width distorted
    letterforms too much when tried on this project's other UI screens,
    so shrinking the font instead is preferred.

    draw_center is independent from the erase box: the erase box must
    stay wide enough to fully cover the original English ink AND clear
    of the ornate corner flourishes (so its own geometric center is
    often a few pixels off from the text's true center), while
    draw_center was measured separately, directly against a zoomed
    ruler-gridded render of the original line, so the Portuguese
    replacement lands exactly on the same spot the original occupied."""
    x0, _, x1, _ = box
    cx, cy = draw_center
    target_width = x1 - x0
    size = base_size
    font = ImageFont.truetype(font_path, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while size > min_size and bbox[2] - bbox[0] > target_width * overflow:
        size -= 1
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)

    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = round(cx - text_w / 2) - bbox[0]
    y = round(cy - text_h / 2) - bbox[1]

    first, rest = text[0], text[1:]
    draw.text((x, y), first, font=font, fill=INK_RED)
    if rest:
        advance = draw.textlength(first, font=font)
        draw.text((x + advance, y), rest, font=font, fill=INK)


# Erase boxes measured by eye against a zoomed (5x), grid-ruled render of
# the pristine panel - kept clear of the ornate corner flourishes, which
# share the same ink color as the text (see module docstring). draw_center
# is the ORIGINAL English text's own measured (x, y) center, read off an
# 8x ruler-gridded crop of each line - see draw_two_tone's docstring for
# why this isn't just the erase box's geometric center.
MENU_ITEMS: list[tuple[Box, str, int, tuple[float, float]]] = [
    ((93, 42, 234, 71), "Carregar Jogo", 18, (167, 56.5)),
    ((93, 97, 245, 122), "Novo Jogo", 17, (166.5, 112)),
    ((135, 145, 210, 170), "Sair", 20, (173.5, 156.5)),
]


def build() -> None:
    filedata = (PARTS_DIR / "MENU.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 8, "MENU.IMG is expected to be type-8 (Huffman) compressed"

    # Type 8's compressed stream starts 2 bytes after the header - those
    # 2 bytes hold the (redundant) decompressed length. See
    # huffman_codec.py's module docstring for the full explanation.
    pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)
    palette_flat_raw = filedata[12 + length:12 + length + 768]

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in palette_flat_raw]

    px = bytearray(pixels)
    for box, _, _, _ in MENU_ITEMS:
        erase_flat(px, width, box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for box, text, base_size, draw_center in MENU_ITEMS:
        draw_two_tone(draw, box, text, NOTO_SERIF_BLACK, base_size, draw_center)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "MENU.png")
    print(f"  MENU.IMG: wrote legivel/MENU.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "MENU_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated MENU.IMG (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build()
    print("Done.")


if __name__ == "__main__":
    main()
