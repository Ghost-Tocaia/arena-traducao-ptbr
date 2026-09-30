"""Single source of truth for how each translated image gets compiled
back into the game's `.IMG` format: which output compression type to
use, and whether the compiled file should carry its own embedded
768-byte palette or rely on the palette the game has active at the time
(external `.COL` file, or borrowed from a sibling `.IMG`'s own embedded
palette - see docs/pipeline-imagens.md).

This used to be duplicated, hard-coded, inside each build_bsa_*.py
script's own final "write the compiled .IMG" step. Centralizing it here
is what lets compile_images.py be the only place left that assembles
compiled `.IMG` bytes - every build_bsa_*.py script instead just saves
its result as a plain PNG into a "legivel/" folder (see that script's
own comments for exactly how).

Only "loose" (top-level "Minha tradução/") files sit in this manifest
plus the ones inside "Minha tradução/GLOBAL_parts/" ("bsa"). The 5 loose
`.INF` overrides and the 55(+2) `.INF` inside GLOBAL.BSA are NOT here -
they go through compile_inf.py instead (see that script).
"""

LOOSE = "loose"
BSA = "bsa"

# name -> (location, comp_type_saida, embute_paleta)
IMAGE_MANIFEST: dict[str, tuple[str, int, bool]] = {
    # Loose (top-level "Minha tradução/")
    "SCROLL03.IMG": (LOOSE, 4, True),
    "CHARSPEL.IMG": (LOOSE, 0, True),
    "TAMRIEL.MNU": (LOOSE, 4, True),
    "TITLE.IMG": (LOOSE, 4, True),
    # Inside GLOBAL.BSA ("Minha tradução/GLOBAL_parts/")
    "SCROLL01.IMG": (BSA, 4, False),
    "SCROLL02.IMG": (BSA, 4, False),
    "INTRO01.IMG": (BSA, 4, False),
    "INTRO02.IMG": (BSA, 4, False),
    "INTRO03.IMG": (BSA, 4, False),
    "INTRO04.IMG": (BSA, 4, False),
    "INTRO05.IMG": (BSA, 4, False),
    "INTRO06.IMG": (BSA, 4, False),
    "INTRO07.IMG": (BSA, 4, False),
    "INTRO08.IMG": (BSA, 4, False),
    "INTRO09.IMG": (BSA, 4, False),
    "HISTORY.IMG": (BSA, 4, True),
    "LOGBOOK.IMG": (BSA, 0, True),
    "BUYSPELL.IMG": (BSA, 0, True),
    "SPELLMKR.IMG": (BSA, 0, True),
    # Originally Huffman "type 8" in the pristine game data; always
    # recompressed to LZSS "type 4" on write (no type-8 encoder exists).
    "MENU.IMG": (BSA, 4, True),
    "CHARSTAT.IMG": (BSA, 4, False),
    "YESNO.IMG": (BSA, 4, False),
    "NEWMENU.IMG": (BSA, 4, False),
    "NEWOLD.IMG": (BSA, 4, False),
    "POPUP3.IMG": (BSA, 0, False),
    "POPUP4.IMG": (BSA, 0, False),
    "NEWEQUIP.IMG": (BSA, 4, False),
    # Descobertos via varredura_img_bruta.py - ver docs/inventario-arquivos.md seção 4
    "BONUS.IMG": (BSA, 4, False),
    "EQUIPB.IMG": (BSA, 4, False),
    "GOLD.IMG": (BSA, 4, False),
    "PAGE2.IMG": (BSA, 4, False),
    "SPELLBK.IMG": (BSA, 4, False),
    "QUOTE.IMG": (BSA, 4, True),
    "AUTOMAP.IMG": (BSA, 0, True),
    "EQUIP.IMG": (BSA, 4, False),
    "OP.IMG": (BSA, 0, False),
    "FORM1.IMG": (BSA, 4, False),
    "FORM2.IMG": (BSA, 4, False),
    "FORM3.IMG": (BSA, 4, False),
    "FORM4.IMG": (BSA, 4, False),
    "FORM4A.IMG": (BSA, 4, False),
    "FORM5.IMG": (BSA, 4, False),
    "FORM6.IMG": (BSA, 4, False),
    "FORM6A.IMG": (BSA, 4, False),
    "FORM7.IMG": (BSA, 4, False),
    "FORM8.IMG": (BSA, 4, False),
    "FORM9.IMG": (BSA, 4, False),
    "FORM10.IMG": (BSA, 4, False),
    "FORM11.IMG": (BSA, 4, False),
    "FORM12.IMG": (BSA, 4, False),
    "FORM13.IMG": (BSA, 4, False),
    "FORM14.IMG": (BSA, 4, False),
    "FORM15.IMG": (BSA, 4, False),
    # Achado via revisão manual de varredura_imagens/ - ver
    # docs/inventario-arquivos.md seção 4.
    "ACCPREJT.IMG": (BSA, 4, False),
}
