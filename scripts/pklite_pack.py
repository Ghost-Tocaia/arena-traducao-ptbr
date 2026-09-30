"""PKLITE-compatible encoder + ACD.EXE reassembly - the write side of
the pklite_unpack.py/pklite_pack.py pair. See pklite_unpack.py's module
docstring for the format background.

Two encoders are provided:

`pack_literal` emits every byte as a literal "Decryption" op, never
using "Duplication" (LZ back-reference) ops - trivial to prove correct,
but produces a stream ~2x the size of a normal PKLITE file. That
mattered: a real-game test of an all-literal-recompressed ACD.EXE hung
at the DOS prompt, while the identical content round-tripped perfectly
through pklite_unpack.py in Python (self-consistency proves nothing
about the real x86 decompression stub). Kept only as the simplest
possible reference encoder.

`pack_lz` is the real one: a greedy LZ77 encoder that emits genuine
Duplication ops for repeated substrings, matching PKLITE's own
bit-tree encodings (reversed from pklite_unpack.py's _D1_RAW/_D2_RAW),
keeping the compressed size in the same ballpark as a genuine PKLITE
file instead of ~2x larger.

`rebuild_exe` assembles a complete, valid ACD.EXE from a patched
decompressed buffer: recompresses the main data with pack_lz, trims
the encoder's own trailing filler byte (see trim_to_consumed_length -
this one actually caused two of the real-game hangs above, found by
decoding the packed stream's own relocation table back and checking it
landed exactly where expected), splices the ORIGINAL relocation table
+ trailer back on unchanged (their content never needed to change -
only the main data before them did), and fixes up the outer MZ
header's file-size fields for the new total length.
"""
import struct

import pklite_unpack as unpk

# Reverse lookup: copy_count -> bit pattern, from _D1_RAW. Skip the
# 6-bit "special case" pattern - a real 6-bit encoding of value 13
# would be indistinguishable from the terminator/long-length escape
# sequence the decoder treats specially; the *real* value-13 encoding
# is the other (7-bit) entry also mapped to 13 in the raw table.
_COUNT_TO_BITS: dict[int, tuple[int, ...]] = {}
for _bits, _value in unpk._D1_RAW:
    if tuple(_bits) == unpk.SPECIAL_CASE_BITS:
        continue
    _COUNT_TO_BITS[_value] = tuple(_bits)

# Reverse lookup: most-significant-offset-byte (0-31) -> bit pattern.
_MSB_TO_BITS: dict[int, tuple[int, ...]] = {
    _value: tuple(_bits) for _bits, _value in unpk._D2_RAW
}

MIN_MATCH = 2
MAX_DIRECT_COUNT = 24  # largest count with a direct bit-tree encoding
# 0xFE/0xFF are reserved (skip-bit / terminate), and independent
# cross-referencing (entropymine's PKLITE format notes, not just
# OpenTESArena's port) gives 277 as "large mode"'s real documented max
# match length - so 0xFD is reserved too, leaving 0x00-0xFC (253
# values) for count-25.
MAX_SPECIAL_COUNT = 25 + 252
MAX_COUNT = MAX_SPECIAL_COUNT
MAX_OFFSET = 31 * 256 + 255  # largest most-sig-byte (31) * 256 + raw byte

COMPRESSED_START = 752  # fixed stub length specific to Arena's ACD.EXE


class BitWriter:
    """Mirrors the decoder's exact byte-cursor semantics: the decoder
    preloads a 16-bit word directly from the first 2 bytes of the
    stream, then - every time 16 bits have been consumed from the
    *current* word - pulls the *next* word from wherever the shared
    byte cursor currently sits (which may be well past raw literal
    bytes emitted for operations that used up those 16 bits). So a
    word's 2 bytes must physically sit in the stream at the position
    they'd be read from, not wherever they happened to become "known".
    We reserve that 2-byte slot up front (matching the decoder always
    having a word ready to consume bits from) and only the raw literal
    bytes get appended at the current tail in between."""

    def __init__(self):
        self.out = bytearray()
        self.cur_word = 0
        self.bits_in_word = 0
        self.word_pos = 0
        self.out += b"\x00\x00"  # reserve slot for the first word

    def write_bit(self, bit: int):
        self.cur_word |= (bit & 1) << self.bits_in_word
        self.bits_in_word += 1
        if self.bits_in_word == 16:
            struct.pack_into("<H", self.out, self.word_pos, self.cur_word)
            self.cur_word = 0
            self.bits_in_word = 0
            self.word_pos = len(self.out)
            self.out += b"\x00\x00"  # reserve slot for the next word

    def write_bits(self, bits):
        for b in bits:
            self.write_bit(b)

    def write_byte_raw(self, value: int):
        """A byte written OUTSIDE the bit-array mechanism (i.e. consumed by
        get_next_byte() directly), matching decoder's get_next_byte()."""
        self.out.append(value & 0xFF)

    def finish(self):
        # Backfill the last (possibly partial) reserved word slot. Its
        # unused high bits are never read by the decoder (decoding stops
        # at the terminator before needing them), so any value is safe.
        struct.pack_into("<H", self.out, self.word_pos, self.cur_word)


def pack_literal(decompressed: bytes) -> bytes:
    """Builds a valid PKLITE main-data compressed stream (bit array +
    interleaved raw bytes) that decodes back to `decompressed` via
    pklite_unpack's algorithm, using only literal Decryption ops plus
    the terminating Duplication special-case+0xFF sequence."""
    bw = BitWriter()
    for byte in decompressed:
        bw.write_bit(0)  # 0 = Decryption (literal) mode
        key = (16 - bw.bits_in_word) & 0xFF
        bw.write_byte_raw(byte ^ key)

    bw.write_bit(1)
    bw.write_bits(unpk.SPECIAL_CASE_BITS)
    bw.write_byte_raw(0xFF)
    bw.finish()
    return bytes(bw.out)


def _write_duplication(bw: BitWriter, count: int, offset: int) -> None:
    assert 1 <= offset <= MAX_OFFSET
    assert MIN_MATCH <= count <= MAX_COUNT
    bw.write_bit(1)
    if count <= MAX_DIRECT_COUNT:
        bw.write_bits(_COUNT_TO_BITS[count])
    else:
        bw.write_bits(unpk.SPECIAL_CASE_BITS)
        bw.write_byte_raw(count - 25)

    if count != 2:
        most_sig = offset >> 8
        bw.write_bits(_MSB_TO_BITS[most_sig])
    else:
        # count==2 never encodes a most-significant byte - offset must
        # fit in the raw least-significant byte alone (0-255).
        assert offset <= 255
    bw.write_byte_raw(offset & 0xFF)


def _find_match(data: bytes, pos: int, chains: dict[bytes, list[int]]) -> tuple[int, int]:
    """Returns (count, offset) for the best match at `pos`, or (0, 0)
    if none found worth using. Only searches candidate positions from
    the same 3-byte-prefix hash chain (bounded list), not the whole
    window - keeps this a greedy-but-fast O(n) encoder rather than
    optimal-but-slow."""
    n = len(data)
    if pos + MIN_MATCH > n:
        return 0, 0
    key = data[pos:pos + 3]
    candidates = chains.get(key)
    if not candidates:
        return 0, 0

    max_len = min(MAX_COUNT, n - pos)
    best_len = 0
    best_offset = 0
    min_pos = max(0, pos - MAX_OFFSET)
    # Search most-recent-first: recent matches are more likely to
    # extend further given typical text/data locality, and capping how
    # many we check keeps this fast.
    for cand in reversed(candidates):
        if cand < min_pos:
            break
        length = 0
        while length < max_len and data[cand + length] == data[pos + length]:
            length += 1
        offset = pos - cand
        if length == 2 and offset > 255:
            # count==2 can't encode an offset needing a most-sig byte.
            continue
        if length > best_len:
            best_len = length
            best_offset = offset
            if best_len >= max_len:
                break
    if best_len < MIN_MATCH:
        return 0, 0
    return best_len, best_offset


# The decompression stub keeps its read (SI/DS) and write (DI/ES) pointers
# in a 20-bit flat-address form, but only ever folds pointer overflow past
# 64KB back into the segment registers at one single code path: handling a
# Duplication special-case escape byte of exactly 0xFE or 0xFF (found by
# disassembling the stub - `cmp al,0xfe / jae` gates entry to that fixup,
# and ordinary direct-length or long-match-length bytes, which are always
# < 0xFE, never take it). 0xFE is otherwise a pure no-op (the decoder's
# `if encrypted_byte == 0xFE: continue` - zero bytes copied) - it exists
# ONLY to force that resync. The real ACD.EXE's own compressed stream
# contains exactly 7 of these, spaced ~40960 decompressed bytes apart
# (confirmed by instrumenting pklite_unpack's decode loop against the
# untouched original) - both the read and write pointers grow past 64KB
# over this file's ~305KB decompressed / ~166KB compressed spans, so
# without periodic resyncs DI or SI silently wrap and the stub reads/
# writes through stale segments - real DOSBox/UNP.EXE just hangs, while
# our own Python decoder (an unbounded bytearray, no segment limit) can't
# detect it. `pack_literal` (no Duplication ops at all besides the final
# terminator) and an earlier version of `pack_lz` (matches were opportunistic,
# not scheduled) both omitted this and both hung identically in real
# testing - independent of content and independent of the LZ vs literal
# choice, matching exactly what this fixup being pointer-count-gated
# rather than content-gated predicts.
RESYNC_INTERVAL = 32768  # comfortably under the 64KB wrap on both pointers


def _write_keepalive(bw: BitWriter) -> None:
    bw.write_bit(1)
    bw.write_bits(unpk.SPECIAL_CASE_BITS)
    bw.write_byte_raw(0xFE)


def pack_lz(decompressed: bytes) -> bytes:
    """Greedy LZ77 encoder producing a genuinely compressed PKLITE main-
    data stream (real Duplication ops, not just literals) - see module
    docstring for why this matters over pack_literal."""
    bw = BitWriter()
    n = len(decompressed)
    chains: dict[bytes, list[int]] = {}
    CHAIN_CAP = 64  # bound search-chain length per 3-byte prefix

    pos = 0
    decomp_since_resync = 0
    packed_since_resync = 0
    while pos < n:
        if decomp_since_resync >= RESYNC_INTERVAL or packed_since_resync >= RESYNC_INTERVAL:
            _write_keepalive(bw)
            decomp_since_resync = 0
            packed_since_resync = 0

        packed_start_len = len(bw.out)
        count, offset = _find_match(decompressed, pos, chains)
        if count >= MIN_MATCH:
            _write_duplication(bw, count, offset)
            end = pos + count
        else:
            byte = decompressed[pos]
            bw.write_bit(0)
            key = (16 - bw.bits_in_word) & 0xFF
            bw.write_byte_raw(byte ^ key)
            end = pos + 1

        # Index every 3-byte prefix within the bytes just emitted so
        # future positions can find them as match candidates.
        for i in range(pos, min(end, n - 2)):
            key3 = decompressed[i:i + 3]
            lst = chains.get(key3)
            if lst is None:
                chains[key3] = [i]
            else:
                lst.append(i)
                if len(lst) > CHAIN_CAP:
                    del lst[0]
        decomp_since_resync += end - pos
        packed_since_resync += len(bw.out) - packed_start_len
        pos = end

    # Terminator: Duplication mode, special-case bits, then 0xFF.
    bw.write_bit(1)
    bw.write_bits(unpk.SPECIAL_CASE_BITS)
    bw.write_byte_raw(0xFF)
    bw.finish()
    return bytes(bw.out)


def trim_to_consumed_length(packed: bytes, expected_len: int) -> bytes:
    """BitWriter always reserves a final word slot that the decoder
    never fully reads (decoding stops the instant the terminator's
    0xFF byte is consumed, which happens via a direct get_next_byte()
    call, not through a word-boundary refill) - so the returned stream
    carries 1 trailing byte the real decoder will never touch. That
    byte must NOT end up between the main-data stream and the
    spliced-on relocation table, or every relocation entry reads
    off-by-one and corrupts every pointer fixup - this is what actually
    caused two live-game hangs before it was found (traced by decoding
    our own packed output and comparing its length to how many bytes
    the decode loop actually consumed).

    Mirrors pklite_unpack.unpack()'s own loop exactly (terminator-
    seeking `while True`, not an expected_len bound) - an earlier
    version of this function stopped as soon as decoded_len reached
    expected_len, which happens *before* ever reading this stream's
    own terminator bits (content and terminator are never
    interleaved), silently chopping the terminator off entirely and
    leaving nothing for a real decoder to stop on before it runs into
    the spliced-on relocation data as if it were more compressed
    content."""
    bit_tree1 = unpk.BitTree(unpk._D1_RAW)
    bit_tree2 = unpk.BitTree(unpk._D2_RAW)
    byte_index = 2
    bit_array = struct.unpack_from("<H", packed, 0)[0]
    bits_read = 0
    decoded_len = 0

    def get_next_byte():
        nonlocal byte_index
        b = packed[byte_index]
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
            copy_bits = []
            copy_value = None
            while copy_value is None:
                copy_bits.append(1 if get_next_bit() else 0)
                copy_value = bit_tree1.match(tuple(copy_bits))
            if tuple(copy_bits) == unpk.SPECIAL_CASE_BITS:
                eb = get_next_byte()
                if eb == 0xFE:
                    continue
                elif eb == 0xFF:
                    break
                else:
                    copy_count = eb + 25
            else:
                copy_count = copy_value
            if copy_count != 2:
                ob = []
                ov = None
                while ov is None:
                    ob.append(1 if get_next_bit() else 0)
                    ov = bit_tree2.match(tuple(ob))
            get_next_byte()  # least_sig_byte
            decoded_len += copy_count
        else:
            get_next_byte()
            decoded_len += 1

    assert decoded_len == expected_len, (
        f"packed stream's terminator landed after decoding {decoded_len} "
        f"bytes, expected exactly {expected_len}"
    )
    return packed[:byte_index]


def find_relocation_bounds(original: bytes) -> tuple[int, int]:
    """Returns (reloc_start, reloc_end) file offsets in the ORIGINAL
    ACD.EXE: reloc_start is where the byte cursor lands right after the
    main-data terminator (0xFF) is consumed; reloc_end is compressed_end
    (n-8), matching pklite_unpack.unpack's own boundary."""
    n = len(original)
    compressed_end = n - 8

    bit_tree1 = unpk.BitTree(unpk._D1_RAW)
    bit_tree2 = unpk.BitTree(unpk._D2_RAW)
    byte_index = COMPRESSED_START + 2
    bit_array = struct.unpack_from("<H", original, COMPRESSED_START)[0]
    bits_read = 0

    def get_next_byte():
        nonlocal byte_index
        b = original[byte_index]
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
            copy_bits = []
            copy_value = None
            while copy_value is None:
                copy_bits.append(1 if get_next_bit() else 0)
                copy_value = bit_tree1.match(tuple(copy_bits))
            if tuple(copy_bits) == unpk.SPECIAL_CASE_BITS:
                eb = get_next_byte()
                if eb == 0xFE:
                    continue
                elif eb == 0xFF:
                    break
                else:
                    copy_count = eb + 25
            else:
                copy_count = copy_value
            if copy_count != 2:
                ob = []
                ov = None
                while ov is None:
                    ob.append(1 if get_next_bit() else 0)
                    ov = bit_tree2.match(tuple(ob))
            get_next_byte()  # least_sig_byte, consumed but unused here
        else:
            get_next_byte()

    return byte_index, compressed_end


def rebuild_exe(original: bytes, patched_decompressed: bytes) -> bytes:
    """Assembles a complete, valid ACD.EXE: original[0:752] (MZ header +
    decompression stub, unchanged) + freshly LZ-recompressed main data
    (from patched_decompressed) + the ORIGINAL relocation table and
    trailer (untouched - their content doesn't depend on what the main
    data says, only on where pointers land in the decompressed image,
    which is unchanged since every patch here is a same-length
    substitution) + a corrected outer MZ header file-size."""
    assert len(patched_decompressed) == len(unpk.unpack(original)), (
        "patched_decompressed must be the exact same length as the original "
        "decompressed image - the game's own code has hardcoded absolute "
        "addresses into this data segment that would break if it moved."
    )

    reloc_start, reloc_end = find_relocation_bounds(original)
    relocation_data = original[reloc_start:reloc_end]
    trailer = original[reloc_end:]  # last_comp_word(2) + seg(2) + off(2) + unused(4)

    new_main_data = pack_lz(patched_decompressed)
    new_main_data = trim_to_consumed_length(new_main_data, len(patched_decompressed))

    new_file = bytearray()
    new_file += original[:COMPRESSED_START]
    new_file += new_main_data
    new_file += relocation_data
    new_file += trailer

    total_size = len(new_file)
    e_cp = (total_size + 511) // 512
    remainder = total_size % 512
    e_cblp = remainder if remainder != 0 else 512
    struct.pack_into("<H", new_file, 2, e_cblp)
    struct.pack_into("<H", new_file, 4, e_cp)

    return bytes(new_file)


# Real DOSBox will not run *any* ACD.EXE this project's own pack_lz
# recompresses - confirmed by extensive bisection (identity repacks,
# hybrid original/pack_lz splices, a real PKLITE resync-token fix) that
# still hang or corrupt somewhere between the stub's decompression loop
# and DOS's own relocation application, root cause never fully pinned
# down without a real x86 debugger. See pipeline-acd-exe.md for the
# full investigation. Sidesteps the problem entirely: never re-run
# PKLITE compression at all for this platform. Instead, splice the
# translated decompressed content directly into a plain (already
# decompressed, standard DOS relocation table) ACD.EXE - produced once,
# by a real third-party PKLITE expander (UNP V3.01) run for real inside
# DOSBox against the pristine original, and checked into
# Originais/ACD_UNPACKED_TEMPLATE.EXE so this never needs DOSBox again.
UNPACKED_TEMPLATE_HEADER_SIZE = 16208  # bytes before the decompressed image starts
# The last 8 bytes of the decompressed image are uninitialized
# stack/BSS space in the *original* file - our own pklite_unpack.py
# (a plain zero-initialized bytearray) never writes them, but the real
# UNP.EXE-produced template has real (irrelevant) values there. Keep
# the template's own bytes instead of zeroing them, just in case
# something actually reads that memory before it's initialized.
UNPACKED_TEMPLATE_TAIL_POSITIONS = [305510, 305511, 305512, 305513, 305514, 305515, 305518, 305519]


def rebuild_dosbox_exe(unpacked_template: bytes, patched_decompressed: bytes) -> bytes:
    """Assembles a plain (non-PKLITE, already-decompressed) ACD.EXE for
    real DOSBox: splices `patched_decompressed` into a copy of
    `unpacked_template` (see Originais/ACD_UNPACKED_TEMPLATE.EXE) at its
    known data offset, leaving the template's own MZ header and native
    DOS relocation table completely untouched - they don't depend on
    the decompressed content, only on where things end up in memory,
    which is unchanged since every patch is a same-length substitution."""
    assert len(patched_decompressed) + UNPACKED_TEMPLATE_HEADER_SIZE == len(unpacked_template), (
        "patched_decompressed must be the exact same length as the template's "
        "own data section - the game's own code has hardcoded absolute "
        "addresses into this data segment that would break if it moved."
    )

    new_file = bytearray(unpacked_template)
    new_data = bytearray(patched_decompressed)
    for pos in UNPACKED_TEMPLATE_TAIL_POSITIONS:
        new_data[pos] = unpacked_template[UNPACKED_TEMPLATE_HEADER_SIZE + pos]
    new_file[UNPACKED_TEMPLATE_HEADER_SIZE:UNPACKED_TEMPLATE_HEADER_SIZE + len(new_data)] = new_data

    return bytes(new_file)
