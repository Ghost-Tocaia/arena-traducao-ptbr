"""Runs the full build pipeline in order:

1. merge_template.py    - merges TEMPLATE_parts/*.DAT into "Minha tradução/TEMPLATE.DAT"
2. build_images.py      - bakes the translated text into SCROLL03.IMG,
                           CHARSPEL.IMG and TITLE.IMG (pixel-art screens),
                           saved as readable PNGs into "Minha tradução/legivel/"
3. split_bsa.py          - (re)extracts every GLOBAL.BSA entry that needs
                           translation into "Minha tradução/GLOBAL_parts/",
                           pristine, mirroring split_template.py
4. build_bsa_scrolls.py - translates SCROLL01.IMG/SCROLL02.IMG (the
                           opening-narration scrolls bundled inside
                           GLOBAL.BSA), saved as readable PNGs into
                           "GLOBAL_parts/legivel/"
5. build_bsa_intro.py   - translates INTRO01.IMG..INTRO09.IMG (the Jagar
                           Tharn coup vision panels), reading the
                           already-blanked PNGs from
                           "GLOBAL_parts/legivel/empty/" (run
                           blank_bsa_intro.py first) and saving the
                           result into "GLOBAL_parts/legivel/"
6. build_bsa_history.py - translates HISTORY.IMG (the backstory
                           paragraph shown before the vision panels),
                           saved as a readable PNG into
                           "GLOBAL_parts/legivel/"
7. build_bsa_ui.py      - translates LOGBOOK.IMG/BUYSPELL.IMG/
                           SPELLMKR.IMG, saved as readable PNGs into
                           "GLOBAL_parts/legivel/"
8. build_bsa_menu.py    - translates MENU.IMG (main menu), saved as a
                           readable PNG into "GLOBAL_parts/legivel/"
                           (compile_images.py later recompresses it from
                           Huffman "type 8" to LZSS "type 4")
9. build_bsa_charstat.py - translates CHARSTAT.IMG (the character
                           attribute sheet), saved as a readable PNG
                           into "GLOBAL_parts/legivel/", same
                           Huffman-to-LZSS recompression as MENU.IMG at
                           compile time
10. build_bsa_yesno.py   - translates YESNO.IMG (the Yes/No/Cancel
                           confirmation dialog), saved as a readable PNG
                           into "GLOBAL_parts/legivel/"
11. build_bsa_popup.py   - translates POPUP3.IMG/POPUP4.IMG (the
                           weapon/armor inventory-list column headers),
                           saved as readable PNGs into
                           "GLOBAL_parts/legivel/"
12. build_bsa_newmenu.py - translates NEWMENU.IMG (the Steal/Exit button
                           bar shown when looting a container), saved as
                           a readable PNG into "GLOBAL_parts/legivel/"
13. build_bsa_newold.py  - translates NEWOLD.IMG (the guild job-board
                           Add Job/Status/Cancel button bar), saved as a
                           readable PNG into "GLOBAL_parts/legivel/"
14. build_bsa_newequip.py - translates NEWEQUIP.IMG (the dungeon loot
                           screen's "Level:" label and Drop/Spellbook/
                           Exit button bar), saved as a readable PNG
                           into "GLOBAL_parts/legivel/"
15. build_bsa_inf.py     - translates the "@TEXT" flavor-text section of
                           every .INF dungeon/location script (signs,
                           notes, riddles), saved as plain readable text
                           (accents kept, not encrypted) into
                           "GLOBAL_parts/legivel/"
16. build_inf_loose.py   - translates the .INF files that ship as LOOSE
                           files in the game folder instead of packed
                           inside GLOBAL.BSA (CRYSTAL3.INF, IMPPAL1-4.INF -
                           the Imperial Palace levels), saved as plain
                           readable text into "Minha tradução/legivel/";
                           a loose file takes precedence over the
                           same-named BSA entry when the game loads it
17. compile_images.py   - compiles every "legivel/" PNG produced by steps
                           2 and 4-14 into the actual game-format `.IMG`
                           (per img_manifest.py's per-file compression/
                           palette rules), written back to wherever the
                           pristine copy already lived
18. compile_inf.py      - compiles every "legivel/" `.INF` text produced
                           by steps 15-16 into the actual game format
                           (accents stripped, and - only for the
                           GLOBAL.BSA-packed ones - re-encrypted), written
                           back to wherever the pristine copy already lived
19. merge_bsa.py         - packs GLOBAL_parts/ back into a full
                           "Minha tradução/GLOBAL.BSA", mirroring
                           merge_template.py
20. build.py             - copies everything from "Minha tradução" into
                           "build/", stripping accents/cedilla from text
                           files (image/archive files, and the "legivel/"
                           working folders, are never touched by this step)

Usage: python3 scripts/build_all.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    "merge_template.py",
    "build_images.py",
    "split_bsa.py",
    "build_bsa_scrolls.py",
    "build_bsa_intro.py",
    "build_bsa_history.py",
    "build_bsa_ui.py",
    "build_bsa_menu.py",
    "build_bsa_charstat.py",
    "build_bsa_yesno.py",
    "build_bsa_popup.py",
    "build_bsa_newmenu.py",
    "build_bsa_newold.py",
    "build_bsa_newequip.py",
    "build_bsa_labels2.py",
    "build_bsa_equip.py",
    "build_bsa_automap.py",
    "build_bsa_slider.py",
    "build_bsa_quote.py",
    "build_bsa_op.py",
    "build_bsa_forms.py",
    "build_bsa_accprejt.py",
    "build_bsa_charspel.py",
    "build_bsa_scroll03.py",
    "build_bsa_inf.py",
    "build_inf_loose.py",
    "compile_images.py",
    "compile_inf.py",
    "merge_bsa.py",
    "build.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n=== {step} ===")
        result = subprocess.run([sys.executable, str(SCRIPTS_DIR / step)])
        if result.returncode != 0:
            print(f"\n{step} failed (exit code {result.returncode}), stopping build.")
            sys.exit(result.returncode)
    print("\nBuild completo.")


if __name__ == "__main__":
    main()
