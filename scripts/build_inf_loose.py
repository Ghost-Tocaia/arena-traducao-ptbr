"""Bakes the Portuguese translation into the .INF files that ship as
LOOSE files directly in the game folder, instead of packed inside
GLOBAL.BSA - CRYSTAL3.INF and IMPPAL1-4.INF (the Imperial Palace
levels, referenced by the loose IMPPAL.MIF).

These are the SAME dungeons as their same-named entries inside
GLOBAL.BSA (confirmed byte-for-byte identical "@TEXT" sections, aside
from one untranslated numeric reference in CRYSTAL3.INF), so this
script reuses build_bsa_inf.py's TRANSLATIONS dict directly rather than
duplicating the translated text.

The key difference from the BSA copies: loose .INF files are NOT
XOR-"encrypted" - per OpenTESArena's INFFile.cpp, that cipher only
applies "isEncrypted = inGlobalBSA". A loose file with the same name as
a BSA entry takes precedence when the game loads it (classic DOS-era
local-file-before-archive resolution), so translating only the
BSA-packed copy - as the very first pass at these five files did -
left the game still showing the English loose copy for the Imperial
Palace and the Crystal Tower bestiary.

Reads the pristine loose files from "Originais/" and writes the
translated result as PLAIN, READABLE text (accents kept) into
"Minha tradução/legivel/<nome>" - never encrypted, same as the
originals. Accent-stripping happens later, in compile_inf.py, the same
way every other translated text file in this project only loses its
accents at the very last "build" step (see build.py) - never before
that. That script also compiles the readable text back into
"Minha tradução/<nome>" (the same place this script used to write the
final file directly).

Usage: python3 scripts/build_inf_loose.py
"""
from pathlib import Path

from build_bsa_inf import TRANSLATIONS, block_id
from inf_codec import join_sections, parse_text_section, split_sections

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
DEST_DIR = ROOT_DIR / "Minha tradução"
LEGIVEL_DIR = DEST_DIR / "legivel"

LOOSE_FILES = ["CRYSTAL3.INF", "IMPPAL1.INF", "IMPPAL2.INF", "IMPPAL3.INF", "IMPPAL4.INF"]


def build_one(name: str) -> None:
    raw = (ORIG_DIR / name).read_bytes()
    text = raw.decode("latin-1")
    sections = split_sections(text)
    translations = TRANSLATIONS.get(name, {})

    new_sections = []
    missing = 0
    for sec_name, lines in sections:
        if sec_name == "@TEXT":
            blocks = parse_text_section(lines)
            new_lines = []
            for b in blocks:
                bid = block_id(b.header)
                if bid in translations:
                    prose, answers = translations[bid]
                else:
                    prose, answers = None, None
                    if any(kind == "prose" for kind, _ in b.lines):
                        missing += 1
                new_lines.extend(b.render(prose, answers))
            new_sections.append((sec_name, new_lines))
        else:
            new_sections.append((sec_name, lines))

    new_text = join_sections(new_sections)

    LEGIVEL_DIR.mkdir(parents=True, exist_ok=True)
    (LEGIVEL_DIR / name).write_text(new_text, encoding="latin-1", newline="")

    warn = f", {missing} block(s) left untranslated" if missing else ""
    print(f"  {name}: wrote legivel/{name}{warn}")


def main() -> None:
    print("Building translated loose .INF files (Minha tradução/legivel/)...")
    for name in LOOSE_FILES:
        build_one(name)
    print("Done.")


if __name__ == "__main__":
    main()
