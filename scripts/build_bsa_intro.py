"""Bakes the Portuguese translation into INTRO01.IMG..INTRO09.IMG, the nine
"vision" panels (bundled inside GLOBAL.BSA) that show Jagar Tharn's coup
against Emperor Uriel Septim VII. Each panel pairs a hand-drawn illustration
with a short caption placed in whatever corner the art leaves free.

Unlike a single bounding-box erase, each caption is specified here as its
own list of ORIGINAL per-line rectangles (measured against 3x zoomed
renders of the pristine English panels), so erasing/redrawing follows the
real, irregular shape of the original text instead of a rectangle that can
bite into the artwork or the scroll's border. The translated text is then
reflowed line by line starting at the first original line's position,
using the widest original line as the wrap width.

These panels carry no built-in palette; in-game they're shown right after
HISTORY.IMG, and reusing HISTORY.IMG's own embedded palette renders them in
the correct parchment tones (confirmed by visual comparison against other
candidate palettes).

Reads the already-blanked PNGs blank_bsa_intro.py saves into
"Minha tradução/GLOBAL_parts/legivel/empty/" (run split_bsa.py then
blank_bsa_intro.py first) and writes the translated result as a
readable PNG into "Minha tradução/GLOBAL_parts/legivel/".
compile_images.py later compiles that PNG into the actual game-format
`.IMG`, written back to "GLOBAL_parts/<nome>.IMG" (the same place
split_bsa.py extracted it), which merge_bsa.py then packs into a full
GLOBAL.BSA.

Usage: python3 scripts/build_bsa_intro.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
EMPTY_DIR = LEGIVEL_DIR / "empty"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"
BG_INDEX = 3
INK = (58, 30, 12)  # sampled from the panels' own caption ink under HISTORY.IMG's palette

Box = tuple[int, int, int, int]


class Caption:
    """A caption block: the ORIGINAL text's per-line rectangles (measured
    from the pristine panel) plus the Portuguese replacement, font size,
    and vertical spacing to reflow it with."""

    def __init__(
        self,
        original_lines: list[Box],
        text: str,
        font_size: int,
        line_height: int,
        draw_lines: list[Box] | None = None,
        draw_top: int | None = None,
        draw_left: int | None = None,
    ):
        self.original_lines = original_lines
        self.text = text
        self.font_size = font_size
        self.line_height = line_height
        # The erase boxes are kept tight to the original English glyphs so
        # erasure never grazes the artwork. But Portuguese is often longer,
        # and wrapping it to that same tight width makes it break far
        # earlier than it has to, even though most lines actually have
        # plenty of clear parchment beyond where the English happened to
        # end. draw_lines gives each line its own wider limit - how far it
        # may really extend before reaching the art - used only when
        # reflowing the translation, never for erasing. Defaults to
        # original_lines (no extra room) when not given.
        self.draw_lines = draw_lines if draw_lines is not None else original_lines
        # Where the translation's first line starts, when the erase box's
        # own top isn't the right spot to hang the reflowed text from
        # (e.g. tightening the erase box moved its top away from where a
        # comfortable text block should start). Defaults to the erase
        # box's own top when not given.
        self.draw_top = draw_top
        # Same idea, horizontally: where the text's left edge starts,
        # when the erase box's own left isn't the right spot.
        self.draw_left = draw_left

    @property
    def left(self) -> int:
        return min(b[0] for b in self.original_lines)

    @property
    def top(self) -> int:
        return min(b[1] for b in self.original_lines)

    @property
    def max_width(self) -> int:
        return max(b[2] - b[0] for b in self.original_lines)


# Per-panel captions. Each original line's box was measured by eye against
# 3x zoomed renders of the pristine (English) panel, so it tightly matches
# that specific line's footprint - never the artwork, never the scroll's
# rolled/torn border.
PANELS: dict[str, list[Caption]] = {
    "INTRO01.IMG": [
        Caption(
            [(14, 21, 150, 39), (14, 39, 150, 57), (14, 57, 148, 76), (14, 76, 130, 88), (14, 88, 130, 108)],
            "Uriel Septim VII, Imperador de Tamriel, aparece ao lado de Talin, líder da Guarda Imperial.",
            11, 21,
        ),
    ],
    "INTRO02.IMG": [
        Caption(
            [(16, 53, 192, 79), (16, 79, 200, 104), (16, 104, 200, 128), (16, 128, 172, 152)],
            "Eles foram convocados por Jagar Tharn, Mago de Batalha Imperial do Império, por rumores de traição...",
            13, 22,
        ),
    ],
    "INTRO03.IMG": [
        Caption(
            [(16, 20, 178, 42), (16, 42, 133, 65)],
            "O Imperador é traído...",
            14, 22,
        ),
    ],
    "INTRO04.IMG": [
        Caption(
            [(130, 24, 288, 45), (130, 44, 293, 61), (130, 61, 224, 80)],
            "E enviado a uma dimensão escolhida por Tharn...",
            13, 22,
        ),
    ],
    "INTRO05.IMG": [
        Caption(
            [(9, 20, 276, 36), (9, 36, 133, 50)],
            "Após meses de preparação, Jagar Tharn toma o trono...",
            13, 22,
        ),
    ],
    "INTRO06.IMG": [
        Caption(
            [(20, 21, 145, 40), (20, 40, 158, 58), (20, 58, 133, 70), (20, 70, 82, 90)],
            "Ria Silmane, antes aprendiz de Tharn, é capturada antes que possa avisar",
            12, 17,
            draw_lines=[(20, 21, 225, 40), (20, 40, 225, 58), (20, 58, 225, 70), (20, 70, 200, 90)],
            draw_top=17,
        ),
        Caption(
            [(148, 133, 296, 150), (100, 155, 316, 172)],
            "o Conselho dos Anciãos sobre a traição do Mago de Batalha Imperial...",
            12, 16,
            draw_lines=[(148, 133, 300, 150), (100, 155, 318, 172)],
            draw_top=124, draw_left=140,
        ),
    ],
    "INTRO07.IMG": [
        Caption(
            [(18, 21, 234, 40), (18, 40, 187, 58), (18, 58, 151, 75), (18, 75, 111, 90), (16, 90, 102, 105)],
            "Manipulando a essência da magia, Tharn se prepara para tomar o lugar do verdadeiro Imperador como governante da terra conhecida...",
            10, 18,
            draw_lines=[(18, 21, 235, 40), (18, 40, 220, 58), (18, 58, 195, 75), (18, 75, 155, 90), (16, 90, 110, 105)],
        ),
    ],
    "INTRO08.IMG": [
        Caption(
            [(18, 21, 163, 38), (18, 38, 125, 55), (18, 55, 97, 70), (18, 70, 84, 85)],
            "O Feiticeiro Imperial não perde tempo reunindo seus servos...",
            13, 16,
            draw_lines=[(18, 21, 163, 38), (18, 38, 125, 55), (18, 55, 116, 70), (18, 70, 84, 85)],
            # Shifted 3px left/up from the erase box's own top-left (18,21)
            # on request. line_height dropped from the placeholder 22 to
            # 16 to match what draw_top=None would have computed anyway
            # (span 85-21=64 over 4 lines) - draw_top switches the
            # spacing formula to use this field literally instead of that
            # dynamic span/line-count division (see erase_panel), so
            # leaving 22 in place after adding draw_top visibly widened
            # the line spacing beyond what was ever asked for.
            draw_top=18, draw_left=15,
        ),
    ],
    "INTRO09.IMG": [
        Caption(
            [(22, 22, 165, 38), (22, 38, 170, 57), (22, 57, 174, 76)],
            "E transformando-os em contrapartes distorcidas da Guarda Imperial...",
            13, 22,
        ),
    ],
}


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


def luminance_table(palette_flat: list[int]) -> list[float]:
    """Perceptual brightness per palette index. This palette is NOT a
    brightness ramp - index 15 (166,125,81), nearly as light as index 1
    (166,117,65), sits right next to index 19 (48,12,12), near-black - so
    comparing raw palette index numbers to judge "darker than" or to
    average two colors is meaningless. Luminance is what "ink vs
    background" actually means visually."""
    table = []
    for i in range(0, len(palette_flat), 3):
        r, g, b = palette_flat[i:i + 3]
        table.append(0.299 * r + 0.587 * g + 0.114 * b)
    return table


def build_integral(values: list[float], width: int, height: int) -> list[float]:
    """Summed-area table over a per-pixel scalar (luminance here), so any
    box's total can be read in O(1) - used to get local-average
    brightness without an O(r^2) scan per pixel."""
    w1 = width + 1
    integral = [0.0] * (w1 * (height + 1))
    for y in range(height):
        row_sum = 0.0
        base = y * width
        prev_row = y * w1
        cur_row = (y + 1) * w1
        for x in range(width):
            row_sum += values[base + x]
            integral[cur_row + x + 1] = integral[prev_row + x + 1] + row_sum
    return integral


def box_avg(integral: list[float], width: int, height: int, x: int, y: int, r: int) -> float:
    w1 = width + 1
    x0, y0 = max(0, x - r), max(0, y - r)
    x1, y1 = min(width, x + r + 1), min(height, y + r + 1)
    total = integral[y1 * w1 + x1] - integral[y0 * w1 + x1] - integral[y1 * w1 + x0] + integral[y0 * w1 + x0]
    return total / ((x1 - x0) * (y1 - y0))


# How much darker (in luminance) than its own immediate surroundings a
# pixel must be to count as ink. A flat threshold can't tell a letter
# stroke from a soft shadow gradient that happens to sit in the same
# brightness range; local contrast can, because a gradient changes slowly
# (so a pixel is close to its neighbors' average) while a letter stroke is
# a sharp, isolated dark mark against whatever's under it.
INK_CONTRAST = 20


def erase_box(
    px: bytearray,
    pristine: bytes,
    lum: list[float],
    integral: list[float],
    width: int,
    height: int,
    box: Box,
    exclude: list[Box],
) -> None:
    """Erases every pixel in the box - trusting the box itself to be
    precisely bounded to where the original English text actually was,
    never touching artwork - with a single flat fill color: the most
    common tone found in a ring immediately around the box (excluding
    ink, other caption boxes, and the panel's decorative border). One
    color for the whole box, taken from its own real surroundings, is
    what "the same color as the background around it" means; hunting for
    a different, individually-closest-matching sample per pixel is what
    produced visible blotches when that search occasionally reached a
    genuinely darker spot (a nearby shadow) instead of the plain
    background the box actually sits on."""
    BORDER = 20

    def is_ink(x: int, y: int) -> bool:
        return box_avg(integral, width, height, x, y, 2) - lum[pristine[y * width + x]] >= INK_CONTRAST

    def excluded(x: int, y: int) -> bool:
        if y < BORDER or y >= height - BORDER:
            return True
        # Only genuinely light, parchment-like pixels are valid fill
        # candidates - this also rules out the void outside the scroll's
        # torn edge (pure black, no local contrast against more black) and
        # a nearby illustration's shaded/dark linework, which a wide
        # search ring can otherwise reach if the box sits close to it.
        if lum[pristine[y * width + x]] < 100:
            return True
        if is_ink(x, y):
            return True
        return any(bx0 <= x < bx1 and by0 <= y < by1 for bx0, by0, bx1, by1 in exclude)

    x0, y0, x1, y1 = box
    samples: list[int] = []
    counts: Counter = Counter()
    # Minimum radius before a result can be trusted at all. A margin
    # check alone isn't enough: at r=6, INTRO08's first line found a
    # nearby shadow fold outvoting the box's true wider surroundings
    # 184-to-133 - a 37% margin, "confident" by any reasonable
    # threshold, yet still the wrong tone (a visibly darker patch) -
    # because at that radius the ring is small enough for one local
    # feature to dominate purely by proximity. The *actual* majority
    # tone doesn't overtake it until r=10, and keeps pulling further
    # ahead at every radius after that, so a small ring's "confidence"
    # here is meaningless - only a wider sample is. r=18 is where this
    # panel's true tone was already a clear, stable plurality, kept as
    # a floor for every panel/box rather than special-casing this one.
    MIN_RADIUS = 18
    r = 6
    while r <= 40:
        samples = [
            pristine[yy * width + xx]
            for yy in range(max(0, y0 - r), min(height, y1 + r))
            for xx in range(max(0, x0 - r), min(width, x1 + r))
            if not excluded(xx, yy) and not (x0 <= xx < x1 and y0 <= yy < y1)
        ]
        counts = Counter(samples)
        if r >= MIN_RADIUS and len(samples) >= 20:
            top = counts.most_common(2)
            if len(top) < 2 or top[0][1] >= top[1][1] * 1.3:
                break
        r += 4
    fill = counts.most_common(1)[0][0] if counts else BG_INDEX

    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = fill


def erase_panel(pixels: bytes, width: int, height: int, palette_flat: list[int], captions: list[Caption]) -> bytes:
    """Erases every caption's original-English boxes and returns the
    resulting pixels - this is the "empty" (text-free) version of a panel,
    saved to EMPTY_DIR so it can be reviewed on its own and reused as the
    base for drawing the translation, without re-running (and re-risking)
    the erase step each time.

    Each ORIGINAL line gets its own rectangle individually - never a
    single box spanning the whole caption, so short lines don't drag a
    wide eraser through nearby artwork or the scroll border. This alone
    guarantees every pixel of the original English is gone."""
    px = bytearray(pixels)
    all_boxes = [box for cap in captions for box in cap.original_lines]
    lum = luminance_table(palette_flat)
    pixel_lum = [lum[p] for p in pixels]
    integral = build_integral(pixel_lum, width, height)
    for cap in captions:
        for box in cap.original_lines:
            erase_box(px, pixels, lum, integral, width, height, box, all_boxes)
    return bytes(px)


def draw_translation(pixels: bytes, width: int, height: int, palette_flat: list[int], captions: list[Caption]) -> bytes:
    """Draws the Portuguese translation onto an already-erased ("empty")
    panel and returns the final quantized pixels, ready to compress."""
    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(pixels)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    # 2) draw the translation line by line. Wrapping width is chosen per
    # caption, as wide as possible while staying safe: try the widest
    # original line's width first, and if that produces more lines than
    # the original had, or any resulting line would be wider than the
    # original line it now lands on, narrow the wrap width and retry.
    # This keeps text at a comfortable width in the (common) case where
    # the translated line count matches the original, while falling back
    # to the narrowest original width - guaranteed never to touch the
    # art no matter how lines get redistributed - only when it must.
    # Line spacing is always span/line-count (no fixed floor), so the
    # block can never extend past the vertical area the original used,
    # regardless of how many lines that ends up being. Starting a little
    # inside the first original line's spot (rather than flush) avoids
    # crowding the scroll's border. Text is drawn straight onto whatever
    # is already there - never behind a manufactured rectangle.
    DRAW_INSET_X, DRAW_INSET_Y = 6, 4
    for cap in captions:
        font = ImageFont.truetype(NOTO_SERIF_ITALIC, cap.font_size)
        text_left = cap.draw_left if cap.draw_left is not None else cap.left
        widest = max(b[2] for b in cap.draw_lines) - text_left - DRAW_INSET_X
        narrowest = min(b[2] for b in cap.draw_lines) - text_left - DRAW_INSET_X

        def fits(trial: list[str]) -> bool:
            return all(
                draw.textbbox((0, 0), trial[i], font=font)[2]
                <= cap.draw_lines[i][2] - text_left - DRAW_INSET_X
                for i in range(len(trial))
            )

        lines = wrap_to_width(draw, cap.text, font, narrowest)
        # Prefer a width that reproduces the original's own line count
        # (matching its visual rhythm) over one that only "fits" by
        # collapsing onto fewer, longer lines.
        for target_le in (False, True):
            for w in range(widest, narrowest, -4):
                trial = wrap_to_width(draw, cap.text, font, w)
                ok_count = len(trial) == len(cap.original_lines) if not target_le else len(trial) <= len(cap.original_lines)
                if ok_count and fits(trial):
                    lines = trial
                    break
            else:
                continue
            break
        x0 = text_left + DRAW_INSET_X
        if cap.draw_top is not None:
            # Manually positioned: start where asked and space lines at
            # the caption's own fixed line_height, instead of stretching
            # them across the erase box's span - used when that span was
            # measured for tightly-erased English and doesn't describe
            # where the reflowed Portuguese should actually sit.
            y = cap.draw_top + DRAW_INSET_Y
            line_height = cap.line_height
        else:
            # Spread the translated lines across the exact vertical span
            # the original caption occupied, rather than the original
            # per-line spacing - otherwise a caption that wraps to fewer
            # lines than the original leaves one of the erased
            # original-line boxes with no text drawn over it, showing up
            # as a flat, un-textured rectangle.
            y = cap.top + DRAW_INSET_Y
            span = max(b[3] for b in cap.original_lines) - cap.top
            line_height = span // len(lines) if lines else span
        for line in lines:
            draw.text((x0, y), line, font=font, fill=INK)
            y += line_height

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    return bytes(quantized.getdata())


def build_translated_file(name: str, palette_flat: list[int]) -> tuple[bytes, int, int]:
    """Reads GLOBAL_parts/legivel/empty/<nome>.png - the already
    text-free version saved by blank_bsa_intro.py - and draws the
    Portuguese translation on top of it. The empty/ PNG is never touched
    here, so it stays available as a clean base to redraw from (no need
    to re-run the erase step, which is the one that risks grazing the
    artwork). Returns the translated pixel indices plus width/height -
    does not write anything itself, see main().

    If a panel has no empty/ copy yet, run split_bsa.py then
    blank_bsa_intro.py first."""
    stem = name.rsplit(".", 1)[0]
    im = Image.open(EMPTY_DIR / f"{stem}.png")
    width, height = im.size
    pixels = bytes(im.getdata())

    new_pixels = draw_translation(pixels, width, height, palette_flat, PANELS[name])
    return new_pixels, width, height


def save_legivel(name: str, pixels: bytes, width: int, height: int, palette_flat: list[int]) -> None:
    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    stem = name.rsplit(".", 1)[0]
    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(pixels)
    im.save(LEGIVEL_DIR / f"{stem}.png")
    print(f"  {name}: wrote legivel/{stem}.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
        PREVIEW_DIR / f"{name.replace('.', '_')}_traduzido.png"
    )


def main() -> None:
    print("Building translated intro-vision panels (GLOBAL_parts/legivel/)...")

    # HISTORY.IMG's own palette is what these panels are shown under
    # in-game; read it from the (still pristine) copy split_bsa.py
    # extracted alongside these panels - HISTORY.IMG's embedded palette
    # bytes never change between the pristine and translated versions,
    # so reading the still-pristine flat copy here is exactly as correct
    # as reading a translated one would be.
    hfiledata = (PARTS_DIR / "HISTORY.IMG").read_bytes()
    _, _, _, _, _, hlength = struct.unpack_from("<HHHHHH", hfiledata, 0)

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in hfiledata[12 + hlength:12 + hlength + 768]]

    for name in PANELS:
        pixels, width, height = build_translated_file(name, palette_flat)
        save_legivel(name, pixels, width, height, palette_flat)

    print("Done.")


if __name__ == "__main__":
    main()
