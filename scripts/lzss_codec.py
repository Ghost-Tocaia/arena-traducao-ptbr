"""LZSS codec matching the Arena/Daggerfall IMG "type 4" compression used by
SCROLL03.IMG, TITLE.IMG and other full-screen .IMG/.MNU assets (verified
against OpenTESArena's Compression::decodeType04).

Ring buffer of 4096 bytes, initialized to 0x20. History position wraps
with & 0xFFF. Matches are length 3..18, position is a 12-bit index into
the ring buffer offset by 18 (so the encoder must subtract 18 before
packing it into the 2-byte match token). Control bits: 1 = literal byte
follows, 0 = match (2 bytes) follows. Control byte's bits are consumed
LSB-first; a new control byte is read every time the previous 8 bits are
exhausted.
"""

N = 4096
F = 18
THRESHOLD = 3


def decode_type04(data: bytes, src: int, srcend: int, outlen: int) -> tuple[bytes, int]:
    """Decode a type-04 LZSS stream. Returns (decoded_bytes, input_offset_reached)."""
    history = bytearray([0x20]) * N
    historypos = 0
    bitcount = 0
    mask = 0
    dst = bytearray()
    i = src
    while i < srcend and len(dst) < outlen:
        if bitcount == 0:
            bitcount = 8
            mask = data[i]
            i += 1
        else:
            mask >>= 1
        if mask & 1:
            b = data[i]
            i += 1
            history[historypos & 0xFFF] = b
            historypos += 1
            dst.append(b)
        else:
            byte1 = data[i]
            i += 1
            byte2 = data[i]
            i += 1
            tocopy = (byte2 & 0x0F) + 3
            copypos = (((byte2 & 0xF0) << 4) | byte1) + 18
            for _ in range(tocopy):
                b = history[copypos & 0xFFF]
                copypos += 1
                history[historypos & 0xFFF] = b
                historypos += 1
                dst.append(b)
        bitcount -= 1
    while len(dst) < outlen:
        dst.append(0)
    return bytes(dst), i


def encode_type04(pixels: bytes) -> bytes:
    """Greedy LZSS encoder producing a stream decodable by decode_type04."""
    out_tokens: list[tuple] = []
    n = len(pixels)
    i = 0
    pos_of_triplet: dict[bytes, list[int]] = {}

    while i < n:
        best_len = 0
        best_pos = 0
        if i + THRESHOLD <= n:
            key = pixels[i:i + 3]
            candidates = pos_of_triplet.get(key)
            if candidates:
                window_start = max(0, i - N)
                for cand in reversed(candidates):
                    if cand < window_start:
                        break
                    max_len = min(F, n - i)
                    length = 0
                    while length < max_len and pixels[cand + length] == pixels[i + length]:
                        length += 1
                    if length > best_len:
                        best_len = length
                        best_pos = cand
                        if best_len >= F:
                            break
        if best_len >= THRESHOLD:
            out_tokens.append(("match", best_pos, best_len))
            for k in range(best_len):
                p = i + k
                if p + 3 <= n:
                    pos_of_triplet.setdefault(pixels[p:p + 3], []).append(p)
            i += best_len
        else:
            out_tokens.append(("lit", pixels[i]))
            if i + 3 <= n:
                pos_of_triplet.setdefault(pixels[i:i + 3], []).append(i)
            i += 1

    # Serialize tokens into the byte stream, tracking historypos exactly like
    # the decoder does, so a token's absolute `pixels` position converts
    # correctly into the ring-buffer-relative copypos.
    out = bytearray()
    bitbuf = 0
    bitcount = 0
    control_pos = None

    def flush_bit(bit: int) -> None:
        nonlocal bitbuf, bitcount, control_pos
        if control_pos is None:
            out.append(0)
            control_pos = len(out) - 1
            bitbuf = 0
            bitcount = 0
        bitbuf |= (bit & 1) << bitcount
        bitcount += 1
        out[control_pos] = bitbuf
        if bitcount == 8:
            control_pos = None

    for tok in out_tokens:
        if tok[0] == "lit":
            flush_bit(1)
            out.append(tok[1])
        else:
            _, pos, length = tok
            flush_bit(0)
            raw = (pos - 18) & 0xFFF
            byte1 = raw & 0xFF
            byte2 = ((raw >> 8) & 0x0F) << 4 | ((length - 3) & 0x0F)
            out.append(byte1)
            out.append(byte2)

    return bytes(out)
