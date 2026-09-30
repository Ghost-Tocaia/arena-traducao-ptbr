"""Reader/writer for Arena's GLOBAL.BSA archive format.

Layout (no relation to the later, incompatible Morrowind+ BSA format):
    offset 0:  uint16 LE  -- number of files (NumFiles)
    offset 2:  raw file data, one file after another, in the SAME order
               the directory below lists them (so each file's offset is
               simply 2 + the sum of every preceding entry's size)
    end of file: NumFiles directory entries of 18 bytes each:
        14 bytes  filename, ASCII, null-terminated, null-padded
         4 bytes  uint32 LE file size

Reverse-engineered against GLOBAL.BSA and cross-checked against
https://www.kultcds.com/FOFF/index.php?id=1.
"""
import struct

ENTRY_SIZE = 18
NAME_SIZE = 14
MAX_NAME_LEN = NAME_SIZE - 1  # last byte must be the null terminator


def read_index(data: bytes) -> list[tuple[str, int]]:
    """Returns [(filename, size), ...] in on-disk directory order."""
    num_files = struct.unpack_from("<H", data, 0)[0]
    dir_start = len(data) - ENTRY_SIZE * num_files
    entries = []
    pos = dir_start
    for _ in range(num_files):
        name_field = data[pos:pos + NAME_SIZE]
        term = name_field.index(b"\x00") if b"\x00" in name_field else NAME_SIZE
        name = name_field[:term].decode("ascii")
        size = struct.unpack_from("<I", data, pos + NAME_SIZE)[0]
        entries.append((name, size))
        pos += ENTRY_SIZE
    return entries


def offsets_by_name(entries: list[tuple[str, int]]) -> dict[str, tuple[int, int]]:
    """Maps filename -> (offset, size) using the implicit cumulative layout."""
    offset = 2
    result = {}
    for name, size in entries:
        result[name] = (offset, size)
        offset += size
    return result


def extract(data: bytes, name: str) -> bytes:
    entries = read_index(data)
    offsets = offsets_by_name(entries)
    off, size = offsets[name]
    return data[off:off + size]


def rebuild(data: bytes, replacements: dict[str, bytes]) -> bytes:
    """Rebuilds the archive with `replacements` swapped in for the named
    entries (which may be a different size than the originals); every
    other file is copied through unchanged. Directory order and filenames
    are preserved; only the affected entries' size fields change.
    """
    entries = read_index(data)
    offsets = offsets_by_name(entries)

    for name in replacements:
        if name not in offsets:
            raise KeyError(f"{name!r} not found in archive")
        if len(name) > MAX_NAME_LEN:
            raise ValueError(f"{name!r} is longer than {MAX_NAME_LEN} chars")

    body = bytearray()
    new_entries = []
    for name, old_size in entries:
        if name in replacements:
            payload = replacements[name]
        else:
            off, size = offsets[name]
            payload = data[off:off + size]
        body += payload
        new_entries.append((name, len(payload)))

    out = bytearray()
    out += struct.pack("<H", len(new_entries))
    out += body
    for name, size in new_entries:
        name_bytes = name.encode("ascii")
        out += name_bytes + b"\x00" * (NAME_SIZE - len(name_bytes))
        out += struct.pack("<I", size)
    return bytes(out)
