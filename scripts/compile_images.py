"""Compiles every translated "legivel/" PNG into the game's binary
`.IMG` format, per img_manifest.py's per-file rules (output compression
type, whether to embed a palette).

Reads:
  - "Minha tradução/legivel/<nome minus .IMG>.png" for LOOSE entries
  - "Minha tradução/GLOBAL_parts/legivel/<nome minus .IMG>.png" for BSA entries

Writes the compiled `.IMG` back to exactly the same place the pristine
copy already lived (top-level "Minha tradução/" for loose files,
"Minha tradução/GLOBAL_parts/" for BSA-packed ones) - the same location
build.py/merge_bsa.py already read from before this refactor, so neither
of those needed to change.

Run this after every build_bsa_*.py/build_images.py (which now only
produce "legivel/" PNGs) and before merge_bsa.py/build.py. Already
wired into build_all.py.

Usage: python3 scripts/compile_images.py
"""
import struct
from pathlib import Path

from PIL import Image

from bsa_codec import offsets_by_name, read_index
from img_codec import encode_img, verify_roundtrip
from img_manifest import IMAGE_MANIFEST, LOOSE

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
DEST_DIR = ROOT_DIR / "Minha tradução"
PARTS_DIR = DEST_DIR / "GLOBAL_parts"


def _pristine_header_bits(
    name: str, location: str, bsa_offsets: dict[str, tuple[int, int]], bsa_data: bytes,
) -> tuple[int, int, int]:
    """(xoff, yoff, flags_extra) read straight from the pristine original
    in Originais/ (the one copy that's always pristine, so this doesn't
    depend on whatever state GLOBAL_parts/ happens to be in). Several
    screens have a non-zero xoff/yoff (e.g. NEWMENU.IMG's yoff=123) that
    every build_bsa_*.py always passed through unchanged - never assume
    0. flags_extra is the upper byte of flags (flags & 0xFF00), which
    carries bits unrelated to compression type/embedded-palette that
    must likewise be preserved byte-for-byte - e.g. every script that
    recompresses from Huffman "type 8" down to LZSS "type 4" always did
    `new_flags = (flags & 0xFF00) | 0x04` rather than inventing a flags
    value from scratch."""
    if location == LOOSE:
        data = (ORIG_DIR / name).read_bytes()
    else:
        off, _size = bsa_offsets[name]
        data = bsa_data[off:off + 12]
    xoff, yoff, _, _, flags, _ = struct.unpack_from("<HHHHHH", data, 0)
    return xoff, yoff, flags & 0xFF00


def legivel_path(name: str, location: str) -> Path:
    stem = name.rsplit(".", 1)[0]
    base = DEST_DIR if location == LOOSE else PARTS_DIR
    return base / "legivel" / f"{stem}.png"


def out_path(name: str, location: str) -> Path:
    return (DEST_DIR if location == LOOSE else PARTS_DIR) / name


def compile_one(name: str, bsa_offsets: dict[str, tuple[int, int]], bsa_data: bytes) -> None:
    location, comp_type, embute_paleta = IMAGE_MANIFEST[name]
    src = legivel_path(name, location)
    if not src.exists():
        print(f"  {name}: skipping, no legivel/{src.name} found (run its build_bsa_*.py first)")
        return

    im = Image.open(src)
    assert im.mode == "P", f"{name}: expected {src} to be a palette ('P' mode) PNG"
    indices = bytes(im.getdata())
    palette = im.getpalette() if embute_paleta else None
    xoff, yoff, flags_extra = _pristine_header_bits(name, location, bsa_offsets, bsa_data)

    file_bytes = encode_img(
        indices, im.width, im.height,
        xoff=xoff, yoff=yoff, comp_type=comp_type, flags_extra=flags_extra, palette_flat_8bit=palette,
    )
    dest = out_path(name, location)
    dest.write_bytes(file_bytes)

    ok = verify_roundtrip(file_bytes, indices, im.width, im.height)
    print(f"  {name}: wrote {len(file_bytes)} bytes to {dest.relative_to(ROOT_DIR)}, roundtrip OK: {ok}")
    if not ok:
        raise RuntimeError(f"{name}: roundtrip verification failed")


def main() -> None:
    print("Compiling legivel/ PNGs into game-format .IMG files...")
    bsa_data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()
    bsa_offsets = offsets_by_name(read_index(bsa_data))
    for name in IMAGE_MANIFEST:
        compile_one(name, bsa_offsets, bsa_data)
    print("Done.")


if __name__ == "__main__":
    main()
