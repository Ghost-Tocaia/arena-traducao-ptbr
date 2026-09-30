"""Rebuilds GLOBAL.BSA using whatever's currently in
"Minha tradução/GLOBAL_parts/" for the entries listed there, copying every
other archived file through unchanged from the pristine original.

Mirrors merge_template.py's role for TEMPLATE_parts/: this is the final
"combine parts into the whole artifact" step, run after the translation
scripts (build_bsa_scrolls.py, build_bsa_intro.py, ...) have edited the
files inside GLOBAL_parts/ in place.

Usage: python3 scripts/merge_bsa.py
"""
from pathlib import Path

from bsa_codec import rebuild

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
DEST_DIR = ROOT_DIR / "Minha tradução"
PARTS_DIR = DEST_DIR / "GLOBAL_parts"


def main() -> None:
    data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()

    replacements = {}
    for f in sorted(PARTS_DIR.iterdir()):
        if f.is_file():
            replacements[f.name] = f.read_bytes()

    if not replacements:
        print(f"No files found in {PARTS_DIR}; nothing to merge.")
        return

    new_bsa = rebuild(data, replacements)

    out_path = DEST_DIR / "GLOBAL.BSA"
    out_path.write_bytes(new_bsa)

    print(f"Merged {len(replacements)} file(s) from {PARTS_DIR.name}/ into {out_path} "
          f"({len(new_bsa)} bytes)")
    for name in replacements:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
