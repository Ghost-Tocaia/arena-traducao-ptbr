"""Bakes the Portuguese direction letters into SLIDER.IMG - the compass
strip that scrolls behind COMPASS.IMG's fixed frame at the top of the
in-game 3D view (not the same asset as AUTOMAP.IMG's full-screen map,
which build_bsa_automap.py already handles). Found via the OpenTESArena
source (GameWorldUiView.cpp) after the user asked about "the compass
that shows during the game" - COMPASS.IMG is just the ornamental frame,
SLIDER.IMG is the strip carrying the actual N/NE/E/SE/S/SW/W/NW glyphs
that the frame's 32px window scrolls across as the camera turns.

SLIDER.IMG is a headerless raw image - no 12-byte header, no comp_type,
no embedded-palette flag. Its dimensions (289x7) only exist as a
hardcoded constant in the game's own code (confirmed via OpenTESArena's
IMGFile.cpp RawImgOverride table; matches 289*7=2023, the file's exact
byte size). img_codec.py/img_manifest.py's whole "read a 12-byte header,
optionally an embedded palette" machinery does not apply here, so this
script bypasses compile_images.py entirely: it reads and writes the raw
2023-byte pixel array directly, and split_bsa.py extracting it via its
normal byte-copy path already works unmodified since that step never
assumed anything about the internal format.

The strip is only 7 pixels tall - far too small for any font used
elsewhere in this project - so every glyph is genuine 5-row pixel art,
hand-placed pixel by pixel (see the GLYPHS table below), not drawn with
PIL/ImageFont. Only the letters that actually change get touched:
E -> L (Leste) and the "W" half of standalone W / SW / NW -> O (Oeste)
half of O / SO / NO. N, NE, SE, S need no change (share initials with
their Portuguese names) and are left byte-for-byte untouched, including
their ink color (alternating red/blue between the 4 main and 4
intercardinal directions - preserved exactly for the redrawn glyphs
too, so O reads red standalone but blue inside SO/NO, matching the
original's own color scheme).

Every column boundary and glyph pixel below was measured directly
against the pristine bytes (Originais/GLOBAL.BSA), isolating real ink
from the strip's dithered parchment-texture background (values
225/226/224/227) and from the small tick marks between labels (thin
single-pixel-wide columns, unlike a letter's multi-row strokes) - see
this project's own investigation notes for the reasoning; spot values
were cross-checked against the two known-unchanged glyphs (standalone
"N" and "S") to pin down exactly where a compound label's own first
letter ends and its second begins.

Reads Originais/GLOBAL.BSA directly (SLIDER.IMG isn't normally listed
in split_bsa.py's TARGET_FILES, since every other script there deals
with the standard 12-byte-header format) and writes straight to
"Minha tradução/GLOBAL_parts/SLIDER.IMG" - no "legivel/" PNG
intermediate, since compile_images.py can't compile this format anyway;
a PNG preview is still written to preview_imagens/ for visual review.

Usage: python3 scripts/build_bsa_slider.py
"""
from pathlib import Path

from PIL import Image

from bsa_codec import offsets_by_name, read_index

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

WIDTH, HEIGHT = 289, 7
BG_INDEX = 225  # dominant dithered-parchment tone; erased regions filled flat with this
RED = 158   # ink color for the 4 main directions (N, E, S, W)
BLUE = 64   # ink color for the 4 intercardinal directions (NE, SE, SW, NW) and tick marks

# 5-row pixel glyphs (row-major, each row a tuple of x-offsets that get
# ink), designed to match the existing font's stroke weight/box size:
# "L" reuses "E"'s exact 4-col x 5-row bounding box; "O" is a 5-col x
# 5-row shape sized to sit centered wherever a "W" used to be.
GLYPH_L: list[tuple[int, ...]] = [
    (0,),
    (0,),
    (0,),
    (0,),
    (0, 1, 2, 3),
]
GLYPH_O: list[tuple[int, ...]] = [
    (1, 2, 3),
    (0, 4),
    (0, 4),
    (0, 4),
    (1, 2, 3),
]


def place_glyph(px: bytearray, x0: int, y0: int, glyph: list[tuple[int, ...]], color: int) -> None:
    for dy, xs in enumerate(glyph):
        for dx in xs:
            px[(y0 + dy) * WIDTH + (x0 + dx)] = color


def erase(px: bytearray, x0: int, x1: int) -> None:
    for y in range(HEIGHT):
        for x in range(x0, x1):
            px[y * WIDTH + x] = BG_INDEX


def build() -> bytes:
    data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()
    offsets = offsets_by_name(read_index(data))
    off, size = offsets["SLIDER.IMG"]
    assert size == WIDTH * HEIGHT, f"SLIDER.IMG: expected {WIDTH * HEIGHT} bytes, found {size}"
    px = bytearray(data[off:off + size])

    # Standalone "E" (x=63-66) -> "L", same box, same red ink.
    erase(px, 62, 68)
    place_glyph(px, 63, 1, GLYPH_L, RED)

    # Standalone "W" (x=190-196) -> "O", red ink.
    erase(px, 189, 197)
    place_glyph(px, 191, 1, GLYPH_O, RED)

    # "SW"'s W-half (x=160-165) -> O, blue ink; "S"-half (x=155-158)
    # left untouched.
    erase(px, 159, 166)
    place_glyph(px, 160, 1, GLYPH_O, BLUE)

    # "NW"'s W-half (x=~226-230) -> O, blue ink; "N"-half (x=220-224)
    # left untouched. Erase starts one column later than the other
    # three (226 not 225) - the "N" glyph's own rightmost pixel sits
    # right at the boundary here (unlike standalone N/S, which have a
    # clean gap before the next tick), so this keeps a 1px safety
    # margin rather than risk clipping N's tail.
    erase(px, 226, 232)
    place_glyph(px, 226, 1, GLYPH_O, BLUE)

    return bytes(px)


def main() -> None:
    print("Building translated SLIDER.IMG...")
    px = build()

    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    (PARTS_DIR / "SLIDER.IMG").write_bytes(px)
    print(f"  wrote {PARTS_DIR / 'SLIDER.IMG'} ({len(px)} bytes)")

    pal_raw = (ORIG_DIR / "PAL.COL").read_bytes()
    palette_flat = list(pal_raw[8:8 + 768])
    im = Image.new("P", (WIDTH, HEIGHT))
    im.putpalette(palette_flat)
    im.putdata(px)

    PREVIEW_DIR.mkdir(exist_ok=True)
    im.convert("RGB").resize((WIDTH * 6, HEIGHT * 6 * 4), Image.NEAREST).save(
        PREVIEW_DIR / "SLIDER_IMG_traduzido.png"
    )
    print(f"  wrote preview_imagens/SLIDER_IMG_traduzido.png")
    print("Done.")


if __name__ == "__main__":
    main()
