"""Compiles a "legivel/" PNG (already the exact pixel indices + palette
the game screen should show) back into the game's binary `.IMG` format:
12-byte header + compressed/raw pixel payload + optional embedded
768-byte palette. This is the encode-only counterpart to decoding a
pristine `.IMG` (which every build_bsa_*.py script still does itself,
unchanged, on its own input side - see img_manifest.py's docstring for
why only the OUTPUT side was centralized here).

Usage (from compile_images.py):
    im = Image.open(legivel_path)  # mode "P", palette already attached
    indices = bytes(im.getdata())
    file_bytes = encode_img(
        indices, im.width, im.height,
        xoff=0, yoff=0, comp_type=4,
        palette_flat_8bit=im.getpalette() if embute_paleta else None,
    )
"""
import struct

from lzss_codec import decode_type04, encode_type04


def unscale_6bit(v8: int) -> int:
    """Inverse of the s6() 6-to-8-bit VGA DAC scale used throughout this
    project (s6(v) = (v<<2)|(v>>4)). Exact as long as v8 actually came
    from an original 6-bit value via s6() - true here, since palettes are
    only ever copied from the pristine game data, never invented."""
    return v8 >> 2


def encode_img(
    indices: bytes,
    width: int,
    height: int,
    *,
    xoff: int = 0,
    yoff: int = 0,
    comp_type: int,
    flags_extra: int = 0,
    palette_flat_8bit: list[int] | None = None,
) -> bytes:
    """Builds a complete `.IMG` file: header + payload (+ palette region
    if palette_flat_8bit is given). comp_type must be 0 (raw) or 4
    (LZSS) - there is no type-8 (Huffman) encoder in this project, so
    every screen that was originally type 8 is always recompressed as
    type 4 on write (see img_manifest.py)."""
    if comp_type == 4:
        payload = encode_type04(bytes(indices))
        assert len(payload) < 65536, "encode_img: compressed size overflowed 16-bit length field"
    elif comp_type == 0:
        payload = bytes(indices)
    else:
        raise ValueError(f"encode_img: unsupported comp_type {comp_type!r} (only 0 or 4 have an encoder)")

    flags = (flags_extra & 0xFF00) | comp_type
    if palette_flat_8bit is not None:
        flags |= 0x100

    header = struct.pack("<HHHHHH", xoff, yoff, width, height, flags, len(payload))
    file_bytes = header + payload
    if palette_flat_8bit is not None:
        pal_6bit = bytes(unscale_6bit(v) for v in palette_flat_8bit[:768])
        file_bytes += pal_6bit
    return file_bytes


def verify_roundtrip(file_bytes: bytes, expected_indices: bytes, width: int, height: int) -> bool:
    """Decodes file_bytes right back and compares pixel-for-pixel against
    what was meant to be written - same discipline every build_bsa_*.py
    already applies to its own compiled output, now shared here since
    compile_images.py is the one place that still writes compiled bytes."""
    xoff, yoff, w, h, flags, length = struct.unpack_from("<HHHHHH", file_bytes, 0)
    comp_type = flags & 0xFF
    if comp_type == 4:
        decoded, _ = decode_type04(file_bytes, 12, 12 + length, width * height)
    elif comp_type == 0:
        decoded = file_bytes[12:12 + width * height]
    else:
        raise ValueError(f"verify_roundtrip: unsupported comp_type {comp_type!r}")
    return bytes(decoded) == bytes(expected_indices)
