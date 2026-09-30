"""Bakes the Portuguese translation into CHARSTAT.IMG - the character
attribute sheet (Str/Int/Wil/Agi/Spd/End/Per/Luc, derived combat stats,
and the Health/Fatigue/Gold/Experience/Level resource block, plus the
"Done" button) shown during character creation and levelling up.

Unlike every other .IMG handled so far, this one has NO embedded
palette (flags & 0x100 is unset) - the game draws it using whatever
palette is already active, which for the character sheet is
CHARSHT.COL (a loose file at the game's root, 8-byte header then 768
bytes already 8-bit-per-channel - unlike embedded .IMG palettes, no
6-bit-to-8-bit s6() expansion here, same convention as DAYTIME.COL).

Also type 8 (Huffman) compressed, like MENU.IMG - decoded with the
same decode_type08(data, 12 + 2, ...) convention (skip the 2-byte
decompressed-length field after the header - see huffman_codec.py's
docstring) and re-saved as LZSS type 4, since no Huffman encoder exists
here either.

The background is a marbled dark teal texture (not a flat color), so
erasing uses the same "flat-fill with the panel's own dominant tone"
approach as MENU.IMG rather than a true per-pixel match - acceptable
here since the texture is subtle and every erase box is small.

Every label's exact box was measured by scanning for the screen's own
ink color (index 253, RGB ~(191,115,0) via CHARSHT.COL - a flat, non-
anti-aliased color, no separate outline) directly against the pristine
panel - see docs/pipeline-imagens.md for why per-file ink colors must
always be sampled fresh rather than reused from another screen.

Labels are drawn with draw_fitted's shrink-and-center approach (see
build_bsa_ui.py) rather than pinned at a fixed size: this screen's
columns are extremely narrow (the left column is ~17px wide for a
3-4 letter abbreviation), so letting the translated label shrink to
fit and center on the original's own midpoint is far more forgiving
than trying to hand-pick a same-length abbreviation for every stat.

Reads the pristine copy split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG` (per
img_manifest.py, always recompressed as LZSS "type 4" since there's no
type-8 encoder), written back to "GLOBAL_parts/CHARSTAT.IMG" (the same
place split_bsa.py extracted it), which merge_bsa.py then packs into a
full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_charstat.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from huffman_codec import decode_type08

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (191, 115, 0)  # sampled palette index 253 - flat, no anti-aliasing/outline
INK_INDEX = 253
BG_INDEX = 250  # fallback dominant marbled-teal background tone

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


def erase_box(px: bytearray, pristine: bytes, width: int, height: int, box: Box, exclude: list[Box]) -> None:
    """Erases by CLONING a same-size patch of real background texture
    from directly above or below the box, rather than filling with a
    flat color. This screen's marbled dark-teal background has high
    local contrast everywhere - a single flat tone (even the locally
    most common one, tried first and rejected) always reads as a
    visible rectangle against it. Copying an actual patch of texture
    keeps the erased area looking exactly like the noise around it,
    since the pattern has no directional bias (any nearby patch looks
    equally plausible in its place). Tries horizontal shifts first
    (same row band, so a vertical brightness gradient in the panel
    can't make the clone read as a mismatched patch), then vertical
    ones, alternating each side, until it finds a patch with no ink and
    no overlap with another label's box; falls back to the
    INTRO-panels-style local mode fill if no clean patch is found."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    offsets = [
        (w, 0), (-w, 0), (2 * w, 0), (-2 * w, 0),
        (0, h), (0, -h), (0, 2 * h), (0, -2 * h),
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

    # Fallback: no clean patch found - use the local mode-fill approach
    # (build_bsa_intro.py's erase_box technique) instead of leaving it.
    r = 4
    samples: list[int] = []
    while len(samples) < 15 and r <= 30:
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


def draw_right_aligned(draw: ImageDraw.ImageDraw, anchor_x1: int, anchor_ybottom: float, text: str, size: int) -> None:
    """Draws text with its RIGHT edge pinned exactly to anchor_x1 and
    its BOTTOM edge pinned to anchor_ybottom. The original screen
    right-aligns every label within its column - "Damage:", "Spell
    Pts:", "Magic Def:" etc. all end their colon at the same x, with
    the label growing leftward to whatever length it needs - not
    left-aligned as an earlier version of this script assumed.
    anchor_x1 is that shared per-column edge (see COL_*_X below), not a
    per-label one. Vertical anchoring is by BOTTOM edge, not center: a
    center anchor let each word's own descenders (a "g", differing
    between e.g. "Agi:" and "Vel:") push it down into the row below
    even though the row spacing was fine on average - anchoring every
    label's bottom to the original's own measured bottom edge instead
    gives a consistent baseline rhythm, matching how the original text
    actually sits. size is still chosen per-label ahead of time (see
    LABELS) to make each translation's natural, undistorted width
    approximate that same original label's own measured width -
    matching width via font size rather than stretching/squeezing
    letterforms, which distorts them (see build_bsa_ui.py's draw_fitted
    for where that was tried and rejected for the same reason)."""
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = anchor_x1 - (bbox[2] - bbox[0]) - bbox[0]
    y = anchor_ybottom - bbox[3]
    draw.text((x, y), text, font=font, fill=INK)


def draw_centered(draw: ImageDraw.ImageDraw, center_x: float, center_y: float, text: str, size: int) -> None:
    """Draws text centered on (center_x, center_y) - used only for the
    "Done" button, which isn't a right-aligned "label:" column entry."""
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = round(center_x - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(center_y - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=INK)


# The original screen right-aligns every label within its column -
# "Damage:", "Spell Pts:", "Magic Def:" all end their colon at the same
# x regardless of word length - so every label here is stored as
# (erase_box, text, size, column_right_x, row_ybottom) and drawn with
# draw_right_aligned, not left-pinned. Sizes are close to a uniform 8px
# cap height (the biggest that fits these ~8px-apart rows without the
# next row's text touching it) for consistent, legible quality; a
# couple of long words (Experiencia) still need a smaller size or they
# would extend past the left edge of the panel entirely.
LabelSpec = tuple[Box, str, int, int, float]
COL_LEFT_X = 24  # shared right edge of the left (attribute) column
COL_MID_X = 84  # shared right edge of the middle (combat stat) column
COL_RIGHT_X = 143  # shared right edge of the right column
COL_RES_X = 43  # shared right edge of the resource/bottom block
LABELS: list[LabelSpec] = [
    # left column: attribute abbreviations
    ((2, 50, 32, 60), "For:", 8, COL_LEFT_X, 57),
    ((2, 58, 32, 68), "Int:", 8, COL_LEFT_X, 66),
    ((2, 66, 32, 77), "Von:", 8, COL_LEFT_X, 74),
    ((2, 75, 32, 85), "Agi:", 8, COL_LEFT_X, 83),
    ((2, 83, 32, 93), "Vel:", 8, COL_LEFT_X, 91),
    ((2, 91, 32, 101), "Res:", 8, COL_LEFT_X, 100),
    ((2, 99, 32, 110), "Per:", 8, COL_LEFT_X, 108),
    ((2, 108, 32, 118), "Sor:", 8, COL_LEFT_X, 117),
    # middle column: derived combat stats
    ((42, 50, 86, 60), "Dano:", 8, COL_MID_X, 59),
    ((42, 58, 86, 68), "Magia:", 8, COL_MID_X, 67),
    ((42, 66, 86, 77), "Def Mag:", 8, COL_MID_X, 75),
    ((42, 75, 86, 85), "Ataque:", 8, COL_MID_X, 81),
    ((42, 91, 86, 101), "Vida:", 8, COL_MID_X, 98),
    ((42, 99, 86, 110), "Carisma:", 8, COL_MID_X, 105),
    # right column
    ((101, 50, 145, 60), "Peso Max:", 8, COL_RIGHT_X, 58),
    ((101, 75, 145, 85), "Defesa:", 8, COL_RIGHT_X, 81),
    ((101, 91, 145, 101), "Cura:", 8, COL_RIGHT_X, 98),
    # resource block
    ((8, 125, 45, 135), "Vida:", 8, COL_RES_X, 133),
    ((8, 133, 45, 144), "Fadiga:", 8, COL_RES_X, 142),
    ((8, 142, 45, 152), "Ouro:", 8, COL_RES_X, 150),
    # bottom - "Experiencia:" is long enough that even at a small size it
    # needs the panel's own left edge as its effective start, so it gets
    # a smaller size than the rest to avoid running off the left side.
    ((0, 156, 45, 167), "Experiencia:", 6, COL_RES_X, 165),
    ((8, 165, 43, 175), "Nivel:", 8, COL_RES_X, 173),
]
# "Done" isn't a right-aligned "label:" column entry - it's a centered
# button - so it's handled separately with draw_centered.
DONE_BOX: Box = (15, 180, 35, 189)
DONE_TEXT = "Feito"
DONE_SIZE = 8
DONE_CENTER = (25, 184.5)


def build() -> None:
    filedata = (PARTS_DIR / "CHARSTAT.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 8, "CHARSTAT.IMG is expected to be type-8 (Huffman) compressed"
    assert (flags & 0x100) == 0, "CHARSTAT.IMG is expected to have no embedded palette"

    pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)

    col_raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    all_boxes = [box for box, _, _, _, _ in LABELS] + [DONE_BOX]
    px = bytearray(pixels)
    for box in all_boxes:
        erase_box(px, pixels, width, height, box, all_boxes)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for _, text, size, right_x, ybottom in LABELS:
        draw_right_aligned(draw, right_x, ybottom, text, size)
    draw_centered(draw, DONE_CENTER[0], DONE_CENTER[1], DONE_TEXT, DONE_SIZE)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "CHARSTAT.png")
    print(f"  CHARSTAT.IMG: wrote legivel/CHARSTAT.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 3, height * 3), Image.NEAREST).save(
        PREVIEW_DIR / "CHARSTAT_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated CHARSTAT.IMG (GLOBAL_parts/legivel/)...")
    PREVIEW_DIR.mkdir(exist_ok=True)
    build()
    print("Done.")


if __name__ == "__main__":
    main()
