"""Bakes the Portuguese translation into EQUIP.IMG - an older/alternate
variant of the dungeon loot screen also handled by
build_bsa_newequip.py (NEWEQUIP.IMG): same "Level: N" indicator and
Drop/Spellbook/Exit button bar, but with EXIT and DROP swapped left-right
(EXIT sits where NEWEQUIP.IMG has DROP, and vice versa) - confirmed by
measuring both files' pristine ink pixel positions independently, not
assumed. Found via the "varredura_img_bruta.py" bulk scan (see
docs/inventario-arquivos.md, seção 4).

Same asset family as NEWEQUIP.IMG/CHARSTAT.IMG: no embedded palette,
LZSS "type 4" already in the original (no recompression needed), same
ink color (palette index 253, RGB (191,115,0)) as every other screen in
this family - but the BACKGROUND palette is CHARSHT.COL here, not
PAL.COL. The bulk scan's default-palette (PAL.COL) render looked like a
plausible lava/marble texture and was accepted without comparing
alternatives - trying CHARSHT.COL side by side later showed it renders
a proper dark stone/teal background (matching CHARSTAT.IMG's own
palette) instead, which is obviously correct for a character
inventory-style screen. The ink index (253) happens to map to the same
RGB under both palettes, so only the palette FILE loaded needed to
change here - the erase technique (texture-clone, still needed: this
stone background is high-contrast too) and every measured box/position
stayed identical.

Reads and overwrites the pristine copy split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG`.

Usage: python3 scripts/build_bsa_equip.py
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
INK = (191, 115, 0)  # sampled palette index 253
INK_INDEX = 253
BG_INDEX = 250

Box = tuple[int, int, int, int]


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


def erase_box(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box], y_bounds: tuple[int, int] | None = None) -> None:
    """Clone-a-patch, horizontal shifts only. The button bar this is
    used for is a narrow strip sandwiched between two visually
    different areas (the map/inventory view above, the panel's bottom
    border below) - a vertical shift big enough to clear the box lands
    in one of those, not in more of the same button-bar texture, and
    plants a visibly wrong-toned rectangle (this actually happened for
    the "Grimorio" button: the horizontal candidates were all rejected
    for overlapping a neighboring button's text box, so it fell through
    to a vertical shift that grabbed the map area instead). Restricting
    to horizontal-only means a bad vertical clone can never be chosen.

    `y_bounds`, when given, clamps the mode-fill fallback's ring
    sampling to stay within that (min_y, max_y) strip - needed for
    "Grimorio", whose box already spans the button bar's full height
    (touches the panel's bottom edge), so a ring search anchored on its
    own box reaches upward past the strip's top border into the darker
    map-view texture above and (being more uniform than the strip's own
    noisy teal) wins the mode vote, painting a visibly wrong dark patch
    - confirmed by sampling (141 - map texture - outvoted 250 - strip
    background - 111 to 38). Without a caller-supplied bound the ring
    has no way to know where the strip actually ends."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    offsets = [
        (w, 0), (-w, 0), (2 * w, 0), (-2 * w, 0), (3 * w, 0), (-3 * w, 0),
    ]
    for dx, dy in offsets:
        candidate = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        if _region_is_clean(pristine, width, height, candidate, exclude):
            cx0, cy0, cx1, _ = candidate
            for row in range(h):
                src_row = (cy0 + row) * width
                dst_row = (y0 + row) * width
                px[dst_row + x0:dst_row + x1] = pristine[src_row + cx0:src_row + cx1]
            return

    y_min, y_max = y_bounds if y_bounds is not None else (0, height)
    r = 4
    samples: list[int] = []
    while len(samples) < 15 and r <= 30:
        samples = [
            pristine[yy * width + xx]
            for yy in range(max(y_min, y0 - r), min(y_max, y1 + r))
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


def erase_plaque_text(px: bytearray, pristine: bytes, width: int, palette_flat: list[int], box: Box) -> None:
    """EQUIPMENT sits on its own small gold-plaque banner (gradient
    metal shades + rivets, NOT the plain stone background) - a
    texture-clone/mode-fill erase over the whole box would replace the
    plaque itself with plain stone, losing the decoration. Instead,
    row by row, every dark ("ink") pixel is replaced with the nearest
    non-dark pixel in that same row (scanning outward on both sides) -
    healing just the letter strokes while leaving the plaque's own
    gold gradient intact underneath."""
    x0, y0, x1, y1 = box

    def lum(idx: int) -> float:
        r, g, b = palette_flat[idx * 3:idx * 3 + 3]
        return 0.299 * r + 0.587 * g + 0.114 * b

    DARK_LUM = 60
    for y in range(y0, y1):
        row = y * width
        for x in range(x0, x1):
            if lum(pristine[row + x]) >= DARK_LUM:
                continue
            left = x
            while left > 0 and lum(pristine[row + left]) < DARK_LUM:
                left -= 1
            right = x
            while right < width - 1 and lum(pristine[row + right]) < DARK_LUM:
                right += 1
            left_ok = lum(pristine[row + left]) >= DARK_LUM
            right_ok = lum(pristine[row + right]) >= DARK_LUM
            if left_ok and (not right_ok or (x - left) <= (right - x)):
                px[row + x] = pristine[row + left]
            elif right_ok:
                px[row + x] = pristine[row + right]


def draw_centered(draw: ImageDraw.ImageDraw, center_x: float, center_y: float, text: str, size: int, max_width: float | None = None, min_size: int = 6, fill=None) -> None:
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while max_width is not None and size > min_size and bbox[2] - bbox[0] > max_width:
        size -= 1
        font = ImageFont.truetype(MONTSERRAT_BOLD, size)
        bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(center_y - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=fill if fill is not None else INK)


# Dark ink sampled from EQUIPMENT's own lettering (palette index 31,
# RGB (41,0,0)) - a near-black red, distinct from every other label's
# gold (INK), since this one sits ON a gold plaque rather than a plain
# background.
PLAQUE_INK = (60, 10, 5)

# (erase_box, text, size, center_x, center_y, max_width) - measured
# against the pristine ink pixels: EQUIPMENT banner x51-114 y39-47;
# LEVEL x105-125 y23-29; EXIT x14-28 y192-198 (left button, unlike
# NEWEQUIP.IMG where EXIT sits on the right); SPELLBOOK x67-101
# y192-198; DROP x138-152 y192-198 (right button, swapped with
# NEWEQUIP.IMG's layout). EQUIPMENT is a title banner baked directly
# into EQUIP.IMG's own pixels - separate from (and easy to miss next
# to) the small standalone EQUIPB.IMG banner used elsewhere - and is
# handled with erase_plaque_text()+PLAQUE_INK instead of the shared
# erase_box()+INK every other entry uses (see build()).
PLAQUE_BOX: Box = (44, 37, 122, 49)
LABELS: list[tuple[Box, str, int, float, float, float | None]] = [
    ((98, 19, 132, 32), "Nivel:", 7, 115, 29, None),
    ((10, 188, 34, 200), "SAIR", 8, 21, 195, None),
    ((60, 188, 108, 200), "GRIMORIO", 7, 83, 195, None),
    ((134, 187, 158, 200), "LARGAR", 6, 145, 195, None),
]

# Global top border row of the button-bar strip (measured: row 187 is
# still the darker map-view texture, row 188 is the strip's own teal
# background, across the full width) - passed as y_bounds to erase_box
# for every footer button so its mode-fill fallback can never sample
# above the strip.
FOOTER_STRIP: tuple[int, int] = (188, 200)


def build() -> None:
    filedata = (PARTS_DIR / "EQUIP.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 4, "EQUIP.IMG is expected to be type-4 (LZSS) compressed"
    assert (flags & 0x100) == 0, "EQUIP.IMG is expected to have no embedded palette"

    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    pixels = bytes(pixels)

    col_raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    all_boxes = [box for box, _, _, _, _, _ in LABELS] + [PLAQUE_BOX]
    footer_boxes = {(10, 188, 34, 200), (60, 188, 108, 200), (134, 187, 158, 200)}
    px = bytearray(pixels)
    for box in [box for box, _, _, _, _, _ in LABELS]:
        y_bounds = FOOTER_STRIP if box in footer_boxes else None
        erase_box(px, pixels, width, height, box, all_boxes, y_bounds=y_bounds)
    erase_plaque_text(px, pixels, width, palette_flat, PLAQUE_BOX)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for box, text, size, cx, cy, max_width in LABELS:
        draw_centered(draw, cx, cy, text, size, max_width=max_width)
    draw_centered(draw, 83, 43, "EQUIPAMENTO", 8, max_width=74, fill=PLAQUE_INK)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "EQUIP.png")
    print(f"  EQUIP.IMG: wrote legivel/EQUIP.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 3, height * 3), Image.NEAREST).save(
        PREVIEW_DIR / "EQUIP_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated EQUIP.IMG (GLOBAL_parts/legivel/)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
