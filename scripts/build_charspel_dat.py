"""Bakes the Portuguese translation into CHARSPEL.DAT - a headerless raw
320x200 screen-buffer dump (no 12-byte header, unlike every other
translated screen in this project) found via manual review, confirmed
referenced by name inside the real ACD.EXE (alongside "charspel.img",
next to the item-encumbrance/spell-deletion-confirmation strings) - see
docs/inventario-arquivos.md for the full story of how this was found
and why it was translated despite uncertain reachability (same
"translate it anyway, for safety" reasoning as the GLOBAL.BSA
CHARSPEL.IMG/SCROLL03.IMG duplicates).

Shows an example character's spell-list/resistances screen: name
"Loviron Highorin" (proper noun, left untouched), race/class, a
"SPELL BOOK" banner, 6 example spell names, elemental resistances, and
a Drop/Equipment/Exit button bar (all three buttons sit within the left
160px character-sheet panel, not spanning the full 320px width under
the portrait - confirmed by ink-column measurement, not assumed).
Renders with CHARSHT.COL (no embedded palette of its own) - same rule
gerar_legivel_originais.py's resolve_external_palette() already applies
to CHARSPEL.IMG/SCROLL03.IMG.

Every erase box below was measured directly from the pristine pixels
(ink-color row/column profiling, the same technique used for
ACCPREJT.IMG/TAMRIEL.MNU), not eyeballed from a screenshot - a first
attempt at eyeballed coordinates left visible remnants of the original
English letters and put "EXIT" outside the actual button bar entirely.

Spell names reuse the exact Portuguese already established for the
same effects elsewhere in ACD.EXE's own enchantment strings (e.g.
"of Stamina" -> "de Vigor" in build_acd_exe.py), for consistency.

Bypasses img_manifest.py/compile_images.py entirely (writes the decoded
+ translated raw bytes directly, verified via round-trip) since there's
no header to assemble - same reasoning as build_bsa_slider.py.

Usage: python3 scripts/build_charspel_dat.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
DEST_DIR = ROOT_DIR / "Minha tradução"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

WIDTH, HEIGHT = 320, 200

NOTO_SANS_BOLD = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
MONTSERRAT_BLACK = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Black.otf"

# Sampled directly from this screen's own pristine pixels (CHARSHT.COL):
WHITE = (197, 197, 197)         # name/race/class text
GOLD = (191, 115, 0)            # resistance labels + button text
SPELL_GOLD = (251, 239, 79)     # spell list entries (brighter)
BANNER_INK = (41, 0, 0)         # "SPELL BOOK" banner's dark embossed text
TOP_BG = (11, 35, 39)           # dark teal - name/race/class/resist./buttons
STONE_BG = (83, 83, 83)         # grey stone - spell list panel
BANNER_BG = (211, 143, 0)       # gold banner box behind "SPELL BOOK"

Box = tuple[int, int, int, int]


def erase(draw: ImageDraw.ImageDraw, box: Box, fill) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=fill)


def draw_left(draw: ImageDraw.ImageDraw, text: str, x, y, font, fill) -> None:
    draw.text((x, y), text, font=font, fill=fill)


def build() -> None:
    pixels = (ORIG_DIR / "CHARSPEL.DAT").read_bytes()
    expected = WIDTH * HEIGHT
    assert len(pixels) == expected, f"expected {expected}, found {len(pixels)}"

    col_raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    im = Image.new("P", (WIDTH, HEIGHT))
    im.putpalette(palette_flat)
    im.putdata(pixels)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    name_font = ImageFont.truetype(NOTO_SANS_BOLD, 8)
    label_font = ImageFont.truetype(NOTO_SANS_BOLD, 8)
    spell_font = ImageFont.truetype(NOTO_SANS_BOLD, 8)
    banner_font = ImageFont.truetype(MONTSERRAT_BLACK, 9)

    # "Loviron Highorin" (name, y=6-14) is a proper noun - left untouched.

    # "High Elf" -> race. Ink measured x=[11,55] y=[15,23].
    erase(draw, (9, 14, 100, 24), TOP_BG)
    draw_left(draw, "Alto Elfo", 11, 15, name_font, WHITE)

    # "Warrior" -> class. Ink measured x=[11,45] y=[24,32] (x<105, to
    # avoid the "10" level value which sits at x=128-134 on the same rows).
    erase(draw, (9, 23, 100, 33), TOP_BG)
    draw_left(draw, "Guerreiro", 11, 24, name_font, WHITE)

    # "Level:" ink measured x=[105,125] y=[23,30] (gold); "10" value at
    # x=[128,134] (white) is a number, left untouched, not erased.
    erase(draw, (103, 22, 127, 32), TOP_BG)
    draw_left(draw, "Nível:", 103, 23, label_font, GOLD)

    # "SPELL BOOK" banner box measured x=[50,115] y=[38,48].
    erase(draw, (50, 38, 116, 49), BANNER_BG)
    bbox = draw.textbbox((0, 0), "GRIMÓRIO", font=banner_font)
    bx = 82 - (bbox[2] - bbox[0]) // 2 - bbox[0]
    draw_left(draw, "GRIMÓRIO", bx, 39, banner_font, BANNER_INK)

    # Spell list: 6 rows, exactly 11px apart starting at y=51 (measured
    # via ink-row profiling). Reuses the Portuguese already established
    # for the same effect names elsewhere in ACD.EXE's own strings
    # (build_acd_exe.py's "of X" enchantment translations).
    for i, text in enumerate((
        "Vigor", "Santuário", "Luz",
        "Luz Errante", "Tranca Mágica", "Força de Orc",
    )):
        y = 51 + 11 * i
        erase(draw, (6, y - 1, 140, y + 9), STONE_BG)
        draw_left(draw, text, 6, y - 1, spell_font, SPELL_GOLD)

    # Resistances: 2 rows x 3 columns. Each label's own ink box measured
    # directly; the "+0" value beside each is untouched (a number).
    for text, x0, x1, y0, y1 in (
        ("Fogo:", 10, 33, 124, 140),
        ("Frio:", 11, 29, 138, 154),
        ("Veneno:", 61, 91, 124, 140),
        ("Choque:", 63, 91, 138, 154),
        ("Magia:", 111, 142, 124, 140),
    ):
        erase(draw, (x0, y0, x1, y1), TOP_BG)
        draw_left(draw, text, x0, y0 + 1, label_font, GOLD)

    # Buttons: all three sit inside the left 160px panel (confirmed by
    # ink measurement, not the wider 0-320 span they might appear to
    # have at a glance), each ~14-15px wide for their pristine text.
    for text, x0, x1, center in (
        ("LARGAR", 12, 34, 23),
        ("EQUIPAMENTO", 55, 115, 85),
        ("SAIR", 130, 156, 143),
    ):
        erase(draw, (x0, 183, x1, 199), TOP_BG)
        bbox = draw.textbbox((0, 0), text, font=label_font)
        bx = center - (bbox[2] - bbox[0]) // 2 - bbox[0]
        draw_left(draw, text, bx, 184, label_font, GOLD)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())
    assert len(new_pixels) == WIDTH * HEIGHT

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    (DEST_DIR / "CHARSPEL.DAT").write_bytes(new_pixels)
    print(f"  wrote {DEST_DIR / 'CHARSPEL.DAT'} ({len(new_pixels)} bytes)")

    PREVIEW_DIR.mkdir(exist_ok=True)
    preview = Image.new("P", (WIDTH, HEIGHT))
    preview.putpalette(palette_flat)
    preview.putdata(new_pixels)
    preview.convert("RGB").resize((WIDTH * 2, HEIGHT * 2), Image.NEAREST).save(
        PREVIEW_DIR / "CHARSPEL_DAT_traduzido.png"
    )
    print("  wrote preview_imagens/CHARSPEL_DAT_traduzido.png")


def main() -> None:
    print("Building translated CHARSPEL.DAT...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
