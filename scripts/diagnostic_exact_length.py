"""DISPOSABLE diagnostic tool - not a real translation fix. Forces every
block body in the translated TEMPLATE.DAT to have EXACTLY the same byte
length as the pristine English original, by bluntly padding (with
trailing spaces) or truncating (mid-word if needed) each block's
content. This deliberately sacrifices translation quality/completeness
in ~613 of 809 blocks (wherever Portuguese is naturally longer) - the
goal is only to test, cheaply, whether byte-exact block alignment
across the WHOLE file resolves the "wrong dialogue triggered" bug
before committing to a real, quality-preserving per-block edit pass.

Writes the result to a scratch path - never touches "Minha tradução/"
or the installed game copy directly; the caller installs it manually.
"""
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_PATH = ROOT_DIR / "Originais" / "TEMPLATE.DAT"
TRAD_PATH = ROOT_DIR / "Minha tradução" / "TEMPLATE.DAT"
OUT_PATH = ROOT_DIR / "TEMPLATE.DAT.teste_tamanho_exato"

HEADER_RE = re.compile(r"(?m)^(#\S+[ \t]*)\r?\n")


def split_into_blocks(text: str):
    matches = list(HEADER_RE.finditer(text))
    preamble = text[: matches[0].start()] if matches else text
    blocks = []
    for i, m in enumerate(matches):
        header_line = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((header_line, text[body_start:body_end]))
    return preamble, blocks


def force_length(pt_body: str, target_len: int) -> str:
    # Preserve the trailing whitespace run (the "\n" or "\n\n..." right
    # before the next header) exactly - only the content before it gets
    # padded/truncated, so the next block's header is never touched.
    stripped = pt_body.rstrip(" \t\r\n")
    trailing_ws = pt_body[len(stripped):]
    content_target = target_len - len(trailing_ws)
    content_bytes = stripped.encode("latin-1")
    if content_target < 0:
        content_target = 0
    if len(content_bytes) > content_target:
        content_bytes = content_bytes[:content_target]
    elif len(content_bytes) < content_target:
        content_bytes = content_bytes + b" " * (content_target - len(content_bytes))
    return content_bytes.decode("latin-1") + trailing_ws


def main() -> None:
    en_text = ORIG_PATH.read_text(encoding="latin-1")
    pt_text = TRAD_PATH.read_text(encoding="latin-1")

    en_pre, en_blocks = split_into_blocks(en_text)
    pt_pre, pt_blocks = split_into_blocks(pt_text)

    if len(en_blocks) != len(pt_blocks):
        raise ValueError(f"block count mismatch: EN={len(en_blocks)} PT={len(pt_blocks)}")

    out_chunks = [en_pre]
    for (eh, eb), (ph, pb) in zip(en_blocks, pt_blocks):
        if eh.strip() != ph.strip():
            raise ValueError(f"header mismatch: {eh!r} vs {ph!r}")
        target_len = len(eb.encode("latin-1"))
        new_body = force_length(pb, target_len)
        out_chunks.append(eh)
        out_chunks.append(new_body)

    result = "".join(out_chunks)
    OUT_PATH.write_text(result, encoding="latin-1")
    print(f"Wrote {OUT_PATH} ({len(result.encode('latin-1'))} bytes)")
    print(f"Original size: {len(en_text.encode('latin-1'))} bytes")


if __name__ == "__main__":
    main()
