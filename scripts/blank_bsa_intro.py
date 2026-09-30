"""Produces text-free ("blank") copies of INTRO01.IMG..INTRO09.IMG - the
original English caption erased, nothing drawn in its place yet - so the
erase step can be reviewed and fixed on its own, separately from drawing
the Portuguese translation on top.

Reads the pristine files from "Minha tradução/GLOBAL_parts/" (run
split_bsa.py first) and writes the blanked versions as readable PNGs
into "Minha tradução/GLOBAL_parts/legivel/empty/", plus preview PNGs
into preview_imagens/. build_bsa_intro.py's drawing step reads from this
"legivel/empty/" folder instead of erasing PARTS_DIR itself.

Usage: python3 scripts/blank_bsa_intro.py
"""
import struct
from pathlib import Path

from PIL import Image

from build_bsa_intro import PANELS, erase_panel
from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
EMPTY_DIR = PARTS_DIR / "legivel" / "empty"
PREVIEW_DIR = ROOT_DIR / "preview_imagens"


def blank_file(name: str, palette_flat: list[int]) -> tuple[bytes, int, int]:
    filedata = (PARTS_DIR / name).read_bytes()
    xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
    pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)

    new_pixels = erase_panel(pixels, width, height, palette_flat, PANELS[name])
    return new_pixels, width, height


def main() -> None:
    print("Blanking intro-vision panels (GLOBAL_parts/legivel/empty/)...")
    EMPTY_DIR.mkdir(parents=True, exist_ok=True)

    hfiledata = (PARTS_DIR / "HISTORY.IMG").read_bytes()
    _, _, _, _, _, hlength = struct.unpack_from("<HHHHHH", hfiledata, 0)

    def s6(v: int) -> int:
        return (v << 2) | (v >> 4)

    palette_flat = [s6(b) for b in hfiledata[12 + hlength:12 + hlength + 768]]

    PREVIEW_DIR.mkdir(exist_ok=True)
    for name in PANELS:
        pixels, width, height = blank_file(name, palette_flat)
        stem = name.rsplit(".", 1)[0]
        im = Image.new("P", (width, height))
        im.putpalette(palette_flat)
        im.putdata(pixels)
        im.save(EMPTY_DIR / f"{stem}.png")
        print(f"  {name}: wrote legivel/empty/{stem}.png ({width}x{height})")

        im.convert("RGB").resize((width * 2, height * 2), Image.NEAREST).save(
            PREVIEW_DIR / f"{name.replace('.', '_')}_vazio.png"
        )

    print("Done.")


if __name__ == "__main__":
    main()
