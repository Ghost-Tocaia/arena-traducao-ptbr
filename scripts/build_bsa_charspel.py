"""Bakes the Portuguese translation into the GLOBAL.BSA-internal copy of
CHARSPEL.IMG - a DIFFERENT variant of the spellbook screen from the
already-translated loose "Minha tradução/CHARSPEL.IMG" (see
build_images.py's build_charspel()), not a byte-identical duplicate.

Confirmed via VFS::Manager::open() (OpenTESArena's components/vfs/
manager.cpp): a loose file always wins over the same-named GLOBAL.BSA
entry, so the game itself never reads this copy - see
docs/inventario-arquivos.md seção 2.2/3.2. Translated anyway, as a
safety net requested by the user, in case anything else ever reads the
BSA copy directly.

The only real difference from the loose version: this layout has no
"Delete Spell" button (3 buttons - Next/Previous/Exit - not 4), so
"Anterior" sits at a different center-x than in the loose script (no
"Excluir" crowding it from the right). Everything else (title, field
labels, font, colors, erase technique) is pixel-identical between the
two - confirmed both copies share the exact same embedded 768-byte
palette, and the field-label positions match visually 1:1 against the
loose screen (only the button row differs).

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first). This bypasses
img_manifest.py/compile_images.py entirely (writes the compiled `.IMG`
directly, verified via img_codec.verify_roundtrip) since "CHARSPEL.IMG"
is already a manifest key for the LOOSE variant - one filename can't
map to two different (location, comp_type, embed_palette) tuples in
that dict. A readable PNG is still written to
"GLOBAL_parts/legivel/CHARSPEL.png" for consistency/review, it just
isn't compiled by compile_images.py.

Usage: python3 scripts/build_bsa_charspel.py
"""
import random
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from img_codec import encode_img, verify_roundtrip

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SANS_BOLD = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
MONTSERRAT_BLACK = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Black.otf"


def s6(v: int) -> int:
    return (v << 2) | (v >> 4)


def build() -> None:
    filedata = (PARTS_DIR / "CHARSPEL.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 0, "CHARSPEL.IMG (BSA) is expected to be uncompressed (type 0)"
    assert (flags & 0x100) != 0, "CHARSPEL.IMG (BSA) is expected to have an embedded palette"

    pixels = filedata[12:12 + width * height]
    pal_region = filedata[12 + width * height:12 + width * height + 768]
    palette_flat = []
    for i in range(256):
        palette_flat += [s6(pal_region[i * 3]), s6(pal_region[i * 3 + 1]), s6(pal_region[i * 3 + 2])]

    # Same erase technique/background sample as build_images.py's
    # build_charspel() (identical embedded palette, so the same index
    # weights apply) - dappled parchment fill instead of a flat color,
    # to match the screen's own subtle texture.
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
        (25, 0, 295, 19),      # title
        (10, 19, 195, 31),     # Name:
        (10, 29, 195, 41),     # Level:
        (197, 19, 300, 31),    # Balance:
        (197, 29, 300, 41),    # Spell Cost:
        (10, 45, 195, 57),     # Spell Name:
        (10, 56, 195, 68),     # Target:
        (197, 45, 300, 57),    # Save Vs.:
        (197, 56, 300, 68),    # Casting Cost:
        (10, 68, 195, 80),     # Effects:
        (0, 184, 320, 200),    # buttons row (3 buttons here, not 4)
    ):
        erase(*box)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    gold = (235, 190, 32)
    gold_shadow = (85, 44, 20)
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

    # Only 3 buttons here (no "Delete Spell" in this layout) - centers
    # measured directly against this screen's own pristine gold-ink
    # bounding boxes (column-profiled, y=183-200): Next ~x[14,59]
    # (center 36.5), Previous ~x[106,170] (center 138 - NOT the loose
    # screen's 130.5, since there's no Delete button crowding it here),
    # Exit ~x[289,304] (center 296.5, matching the loose screen almost
    # exactly since Exit is flush against the right edge either way).
    for text, center in (
        ("Próximo", 36.5), ("Anterior", 138.0), ("Sair", 296.5),
    ):
        x = centered_on(text, label_font, center)
        draw_text(text, x, 188, label_font)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "CHARSPEL.png")
    print(f"  CHARSPEL.IMG (BSA): wrote legivel/CHARSPEL.png ({width}x{height})")

    file_bytes = encode_img(
        new_pixels, width, height, xoff=xoff, yoff=yoff, comp_type=0,
        palette_flat_8bit=palette_flat,
    )
    ok = verify_roundtrip(file_bytes, new_pixels, width, height)
    assert ok, "CHARSPEL.IMG (BSA): round-trip verification failed"
    (PARTS_DIR / "CHARSPEL.IMG").write_bytes(file_bytes)
    print(f"  CHARSPEL.IMG (BSA): wrote {len(file_bytes)} bytes to GLOBAL_parts/CHARSPEL.IMG, roundtrip OK: {ok}")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / "CHARSPEL_BSA_traduzido.png"
    )


def main() -> None:
    print("Building translated CHARSPEL.IMG (GLOBAL.BSA variant)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
