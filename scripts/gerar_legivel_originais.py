"""Generates a pristine, English, readable mirror of every translatable
asset inside "Originais/" - PNGs (mode "P", palette embedded) for the
`.IMG` screens, plain decrypted text for the `.INF` files that carry
`@TEXT` flavor text - so there's always an untouched reference to open
side by side with the translated "legivel/" working copies.

This is a pure, deterministic derivation from "Originais/GLOBAL.BSA"
and the loose "Originais/{TITLE,CHARSPEL,SCROLL03}.IMG" - it never
reads anything from "Minha tradução/". Per this project's own rule
("Originais/ nunca é editado"), "Originais/legivel/" is generated
output, not something to hand-edit: if it's ever missing or you doubt
it matches the master GLOBAL.BSA, just run this again - it always
overwrites with a fresh, correct render.

Usage: python3 scripts/gerar_legivel_originais.py
"""
import struct
from pathlib import Path

from PIL import Image

from bsa_codec import offsets_by_name, read_index
from huffman_codec import decode_type08
from img_manifest import IMAGE_MANIFEST, LOOSE
from inf_codec import xor_crypt
from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
LEGIVEL_DIR = ORIG_DIR / "legivel"

# The 55 GLOBAL.BSA .INF entries with real @TEXT prose, plus the 2 whose
# @TEXT section only holds engine markers (no prose) - see
# docs/inventario-arquivos.md. Kept as a flat list here (not imported
# from build_bsa_inf.py's TRANSLATIONS, which only has translated text,
# not the pristine set) since this script only needs the filenames.
INF_WITH_TEXT = [
    "AGTEMPL.INF", "BGATE2.INF", "CASTLE.INF", "CRYPT1.INF", "CRYPT2.INF",
    "CRYPT3.INF", "CRYPT4.INF", "CRYSTAL1.INF", "CRYSTAL2.INF", "CRYSTAL3.INF",
    "CRYSTAL4.INF", "DAGOTH1.INF", "DAGOTH2.INF", "DAGOTH3.INF", "DEMO.INF",
    "ELDEN1.INF", "ELDEN2.INF", "FANG1.INF", "FANG2.INF", "FORTI2.INF",
    "GEMIN1.INF", "GEMIN2.INF", "HALLS1.INF", "HALLS2.INF", "HALLS3.INF",
    "IMPPAL1.INF", "IMPPAL2.INF", "IMPPAL3.INF", "IMPPAL4.INF", "KHU1.INF",
    "KHU2.INF", "KHUTEST.INF", "LABRNTH1.INF", "LABRNTH2.INF", "MAGE.INF",
    "MGTEMPL1.INF", "MGTEMPL2.INF", "MURK1.INF", "MURK2.INF", "NOBLE.INF",
    "NOBLE1.INF", "NOBLE2.INF", "NOBLE3.INF", "SD1.INF", "SD3.INF",
    "SELENE1.INF", "SELENE2.INF", "SKEEP1.INF", "SKEEP2.INF", "START.INF",
    "STKEEP1.INF", "TOWER.INF", "TOWER1.INF", "TOWER2.INF", "TOWER6.INF",
    "TOWER8.INF", "VILPAL.INF",
]


def s6(v: int) -> int:
    return (v << 2) | (v >> 4)


def decode_any(filedata: bytes) -> tuple[bytes, int, int, list[int] | None]:
    """Decodes any of the 3 known compression types, returning
    (pixel indices, width, height, comp_type)."""
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    comp_type = flags & 0xFF
    if comp_type == 0:
        pixels = filedata[12:12 + width * height]
    elif comp_type == 4:
        pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
    elif comp_type == 8:
        pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)
    else:
        raise ValueError(f"decode_any: unsupported comp_type {comp_type!r}")
    has_palette = bool(flags & 0x100)
    palette_flat = None
    if has_palette:
        pal_region = filedata[12 + length:12 + length + 768]
        palette_flat = [s6(b) for b in pal_region]
    return bytes(pixels), width, height, palette_flat


def resolve_external_palette(name: str) -> list[int]:
    """For every image with no embedded palette EXCEPT the INTRO panels
    (handled separately in main(), since they borrow HISTORY.IMG's own
    embedded palette instead of an external .COL file) - confirmed by
    trial, see docs/pipeline-imagens.md."""
    if name in ("SCROLL01.IMG", "SCROLL02.IMG", "CHARSTAT.IMG", "EQUIP.IMG", "EQUIPB.IMG"):
        raw = (ORIG_DIR / "CHARSHT.COL").read_bytes()
    else:
        raw = (ORIG_DIR / "PAL.COL").read_bytes()
    return list(raw[8:8 + 768])


def main() -> None:
    LEGIVEL_DIR.mkdir(exist_ok=True)

    bsa_data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()
    offsets = offsets_by_name(read_index(bsa_data))

    # INTRO01-09.IMG have no embedded palette and are shown in-game right
    # after HISTORY.IMG, using HISTORY.IMG's own embedded palette (see
    # build_bsa_intro.py) - resolve that once here.
    hist_off, hist_size = offsets["HISTORY.IMG"]
    _, _, _, _, hflags, hlength = struct.unpack_from("<HHHHHH", bsa_data, hist_off)
    intro_palette = [s6(b) for b in bsa_data[hist_off + 12 + hlength:hist_off + 12 + hlength + 768]]

    n_images = 0
    for name, (location, _comp_type, _embed) in IMAGE_MANIFEST.items():
        if location == LOOSE:
            filedata = (ORIG_DIR / name).read_bytes()
        else:
            off, size = offsets[name]
            filedata = bsa_data[off:off + size]

        pixels, width, height, palette_flat = decode_any(filedata)
        if palette_flat is None:
            palette_flat = intro_palette if name.startswith("INTRO") else resolve_external_palette(name)

        im = Image.new("P", (width, height))
        im.putpalette(palette_flat)
        im.putdata(pixels)
        stem = name.rsplit(".", 1)[0]
        im.save(LEGIVEL_DIR / f"{stem}.png")
        n_images += 1

    n_inf = 0
    for name in INF_WITH_TEXT:
        off, size = offsets[name]
        text = xor_crypt(bsa_data[off:off + size]).decode("latin-1")
        (LEGIVEL_DIR / name).write_text(text, encoding="latin-1", newline="")
        n_inf += 1

    print(f"Wrote {n_images} PNG(s) and {n_inf} .INF text file(s) to {LEGIVEL_DIR}")


if __name__ == "__main__":
    main()
