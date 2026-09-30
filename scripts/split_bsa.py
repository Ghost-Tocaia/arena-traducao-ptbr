"""Extracts the GLOBAL.BSA entries that need translation into
"Minha tradução/GLOBAL_parts/", as individual standalone .IMG files
(pristine, byte-for-byte exactly as stored in the archive).

Mirrors split_template.py's role for TEMPLATE_parts/: this is the
"reset to original" step. The extracted files here are then translated
in place by build_bsa_scrolls.py / build_bsa_intro.py / etc., and finally
recombined into a full GLOBAL.BSA by merge_bsa.py.

Usage: python3 scripts/split_bsa.py
"""
from pathlib import Path

from bsa_codec import read_index, offsets_by_name

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"

# every GLOBAL.BSA entry identified so far as needing translation
TARGET_FILES = [
    "SCROLL01.IMG", "SCROLL02.IMG",
    "INTRO01.IMG", "INTRO02.IMG", "INTRO03.IMG", "INTRO04.IMG",
    "INTRO05.IMG", "INTRO06.IMG", "INTRO07.IMG", "INTRO08.IMG", "INTRO09.IMG",
    "HISTORY.IMG", "MENU.IMG", "LOGBOOK.IMG", "BUYSPELL.IMG", "SPELLMKR.IMG",
    "CHARSTAT.IMG", "YESNO.IMG",
    "POPUP3.IMG", "POPUP4.IMG", "NEWEQUIP.IMG", "NEWMENU.IMG", "NEWOLD.IMG",
    "BONUS.IMG", "EQUIPB.IMG", "GOLD.IMG", "PAGE2.IMG", "SPELLBK.IMG",
    "QUOTE.IMG", "AUTOMAP.IMG", "EQUIP.IMG", "OP.IMG",
    "FORM1.IMG", "FORM2.IMG", "FORM3.IMG", "FORM4.IMG", "FORM4A.IMG",
    "FORM5.IMG", "FORM6.IMG", "FORM6A.IMG", "FORM7.IMG", "FORM8.IMG",
    "FORM9.IMG", "FORM10.IMG", "FORM11.IMG", "FORM12.IMG", "FORM13.IMG",
    "FORM14.IMG", "FORM15.IMG", "ACCPREJT.IMG",
    # Cópias diferentes das versões soltas já traduzidas (mesmo texto,
    # layout distinto) - ver docs/inventario-arquivos.md seção 2.2.
    "CHARSPEL.IMG", "SCROLL03.IMG",
    # .INF dungeon/location scripts that carry an "@TEXT" section (flavor
    # text, signs, riddles) - see build_bsa_inf.py and inf_codec.py.
    "AGTEMPL.INF", "BGATE2.INF", "CASTLE.INF", "CRYPT1.INF", "CRYPT2.INF",
    "CRYPT3.INF", "CRYPT4.INF", "CRYSTAL1.INF", "CRYSTAL2.INF", "CRYSTAL3.INF",
    "CRYSTAL4.INF", "DAGOTH1.INF", "DAGOTH2.INF", "DAGOTH3.INF", "DEMO.INF",
    "ELDEN1.INF", "ELDEN2.INF", "FANG1.INF", "FANG2.INF", "FORTI2.INF",
    "GEMIN1.INF", "GEMIN2.INF", "HALLS1.INF", "HALLS2.INF", "HALLS3.INF",
    "IMPPAL1.INF", "IMPPAL2.INF", "IMPPAL3.INF", "IMPPAL4.INF", "KHU1.INF",
    "KHU2.INF", "KHUTEST.INF", "LABRNTH1.INF", "LABRNTH2.INF", "MAGE.INF",
    "MGTEMPL1.INF", "MGTEMPL2.INF", "MURK1.INF", "MURK2.INF", "NOBLE.INF",
    "NOBLE1.INF", "NOBLE2.INF", "NOBLE3.INF", "SD1.INF", "SD3.INF",
    "SELENE1.INF", "SELENE2.INF", "SKEEP1.INF", "SKEEP2.INF", "START.INF",
    "STKEEP1.INF", "TOWER.INF", "TOWER1.INF", "TOWER2.INF", "TOWER6.INF",
    "TOWER8.INF", "VILPAL.INF",
]


def main() -> None:
    data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()
    offsets = offsets_by_name(read_index(data))

    PARTS_DIR.mkdir(parents=True, exist_ok=True)

    for name in TARGET_FILES:
        if name not in offsets:
            print(f"Skipping {name}: not found in GLOBAL.BSA")
            continue
        off, size = offsets[name]
        (PARTS_DIR / name).write_bytes(data[off:off + size])
        print(f"Extracted: {name} ({size} bytes) -> {PARTS_DIR.name}/{name}")


if __name__ == "__main__":
    main()
