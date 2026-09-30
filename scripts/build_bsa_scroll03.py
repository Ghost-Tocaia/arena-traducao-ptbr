"""Bakes the Portuguese translation into the GLOBAL.BSA-internal copy of
SCROLL03.IMG - a DIFFERENT variant of the opening-narration scroll from
the already-translated loose "Minha tradução/SCROLL03.IMG" (see
build_images.py's build_scroll03()), not a byte-identical duplicate:
same 3 lines of text, but this copy has no landscape illustration in
the lower two-thirds (plain speckled parchment instead) and has no
embedded palette of its own (uses CHARSHT.COL externally, same rule
gerar_legivel_originais.py's resolve_external_palette() already applies
to this exact filename).

Confirmed via VFS::Manager::open() (OpenTESArena's components/vfs/
manager.cpp): a loose file always wins over the same-named GLOBAL.BSA
entry, so the game itself never reads this copy - see
docs/inventario-arquivos.md seção 2.2/3.2. Translated anyway, as a
safety net requested by the user, in case anything else ever reads the
BSA copy directly.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first). This bypasses
img_manifest.py/compile_images.py entirely (writes the compiled `.IMG`
directly, verified via img_codec.verify_roundtrip) since "SCROLL03.IMG"
is already a manifest key for the LOOSE variant - one filename can't
map to two different (location, comp_type, embed_palette) tuples in
that dict. A readable PNG is still written to
"GLOBAL_parts/legivel/SCROLL03.png" for consistency/review, it just
isn't compiled by compile_images.py.

Usage: python3 scripts/build_bsa_scroll03.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from img_codec import encode_img, verify_roundtrip
from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"

# Sampled directly from this screen's own first text line (y=18-30) in
# CHARSHT.COL - the darkest ink pixels actually used for the pristine
# English glyphs (idx 24, count=2 - anti-aliased core stroke), not the
# loose screen's own ink (48,12,12), since that color doesn't exist in
# this different palette. idx 3 (208,195,167) is the dominant parchment
# tone in the same region, used as the erase fill.
INK = (97, 52, 42)
BG = (208, 195, 167)


def build() -> None:
    filedata = (PARTS_DIR / "SCROLL03.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 4, "SCROLL03.IMG (BSA) is expected to be LZSS-compressed (type 4)"
    assert (flags & 0x100) == 0, "SCROLL03.IMG (BSA) is expected to have no embedded palette"

    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)

    col_raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(pixels)
    rgb = im.convert("RGB")

    # Erase the pristine English text - same box build_scroll03() uses
    # for the loose screen (the two scrolls share the same overall
    # frame layout, only the lower artwork differs).
    draw = ImageDraw.Draw(rgb)
    draw.rectangle((10, 18, 309, 71), fill=BG)

    font = ImageFont.truetype(NOTO_SERIF_ITALIC, 13)
    lines = [
        "Diz-se que a esperança voa nas asas da morte.",
        "Prepare-se então, pois como os Elder Scrolls",
        "profetizaram, é aqui que sua aventura começa...",
    ]
    for text, y in zip(lines, (19, 37, 55)):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2 - bbox[0]
        draw.text((x, y), text, font=font, fill=INK)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "SCROLL03.png")
    print(f"  SCROLL03.IMG (BSA): wrote legivel/SCROLL03.png ({width}x{height})")

    file_bytes = encode_img(
        new_pixels, width, height, xoff=xoff, yoff=yoff, comp_type=4,
        palette_flat_8bit=None,
    )
    ok = verify_roundtrip(file_bytes, new_pixels, width, height)
    assert ok, "SCROLL03.IMG (BSA): round-trip verification failed"
    (PARTS_DIR / "SCROLL03.IMG").write_bytes(file_bytes)
    print(f"  SCROLL03.IMG (BSA): wrote {len(file_bytes)} bytes to GLOBAL_parts/SCROLL03.IMG, roundtrip OK: {ok}")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "SCROLL03_BSA_traduzido.png"
    )


def main() -> None:
    print("Building translated SCROLL03.IMG (GLOBAL.BSA variant)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
