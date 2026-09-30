"""One-off fix for TEMPLATE.DAT: the translated file's paragraphs are
structurally correct (same paragraph count as the pristine English, per
manual audit), but every paragraph's PHYSICAL LINE COUNT was forced down
to a uniform ~31-char wrap by the old split/translate/merge pipeline -
whereas the original data is NOT uniformly wrapped: some paragraphs
(short "citizen response" variants) are always exactly ONE physical
line no matter how long, while others (long narration) span several
lines. This mismatch is suspected of breaking the real DOS engine's
line-based block reader (it likely reads one physical line per record
for these short-variant blocks) even though OpenTESArena's own
reimplementation clearly doesn't care.

Fix: rebuild "Minha tradução/TEMPLATE.DAT" directly (no
TEMPLATE_parts/split/merge round-trip - this script IS the whole
pipeline for this file from now on) by taking the pristine English
file as the structural skeleton (exact header lines, exact blank-line
separators between paragraphs) and, for each paragraph, re-wrapping the
EXISTING correct Portuguese wording to match the English paragraph's
own physical line count - never changing wording, only where the line
breaks fall.
"""
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_PATH = ROOT_DIR / "Originais" / "TEMPLATE.DAT"
TRAD_PATH = ROOT_DIR / "Minha tradução" / "TEMPLATE.DAT"

HEADER_RE = re.compile(r"(?m)^(#\S+[ \t]*)\r?\n")


def split_into_blocks(text: str):
    """Returns (preamble, [(header_line, body), ...]) preserving the
    exact header line text (including any trailing spaces) verbatim."""
    matches = list(HEADER_RE.finditer(text))
    preamble = text[: matches[0].start()] if matches else text
    blocks = []
    for i, m in enumerate(matches):
        header_line = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((header_line, text[body_start:body_end]))
    return preamble, blocks


PARA_SPLIT_RE = re.compile(r"(\r?\n[ \t]*\r?\n)")


def split_paragraphs_keep_seps(body: str):
    """Splits on blank-line separators, keeping the separators so the
    original structure can be reassembled exactly. Returns a list where
    even indices are paragraph text and odd indices are the separator
    whitespace that followed them (last element has no trailing sep)."""
    return PARA_SPLIT_RE.split(body)


def rewrap_to_line_count(text: str, target_lines: int) -> str:
    """Re-wraps a flat (single-line-joined) paragraph's words into
    exactly `target_lines` physical lines, balancing length across
    them. Never touches wording - only where the breaks fall."""
    words = text.split()
    if not words:
        return text
    if target_lines <= 1:
        return " ".join(words)

    lines = []
    remaining = words
    for i in range(target_lines):
        lines_left = target_lines - i
        if lines_left == 1:
            lines.append(" ".join(remaining))
            remaining = []
            break
        total_len = sum(len(w) for w in remaining) + max(len(remaining) - 1, 0)
        target_len = total_len / lines_left
        line_words = []
        cur_len = 0
        for w in remaining:
            add_len = len(w) + (1 if line_words else 0)
            words_left_after = len(remaining) - len(line_words) - 1
            if line_words and (cur_len + add_len > target_len) and (words_left_after >= (lines_left - 1)):
                break
            line_words.append(w)
            cur_len += add_len
        if not line_words:
            line_words = [remaining[0]]
        lines.append(" ".join(line_words))
        remaining = remaining[len(line_words):]
    if remaining:
        lines[-1] += " " + " ".join(remaining)
    return "\r\n".join(lines)


def paragraph_line_count(paragraph: str) -> int:
    lines = paragraph.split("\n")
    return len([l for l in lines if l.strip("\r") != ""]) or 1


def flatten_paragraph_text(paragraph: str) -> str:
    lines = [l.rstrip("\r") for l in paragraph.split("\n")]
    return " ".join(l.strip() for l in lines if l.strip())


def reflow_block(en_body: str, pt_body: str, label: str) -> str:
    en_parts = split_paragraphs_keep_seps(en_body)
    pt_parts = split_paragraphs_keep_seps(pt_body)

    en_paragraphs = en_parts[0::2]
    pt_paragraphs = pt_parts[0::2]
    if len(en_paragraphs) != len(pt_paragraphs):
        raise ValueError(
            f"{label}: paragraph count mismatch (EN={len(en_paragraphs)} PT={len(pt_paragraphs)})"
        )

    out_paragraphs = []
    for en_para, pt_para in zip(en_paragraphs, pt_paragraphs):
        if not pt_para.strip():
            out_paragraphs.append(pt_para)
            continue
        target_lines = paragraph_line_count(en_para)
        flat = flatten_paragraph_text(pt_para)
        out_paragraphs.append(rewrap_to_line_count(flat, target_lines))

    # Reassemble using EN's own separators (blank-line whitespace) verbatim.
    rebuilt = []
    for i, para in enumerate(out_paragraphs):
        rebuilt.append(para)
        sep_index = i * 2 + 1
        if sep_index < len(en_parts):
            rebuilt.append(en_parts[sep_index])
    result = "".join(rebuilt)

    # The last paragraph's own trailing whitespace (a lone "\n" before the
    # next header, with no blank-line gap) isn't a "separator" caught by
    # PARA_SPLIT_RE, so it's part of the last paragraph's raw text and
    # gets silently dropped by flatten_paragraph_text/rewrap_to_line_count
    # above - without restoring it here, the next block's header ends up
    # glued directly onto this block's last line with no line break at
    # all, corrupting every block that follows.
    en_trailing_ws = en_body[len(en_body.rstrip(" \t\r\n")):]
    if en_trailing_ws and not result.endswith(en_trailing_ws):
        result = result.rstrip(" \t\r\n") + en_trailing_ws
    return result


def main() -> None:
    en_text = ORIG_PATH.read_text(encoding="latin-1")
    pt_text = TRAD_PATH.read_text(encoding="latin-1")

    en_preamble, en_blocks = split_into_blocks(en_text)
    pt_preamble, pt_blocks = split_into_blocks(pt_text)

    if len(en_blocks) != len(pt_blocks):
        raise ValueError(f"block count mismatch: EN={len(en_blocks)} PT={len(pt_blocks)}")

    # Headers repeat (e.g. "#0000a" reappears once per province section),
    # so pairing must be positional (same sequential order in both files),
    # never a dict keyed by header text - that silently collapses every
    # repeated header onto whichever occurrence happened to be inserted
    # last, corrupting every earlier occurrence's content.
    out_chunks = [en_preamble]
    fixed = 0
    for (header_line, en_body), (pt_header_line, pt_body) in zip(en_blocks, pt_blocks):
        key = header_line.strip()
        pt_key = pt_header_line.strip()
        if key != pt_key:
            raise ValueError(
                f"header mismatch at position {fixed}: EN={key!r} PT={pt_key!r}"
            )
        new_body = reflow_block(en_body, pt_body, key)
        out_chunks.append(header_line)
        out_chunks.append("\r\n")
        out_chunks.append(new_body)
        fixed += 1

    result = "".join(out_chunks)
    TRAD_PATH.write_text(result, encoding="latin-1")
    print(f"Reflowed {fixed} blocks. Wrote {TRAD_PATH} ({len(result)} bytes).")


if __name__ == "__main__":
    main()
