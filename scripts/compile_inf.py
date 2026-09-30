"""Compiles every translated "legivel/" `.INF` text file into the
game's actual `.INF` format: accents stripped (same pass every other
translated text file goes through, via build.py's remover_acentos_str),
and - only for the files packed inside GLOBAL.BSA - re-encrypted with
the same XOR cipher inf_codec.py already uses for reading.

Reads:
  - "Minha tradução/legivel/<nome>" for the 5 loose overrides
    (CRYSTAL3.INF, IMPPAL1-4.INF) - never encrypted, in-game.
  - "Minha tradução/GLOBAL_parts/legivel/<nome>" for the 55(+2) `.INF`
    packed inside GLOBAL.BSA - encrypted, in-game.

Writes the compiled result back to exactly the same place the pristine
copy already lived (top-level "Minha tradução/" for loose files,
"Minha tradução/GLOBAL_parts/" for BSA-packed ones) - the same location
build.py/merge_bsa.py already read from before this refactor, so
neither of those needed to change.

Run this after build_bsa_inf.py/build_inf_loose.py (which now only
produce "legivel/" plain text) and before merge_bsa.py/build.py.
Already wired into build_all.py.

Usage: python3 scripts/compile_inf.py
"""
from pathlib import Path

from build import remover_acentos_str
from build_bsa_inf import TRANSLATIONS
from build_inf_loose import LOOSE_FILES
from inf_codec import xor_crypt

ROOT_DIR = Path(__file__).resolve().parent.parent
DEST_DIR = ROOT_DIR / "Minha tradução"
PARTS_DIR = DEST_DIR / "GLOBAL_parts"


def compile_one(name: str, base_dir: Path, encrypt: bool) -> None:
    src = base_dir / "legivel" / name
    if not src.exists():
        print(f"  {name}: skipping, no legivel/{name} found (run its build script first)")
        return

    text = src.read_text(encoding="latin-1", newline="")
    text = remover_acentos_str(text)
    raw = text.encode("latin-1")
    if encrypt:
        raw = xor_crypt(raw)

    dest = base_dir / name
    dest.write_bytes(raw)

    if encrypt:
        verify_text = xor_crypt(raw).decode("latin-1")
    else:
        verify_text = raw.decode("latin-1")
    ok = verify_text == text
    print(f"  {name}: wrote {len(raw)} bytes to {dest.relative_to(ROOT_DIR)}, roundtrip OK: {ok}")
    if not ok:
        raise RuntimeError(f"{name}: roundtrip verification failed")


def main() -> None:
    print("Compiling legivel/ .INF text into game-format .INF files...")
    for name in TRANSLATIONS:
        compile_one(name, PARTS_DIR, encrypt=True)
    for name in LOOSE_FILES:
        compile_one(name, DEST_DIR, encrypt=False)
    print("Done.")


if __name__ == "__main__":
    main()
