"""Python port of OpenTESArena's ExeUnpacker.cpp (PKLITE decompressor
for Arena's ACD.EXE / A.EXE). See ExeUnpacker.cpp for the original
C++ and pklite_specification.md for the bit-table source.
"""
import struct
from pathlib import Path


# Duplication1 table: (bit pattern as tuple of 0/1, decoded value)
_D1_RAW = [
    ((1, 0), 2),
    ((1, 1), 3),
    ((0, 0, 0), 4),
    ((0, 0, 1, 0), 5),
    ((0, 0, 1, 1), 6),
    ((0, 1, 0, 0), 7),
    ((0, 1, 0, 1, 0), 8),
    ((0, 1, 0, 1, 1), 9),
    ((0, 1, 1, 0, 0), 10),
    ((0, 1, 1, 0, 1, 0), 11),
    ((0, 1, 1, 0, 1, 1), 12),
    ((0, 1, 1, 1, 0, 0), 13),  # special case marker, value overridden below
    ((0, 1, 1, 1, 0, 1, 0), 13),
    ((0, 1, 1, 1, 0, 1, 1), 14),
    ((0, 1, 1, 1, 1, 0, 0), 15),
    ((0, 1, 1, 1, 1, 0, 1, 0), 16),
    ((0, 1, 1, 1, 1, 0, 1, 1), 17),
    ((0, 1, 1, 1, 1, 1, 0, 0), 18),
    ((0, 1, 1, 1, 1, 1, 0, 1, 0), 19),
    ((0, 1, 1, 1, 1, 1, 0, 1, 1), 20),
    ((0, 1, 1, 1, 1, 1, 1, 0, 0), 21),
    ((0, 1, 1, 1, 1, 1, 1, 0, 1), 22),
    ((0, 1, 1, 1, 1, 1, 1, 1, 0), 23),
    ((0, 1, 1, 1, 1, 1, 1, 1, 1), 24),
]
SPECIAL_CASE_BITS = (0, 1, 1, 1, 0, 0)

_D2_RAW = [
    ((1,), 0),
    ((0, 0, 0, 0), 1),
    ((0, 0, 0, 1), 2),
    ((0, 0, 1, 0, 0), 3),
    ((0, 0, 1, 0, 1), 4),
    ((0, 0, 1, 1, 0), 5),
    ((0, 0, 1, 1, 1), 6),
    ((0, 1, 0, 0, 0, 0), 7),
    ((0, 1, 0, 0, 0, 1), 8),
    ((0, 1, 0, 0, 1, 0), 9),
    ((0, 1, 0, 0, 1, 1), 10),
    ((0, 1, 0, 1, 0, 0), 11),
    ((0, 1, 0, 1, 0, 1), 12),
    ((0, 1, 0, 1, 1, 0), 13),
    ((0, 1, 0, 1, 1, 1, 0), 14),
    ((0, 1, 0, 1, 1, 1, 1), 15),
    ((0, 1, 1, 0, 0, 0, 0), 16),
    ((0, 1, 1, 0, 0, 0, 1), 17),
    ((0, 1, 1, 0, 0, 1, 0), 18),
    ((0, 1, 1, 0, 0, 1, 1), 19),
    ((0, 1, 1, 0, 1, 0, 0), 20),
    ((0, 1, 1, 0, 1, 0, 1), 21),
    ((0, 1, 1, 0, 1, 1, 0), 22),
    ((0, 1, 1, 0, 1, 1, 1), 23),
    ((0, 1, 1, 1, 0, 0, 0), 24),
    ((0, 1, 1, 1, 0, 0, 1), 25),
    ((0, 1, 1, 1, 0, 1, 0), 26),
    ((0, 1, 1, 1, 0, 1, 1), 27),
    ((0, 1, 1, 1, 1, 0, 0), 28),
    ((0, 1, 1, 1, 1, 0, 1), 29),
    ((0, 1, 1, 1, 1, 1, 0), 30),
    ((0, 1, 1, 1, 1, 1, 1), 31),
]


class BitTree:
    def __init__(self, entries):
        # entries: list of (bits tuple, value)
        self.table = {}
        for bits, value in entries:
            self.table[bits] = value
        self.max_len = max(len(b) for b, _ in entries)

    def match(self, bits):
        """bits: tuple accumulated so far. Returns value or None."""
        return self.table.get(bits)


def unpack(data: bytes) -> bytes:
    n = len(data)
    compressed_start = 752
    compressed_end = n - 8

    last_comp_word = struct.unpack_from("<H", data, compressed_end - 2)[0]
    if last_comp_word != 0xFFFF:
        raise ValueError(f"Invalid last compressed word 0x{last_comp_word:04X}")

    seg = struct.unpack_from("<H", data, compressed_end)[0]
    off = struct.unpack_from("<H", data, compressed_end + 2)[0]
    decomp_len = seg * 16 + off

    out = bytearray(decomp_len)
    decomp_index = 0

    bit_tree1 = BitTree(_D1_RAW)
    bit_tree2 = BitTree(_D2_RAW)

    byte_index = compressed_start + 2
    bit_array = struct.unpack_from("<H", data, compressed_start)[0]
    bits_read = 0

    def get_next_byte():
        nonlocal byte_index
        b = data[byte_index]
        byte_index += 1
        return b

    def get_next_bit():
        nonlocal bit_array, bits_read
        bit = (bit_array & (1 << bits_read)) != 0
        bits_read += 1
        if bits_read == 16:
            bits_read = 0
            b1 = get_next_byte()
            b2 = get_next_byte()
            bit_array = b1 | (b2 << 8)
        return bit

    while True:
        if get_next_bit():
            # Duplication mode
            copy_bits = []
            copy_value = None
            while copy_value is None:
                copy_bits.append(1 if get_next_bit() else 0)
                copy_value = bit_tree1.match(tuple(copy_bits))
                if len(copy_bits) > 12:
                    raise ValueError(f"bitTree1 no match after {copy_bits}")

            if tuple(copy_bits) == SPECIAL_CASE_BITS:
                encrypted_byte = get_next_byte()
                if encrypted_byte == 0xFE:
                    continue
                elif encrypted_byte == 0xFF:
                    break
                else:
                    copy_count = encrypted_byte + 25
            else:
                copy_count = copy_value

            most_sig_byte = 0
            if copy_count != 2:
                offset_bits = []
                offset_value = None
                while offset_value is None:
                    offset_bits.append(1 if get_next_bit() else 0)
                    offset_value = bit_tree2.match(tuple(offset_bits))
                    if len(offset_bits) > 8:
                        raise ValueError(f"bitTree2 no match after {offset_bits}")
                most_sig_byte = offset_value

            least_sig_byte = get_next_byte()
            offset = least_sig_byte | (most_sig_byte << 8)

            dup_begin = decomp_index - offset
            dup_end = dup_begin + copy_count
            for i in range(dup_begin, dup_end):
                out[decomp_index] = out[i]
                decomp_index += 1
        else:
            # Decryption mode
            encrypted_byte = get_next_byte()
            key = (16 - bits_read) & 0xFF
            decrypted_byte = encrypted_byte ^ key
            out[decomp_index] = decrypted_byte
            decomp_index += 1

    return bytes(out)


if __name__ == "__main__":
    import sys
    ROOT_DIR = Path(__file__).resolve().parent.parent
    with open(ROOT_DIR / "Originais" / "ACD.EXE", "rb") as f:
        raw = f.read()
    decompressed = unpack(raw)
    print("decompressed length:", len(decompressed))
    out_path = ROOT_DIR / "ACD_decompressed.bin"
    with open(out_path, "wb") as f:
        f.write(decompressed)
    print("wrote", out_path)

    # Sanity check known offsets
    tests = [
        ("ChooseGender", 0x35D74, 20),
        ("ChooseGenderMale", 0x3F98E, 4),
        ("ChooseGenderFemale", 0x3F994, 6),
        ("ClassNames", 0x3E462, 120),
        ("ChooseName", 0x35D58, 26),
    ]
    for name, addr, length in tests:
        chunk = decompressed[addr:addr+length]
        print(f"{name} @0x{addr:X}: {chunk!r}")
