"""Bakes the Portuguese translation into the 17 FORM*.IMG screens - the
Cria-Feitiços (Spellmaker) spell-effect configuration forms, one per
effect type (Range, Chance, Duration, Strength, ...), each with a
"Spell Cost:"/"Exit" footer in common. Found via the
"varredura_img_bruta.py" bulk scan (see docs/inventario-arquivos.md,
seção 4) - `SPELLMKR.IMG` itself (already translated) never references
these files by name, which is why they went unnoticed for so long.

All 17 are LZSS "type 4" compressed, no embedded palette of their own -
they rely on whatever palette is already active on screen. **Not
PAL.COL**: these are small dialog boxes (e.g. FORM1.IMG is 175x120,
never the full 320x200) drawn as an overlay directly on top of the
still-visible SPELLMKR.IMG screen behind them, never a full-screen
replacement. VGA mode 13h has exactly one palette active for the whole
screen at a time, so a partial overlay can only ever render correctly
using the SAME palette its background (SPELLMKR.IMG's own embedded
one) already loaded - loading PAL.COL for just the FORM sprite would
require the whole screen (SPELLMKR's parchment included) to have
switched palettes too, which doesn't happen for a modal dialog. An
earlier pass accepted PAL.COL because it "rendered something legible"
(an orange/lava marble look) without checking this - same mistake as
SCROLL01/02.IMG and EQUIP.IMG/EQUIPB.IMG, see docs/pipeline-imagens.md.
Confirmed two ways: (1) PAL.COL and SPELLMKR.IMG's embedded palette
differ in 731 of 768 bytes - not remotely interchangeable; (2)
OpenTESArena's own reimplementation (github.com/afritz1/OpenTESArena,
src/Assets/ArenaPaletteName.h) names PAL.COL literally "Default" - the
generic palette for regular first-person gameplay, which is also why
OP.IMG (opened via Escape from that same generic context) correctly
keeps using PAL.COL; FORM has no such connection to that context, only
to SPELLMKR.IMG.

Two distinct inks are used, resampled under SPELLMKR.IMG's own embedded
palette (the values below are meaningless under PAL.COL and vice
versa): palette index 255 (RGB (255,255,255), white) for every
label/spinner-border/checkbox, and a SEPARATE palette index 254 (RGB
(199,199,199), light gray) used ONLY for the "Exit" word - confirmed by
direct pixel sampling, not assumed from another screen.

Coordinates below were measured programmatically (not by eye): for each
row, a per-column "ink fill ratio" profile isolates continuous
wide runs (the numeric entry boxes' top/bottom border, which spans the
box's full width but only 1-2px of the row's height) from narrow runs
(individual letter strokes). Spinner up/down arrows sit ONLY to the
left of a row's first box (never in the gap between two boxes on the
same row, and never right after a row's only box) - so inner gaps
between two boxes use a tight margin, while the space before a row's
first box and after its last box (when the row has two boxes) use a
15px safety margin to guarantee never touching the spinner artwork.

Erasing uses a local ring-sampled mode fill (INTRO-panel/POPUP3.IMG
style), NOT texture-clone: this panel's orange marble has soft,
large-scale brightness blobs that make a cloned same-size patch land on
a visibly different-toned patch of the blob often enough to be worse
than a flat local-mode fill.

Reads and overwrites the pristine copies split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as readable PNGs into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles each PNG into the actual game-format `.IMG`.

Usage: python3 scripts/build_bsa_forms.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (255, 255, 255)  # sampled palette index 255 under SPELLMKR.IMG's own embedded palette
INK_EXIT = (199, 199, 199)  # sampled palette index 254 under the same palette - "Exit" only
INK_INDEX = 255
BG_INDEX = 246

Box = tuple[int, int, int, int]
LabelSpec = tuple[Box, str, int]


def _region_is_clean(pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        return False
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pristine[y * width + x] == INK_INDEX:
                return False
            if any(bx0 <= x < bx1 and by0 <= y < by1 for bx0, by0, bx1, by1 in exclude):
                return False
    return True


def erase_mode_fill(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> None:
    """Small horizontal clone first, flat local-mode fill as fallback.
    The module docstring's "moda local, not clone" call was about the
    big label boxes, where a clone offset large enough to clear the box
    can land on a different part of this panel's large-scale brightness
    blob. That reasoning doesn't hold for the small "safety margin" gap
    boxes between a label and its numeric entry box (e.g. after "% por"
    / "Niveis") - a shift of just the box's own (small) width stays
    well inside the same patch of the blob, so a real cloned patch
    (with its own genuine noise) is both safe and looks far better than
    a flat fill, which read as a visibly smooth rectangle once the
    palette was corrected to the darker, higher-contrast SPELLMKR.IMG
    one (see module docstring) - the flatness was far less noticeable
    under the old, wrong PAL.COL. Big boxes still have no clean
    same-size offset available (they're hemmed in by neighboring
    boxes/panel edges) and fall through to the flat fill exactly like
    before."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for dx in (w, -w, 2 * w, -2 * w):
        candidate = (x0 + dx, y0, x1 + dx, y1)
        if _region_is_clean(pristine, width, height, candidate, exclude):
            cx0, cy0, cx1, _ = candidate
            for row in range(h):
                src_row = (cy0 + row) * width
                dst_row = (y0 + row) * width
                px[dst_row + x0:dst_row + x1] = pristine[src_row + cx0:src_row + cx1]
            return

    r = 4
    samples: list[int] = []
    while len(samples) < 15 and r <= 40:
        samples = [
            pristine[yy * width + xx]
            for yy in range(max(0, y0 - r), min(height, y1 + r))
            for xx in range(max(0, x0 - r), min(width, x1 + r))
            if pristine[yy * width + xx] != INK_INDEX
            and not (x0 <= xx < x1 and y0 <= yy < y1)
            and not any(bx0 <= xx < bx1 and by0 <= yy < by1 for bx0, by0, bx1, by1 in exclude)
        ]
        r += 4
    fill = Counter(samples).most_common(1)[0][0] if samples else BG_INDEX
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = fill


def draw_left_fitted(draw: ImageDraw.ImageDraw, box: Box, text: str, base_size: int, fill=INK, min_size: int = 6) -> None:
    """Shrinks the font until the text's natural width fits the box
    (small overflow allowance), then draws it with its left edge
    pinned to the box's left edge, vertically centered - matching how
    every FORM*.IMG label is left-anchored right before its widget."""
    x0, y0, x1, y1 = box
    target_width = (x1 - x0) * 1.05
    size = base_size
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while size > min_size and bbox[2] - bbox[0] > target_width:
        size -= 1
        font = ImageFont.truetype(MONTSERRAT_BOLD, size)
        bbox = draw.textbbox((0, 0), text, font=font)
    cy = (y0 + y1) / 2
    x = x0 - bbox[0]
    y = round(cy - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


# Every screen's own list of (erase_box, translated_text, base_font_size).
# "Sair" (was "Exit") is always the last entry in each list and is drawn
# in INK_EXIT instead of INK - see build().
FORMS: dict[str, list[LabelSpec]] = {
    "FORM1.IMG": [
        ((6, 26, 60, 41), "Alcance:", 9),
        ((96, 26, 106, 41), "a", 9),
        ((6, 52, 60, 66), "Aumento:", 9),
        ((96, 52, 106, 66), "a", 9),
        ((142, 52, 167, 66), "por", 8),
        ((92, 72, 150, 89), "Niveis", 9),
        ((6, 96, 146, 109), "Custo do Feitico:", 8),
        ((148, 96, 167, 109), "Sair", 8),
    ],
    "FORM2.IMG": [
        ((6, 26, 60, 41), "Alcance:", 9),
        ((96, 26, 106, 41), "a", 9),
        ((6, 49, 60, 64), "Aumento:", 9),
        ((96, 49, 106, 64), "a", 9),
        ((142, 49, 167, 64), "por", 8),
        ((92, 72, 150, 87), "Niveis", 9),
        ((6, 95, 60, 110), "Golpes:", 9),
        ((92, 95, 150, 110), "vezes", 9),
        ((6, 118, 146, 129), "Custo do Feitico:", 8),
        ((148, 118, 167, 129), "Sair", 8),
    ],
    "FORM3.IMG": [
        ((6, 31, 66, 46), "Chance:", 9),
        ((102, 31, 130, 46), "%", 9),
        ((6, 54, 66, 69), "Aumento:", 9),
        ((102, 54, 139, 69), "% por", 7),
        ((158, 54, 206, 69), "Niveis", 9),
        ((6, 79, 182, 90), "Custo do Feitico:", 7),
        ((184, 79, 206, 90), "Sair", 8),
    ],
    "FORM4.IMG": [
        ((6, 30, 75, 45), "Chance:", 10),
        ((111, 30, 135, 45), "%", 10),
        ((6, 53, 75, 68), "Aumento:", 10),
        ((111, 53, 152, 68), "% por", 8),
        ((168, 53, 206, 68), "Niveis", 9),
        ((6, 78, 75, 93), "Deterioracao:", 7),
        ((108, 78, 156, 93), "pts por", 7),
        ((176, 78, 206, 93), "Rod", 7),
        ((6, 101, 75, 116), "Duracao:", 9),
        ((108, 101, 206, 116), "Rod por nivel", 7),
        ((6, 128, 178, 139), "Custo do Feitico:", 8),
        ((180, 128, 206, 139), "Sair", 8),
    ],
    "FORM4A.IMG": [
        ((6, 30, 75, 45), "Chance:", 10),
        ((111, 30, 135, 45), "%", 10),
        ((6, 53, 75, 68), "Aumento:", 10),
        ((111, 53, 152, 68), "% por", 8),
        ((168, 53, 206, 68), "Niveis", 9),
        ((6, 78, 75, 93), "Deterioracao:", 7),
        ((108, 78, 156, 93), "pts por", 7),
        ((176, 78, 206, 93), "Rod", 7),
        ((6, 101, 75, 116), "Duracao:", 9),
        ((108, 101, 206, 116), "Rod por nivel", 7),
        ((6, 128, 178, 139), "Custo do Feitico:", 8),
        ((180, 128, 206, 139), "Sair", 8),
    ],
    "FORM5.IMG": [
        ((6, 30, 75, 45), "Chance:", 10),
        ((111, 30, 135, 45), "%", 10),
        ((6, 53, 75, 68), "Aumento:", 10),
        ((111, 53, 152, 68), "% por", 8),
        ((168, 53, 206, 68), "Niveis", 9),
        ((6, 77, 74, 92), "Duracao:", 9),
        ((105, 77, 157, 92), "Rod por", 7),
        ((173, 77, 206, 92), "Niveis", 8),
        ((6, 113, 178, 124), "Custo do Feitico:", 8),
        ((180, 113, 206, 124), "Sair", 8),
    ],
    "FORM6.IMG": [
        ((6, 29, 84, 44), "Aumento:", 10),
        ((122, 29, 145, 44), "pts", 9),
        ((6, 52, 83, 67), "Duracao:", 10),
        ((121, 52, 206, 67), "Rod por nivel", 8),
        ((6, 75, 83, 90), "Taxa Liberacao:", 7),
        ((114, 75, 163, 90), "pts por", 7),
        ((179, 75, 206, 90), "Rod", 7),
        ((6, 102, 178, 113), "Custo do Feitico:", 8),
        ((180, 102, 206, 113), "Sair", 8),
    ],
    "FORM6A.IMG": [
        ((6, 29, 84, 44), "Reducao:", 10),
        ((122, 29, 145, 44), "pts", 9),
        ((6, 52, 83, 67), "Duracao:", 10),
        ((121, 52, 206, 67), "Rod por nivel", 8),
        ((6, 75, 87, 90), "Taxa Recup.:", 7),
        ((118, 75, 165, 90), "pts por", 7),
        ((181, 75, 206, 90), "Rod", 7),
        ((6, 102, 178, 113), "Custo do Feitico:", 8),
        ((180, 102, 206, 113), "Sair", 8),
    ],
    "FORM7.IMG": [
        ((6, 29, 84, 44), "Reducao:", 10),
        ((122, 29, 145, 44), "pts", 9),
        ((6, 54, 178, 65), "Custo do Feitico:", 8),
        ((180, 54, 206, 65), "Sair", 8),
    ],
    "FORM8.IMG": [
        ((6, 24, 83, 39), "Luz:", 10),
        ((6, 47, 83, 62), "Duracao:", 10),
        ((121, 47, 206, 62), "Rod por nivel", 8),
        ((6, 72, 160, 83), "Tipo: Segue o conjurador", 6),
        ((80, 84, 155, 95), "Projetil", 7),
        ((6, 102, 178, 113), "Custo do Feitico:", 8),
        ((180, 102, 206, 113), "Sair", 8),
    ],
    "FORM9.IMG": [
        ((6, 25, 63, 40), "Forca:", 10),
        ((99, 25, 206, 40), "Pontos de Vida", 8),
        ((6, 48, 63, 63), "Aumento:", 10),
        ((94, 48, 141, 63), "Vida por", 7),
        ((161, 48, 206, 63), "Niveis", 8),
        ((6, 101, 180, 112), "Custo do Feitico:", 8),
        ((182, 101, 206, 112), "Sair", 8),
    ],
    "FORM10.IMG": [
        ((6, 25, 63, 40), "Chance:", 9),
        ((99, 25, 125, 40), "%", 9),
        ((6, 48, 63, 63), "Aumento:", 9),
        ((94, 48, 136, 63), "% por", 7),
        ((152, 48, 206, 63), "Niveis", 8),
        ((6, 71, 63, 86), "Duracao:", 9),
        ((94, 71, 146, 86), "Rod por", 7),
        ((162, 71, 206, 86), "Niveis", 8),
        ((6, 95, 182, 109), "Feiticos Ofensivos?", 8),
        ((6, 124, 180, 135), "Custo do Feitico:", 8),
        ((182, 124, 206, 135), "Sair", 8),
    ],
    "FORM11.IMG": [
        ((6, 25, 64, 40), "Tempo:", 9),
        ((95, 25, 206, 40), "Rod", 9),
        ((6, 48, 63, 63), "Aumento:", 9),
        ((94, 48, 144, 63), "Rod por", 7),
        ((160, 48, 206, 63), "Niveis", 8),
        ((6, 74, 180, 85), "Custo do Feitico:", 8),
        ((182, 74, 206, 85), "Sair", 8),
    ],
    "FORM12.IMG": [
        ((6, 22, 66, 37), "Chance:", 9),
        ((102, 22, 130, 37), "%", 9),
        ((6, 45, 66, 60), "Aumento:", 9),
        ((102, 45, 143, 60), "% por", 7),
        ((159, 45, 206, 60), "Niveis", 8),
        ((6, 86, 183, 97), "Custo do Feitico:", 8),
        ((185, 86, 206, 97), "Sair", 8),
    ],
    "FORM13.IMG": [
        ((6, 30, 61, 45), "Numero:", 9),
        ((6, 82, 182, 93), "Custo do Feitico:", 8),
        ((184, 82, 206, 93), "Sair", 8),
    ],
    "FORM14.IMG": [
        ((6, 31, 66, 46), "Chance:", 9),
        ((102, 31, 130, 46), "%", 9),
        ((6, 54, 66, 69), "Aumento:", 9),
        ((102, 54, 143, 69), "% por", 7),
        ((159, 54, 206, 69), "Niveis", 8),
        ((6, 78, 65, 93), "Duracao:", 9),
        ((96, 78, 148, 93), "Rod por", 7),
        ((164, 78, 206, 93), "Niveis", 8),
        ((6, 106, 182, 117), "Custo do Feitico:", 8),
        ((184, 106, 206, 117), "Sair", 8),
    ],
    "FORM15.IMG": [
        ((6, 27, 54, 42), "Ganho:", 9),
        ((85, 27, 173, 42), "de Vida", 9),
        ((6, 50, 54, 65), "Cada:", 9),
        ((85, 50, 173, 65), "Rod", 9),
        ((6, 73, 54, 88), "Durante:", 9),
        ((85, 73, 173, 88), "Rod por nivel", 7),
        ((6, 101, 143, 112), "Custo do Feitico:", 7),
        ((145, 101, 173, 112), "Sair", 8),
    ],
}


def unscale_6bit(v: int) -> int:
    return (v << 2) | (v >> 4)


def load_spellmkr_palette() -> list[int]:
    """FORM*.IMG has no palette of its own - it's a partial dialog
    drawn over the still-visible SPELLMKR.IMG screen, so it must use
    that screen's own embedded palette (see module docstring). Reads
    the pristine SPELLMKR.IMG that split_bsa.py already extracted
    (unmodified by anything that runs before this script in
    build_all.py's pipeline) rather than GLOBAL.BSA directly."""
    filedata = (PARTS_DIR / "SPELLMKR.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert flags & 0x100, "SPELLMKR.IMG is expected to have an embedded palette"
    pal_start = 12 + length
    pal_6bit = filedata[pal_start:pal_start + 768]
    return [unscale_6bit(v) for v in pal_6bit]


def build(name: str, palette_flat: list[int]) -> None:
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 4, f"{name} is expected to be type-4 (LZSS) compressed"
    assert (flags & 0x100) == 0, f"{name} is expected to have no embedded palette"

    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    pixels = bytes(pixels)

    specs = FORMS[name]
    all_boxes = [box for box, _, _ in specs]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_mode_fill(px, pixels, width, height, box, all_boxes)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for i, (box, text, size) in enumerate(specs):
        fill = INK_EXIT if i == len(specs) - 1 else INK
        draw_left_fitted(draw, box, text, size, fill=fill)

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
    im_out.convert("RGB").resize((width * 3, height * 3), Image.NEAREST).save(
        PREVIEW_DIR / f"{name.replace('.', '_')}_traduzido.png"
    )


def main() -> None:
    print("Building translated FORM*.IMG screens (GLOBAL_parts/legivel/)...")
    palette_flat = load_spellmkr_palette()
    for name in FORMS:
        build(name, palette_flat)
    print("Done.")


if __name__ == "__main__":
    main()
