"""Bakes the Portuguese translation into OP.IMG - an in-game options
screen (Sound/Music/Detail sliders + New/Load/Save Game, Drop to DOS,
Continue) shown during play, distinct from MENU.IMG (the title-screen
main menu, already translated). Found via the "varredura_img_bruta.py"
bulk scan (see docs/inventario-arquivos.md, seção 4).

Uncompressed (type 0), no embedded palette - PAL.COL confirmed correct
by the bulk scan's default-palette render. Same ink color (palette
index 192, RGB (215,159,7)) as NEWMENU.IMG - same in-game text-overlay
palette region. The "The Elder Scrolls ARENA" logo at the top is
decorative artwork (same branding as TITLE.IMG's main logo) and is left
completely untouched - only the option labels and button row are
translated.

Background is a busy, high-contrast stone/marble texture, so this uses
the texture-clone erase technique from CHARSTAT.IMG/NEWEQUIP.IMG. The
Sound/Music toggle spinner icons and the Detail slider bar graphic are
NOT text (same ink color, but genuinely part of the UI widget) - erase
boxes are kept clear of them, and they're listed in `exclude` so the
texture-clone search never samples across them.

Reads and overwrites the pristine copy split_bsa.py already extracted
into "Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as a readable PNG into
"Minha tradução/GLOBAL_parts/legivel/". compile_images.py later
compiles that PNG into the actual game-format `.IMG`.

Usage: python3 scripts/build_bsa_op.py
"""
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"
ORIG_DIR = ROOT_DIR / "Originais"

MONTSERRAT_BOLD = "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Bold.otf"
INK = (215, 159, 7)  # sampled palette index 192
INK_INDEX = 192
BG_INDEX = 112

Box = tuple[int, int, int, int]

# UI widgets that share the text ink color but are NOT text - kept out
# of every erase box, and passed as `exclude` so texture-clone never
# samples across them.
WIDGETS: list[Box] = [
    (63, 74, 100, 100),    # Sound spinner (up/down arrows + box)
    (136, 68, 163, 100),   # Music spinner
    (202, 88, 315, 100),   # Detail slider bar
]


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


def erase_flat(px: bytearray, width: int, box: Box) -> None:
    """Plain flat fill with the panel's own dominant dark-stone tone
    (BG_INDEX). Used for the SOUND/MUSIC/DETAIL labels - they sit right
    next to spinner/slider widgets whose reddish inner-border trim is
    close enough that both the clone technique and a ring-sampled mode
    fill end up picking up that trim color instead of the plain dark
    background the label itself actually sits on. This area is flat/
    uniform enough (unlike CHARSTAT.IMG's marbled panel) that a single
    known-good fill color is simpler and safer than sampling."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[y * width + x] = BG_INDEX


def draw_fitted(draw: ImageDraw.ImageDraw, box: Box, text: str, base_size: int, min_size: int = 6) -> None:
    """Shrinks the font until the text fits the box width (small
    overflow allowance) then draws it centered on the box."""
    x0, y0, x1, y1 = box
    target_width = (x1 - x0) * 1.05
    size = base_size
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while size > min_size and bbox[2] - bbox[0] > target_width:
        size -= 1
        font = ImageFont.truetype(MONTSERRAT_BOLD, size)
        bbox = draw.textbbox((0, 0), text, font=font)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x = round(cx - (bbox[2] - bbox[0]) / 2) - bbox[0]
    y = round(cy - (bbox[3] - bbox[1]) / 2) - bbox[1]
    draw.text((x, y), text, font=font, fill=INK)


# (erase_box, text, base_size) - measured against the pristine ink
# pixels: SOUND x11-59 y83-99; MUSIC x105-139 y83-99; DETAIL x201-257
# y89-99; NEW GAME x3-59, LOAD GAME x68-123, SAVE GAME x132-187, DROP
# TO DOS x196-251 (two lines), CONTINUE x260-315, all y~126-143.
ROW1_LABELS: list[tuple[Box, str, int]] = [
    ((8, 79, 63, 99), "SOM", 9),
    ((81, 79, 136, 99), "MUSICA", 9),
    ((160, 88, 202, 99), "DETALHE", 8),
]
ROW2_LABELS: list[tuple[Box, str, int]] = [
    ((0, 126, 63, 145), "NOVO JOGO", 8),
    ((64, 126, 127, 145), "CARREGAR", 8),
    ((128, 126, 191, 145), "SALVAR", 8),
    ((263, 126, 319, 145), "CONTINUAR", 7),
]
LABELS = ROW1_LABELS + ROW2_LABELS

# Two-line button, handled separately from the single-line LABELS.
DROPDOS_BOX: Box = (192, 122, 255, 145)
DROPDOS_LINES = ["SAIR PARA", "DOS"]


def draw_two_lines(draw: ImageDraw.ImageDraw, box: Box, lines: list[str], size: int) -> None:
    x0, y0, x1, y1 = box
    font = ImageFont.truetype(MONTSERRAT_BOLD, size)
    cx = (x0 + x1) / 2
    line_height = size + 2
    total_h = line_height * len(lines)
    y = (y0 + y1) / 2 - total_h / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = round(cx - (bbox[2] - bbox[0]) / 2) - bbox[0]
        draw.text((x, round(y) - bbox[1]), line, font=font, fill=INK)
        y += line_height


def build() -> None:
    filedata = (PARTS_DIR / "OP.IMG").read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    assert (flags & 0xFF) == 0, "OP.IMG is expected to be uncompressed"
    assert (flags & 0x100) == 0, "OP.IMG is expected to have no embedded palette"

    pixels = filedata[12:12 + width * height]

    col_raw = (ORIG_DIR / "PAL.COL").read_bytes()
    palette_flat = list(col_raw[8:8 + 768])

    all_boxes = [box for box, _, _ in LABELS] + [DROPDOS_BOX] + WIDGETS
    px = bytearray(pixels)
    for box in [box for box, _, _ in ROW1_LABELS]:
        erase_flat(px, width, box)
    for box in [box for box, _, _ in ROW2_LABELS] + [DROPDOS_BOX]:
        erase_box(px, pixels, width, height, box, all_boxes)

    im = Image.new("P", (width, height))
    im.putpalette(palette_flat)
    im.putdata(bytes(px))
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)

    for box, text, size in LABELS:
        draw_fitted(draw, box, text, size)
    draw_two_lines(draw, DROPDOS_BOX, DROPDOS_LINES, 8)

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(palette_flat)
    quantized = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)
    new_pixels = bytes(quantized.getdata())

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    im_out = Image.new("P", (width, height))
    im_out.putpalette(palette_flat)
    im_out.putdata(new_pixels)
    im_out.save(LEGIVEL_DIR / "OP.png")
    print(f"  OP.IMG: wrote legivel/OP.png ({width}x{height})")

    PREVIEW_DIR.mkdir(exist_ok=True)
    im_out.convert("RGB").resize((width * 3, height * 3), Image.NEAREST).save(
        PREVIEW_DIR / "OP_IMG_traduzido.png"
    )


def main() -> None:
    print("Building translated OP.IMG (GLOBAL_parts/legivel/)...")
    build()
    print("Done.")


if __name__ == "__main__":
    main()
