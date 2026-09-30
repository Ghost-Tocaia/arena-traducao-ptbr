"""Bakes the Portuguese translation into SCROLL01.IMG and SCROLL02.IMG, the
opening-narration scrolls bundled inside GLOBAL.BSA (they don't exist as
loose files — unlike SCROLL03.IMG, which build_images.py handles).

These two images carry no built-in palette of their own (unlike
SCROLL03.IMG/TITLE.IMG); the game paints them using whatever palette is
active at the time. Several palette guesses were tried and looked
plausible in isolated preview renders (DAYTIME.COL, then CHARSHT.COL,
then briefly DREARY.COL) but never actually matched what the user saw
in real play - because none of them were the palette the game actually
uses here. The real answer was found in OpenTESArena's own source
(IntroUiMVC.cpp, IntroUiView::getIntroStoryPaletteNames()): all three
intro-story panels (SCROLL01/02/03) are painted using **SCROLL03.IMG's
own embedded palette**, not any standalone .COL file. Confirmed by
re-rendering the pristine English art through SCROLL03's palette and
comparing against the user's own in-game screenshot - matched closely
(dark parchment-shadow background, warm ink).

Once the right palette was known, a second, subtler bug explained why
earlier CHARSHT.COL-based attempts sometimes looked fine in preview but
came out wrong once compiled: the render pipeline converts palette
indices to RGB, draws antialiased text, then re-quantizes the whole
image back to indices for compile_images.py (which stores raw indices
verbatim - see img_manifest.py's embute_paleta=False for these two
files). Under CHARSHT.COL, index 3 (208,195,167) and index 4
(207,191,161) are near-indistinguishable, so Pillow's quantizer could
land on either one for the same background fill - harmless under
CHARSHT.COL where both look identical, but catastrophic once
interpreted through SCROLL03's real palette, where index 3 is light
tan (170,130,81) and index 4 is dark chocolate-brown (77,40,16): a
coin-flip between "correct" and "wrong" baked in at build time,
explaining why the same script's output could render differently
across builds. Rendering natively in SCROLL03's own palette sidesteps
this - its near-duplicate index pairs (checked directly) are all
visually close to each other *within that same palette*, so any
quantizer ambiguity stays harmless.

BG_INDEX=3 for the erase fill turned out to already be correct - a
fresh histogram of the erase box's own pristine (English) pixels,
re-run after finding the real palette, still shows index 3 dominant
(SCROLL01: 18886/34000, SCROLL02: 21004/34000, matching the original
measurement) - the bug was only ever in which palette interpreted that
index. INK is likewise still sourced from the original art's own core
stroke index (19), just now correctly read as SCROLL03 palette's
(48,12,12) - a dark maroon, not CHARSHT.COL's (143,89,72).

A "heal only the real ink pixels, leave every other pixel exactly
pristine" technique (matching build_bsa_intro.py's local-contrast
is_ink() test) was tried next as a way to sidestep needing a single
"right" replacement color at all - reverted after it left visible
ghost fragments of the original English text: this scroll's font is
small enough (FONT_SIZE 11, ~1px stroke width) that many genuine ink
pixels don't clear the same local-contrast threshold that works fine
for the intro panels' larger lettering, no matter how far the
threshold was lowered, without also flagging real parchment grain as
ink elsewhere. So this is back to the flat BG_INDEX fill - already
verified (histogram of the erase box's own pristine pixels) to be the
actual statistically dominant background tone, not a guess.

SCROLL01.IMG has an illuminated drop-cap "F" (a decorative mosaic box,
NOT plain text) at the top-left, exactly like HISTORY.IMG's own drop
cap - the first version of this script naively erased/centered text
over the WHOLE panel, which erased the drop cap along with the text and
looked wrong once the palette was fixed enough to actually see it
(under the old wrong palette this was much less noticeable). Fixed the
same way as HISTORY.IMG: the drop cap is never touched, the first 3
lines wrap narrower to clear it, and every line is LEFT-aligned - not
centered - matching the original's own plain left-aligned prose block
(same fix applied to SCROLL02.IMG, which has no drop cap but was also
wrongly centered instead of left-aligned).

Since the drop cap's "F" glyph is baked into the artwork itself, the
Portuguese text starts from "acções..." (the "F" of "Facções" is
already provided by the drop cap) - same convention as HISTORY.IMG's
"alin Warhaft..." continuing from its own baked-in "T".

Reads the pristine copies split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later compiles
that PNG into the actual game-format `.IMG`, written back to
"GLOBAL_parts/<nome>.IMG" (the same place split_bsa.py extracted it),
which merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_scrolls.py
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"

NOTO_SERIF_ITALIC = "/usr/share/fonts/google-noto/NotoSerif-Italic.ttf"

FONT_SIZE = 11
LINE_HEIGHT = 16
INK = (48, 12, 12)      # scroll's own text ink (index 19), read under SCROLL03.IMG's real palette
# Dominant background tone within the erase box's own pristine pixels -
# confirmed by histogram (SCROLL01: 18886 of ~34000 sampled pixels,
# SCROLL02: 21004 - both far ahead of any runner-up), not assumed.
BG_INDEX = 3

Box = tuple[int, int, int, int]

# SCROLL01.IMG's illuminated drop-cap "F" - decorative art, never
# erased or drawn over. Measured against a 3x zoomed, 10px-ruled render
# of the pristine (English) panel. The exact height where the cap's own
# art ends and the 4th line of original English text begins turned out
# to be hard to pin down precisely by eye (off-by-a-few-rows guesses
# left ghost text either from the original 4th line or, once nudged the
# other way, ate into the cap itself) - so instead of tuning a seam
# between two erase boxes, the whole text area (SCROLL01_ERASE) is
# erased flat first, and then DROP_CAP's own pristine pixels are pasted
# back on top, guaranteeing no ghosting anywhere else regardless of
# exactly where the cap's real edge sits.
# Re-measured against a 3x zoomed, 5px-ruled render of the pristine
# panels after the user reported leftover English text still visible:
# the drop cap's own decorative border actually closes by y~=74 (not
# 92 as originally measured) - the box extended 18px past the art,
# into the *original* line 4 ("all those who opposed..."), so
# restore_box was pasting back a fragment of pristine English text
# along with the cap. SCROLL02_ERASE's top (24) sat 4-7px below where
# the pristine first line's ascenders/dots actually start (~17-18),
# leaving their tops peeking through above the erased block. Both
# scrolls' erase bottom (178) landed a couple rows above where the
# pristine last line's descenders actually end (~180-181), leaving a
# sliver of them visible just under the translated text.
DROP_CAP: Box = (14, 22, 78, 74)
SCROLL01_ERASE: Box = (12, 22, 306, 182)
SCROLL02_ERASE: Box = (12, 17, 306, 182)
# Text still starts at the original 24 (unchanged layout) even though
# the erase box's own top moved to 17 to also clear the pristine first
# line's ascenders - erasing more than the text needs is harmless, but
# there's no reason to also shift where the translation itself starts.
SCROLL02_DRAW_TOP = 24

NARROW_LEFT, NARROW_WIDTH = 82, 218
FULL_LEFT, FULL_WIDTH = 14, 288
# 5 lines at LINE_HEIGHT=16 covers the drop cap's full ~70px height
# (22 to 92, with a little margin) before switching to the full-width
# left margin, which would otherwise overlap the cap's own artwork.
NARROW_LINE_BUDGET = 5

SCROLL01_TEXT = (
    "acções diferentes batalharam por séculos em pequenas guerras e "
    "conflitos de fronteira, até que em 2E 896, Tiber Septim esmagou todos "
    "que o desafiaram e tomou o controle, proclamando-se Imperador. Ainda "
    "assim, os amargos anos de guerra deixaram marcas na população. O nome "
    "Tamriel, élfico para ‘Beleza da Aurora’, raramente escapava de lábios "
    "angustiados e logo era esquecido. Em um lugar onde vida e morte eram"
)
SCROLL02_PARAGRAPHS = [
    "lados diferentes da mesma moeda, jogada todos os dias, o povo do "
    "mundo conhecido passou a chamar a terra de sua tristeza de Arena...",
    "Agora, 197 anos depois de Tiber Septim tomar o controle e manter a "
    "paz, a terra de Arena enfrenta uma nova ameaça. O Imperador, Uriel "
    "Septim VII, celebra seu quadragésimo terceiro aniversário. Mas "
    "corações invejosos desejam o trono e tramam sua queda.",
]


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def restore_box(px: bytearray, pristine: bytes, width: int, box: Box) -> None:
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        row = y * width
        px[row + x0:row + x1] = pristine[row + x0:row + x1]


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


def wrap_two_phase(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> list[tuple[str, int]]:
    """Wraps text to NARROW_WIDTH for up to NARROW_LINE_BUDGET lines (the
    rows beside the drop cap), then continues wrapping whatever's left to
    FULL_WIDTH. Returns (line, left_x) pairs - same technique as
    HISTORY.IMG's own wrap_two_phase."""
    words = text.split()
    lines: list[tuple[str, int]] = []
    cur: list[str] = []
    i = 0
    while i < len(words):
        narrow = len(lines) < NARROW_LINE_BUDGET
        width = NARROW_WIDTH if narrow else FULL_WIDTH
        left = NARROW_LEFT if narrow else FULL_LEFT
        trial = " ".join(cur + [words[i]])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= width or not cur:
            cur.append(words[i])
            i += 1
        else:
            lines.append((" ".join(cur), NARROW_LEFT if len(lines) < NARROW_LINE_BUDGET else FULL_LEFT))
            cur = []
    if cur:
        lines.append((" ".join(cur), NARROW_LEFT if len(lines) < NARROW_LINE_BUDGET else FULL_LEFT))
    return lines


def render_scroll01(pixels: bytes, width: int, height: int, palette_flat: list[int]) -> bytes:
    px = bytearray(pixels)
    erase_flat(px, width, SCROLL01_ERASE)
    restore_box(px, pixels, width, DROP_CAP)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)
    font = ImageFont.truetype(NOTO_SERIF_ITALIC, FONT_SIZE)

    y = DROP_CAP[1]
    for line, x0 in wrap_two_phase(draw, SCROLL01_TEXT, font):
        draw.text((x0, y), line, font=font, fill=INK)
        y += LINE_HEIGHT

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    return bytes(quantized.getdata())


def render_scroll02(pixels: bytes, width: int, height: int, palette_flat: list[int]) -> bytes:
    px = bytearray(pixels)
    erase_flat(px, width, SCROLL02_ERASE)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(px)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)
    font = ImageFont.truetype(NOTO_SERIF_ITALIC, FONT_SIZE)

    all_lines: list[str] = []
    for i, para in enumerate(SCROLL02_PARAGRAPHS):
        if i > 0:
            all_lines.append("")  # blank line between paragraphs
        all_lines.extend(wrap_to_width(draw, para, font, FULL_WIDTH))

    y = SCROLL02_DRAW_TOP
    for line in all_lines:
        if line:
            draw.text((FULL_LEFT, y), line, font=font, fill=INK)
        y += LINE_HEIGHT

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    return bytes(quantized.getdata())


def build_translated_file(name: str, palette_flat: list[int], render) -> tuple[bytes, int, int]:
    """Reads GLOBAL_parts/<name> (still pristine English) and returns the
    translated pixel indices plus width/height - does not write anything
    itself, see main()."""
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)

    new_pixels = render(pixels, width, height, palette_flat)
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


def unscale_6bit(v: int) -> int:
    return (v << 2) | (v >> 4)


def load_scroll03_palette() -> list[int]:
    """SCROLL01/02.IMG carry no palette of their own; per OpenTESArena's
    own source (see module docstring) the real game paints all three
    intro-story panels using SCROLL03.IMG's embedded palette. SCROLL03
    is a loose file (not in GLOBAL.BSA), so it's always read straight
    from Originais/ - pristine, unaffected by anything else in this
    pipeline."""
    filedata = (ORIG_DIR / "SCROLL03.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert flags & 0x100, "SCROLL03.IMG is expected to have an embedded palette"
    pal_start = 12 + length
    pal_6bit = filedata[pal_start:pal_start + 768]
    return [unscale_6bit(v) for v in pal_6bit]


def main() -> None:
    print("Building translated intro scrolls (GLOBAL_parts/legivel/)...")

    palette_flat = load_scroll03_palette()

    pixels01, w1, h1 = build_translated_file("SCROLL01.IMG", palette_flat, render_scroll01)
    pixels02, w2, h2 = build_translated_file("SCROLL02.IMG", palette_flat, render_scroll02)

    save_legivel("SCROLL01.IMG", pixels01, w1, h1, palette_flat)
    save_legivel("SCROLL02.IMG", pixels02, w2, h2, palette_flat)

    print("Done.")


if __name__ == "__main__":
    main()
