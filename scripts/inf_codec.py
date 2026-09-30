"""Codec for Arena's .INF files as stored inside GLOBAL.BSA: dungeon/
level layout scripts (floor/wall textures, monster/item placement) that
also carry an "@TEXT" section with the flavor text shown while exploring
(signs, notes, ambient descriptions, riddles).

Every .INF read out of GLOBAL.BSA is XOR-"encrypted" with a fixed 8-byte
key, confirmed against OpenTESArena's INFFile.cpp (loadFromBSA's
isEncrypted branch, "Adapted from BSATool" in the original comment).
Since XOR is its own inverse, the exact same function encrypts and
decrypts - there is no separate encode/decode direction to keep in sync,
unlike the LZSS/Huffman .IMG codecs.
"""

ENCRYPTION_KEYS = (0xEA, 0x7B, 0x4E, 0xBD, 0x19, 0xC9, 0x38, 0x99)


def xor_crypt(data: bytes) -> bytes:
    """Encrypts or decrypts .INF bytes in place (same operation either
    way). The key byte cycles every 8 bytes; a running counter (wrapping
    every 256 bytes, since it's added as a uint8) is added to the key
    before XORing."""
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ ((i + ENCRYPTION_KEYS[i % 8]) & 0xFF)
    return bytes(out)


# --- @TEXT section parsing -------------------------------------------
#
# An .INF's @TEXT section is a sequence of blocks, each introduced by a
# "*TEXT <id>" line, containing the flavor text (signs, notes, ambient
# descriptions, riddles) shown while exploring that dungeon/location.
# Lines within a block are one of:
#   - a structural/game-logic line, kept byte-for-byte unchanged:
#     blank, a lone "-" (separator, used around riddle verses), a line
#     starting with "^" (display code, e.g. "^255 0"), a line starting
#     with "+" followed only by digits (a numeric reference into
#     another table, e.g. "+57"), or a line starting with "`" (a branch
#     label like "`CORRECT"/"`WRONG").
#   - an "answer" line, starting with ":" - a keyword the player must
#     type to solve a riddle (e.g. ":sun"). Translatable, but must be
#     kept consistent with whatever the translated riddle's solution is.
#   - a "prose" line - the translatable flavor text itself. A leading
#     "~" (seen on some blocks, e.g. a location's first-visit
#     description) is a marker character, not part of the sentence, and
#     is preserved separately from the translatable text.
#
# Blocks are translated as a whole (their prose lines joined into one
# string) rather than line-by-line, since original line breaks are just
# wherever the original author's paragraph or verse happened to wrap and
# carry no meaning of their own to preserve exactly.

Line = tuple[str, str]  # (kind, raw_line) where kind in {"raw","answer","prose"}


CORRECT_WRONG_LABELS = ("`CORRECT", "`WRONG", "'CORRECT", "'WRONG")


def classify_line(line: str) -> str:
    if line == "" or line == "-":
        return "raw"
    if line.startswith("^"):
        return "raw"
    if line in CORRECT_WRONG_LABELS:
        return "raw"
    if line.startswith("+") and line[1:].strip().isdigit():
        return "raw"
    if line.startswith(":"):
        return "answer"
    return "prose"


class TextBlock:
    def __init__(self, header: str):
        self.header = header  # the "*TEXT <id>" line itself, unchanged
        self.lines: list[Line] = []

    def _prose_run_spans(self) -> list[tuple[int, int]]:
        """Returns (start, end) index pairs (into self.lines) for each
        maximal run of consecutive prose lines. A block's raw markers
        (a lone '-', '`CORRECT'/'`WRONG' branch labels, '^'/'+N' codes)
        commonly sit BETWEEN separate prose runs within the very same
        block (e.g. riddle setup / riddle body / question / correct-
        answer response / wrong-answer response are five separate
        runs in one block) - each run has to be translated and
        rewrapped independently, never flattened into one string,
        or the markers end up re-inserted at the wrong point relative
        to the new (different-length) translated text."""
        spans = []
        start = None
        for i, (kind, _) in enumerate(self.lines):
            if kind == "prose" and start is None:
                start = i
            elif kind != "prose" and start is not None:
                spans.append((start, i))
                start = None
        if start is not None:
            spans.append((start, len(self.lines)))
        return spans

    def prose_runs(self) -> list[str]:
        """One translatable string per contiguous prose run, in order.
        A leading '~' on the very first run's first line is stripped
        here and restored by render() - it's a marker, not part of the
        sentence. A single-run block (the common case) returns a
        1-element list."""
        spans = self._prose_run_spans()
        runs = [" ".join(self.lines[i][1] for i in range(s, e)) for s, e in spans]
        if runs and runs[0].startswith("~"):
            runs[0] = runs[0][1:]
        return runs

    # Backwards-compatible single-string accessor for single-run blocks.
    def prose_text(self) -> str:
        runs = self.prose_runs()
        return " ".join(runs)

    def answers(self) -> list[str]:
        """Riddle answer keywords (without their leading ':')."""
        return [text[1:] for kind, text in self.lines if kind == "answer"]

    def render(
        self,
        translated_prose: str | list[str] | None,
        translated_answers: list[str] | None,
    ) -> list[str]:
        """Rebuilds this block's lines: raw lines unchanged, each prose
        run replaced by the matching entry of translated_prose
        (re-wrapped to the number of lines that specific run had - not
        the block's total prose line count), answers replaced by
        translated_answers (matched up in order). Passing None for
        either leaves that part of the block in the original language
        (used when a translation hasn't been written yet, matching
        mount_template_part.py's "leave untranslated, don't fail"
        behavior for missing entries).

        translated_prose must be a list with exactly one entry per
        prose run (see prose_runs()/_prose_run_spans()) - a bare str is
        accepted as shorthand ONLY when the block has a single run."""
        spans = self._prose_run_spans()
        n_answers = sum(1 for kind, _ in self.lines if kind == "answer")

        new_lines = list(self.lines)
        if translated_prose is not None:
            if isinstance(translated_prose, str):
                translated_prose = [translated_prose]
            if len(translated_prose) != len(spans):
                raise ValueError(
                    f"{self.header.strip()}: block has {len(spans)} prose run(s) "
                    f"but translation provides {len(translated_prose)}"
                )
            for run_idx, (s, e) in enumerate(spans):
                n = e - s
                wrapped = _wrap_to_lines(translated_prose[run_idx], n)
                if run_idx == 0 and self.lines[s][1].startswith("~"):
                    wrapped[0] = "~" + wrapped[0]
                for offset, new_text in enumerate(wrapped):
                    new_lines[s + offset] = ("prose", new_text)

        new_answer_lines = [text for kind, text in self.lines if kind == "answer"]
        if translated_answers is not None and n_answers > 0:
            new_answer_lines = [":" + a for a in translated_answers[:n_answers]]

        out = [self.header]
        ai = 0
        for kind, text in new_lines:
            if kind == "answer":
                out.append(new_answer_lines[ai])
                ai += 1
            else:
                out.append(text)
        return out


def _wrap_to_lines(text: str, n: int) -> list[str]:
    """Splits text into exactly n non-empty-preferring chunks by word
    boundaries, as evenly as possible. Used to fit a translated prose
    string back into the same number of physical lines the original
    block used (the .INF format has no explicit line-wrap width; this
    just keeps the block's line count/shape stable)."""
    words = text.split()
    if n <= 1 or len(words) <= n:
        lines = [""] * n
        for i, w in enumerate(words):
            lines[min(i, n - 1)] = (lines[min(i, n - 1)] + " " + w).strip()
        return [line if line else "" for line in lines]
    per = len(words) / n
    lines = []
    idx = 0.0
    prev = 0
    for i in range(n):
        idx += per
        cut = round(idx) if i < n - 1 else len(words)
        lines.append(" ".join(words[prev:cut]))
        prev = cut
    return lines


def parse_text_section(section_lines: list[str]) -> list[TextBlock]:
    """section_lines is everything from the line after '@TEXT' up to
    (excluding) the next '@SECTION' line or end of file."""
    blocks: list[TextBlock] = []
    current: TextBlock | None = None
    for line in section_lines:
        if line.startswith("*TEXT "):
            current = TextBlock(line)
            blocks.append(current)
            continue
        if current is None:
            continue
        current.lines.append((classify_line(line), line))
    return blocks


def split_sections(text: str) -> list[tuple[str | None, list[str]]]:
    """Splits a whole decrypted .INF's text into (section_name, lines)
    pairs, one per '@SECTION' header (e.g. '@FLOORS', '@TEXT'), in
    order. A few files (e.g. DAGOTH1.INF) have floor-layout lines before
    any '@' header at all - that leading content is kept as a section
    with name=None (implicitly "@FLOORS") rather than dropped; join_
    sections() knows not to emit a header line for it. Every .INF uses
    CRLF line endings; the trailing '\\r' is stripped here so line
    comparisons elsewhere (e.g. a lone '-') work, and join_sections()
    puts CRLF back on the way out."""
    lines = text.replace("\r\n", "\n").split("\n")
    sections: list[tuple[str | None, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []
    started = False
    for line in lines:
        if line.startswith("@"):
            if started:
                sections.append((current_name, current_lines))
            current_name = line
            current_lines = []
            started = True
        else:
            current_lines.append(line)
            started = True
    if started:
        sections.append((current_name, current_lines))
    return sections


def join_sections(sections: list[tuple[str | None, list[str]]]) -> str:
    """Inverse of split_sections: flattens (section_name, lines) pairs
    back into the full CRLF-joined text ready to be latin-1-encoded and
    re-encrypted."""
    all_lines: list[str] = []
    for name, lines in sections:
        if name is not None:
            all_lines.append(name)
        all_lines.extend(lines)
    return "\r\n".join(all_lines)
