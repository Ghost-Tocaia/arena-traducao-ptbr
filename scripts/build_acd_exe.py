"""Bakes the Portuguese translation into ACD.EXE - Arena's main
executable, PKLITE-compressed. Unlike every other translated asset in
this project, the game's text here lives inside compiled machine-code
data (not a loose file or an entry in GLOBAL.BSA), so this pipeline is
its own thing: decompress (pklite_unpack.py) -> patch the strings at
their real offsets in the decompressed buffer -> recompress
(pklite_pack.py) -> reassemble a valid ACD.EXE around that.

Every string offset here was found by searching for the known
pristine ENGLISH text directly in the decompressed buffer (not by
hand-computed arithmetic) and asserting the exact original bytes
match before patching - the same "never trust a guessed offset"
discipline as everywhere else in this project, just applied to a
buffer instead of an image.

**Byte budgets are absolute.** Every field patched here is either a
fixed-length slot (the game reads exactly N raw bytes, more would
spill into whatever data follows) or a null-terminated string/array
whose *total* combined length must not change (the game has hardcoded
absolute addresses elsewhere in this same ~300KB data segment that
would break if anything after this point shifted). Every translation
below is verified (padded with trailing spaces, harmless and
invisible in a UI label) to fit its exact original budget - see the
`patch_*` helpers' assertions.

Working files: the read-only middle step (decompressed + patched, but
not yet recompressed) is saved to "Minha tradução/ACD_unpacked.bin" -
useful for inspecting/diffing without redoing the PKLITE encode.

Real DOSBox hangs on *any* ACD.EXE this project recompresses with
PKLITE, no matter the content (see pipeline-acd-exe.md for the full
investigation) - only OpenTESArena (which decompresses in software,
never executes the real x86 stub) can run one. So this writes two
different, platform-specific files instead of one:
  - "build/opentes/ACD.EXE": PKLITE-recompressed (pklite_pack.rebuild_exe)
  - "build/dosbox/ACD.EXE": plain/uncompressed (pklite_pack.rebuild_dosbox_exe),
    spliced into Originais/ACD_UNPACKED_TEMPLATE.EXE instead of recompressing
"Minha tradução/ACD.EXE" keeps the PKLITE-compressed copy as a working
file, mirroring how GLOBAL.BSA is both a working copy and the thing
build.py later copies through unchanged - ACD.EXE is binary, never
accent-stripped, same as GLOBAL.BSA.

Usage: python3 scripts/build_acd_exe.py
"""
from pathlib import Path

import pklite_pack as pk
import pklite_unpack as unpk

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
WORK_DIR = ROOT_DIR / "Minha tradução"
BUILD_DIR = ROOT_DIR / "build"


def patch_find(data: bytearray, needle: bytes, budget: int, text: str, label: str) -> None:
    """Finds `needle` (the exact pristine English bytes, already
    verified to include whatever \\r/\\x00 terminator belongs to it),
    asserts it's found exactly once, and overwrites those `budget`
    bytes with `text` (padded with trailing spaces to fill the exact
    same span - never fewer, never more)."""
    offset = data.find(needle)
    if offset == -1:
        raise ValueError(f"{label}: needle not found: {needle!r}")
    if data.find(needle, offset + 1) != -1:
        raise ValueError(f"{label}: needle found more than once: {needle!r}")
    b = text.encode("latin-1")
    if len(b) > budget:
        raise ValueError(f"{label}: {len(b)} bytes over budget {budget}: {text!r}")
    b = b + b" " * (budget - len(b))
    data[offset:offset + budget] = b


def accel_bytes(word: str, highlight_idx: int = 0) -> bytes:
    """Builds the \\t\\xc0/\\t\\xd4-marked-up form of a menu button label:
    the game's own convention for "one letter shown highlighted as the
    keyboard accelerator, rest plain" (see ChooseAttributesSave/Reroll
    and every Services menu button). `highlight_idx` picks which
    letter is highlighted - normally 0 (first letter), but shifted
    when two options in the same on-screen menu would otherwise
    highlight the same letter (the game itself does this: compare
    Equipment's Sell/Steal, or Citizen's Who-are-you/Where-is)."""
    before, letter, after = word[:highlight_idx], word[highlight_idx], word[highlight_idx + 1:]
    out = ""
    if before:
        out += "\t\xd4" + before
    out += "\t\xc0" + letter
    out += "\t\xd4" + after
    return out.encode("latin-1")


def patch_button(data: bytearray, offset: int, original: bytes, new_word: str, label: str, highlight_idx: int = 0) -> None:
    """Patches a single accelerator-key menu button (see accel_bytes) at
    a fixed absolute offset - these short button labels ("Exit", "Buy")
    repeat verbatim across many different menus (7 copies of "Exit"
    alone), so a text search can't disambiguate which one is meant;
    the offset is asserted against `original` (the pristine bytes
    including the trailing \\r\\x00) first. Each of these buttons is its
    own independently-addressed field with zero slack - unlike
    ClassNames-style arrays, there's no shared budget to redistribute
    (see this file's own exploration notes on the Services menus)."""
    actual = bytes(data[offset:offset + len(original)])
    if actual != original:
        raise ValueError(f"{label} @{offset}: expected {original!r}, found {actual!r}")
    budget = len(original) - 2  # exclude \r\x00, added back below
    new_bytes = accel_bytes(new_word, highlight_idx)
    if len(new_bytes) > budget:
        raise ValueError(f"{label}: {len(new_bytes)} bytes over budget {budget}: {new_word!r}")
    # Pad with trailing spaces (inserted just before the highlighted
    # word ends, i.e. right into accel_bytes' own "rest" segment) so
    # the field's total length never changes - a slice assignment
    # shorter than `original` would silently shrink the whole buffer
    # and shift everything after it.
    new_bytes = new_bytes + b" " * (budget - len(new_bytes))
    new_bytes = new_bytes + b"\r\x00"
    data[offset:offset + len(original)] = new_bytes


def patch_after(data: bytearray, prefix: bytes, budget: int, text: str, label: str) -> None:
    """Like patch_find, but the translatable text starts right AFTER a
    fixed binary `prefix` blob that must be left completely untouched
    (here: the \\t\\xfe/\\t\\xfd accelerator-key control bytes in the
    Save/Reroll-stats buttons, which have no null before the visible
    label text)."""
    prefix_at = data.find(prefix)
    if prefix_at == -1:
        raise ValueError(f"{label}: prefix not found: {prefix!r}")
    if data.find(prefix, prefix_at + 1) != -1:
        raise ValueError(f"{label}: prefix found more than once: {prefix!r}")
    offset = prefix_at + len(prefix)
    b = text.encode("latin-1")
    if len(b) > budget:
        raise ValueError(f"{label}: {len(b)} bytes over budget {budget}: {text!r}")
    b = b + b" " * (budget - len(b))
    data[offset:offset + budget] = b


def patch_at(data: bytearray, offset: int, expected: bytes, text: str, label: str) -> None:
    """Patches a fixed absolute offset (from OpenTESArena's own
    acdExeStrings.txt offset map, cross-checked against this project's
    pklite_unpack.py output - see build_acd_exe.py's module docstring),
    asserting the pristine bytes there are exactly `expected` first.
    Used instead of patch_find for the CharacterCreation section, where
    several original strings ("Select", "Male") are short/generic
    enough that a plain text search could match more than one spot."""
    budget = len(expected)
    actual = bytes(data[offset:offset + budget])
    if actual != expected:
        raise ValueError(f"{label} @{offset}: expected {expected!r}, found {actual!r}")
    b = text.encode("latin-1")
    if len(b) > budget:
        raise ValueError(f"{label}: {len(b)} bytes over budget {budget}: {text!r}")
    b = b + b" " * (budget - len(b))
    data[offset:offset + budget] = b


def apply_character_creation(data: bytearray) -> None:
    patch_at(data, 0x35C80, b"How do you wish\rto select your class?",
             "Como desejas escolher\rtua classe?", "ChooseClassCreation")
    patch_at(data, 0x3F973, b"Generate", "Sugerir", "ChooseClassCreationGenerate")
    patch_at(data, 0x3F97D, b"Select", "Listar", "ChooseClassCreationSelect")
    patch_at(
        data, 0x35CA7,
        b"10 questions shall be asked that will\rdetermine the path of your destiny.\r"
        b"The scroll bars roll the parchment up\ror down. Use the 'A', 'B', or 'C' keys\r"
        b"to answer the questions.",
        "10 perguntas serao feitas para\rdeterminar o rumo de teu destino.\r"
        "As barras de rolagem sobem e descem\ro pergaminho. Usa 'A', 'B' ou 'C'\r"
        "para responder as perguntas.",
        "ClassQuestionsIntro",
    )
    patch_at(
        data, 0x35DB1,
        b"Thou wouldst survive\rlongest as a %s.\rWilt thou accept this\ras thy destiny?",
        "Tu sobreviverias por mais\rtempo como %s.\rAceitas isto\rcomo teu destino?",
        "SuggestedClass",
    )
    patch_at(data, 0x3F956, b"Choose thy class...", "Escolhe tua classe.", "ChooseClassList")
    patch_at(data, 0x35D58, b"What will be thy name, %s?", "Qual sera teu nome, %s?", "ChooseName")
    patch_at(data, 0x35D74, b"Choose thy gender...", "Escolhe o genero...", "ChooseGender")
    patch_at(data, 0x3F98E, b"Male", "Masc", "ChooseGenderMale")
    patch_at(data, 0x3F994, b"Female", "Femea ", "ChooseGenderFemale")
    # Confirmed NOT the cause of the "New Game" crash (bisected live
    # against OpenTESArena 0.18.0 - see apply_entities' docstring for
    # what the actual cause turned out to be: AttributeNames).
    patch_at(data, 0x35D8A, b"From where dost thou hail,\r%s\rthe\r%s?",
             "De onde vens,\r%s\ro %s?", "ChooseRace")
    patch_at(
        data, 0x35DFF, b"Thou hast chosen %s,\rland of the %s.\rWouldst thou accept this\ras thy home?",
        "Tu escolheste %s,\rterra dos %s.\rAceitas isto como\rteu lar de origem?",
        "ConfirmRace",
    )
    patch_at(
        data, 0x35E4C,
        b"Then thou wilt be known as the %s\r%s, who wouldst call %s,\rland of the %s, his home.",
        "Entao seras conhecido como o %s\r%s, que chamaria %s,\rterra dos %s, de lar natal.",
        "ConfirmedRace1",
    )
    patch_at(data, 0x3F8AA, b"Know ye this also:", "Sabe tambem isto: ", "ConfirmedRace2")
    patch_at(
        data, 0x35EA2, b"Thy body and mind must be\r%s\rif thou art to succeed\ras a %s.",
        "Teu corpo e mente devem\rser %s\rpara teres sucesso\rcomo %s.",
        "ConfirmedRace3",
    )
    patch_at(
        data, 0x35EE0, b"Go ye now in peace.\rLet thy fate be written\rin the Elder Scrolls...",
        "Vai agora em paz.\rQue teu destino seja escrito\rnos Elder Scrolls...",
        "ConfirmedRace4",
    )
    patch_at(
        data, 0x35F25,
        b"Distribute thy points as needed,\rkeeping in mind the recommendations \rfor thy chosen class...",
        "Distribui teus pontos conforme\rpreciso, tendo em mente as\rrecomendacoes para tua classe...",
        "DistributeClassPoints",
    )

    # Per-class attribute descriptions (18 entries, same order as
    # ClassNames), a 367-byte block ending exactly where
    # ChooseAttributes begins.
    attrs = [
        "inteligente e obstinado", "forte e inteligente", "rapido e inteligente",
        "inteligente e agil", "inteligente e obstinado", "agil e inteligente",
        "inteligente e sociavel", "agil e rapido", "forte e inteligente",
        "agil e rapido", "agil e inteligente", "forte e agil", "agil e robusto",
        "forte e agil", "forte e inteligente", "forte e robusto", "forte e robusto",
        "forte e obstinado",
    ]
    patch_at(
        data, 0x36034,
        b"intelligent and willful\x00strong and intelligent\x00quick and intelligent\x00"
        b"intelligent and agile\x00intelligent and willful\x00agile and intelligent\x00"
        b"intelligent and personable\x00agile and quick\x00strong and intelligent\x00"
        b"agile and quick\x00agile and intelligent\x00strong and agile\x00agile and hardy\x00"
        b"strong and agile\x00strong and intelligent\x00strong and hardy\x00strong and hardy\x00"
        b"strong and willful\x00",
        "\x00".join(attrs) + "\x00",
        "PreferredAttributes",
    )

    patch_at(data, 0x361A3, b"Which dost thou choose?", "Qual tu escolhes agora?", "ChooseAttributes")

    # \t\xfe / \t\xfd mark the accelerator-key letter (S in Save, R in
    # Reroll) - keep those 5 control bytes untouched, only the visible
    # text after them is ours.
    patch_after(data, b"\t\xfeS\t\xfd", 9, "alvar    ", "ChooseAttributesSave")
    patch_after(data, b"\t\xfeR\t\xfd", 11, "olar dados ", "ChooseAttributesReroll")

    patch_at(data, 0x3F817, b"You must distribute all your bonus points.\x00",
             "Distribui todos teus pontos de bonus.\x00     ", "ChooseAttributesBonusPointsRemaining")
    patch_at(
        data, 0x35F84,
        b"Thou wilt now choose thy appearance.\rThy mien canst be altered by clicking thy face.\r"
        b"When thou art finished, select 'Done' to enter\rthe world of Tamriel, home of the Arena...",
        "Agora escolheras tua aparencia.\rTeu semblante muda ao clicares em teu rosto.\r"
        "Quando terminares, escolhe 'Pronto' para\rentrares no mundo de Tamriel, lar da Arena...",
        "ChooseAppearance",
    )

    classes = [
        "Mago", "Espadamago", "MagoGuerra", "Bruxo", "Cura", "Sombra", "Bardo",
        "Gatuno", "Ladino", "Acrobata", "Ladrao", "Assassino", "Monge",
        "Arqueiro", "Batedor", "Barbaro", "Lutador", "Cavaleiro",
    ]
    class_names_original = (
        b"Mage\x00Spellsword\x00Battlemage\x00Sorceror\x00Healer\x00Nightblade\x00Bard\x00"
        b"Burglar\x00Rogue\x00Acrobat\x00Thief\x00Assassin\x00Monk\x00Archer\x00Ranger\x00"
        b"Barbarian\x00Warrior\x00Knight\x00"
    )
    class_names_translated = "\x00".join(classes) + "\x00"
    # ClassNames is genuinely duplicated verbatim at two offsets: 0x3E462
    # (the character-creation class list, per acdExeStrings.txt) and
    # 0x36E77 (immediately after CreatureNames - these same names get
    # reused as human enemy types, e.g. "a Mage attacks you"). Both
    # need translating or enemy encounters would show English names
    # while character creation shows Portuguese ones.
    patch_at(data, 0x3E462, class_names_original, class_names_translated, "ClassNames")
    patch_at(data, 0x36E77, class_names_original, class_names_translated, "ClassNames (enemy-type copy)")


def apply_status_and_locations(data: bytearray) -> None:
    patch_find(data, b"You are not a spellcaster!\r\x00", 28,
               "Nao es um conjurador!\r\x00     ", "spellcaster")
    patch_find(data, b"Your logbook is empty.\x00", 23,
               "Teu diario esta vazio.\x00", "logbook_empty")
    patch_find(data, b"Select target for pilfering...\x00", 31,
               "Escolhe alvo para furtar...\x00   ", "pilfering")
    patch_find(data, b"You have found %s key.\x00", 23,
               "Achaste chave de %s.\x00  ", "found_key")
    patch_find(data, b"You open door with %s key.\x00", 27,
               "Abres porta com chave %s.\x00 ", "open_door_key")
    patch_find(data, b"You have found %u gold pieces!!\x00", 32,
               "Encontraste %u moedas!!\x00", "found_gold")
    patch_find(
        data,
        b"You are in %s.\rIt is %s.\rThe date is %sYou are currently carrying %d kg out of %d kg.\r\x00",
        87,
        "Estas em %s.\rE %s.\rA data e %sCarregas atualmente %d kg de %d kg.\r\x00                    ",
        "you_are_in",
    )

    key_materials = ["Latao", "Ferro", "Aco", "Prata", "Ouro", "Mithril", "Ametista",
                      "Diamante", "Esmeralda", "Rubi", "Safira", "Cristal"]
    key_bytes = ("\x00".join(key_materials) + "\x00").encode("latin-1")
    key_bytes += b" " * (111 - len(key_bytes))
    assert len(key_bytes) == 111
    needle = (
        b"a Brass\x00an Iron\x00a Steel\x00a Silver\x00a Gold\x00a Mithril\x00an Amethyst\x00"
        b"a Diamond\x00an Emerald\x00a Ruby\x00a Sapphire\x00a Crystal\x00"
    )
    offset = data.find(needle)
    if offset == -1:
        raise ValueError("key materials: needle not found")
    data[offset:offset + 111] = key_bytes

    status_prefixes = ["Teu %s esta fortificado.\r", "Tens %s.\r", "Estas %s.\r"]
    status_words = [
        "saudavel", "doente", "envenenado", "em estado critico", "bebado", "invisivel",
        "nao-alvo", "resistente a fogo", "resistente a frio", "resistente a choque",
        "resistente a acido", "resistente a veneno", "levitando",
    ]
    combined = "\x00".join(status_prefixes) + "\x00" + "\x00".join(status_words) + "\x00"
    combined_bytes = combined.encode("latin-1")
    combined_bytes += b" " * (231 - len(combined_bytes))
    assert len(combined_bytes) == 231, len(combined_bytes)
    needle = (
        b"Your %s is fortified.\r\x00You have %s.\r\x00You are %s.\r\x00healthy\x00diseased\x00"
        b"poisoned\x00in critical condition\x00drunk\x00invisible\x00a non-target\x00"
        b"resistant to fire\x00resistant to cold\x00resistant to shock\x00resistant to acid\x00"
        b"resistant to poison\x00levitating\x00"
    )
    offset = data.find(needle)
    if offset == -1:
        raise ValueError("status cluster: needle not found")
    data[offset:offset + 231] = combined_bytes

    patch_find(data, b"Imperial Dungeons\x00", 18, "Masmorra Imperial\x00", "StartDungeonName")

    loctypes = ["Capital", "Vila", "Aldeia", "Aldeia", "Masmorra"]
    loc_bytes = ("\x00".join(loctypes) + "\x00").encode("latin-1")
    loc_bytes += b" " * (40 - len(loc_bytes))
    assert len(loc_bytes) == 40
    patch_find(data, b"City-State\x00Town\x00Village\x00Village\x00Dungeon\x00", 40,
               loc_bytes.decode("latin-1"), "LocationTypes")

    loctypes_lower = ["capital", "vila", "aldeia", "aldeia", "masmorra"]
    loc_bytes2 = ("\x00".join(loctypes_lower) + "\x00").encode("latin-1")
    loc_bytes2 += b" " * (40 - len(loc_bytes2))
    assert len(loc_bytes2) == 40
    patch_find(data, b"city-state\x00town\x00village\x00village\x00dungeon\x00", 40,
               loc_bytes2.decode("latin-1"), "LocationTypesLowercase")

    # 3 potions found past the original search window used the first
    # time round; "Staff" (weapon type) and "of Wizard's Fire"
    # (enchantment suffix, preceded by a run of unrelated binary data
    # with no null separator) are both handled by the search-based
    # linear scan in apply_equipment() below instead, since a plain
    # text search doesn't care what precedes the needle.
    patch_find(data, b"Potion of Cure Poison\x00", 22, "Pocao Cura Veneno\x00    ", "PotionCurePoison")
    patch_find(data, b"Potion of Invisibility\x00", 23, "Pocao Invisibilidade\x00  ", "PotionInvisibility")
    patch_find(data, b"Potion of Purification\x00", 23, "Pocao de Purificacao\x00  ", "PotionPurification")


# Weapons/armor/materials/potions/enchantment-suffix vocabulary shared
# across several repeated tables in the Items/Equipment region - see
# apply_equipment() below, which walks that whole region once and
# substitutes any \x00-terminated run found in this dict, leaving
# everything else (including the several unrelated binary tables
# interleaved in there with no null separator) untouched.
EQUIPMENT_TRANSLATIONS = {
    # unique artifacts: generic parts translated, proper nouns
    # (Magnus/Auriel/Phynaster/Orgnum/Khajiit) kept, "Lord's Mail" and
    # the fully-invented names (Oghma Infinium, Chrysamere, Volendrung)
    # left in English entirely per the user's own call.
    "Staff of Magnus": "Cetro de Magnus",
    "Spell Breaker": "QuebraFeitico",
    "Necromancer's Amulet": "Amuleto Necromante",
    "Auriel's Shield": "Escudo Auriel",
    "Ebony Blade": "Gume Ebano",
    "Warlock's Ring": "Anel do Bruxo",
    "Auriel's Bow": "Arco Auriel",
    "Skeleton's Key": "Chave-Mestra",
    "Ring of Phynaster": "Anel de Phynaster",
    "King Orgnum's Coffer": "Cofre do Rei Orgnum",
    "Ebony Mail": "Cota Ebano",
    "Ring of Khajiit": "Anel Khajiit",

    # jewelry base types
    "Mark": "Selo",
    "Crystal": "Cristal",
    "Bracers": "Manopla",
    "Ring": "Anel",
    "Bracelet": "Bracelete",
    "Belt": "Cint",
    "Torc": "Torc",
    "Amulet": "Amulet",

    # enchantment suffixes ("of X" -> "de Y"), repeated across several tables
    "of Wizard's Fire": "de Fogo do Mago",
    "of Shocking": "de Choque",
    "of Curse": "de Praga",
    "of Far Silence": "de Silencio",
    "of Poison Dart": "de Veneno",
    "of Fireball": "de Fogo",
    "of Ice Storm": "de Temp Gelo",
    "of Lightning": "de Relampago",
    "of Pitfall": "de Armad.",
    "of Fire Storm": "de Temp. Fogo",
    "of Life Steal": "de Rouba-Vida",
    "of Toxic Cloud": "de Gas Toxico",
    "of Paralyzation": "de Paralisia",
    "of Wildfire": "de Incendio",
    "of Free Action": "de Acao Livre",
    "of Stamina": "de Vigor",
    "of Sanctuary": "de Santuario",
    "of Shielding": "de Protecao",
    "of Healing": "de Cura",
    "of Levitation": "de Levitacao",
    "of Force Bolt": "de Raio Forca",
    "of Force Wall": "de Muro Forca",
    "of Silence": "de Silenc",
    "of Passwall": "de Atravess",
    "of Light": "de Luz",
    "of Wanderlight": "de Luz Errante",
    "of Wizard Lock": "de Tranca Mag",
    "of Opening": "de Abrir",
    "of Cure Poison": "de Cura Ven.",
    "of Heal True": "de Cura Tot",
    "of Purification": "de Purificacao",
    "of Strength": "de Forca",
    "of Intelligence": "de Inteligencia",
    "of Willpower": "de Vontade",
    "of Agility": "de Agil",
    "of Speed": "de Veloc",
    "of Endurance": "de Resist",
    "of Personality": "de Personalid",
    "of Luck": "de Sort",
    "of Shock Resistance": "de Resist. Choque",
    "of Will": "de Vont",
    "of Fire Resistance": "de Resist. Fogo",
    "of Frost Resistance": "de Resist. Frio",
    "of Firestorm": "de Temp Fogo",
    "of Jumping": "de Salto",
    "of Invisibility": "de Invisibil.",
    "of Spell Reflection": "de Reflexao",
    "of Regeneration": "de Regeneracao",

    # weapon types (Tanto/Wakizashi/Katana/Dai-Katana kept - Japanese
    # weapon names, not generic English terms)
    "Staff": "Cajado",
    "Dagger": "Adaga",
    "Shortsword": "Esp.Curta",
    "Broadsword": "Esp.Larga",
    "Saber": "Sabre",
    "Longsword": "Esp.Longa",
    "Claymore": "Montante",
    "Mace": "Maca",
    "Flail": "Flail",
    "War Hammer": "M.Guerra",
    "War Axe": "Mach.Gr",
    "Battle Axe": "Mach.Bat",
    "Short Bow": "Arco Crt",
    "Long Bow": "Arco Lg",

    # armor pieces (repeats across base/plate/chain/leather tables)
    "Cuirass": "Couraca",
    "Gauntlets": "Manoplas",
    "Greaves": "Grevas",
    "Pauldron (L)": "Ombreira Esq",
    "Pauldron (R)": "Ombreira Dir",
    "Helm": "Elmo",
    "Boots": "Botas",
    "Buckler": "Broquel",
    "Round Shield": "Esc.Redondo",
    "Kite Shield": "Esc.Chanfr",
    "Kite shield": "Esc.Chanfr",
    "Tower Shield": "Escudo Torre",
    "Tower shield": "Escudo Torre",
    "Plate Cuirass": "Couraca Placas",
    "Plate Gauntlets": "Manoplas Placas",
    "Plate Greaves": "Grevas Placas",
    "Plate Pauldron (L)": "Ombreira Pl.Esq",
    "Plate Pauldron (R)": "Ombreira Pl.Dir",
    "Plate Helm": "Elmo Pl",
    "Plate Boots": "Botas Pl",
    "Chain Cuirass": "Couraca Malha",
    "Chain Gauntlets": "Manoplas Malha",
    "Chain Greaves": "Grevas Malha",
    "Chain Pauldron (L)": "Ombreira Ma.Esq",
    "Chain Pauldron (R)": "Ombreira Ma.Dir",
    "Chain Helm": "Elmo Malha",
    "Chain Boots": "Botas Malha",
    "Leather Cuirass": "Couraca Couro",
    "Leather Gauntlets": "Manoplas Couro",
    "Leather Greaves": "Grevas de Couro",
    "Leather Pauldron (L)": "Ombreira Co.Esq",
    "Leather Pauldron (R)": "Ombreira Co.Dir",
    "Leather Helm": "Elmo Couro",
    "Leather Boots": "Botas Couro",
    "Chest": "Peito",
    "Hands": "Maos",
    "Legs": "Pern",
    "Shoulder": "Ombro",
    "Head": "Cab.",
    "Foot": "Pe",
    "General": "Geral",

    # materials
    "Iron": "Ferro",
    "Steel": "Aco",
    "Silver": "Prata",
    "Elven": "Elfic",
    "Dwarven": "Anao",
    "Adamantium": "Adamantio",
    "Ebony": "Ebano",

    # tavern room types
    "Single": "Simples",
    "Double": "Duplo",
    "Suite": "Suite",
    "King's Suite": "Suite Real",
    "Emperor's Suite": "Suite Imperial",

    # potions
    "Potion of Stamina": "Pocao de Vigor",
    "Potion of Strength": "Pocao de Forca",
    "Potion of Healing": "Pocao de Cura",
    "Potion of Restore Power": "Pocao Restaura Poder",
    "Potion of Resist Fire": "Pocao Resiste Fogo",
    "Potion of Resist Cold": "Pocao Resiste Frio",
    "Potion of Resist Shock": "Pocao Resiste Choque",
    "Potion of Cure Disease": "Pocao Cura Doenca",
    "Potion of Heal True": "Pocao Cura Total",
    "Potion of Levitation": "Pocao de Levitacao",
    "Potion of Resist Poison": "Pocao Resiste Veneno",
    "Potion of Free Action": "Pocao Acao Livre",

    # tavern drinks - only the generic ones; loanword-style beer/wine
    # styles (Ale, Stout, Bock, Lager, Grog, Port) and the punny
    # invented names (Djinn 'n Tonic, Golem-maker, etc.) left in
    # English, same as real-world PT-BR drink menus keep those terms.
    "Beer": "Cerv",
    "Bitters": "Amargo",
    "Pilsner": "Pilsen",
    "Red wine": "V.Tinto",
    "White wine": "V.Branco",
    "Cider": "Sidra",
}


def patch_array(data: bytearray, original_items: list[str], span: int, items: list[str], label: str) -> None:
    """Patches a sequential null-terminated string array (like
    ClassNames) in place. `original_items` must be the array's exact
    pristine content, in order - used both as the search needle (the
    full joined content, not just the first item: a short/generic
    first item like "Strength\\x00" can and does collide with unrelated
    data elsewhere - e.g. the "of Strength" enchantment tables) and as
    a check that the array's total combined span from there is exactly
    `span` bytes (verified against whatever unrelated field follows it
    in the buffer - see this file's own exploration notes). Patches
    EVERY occurrence found, not just the first: several of these arrays
    (ClassNames, AttributeNames confirmed so far) are genuinely
    duplicated verbatim elsewhere in the data segment for a different
    UI screen, and both copies need to match or the game reads
    English in one place and Portuguese in another. Unlike patch_at's
    fixed per-field budget, an array's *individual* item lengths are
    free to change as long as the combined total doesn't grow -
    nothing reads past the last real item, and the array as a whole
    must not shift whatever comes right after it."""
    needle = ("\x00".join(original_items) + "\x00").encode("latin-1")
    if len(needle) != span:
        raise ValueError(f"{label}: original_items span {len(needle)} != declared span {span}")
    joined = ("\x00".join(items) + "\x00").encode("latin-1")
    if len(joined) > span:
        raise ValueError(f"{label}: {len(joined)} bytes over span {span}")
    joined = joined + b"\x00" * (span - len(joined))

    offsets = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos == -1:
            break
        offsets.append(pos)
        pos += 1
    if not offsets:
        raise ValueError(f"{label}: original array content not found: {needle!r}")
    for offset in offsets:
        data[offset:offset + span] = joined
    print(f"  {label}: patched {len(offsets)} occurrence(s) at {[hex(o) for o in offsets]}")


def apply_calendar_and_camping(data: bytearray) -> None:
    # TimesOfDay: used as "%s" inside "you_are_in"'s "E %s." sentence
    # (see apply_status_and_locations) - each phrase reads naturally
    # after "E ". 7 items, 84-byte original combined span (verified:
    # ends exactly where the unrelated "pointer1.dat" string begins).
    patch_array(
        data,
        [
            "early morning", "in the morning", "noon", "in the afternoon",
            "in the evening", "at night", "midnight",
        ],
        84,
        [
            "de madrugada", "de manha", "ao meio-dia", "de tarde",
            "ao entardecer", "de noite", "a meia-noite",
        ],
        "TimesOfDay",
    )

    # MonthNames: 12 items, 150-byte combined span (ends exactly where
    # WeekdayNames begins - those stay untranslated, invented names
    # like Tamriel). Evocative but compact - budget is tight. (Real
    # combined span of the 12 items is 136, not the 150-byte gap to
    # WeekdayNames - there are 14 bytes of unrelated non-string data
    # between "Evening Star\0" and "Morndas\0" that must stay untouched.)
    patch_array(
        data,
        [
            "Morning Star", "Sun's Dawn", "First Seed", "Rain's Hand",
            "Second Seed", "Mid Year", "Sun's Height", "Last Seed",
            "Hearthfire", "Frostfall", "Sun's Dusk", "Evening Star",
        ],
        136,
        [
            "Estrela Matina", "Alvorada", "Semente Nova", "Mao da Chuva",
            "Semente II", "Meio-Ano", "Auge do Sol", "Ultima Semente",
            "Lareira", "Geada", "Crepusculo", "Estrela-Tarde",
        ],
        "MonthNames",
    )

    # HolidayNames: 15 items, real combined span is 242 (not the 332
    # bytes to the next known field - there's ~90 bytes of unrelated
    # non-string data, likely per-holiday date encodings, between the
    # last name and the true HolidayDates table start).
    patch_array(
        data,
        [
            "New Life Festival", "South Wind's Prayer", "Hearts Day",
            "First Planting", "Jester's Day", "Second Planting",
            "Mid-Year Celebration", "Merchants Festival", "Sun's Rest",
            "Harvest End", "Tales and Tallow", "Witches Festival",
            "Emperor's Day", "Warriors Festival", "North Wind's Prayer",
        ],
        242,
        [
            "Festa Vida Nova", "Prece Vento Sul", "Dia dos Coracoes",
            "Primeiro Plantio", "Dia do Bobo", "Segundo Plantio",
            "Festa Meio-Ano", "Festa Mercadores",
            "Descanso do Sol", "Fim da Colheita", "Contos e Velas",
            "Festa Bruxas", "Dia do Imperador",
            "Festa Guerreiros", "Prece Vento Norte",
        ],
        "HolidayNames",
    )

    # Status.Date: the full in-game date line, e.g.
    # "Morndas, 4th of Morning Star in the year 3E 896".
    # NOTE on all budgets in this function: each is exactly len(needle) -
    # the needle here does NOT include the field's trailing \x00, and
    # budget must not either, or patch_find's automatic space-padding
    # overwrites that null terminator (destroying the string boundary -
    # the game then reads straight through into whatever text follows
    # until it happens to hit a later, unrelated null byte). This was
    # off by one in all of these calls until a live bug report from the
    # user showed multiple camping/status messages bleeding together on
    # screen - see this project's own session history/build_acd_exe.py
    # git log for the fix.
    patch_find(data, b"%s, %u%s of %s in the year 3E %d\r", 33,
               "%s, %u%s de %s no ano 3E %d\r", "Status.Date")

    # Camping ("Camp Options" - reported untranslated).
    patch_find(data, b"%u hour passed....", 18, "%u hora passou....", "SingularHourPassed")
    patch_find(data, b"%u hours passed...", 18, "%u horas passaram.", "PluralHoursPassed")
    patch_find(data, b"%u hour remaining...", 20, "%u hora restante...", "SingularHourRemaining")
    patch_find(data, b"%u hours remaining...", 21, "%u horas restantes...", "PluralHoursRemaining")
    patch_find(data, b"\t\xc0 CAMP OPTIONS\r", 16, "\t\xc0 OPCOES CAMPO\r", "Camping.ModalTitle")
    # \t\xc0<letter>\t\xd4<rest> marks an accelerator key (highlighted
    # first letter) - same control-code convention as
    # ChooseAttributesSave/Reroll. The letter itself is plain ASCII and
    # free to pick, as long as it's the literal first letter of the
    # translated phrase that follows.
    patch_find(data, b"\t\xc0C\t\xd4amp for a while...\r", 24,
               "\t\xc0A\t\xd4campar por tempo\r", "Camping.ModalRestManualHours")
    patch_find(data, b"\t\xc0U\t\xd4ntil fully  healed\r", 24,
               "\t\xc0D\t\xd4escansar ate curar\r", "Camping.ModalRestUntilHealed")
    patch_find(data, b"How many hours do you wish to rest?         ", 44,
               "Quantas horas desejas descansar?            ", "Camping.HoursToRest")
    patch_find(data, b"You are healed...", 17, "Estas curado...", "Camping.DoneRestingHealed")
    patch_find(data, b"You wake up... ", 15, "Tu acordas...  ", "Camping.DoneRestingWakeUp")
    patch_find(data, b"Your time is up...", 18, "Teu tempo acabou..", "Camping.DoneRestingTimesUp")
    patch_find(data, b"You can't camp. Enemies are nearby!!!", 37,
               "Nao podes acampar. Inimigos perto!!", "Camping.EnemiesNearbyBeforeResting")
    patch_find(data, b"There are enemies nearby...", 27,
               "Ha inimigos por perto...", "Camping.EnemiesNearbyAfterResting")
    patch_find(data, b"You don't need to rest.", 23,
               "Nao precisas descansar.", "Camping.AlreadyFullyRested")
    patch_find(data, b"You can't camp here.", 20, "Nao acampa aqui.", "Camping.CampingNotAllowed")
    patch_find(data, b"You must first rent a room.", 27,
               "Primeiro aluga um quarto.  ", "Camping.TavernBedNotRented")


def apply_entities(data: bytearray) -> None:
    # AttributeNames left UNTRANSLATED (English: Strength, Intelligence,
    # Willpower, Agility, Speed, Endurance, Personality, Luck) - bisected
    # live against OpenTESArena 0.18.0 (with the user's help testing
    # "New Game" repeatedly) down to this one field: patching it at all
    # - even just its single documented occurrence (0x3E500), with
    # short, well-formed content nowhere near the 32-byte buffer
    # PrimaryAttribute::name copies into - reliably crashes the engine
    # ("KeyValuePool.h index -1") between confirming race and entering
    # the ChooseAttributes screen. Read through PrimaryAttribute::init,
    # PrimaryAttributes::init, and initStringArrayNullTerminated in
    # OpenTESArena's own source and found nothing that should care
    # about the string content itself, only two other read sites
    # (CharacterEquipmentUiState.cpp, ItemLibrary.cpp) neither of which
    # runs this early - so the actual mechanism is still unconfirmed.
    # Tried 4 variations before giving up: both occurrences patched,
    # just 0x3E500 space-padded, just 0x3E500 null-padded, and finally
    # a single-byte change (just "Luck" -> "Luk", everything else left
    # pristine English) - all 4 crashed identically, ruling out padding
    # style or which occurrence and confirming it's not about the
    # specific translated words either: ANY modification to this
    # address crashes the game, even the smallest one. This is a
    # real, user-visible field (attribute names shown on the points-
    # distribution and character sheet screens - not just internal
    # logic), so it's a genuine loss, not a "safe to skip" field - but
    # every other translated field in this function, plus all of
    # apply_races, was independently confirmed to work fine, so this
    # is isolated to AttributeNames specifically. Revisit if a future
    # session gets interactive access to the running game or its debug
    # output (this session could only read log files the user pasted
    # back after manually testing each build).

    # CreatureNames: 22 monster names, 185-byte combined span (ends
    # exactly where the class names get reused for human enemy types -
    # those are already translated by apply_character_creation).
    patch_array(
        data,
        [
            "Rat", "Goblin", "Lizard Man", "Wolf", "Snow Wolf", "Orc", "Skeleton",
            "Minotaur", "Spider", "Ghoul", "Hell Hound", "Ghost", "Zombie", "Troll",
            "Wraith", "Homonculus", "Ice Golem", "Stone Golem", "Iron Golem",
            "Fire Daemon", "Medusa", "Vampire", "Lich",
        ],
        185,
        [
            "Rato", "Goblin", "Lagarto", "Lobo", "LoboNeve", "Orc", "Esqueleto",
            "Minotauro", "Aranha", "Ghoul", "Cerbero", "Fantasma", "Zumbi", "Troll",
            "Espectro", "Homunculo", "GolemGelo", "Golem Pedra", "GolemFerro",
            "Demonio Fogo", "Medusa", "Vampiro", "Lich",
        ],
        "CreatureNames",
    )

    # DiseaseNames: 17 items, 185-byte combined span (ends exactly
    # where an unrelated kinship-term array begins).
    patch_array(
        data,
        [
            "Witch Pox", "Plague", "Yellow Fever", "Stomach Rot", "Consumption",
            "Brain Fever", "Swamp Rot", "Calirons Curse", "Cholera", "Leprosy",
            "Wound Rot", "Red Death", "Blood Rot", "Typhoid Fever", "Dementia",
            "Chrondiasis", "Wizard Fever",
        ],
        185,
        [
            "Bexiga", "Peste", "Febre Amarela", "Mal-Estomago", "Tise",
            "Febre Cerebral", "Mal-Pantano", "Praga-Caliron", "Colera",
            "Lepra", "Mal-Ferida", "Morte Vermelha", "Mal-Sangue",
            "Febre Tifoide", "Demencia", "Crondiase", "Febre do Mago",
        ],
        "DiseaseNames",
    )

    # Budgets below are exactly len(needle) - see apply_calendar_and_camping's
    # note on why (patch_find must never write into the field's own \x00).
    patch_find(data, b"You have gained a level of experience!", 38,
               "Ganhaste um nivel de experiencia!     ", "ReadyToLevelUp")
    patch_find(data, b"Hit 'J' to exit boat.", 21, "Aperta 'J' sai barco.", "boat_exit")
    patch_find(data, b"The magic coffer yields %d gold.", 32,
               "O cofre magico rende %d moedas.", "magic_coffer")
    patch_find(data, b"You have already used that today...", 35,
               "Ja usaste isso hoje...            ", "already_used_today")


def apply_races(data: bytearray) -> None:
    # Redguard/Khajiit kept untranslated per the user's explicit call.
    # Dark/High/Wood Elf all use the canonical Elder Scrolls lore
    # demonyms (Dunmer/Altmer/Bosmer) instead of descriptive compounds -
    # short enough to leave room for Nordico/Argoniano in full, and
    # (like Khajiit) the same word for singular and plural, matching
    # how these elvish demonyms are actually used in TES lore.
    patch_array(
        data,
        [
            "Bretons", "Redguards", "Nords", "Dark Elves", "High Elves",
            "Wood Elves", "Khajiit", "Argonians",
        ],
        75,
        [
            "Bretoes", "Redguards", "Nordicos", "Dunmers", "Altmers",
            "Bosmers", "Khajiit", "Argonianos",
        ],
        "PluralNames (races)",
    )

    # SingularNames: 8 items, 65-byte combined span (ends exactly
    # where the numeric HealthDice table begins).
    patch_array(
        data,
        [
            "Breton", "Redguard", "Nord", "Dark Elf", "High Elf",
            "Wood Elf", "Khajiit", "Argonian",
        ],
        65,
        [
            "Bretao", "Redguard", "Nordico", "Dunmer", "Altmer",
            "Bosmer", "Khajiit", "Argoniano",
        ],
        "SingularNames (races)",
    )


def apply_city_generation(data: bytearray) -> None:
    """Procedurally-generated tavern names: the game concatenates
    tavernPrefixes[i] + ' ' + (tavernSuffixes or tavernMarineSuffixes)[j]
    (OpenTESArena's MapGeneration.cpp, createTavernName) - always in that
    fixed order, hardcoded in the engine, which we can't change. English
    reads naturally as Adjective+Noun ("Green Griffin"); Portuguese wants
    Noun+Adjective. Since we can only edit the DATA not the concatenation
    logic, the fix is to invert which *kind* of word lives in which slot:
    nouns (translated from the original TavernSuffixes) go into the
    TavernPrefixes address (always read first, regardless of coastal
    status), and adjectives go into both suffix addresses (read second,
    chosen by coastal/non-coastal). Reviewed word-by-word with the user,
    including inventing a new set of maritime-themed adjectives for
    TavernMarineSuffixes - the original marine *nouns* (Ship, Anchor,
    Sailor's...) don't survive the inversion, since only one prefix array
    is shared regardless of coastal status, so the coastal/non-coastal
    distinction moves to the adjective side instead. All three arrays are
    byte-budget-tight fixed 23-item arrays (same constraint as
    AttributeNames elsewhere), verified against the exact original span
    before writing.
    """
    # TavernPrefixes (0x36416, 167-byte span): now holds NOUNS translated
    # from the original TavernSuffixes content (23 items). The needle here
    # must be the pristine content actually AT this address (the original
    # adjectives), not the nouns we're writing.
    patch_array(
        data,
        [
            "Green", "Black", "Red", "Blue", "Gold", "White", "Silver", "Crimson",
            "Dirty", "Haunted", "Flying", "Dancing", "Laughing", "Restless",
            "King's", "Queen's", "Thirsty", "Unfortunate", "Lucky", "Devil's",
            "Rusty", "Howling", "Screaming",
        ],
        167,
        [
            "Grifo", "Dragao", "Golem", "Goblin", "Ogro", "Gigantes", "Djinn",
            "Lobo", "Cacador", "Calice", "Copo", "Garfo", "Esqueleto", "Martelo",
            "Guarda", "Covil", "Poco", "Elmo", "Abismo", "Castelo", "Jarro",
            "Urubu", "Passaro",
        ],
        "TavernPrefixes (now nouns)",
    )

    # TavernSuffixes (0x36557, 138-byte span, non-coastal cities): now
    # holds general ADJECTIVES translated from the original TavernPrefixes
    # content. Several had to be swapped for shorter synonyms to fit the
    # tight budget (Portuguese adjectives run longer than the short
    # English nouns this span was originally sized for) - chosen with the
    # user word-by-word; "Seco" (Restless) and "Baixo" (Laughing) are
    # budget-driven substitutions that don't carry the original meaning,
    # accepted since this is flavor text, not user-facing translated UI.
    patch_array(
        data,
        [
            "Griffin", "Dragon", "Golem", "Goblin", "Ogre", "Giants", "Djinn",
            "Wolf", "Huntsman", "Mug", "Cup", "Dagger", "Skull", "Sword",
            "Guard", "Dungeon", "Pit", "Helm", "Chasm", "Castle", "Jug",
            "Eagle", "Bird",
        ],
        138,
        [
            "Verde", "Preto", "Rubro", "Azul", "Belo", "Branco", "Alvo", "Quente",
            "Sujo", "Feio", "Voador", "Bom", "Baixo", "Seco",
            "Real", "Real", "Sedento", "Infeliz", "Sortudo", "Mal",
            "Negro", "Uivante", "Alto",
        ],
        "TavernSuffixes (now general adjectives)",
    )

    # TavernMarineSuffixes (0x364BD, 154-byte span, coastal cities): now
    # holds new maritime-themed ADJECTIVES (not a translation of the
    # original marine nouns - Ship/Anchor/Sailor's don't survive the
    # inversion, see this function's docstring) - chosen with the user,
    # some repeated to fill the 23 slots within budget.
    patch_array(
        data,
        [
            "Sailor's", "Ship", "Galley", "Wharf", "Pier", "Serpent", "Anchor",
            "Crow's Nest", "Tide", "Mug", "Cup", "Dagger", "Skull", "Cutlass",
            "Saber", "Treasure", "Locker", "Chest", "Port", "Noose", "Gibbet",
            "Gull", "Albatross",
        ],
        154,
        [
            "Bravio", "Rugente", "Salgado", "Marinho", "Abissal", "Salobre",
            "Insular", "Aqueo", "Salino", "Aquoso", "Turvo", "Turvo", "Largo",
            "Largo", "Aberto", "Morto", "Vivo", "Vivo", "Vivo", "Sereno",
            "Gelido", "Tepido", "Areno",
        ],
        "TavernMarineSuffixes (now maritime adjectives)",
    )

    # Temple names: templePrefixes[model] + templeSuffix (no explicit
    # space in the concatenation - the trailing space lives inside each
    # prefix string itself) - a genitive "Order of X" construction that
    # already reads correctly in Portuguese as "Ordem de X" without
    # needing the noun/adjective inversion Tavern needed. `model` (0-2)
    # picks both the prefix AND which of the 3 differently-sized suffix
    # arrays is used, so each prefix is only ever paired with its own
    # suffix array - not a shared pool like Tavern.
    patch_array(
        data,
        ["Order of the ", "Brotherhood of ", "Conclave of "],
        43,
        ["Ordem de ", "Irmandade de ", "Conclave de "],
        "TemplePrefixes",
    )
    # Temple1Suffixes (paired with "Ordem de "): tight budget forced
    # trimming "Knights of Hope" down to just "Esperanca".
    patch_array(
        data,
        ["Red Rose", "One Prophet", "Golden Tomb", "Knights of Hope", "Gentle Hand"],
        61,
        ["Rosa Rubra", "Profeta Uno", "Tumulo Ouro", "Esperanca", "Mao Gentil"],
        "Temple1Suffixes",
    )
    # Temple2Suffixes (paired with "Irmandade de "): Seth/Gideon are
    # proper nouns, kept untranslated.
    patch_array(
        data,
        ["Mercy", "Faith", "Charity", "War", "Justice", "Temperance",
         "the One", "Seth", "Gideon"],
        63,
        ["Piedade", "Fe", "Caridade", "Guerra", "Justica", "Temperanca",
         "Uno", "Seth", "Gideon"],
        "Temple2Suffixes",
    )
    # Temple3Suffixes (paired with "Conclave de "): Baal/Riana are
    # proper nouns, kept untranslated.
    patch_array(
        data,
        ["Mercy", "Faith", "Charity", "Justice", "Temperance", "the One",
         "Truth", "Solitude", "Baal", "Riana"],
        73,
        ["Piedade", "Fe", "Caridade", "Justica", "Temperanca", "Uno",
         "Verdade", "Solidao", "Baal", "Riana"],
        "Temple3Suffixes",
    )

    # Equipment store names: equipmentPrefixes[i] + ' ' + equipmentSuffixes[j],
    # then %ct/%ef/%n get substituted into the result (city type / a
    # generated NPC name) wherever they appear - order-independent, so
    # no inversion needed there. Instead of literal "'s" possessives
    # (which would read backwards in Portuguese before the noun - same
    # problem Tavern had with King's/Queen's), this uses the real
    # Portuguese shop-naming convention of bare name+category
    # juxtaposition ("Silva Ferragens") and the "-aria" shop suffix
    # (Mercearia, Ferraria...) - which is reliably always feminine, so
    # every adjective in the prefix list can safely use one fixed
    # feminine form with zero gender-agreement mismatches, without
    # needing Tavern's "make every noun masculine" trick.
    patch_array(
        data,
        ["%ef's", "%n's", "The %ct", "The Essential", "Used", "The Practical",
         "The Adventurer's", "Rare", "%ef's Finest", "New", "Unearthed",
         "Vintage", "The Emperor's", "Elite", "Bargain", "%ef's General",
         "The Basic", "The Wyrm's", "%ef's Professional", "%ef's Quality"],
        205,
        ["%ef", "%n", "%ct", "Essencial", "Usada", "Pratica", "Aventureira",
         "Rara", "%ef Fina", "Nova", "Desenterrada", "Vintage", "Imperial",
         "Elite", "Barata", "%ef Geral", "Basica", "Draconica",
         "%ef Profissional", "%ef de Qualidade"],
        "EquipmentPrefixes",
    )
    patch_array(
        data,
        ["Supply Store", "Gear Store", "Equipment Store", "Sundries",
         "Weaponry Store", "Tool Store", "Accouterments", "Provisions",
         "Merchandise", "Armaments"],
        122,
        ["Mercearia", "Selaria", "Armaria", "Bugigangaria", "Espadaria",
         "Ferramentaria", "Correaria", "Provisoes", "Mercancia", "Panoplia"],
        "EquipmentSuffixes",
    )


def apply_locations(data: bytearray) -> None:
    # RulerTitles: 14 items, 96-byte combined span (ends exactly where
    # KeyNames begins) - zero slack. Emperor/Empress -> Czar/Czarina
    # (shorter loanword synonym, user's choice) instead of
    # Imperador/Imperatriz, which alone don't fit; Lord kept as the
    # English spelling (drops the "e" of "Lorde") for the last needed
    # byte - everything else translates in full, correct Portuguese.
    patch_array(
        data,
        [
            "Lord", "Duke", "Baron", "Count", "Prince", "King", "Emperor",
            "Lady", "Duchess", "Baroness", "Countess", "Princess", "Queen", "Empress",
        ],
        96,
        [
            "Lord", "Duque", "Barao", "Conde", "Principe", "Rei", "Czar",
            "Dama", "Duquesa", "Baronesa", "Condessa", "Princesa", "Rainha", "Czarina",
        ],
        "RulerTitles",
    )

    # ItemConditionNames: 8 items, 63-byte combined span (ends exactly
    # where "Potion" - UnidentifiedPotionName - begins) - zero slack.
    patch_array(
        data,
        ["Broken", "Useless", "Battered", "Worn", "Used", "Slightly Used", "Almost New", "New"],
        63,
        ["Quebrado", "Inutil", "Amassado", "Gasto", "Usado", "PoucoUsado", "QuaseNovo", "Novo"],
        "ItemConditionNames",
    )

    # MainQuestItemNames: 8 items, 81-byte combined span (ends exactly
    # where "fanfare2.voc" begins) - zero slack. "Tablet" repeats 3x
    # (the main quest's Tablet of the times, referenced at different
    # points); "Selene"/"Gharen" are proper nouns, kept untranslated.
    patch_array(
        data,
        [
            "Parchment", "Tablet piece", "Selene's heart", "Tablet",
            "Diamond", "map", "Tablet", "Hammer of Gharen",
        ],
        81,
        [
            "Pergaminho", "Fragmento", "CoracaoSelene", "Tabuleta",
            "Diamante", "mapa", "Tabuleta", "MarteloGharen",
        ],
        "MainQuestItemNames",
    )


def apply_services_menus(data: bytearray) -> None:
    """The Services menus (Equipment shop, Mages Guild, Tavern, Temple,
    Citizen dialogue) are built almost entirely out of short
    accelerator-key buttons (see accel_bytes/patch_button) - each an
    independently fixed-size field the exact same length as the
    English word, no slack at all. Portuguese is routinely longer, so
    these are heavily abbreviated (Buy -> Cmp, Repair -> Reparo, etc.)
    - reviewed and chosen together with the user, one full menu at a
    time, checking for accelerator-letter collisions within each
    on-screen menu along the way (only one found: Weapon/Armor would
    both highlight "A" as "Arma"/"Armdr", so Armor's highlight moves to
    its second letter "r" - the same trick the original game itself
    uses for Equipment's Sell/Steal and Citizen's Who-are-you/Where-is)."""
    # --- Equipment shop ---
    patch_button(data, 0x44497, b"\t\xc0B\t\xd4uy\r\x00", "Cmp", "Equipment.Buy")
    patch_button(data, 0x444a0, b"\t\xc0S\t\xd4ell\r\x00", "Vend", "Equipment.Sell")
    patch_button(data, 0x444aa, b"\t\xc0R\t\xd4epair\r\x00", "Reparo", "Equipment.Repair")
    patch_button(data, 0x444b6, b"\t\xd4S\t\xc0t\t\xd4eal\r\x00", "Furto", "Equipment.Steal")
    patch_button(data, 0x444c3, b"\t\xc0E\t\xd4xit\r\x00", "Sair", "Equipment.Exit")
    patch_button(data, 0x444ee, b"\t\xc0W\t\xd4eapon\r\x00", "Arma", "Equipment.BuyWeapons")
    # Collides with Weapon/"Arma" on the highlighted letter (both A) -
    # the 2nd-letter disambiguation trick (like Steal above) needs 2
    # more bytes than this field's budget allows, so this one letter
    # collision is accepted as-is (the original game itself tolerates
    # an equivalent case: Mages Guild's Spellmaker/Steal both highlight "S").
    patch_button(data, 0x444fa, b"\t\xc0A\t\xd4rmor\r\x00", "Armdr", "Equipment.BuyArmor")
    patch_button(data, 0x44586, b"\t\xc0Y\t\xd4es\r\x00", "Sim", "Equipment.SellYes")
    patch_button(data, 0x4458f, b"\t\xc0N\t\xd4o\r\x00", "No", "Equipment.SellNo")

    # --- Mages Guild ---
    patch_button(data, 0x428d1, b"\t\xc0B\t\xd4uy\r\x00", "Cmp", "MagesGuild.Buy")
    patch_button(data, 0x428da, b"\t\xc0D\t\xd4etect Magic\r\x00", "Identificar", "MagesGuild.DetectMagic")
    patch_button(data, 0x428ec, b"\t\xc0S\t\xd4pellmaker\r\x00", "Feiticaria", "MagesGuild.Spellmaker")
    patch_button(data, 0x42947, b"\t\xc0S\t\xd4teal\r\x00", "Furto", "MagesGuild.Steal")
    patch_button(data, 0x42952, b"\t\xc0E\t\xd4xit\r\x00", "Sair", "MagesGuild.Exit")
    patch_button(data, 0x429e7, b"\t\xc0P\t\xd4otions\r\x00", "Pocoes", "MagesGuild.PickPotions")
    patch_button(data, 0x429f4, b"\t\xc0M\t\xd4agic items\r\x00", "Itens Magia", "MagesGuild.PickMagicItems")
    patch_button(data, 0x42a05, b"\t\xc0S\t\xd4pells\r\x00", "Magias", "MagesGuild.PickSpells")

    # --- Tavern ---
    patch_button(data, 0x42c5f, b"\t\xc0B\t\xd4uy Drinks\r\x00", "Comprar", "Tavern.BuyDrinks")
    patch_button(data, 0x42c6f, b"\t\xc0G\t\xd4et a Room\r\x00", "Alugar", "Tavern.GetARoom")
    patch_button(data, 0x42c7f, b"\t\xc0S\t\xd4neak into a Room\r\x00", "Furtar Quarto", "Tavern.SneakIntoARoom")
    patch_button(data, 0x42c96, b"\t\xc0R\t\xd4umors\r\x00", "Boatos", "Tavern.Rumors")
    patch_button(data, 0x42ca2, b"\t\xc0E\t\xd4xit\r\x00", "Sair", "Tavern.Exit")

    # --- Temple ---
    patch_button(data, 0x42f74, b"\t\xc0B\t\xd4less\r\x00", "Benca", "Temple.Bless")
    patch_button(data, 0x42f7f, b"\t\xc0C\t\xd4ure\r\x00", "Cura", "Temple.Cure")
    patch_button(data, 0x42f89, b"\t\xc0H\t\xd4eal\r\x00", "Vida", "Temple.Heal")
    patch_button(data, 0x42f93, b"\t\xc0E\t\xd4xit\r\x00", "Sair", "Temple.Exit")

    # --- Citizen dialogue ---
    patch_button(data, 0x43f40, b"\t\xc0W\t\xd4ho are you?\r\x00", "Quem es tu?", "Citizen.WhoAreYou")
    patch_button(data, 0x43f52, b"\t\xd4W\t\xc0h\t\xd4ere is...\r\x00", "Onde e...", "Citizen.WhereIs")
    patch_button(data, 0x43f65, b"\t\xc0R\t\xd4umors\r\x00", "Boatos", "Citizen.Rumors")
    patch_button(data, 0x43f71, b"\t\xc0E\t\xd4xit\r\x00", "Sair", "Citizen.Exit")
    patch_button(data, 0x43f92, b"\t\xc0G\t\xd4eneral\r\x00", "Geral", "CitizenRumors.General")
    patch_button(data, 0x43f9f, b"\t\xc0W\t\xd4ork\r\x00", "Trab", "CitizenRumors.Work")


def apply_services_text(data: bytearray) -> None:
    """The rest of the Services section: flavor text and modal titles,
    which (unlike the accelerator buttons above) have real slack to
    work with, so these translate close to in full rather than needing
    heavy abbreviation. Modal titles ("MENU  OPTIONS" etc.) repeat
    verbatim across several menus (Equipment/MagesGuild/Tavern/Temple
    all share the exact same "\\t`MENU  OPTIONS\\r" bytes) so they're
    patched by absolute offset, like the buttons above, not by search."""
    patch_at(data, 0x44474, b"\t`MENU  OPTIONS\r", "\t`MENU  OPCOES\r", "EquipmentModalTitle")
    patch_at(data, 0x444d5, b"\t`BUY  OPTIONS\r", "\t`CMP OPCOES\r", "EquipmentBuyModalTitle")
    patch_at(data, 0x44529, b"You successfully stole a %s.",
             "Furtaste %s com sucesso.", "EquipmentStealSuccess")
    patch_at(
        data, 0x44546, b"\t`Your %s is equipped.\r\t`Do you still want to sell it?",
        "\t`Teu %s esta equipado.\r\t`Queres mesmo vende-lo?",
        "EquipmentItemEquippedWhenSelling",
    )

    patch_at(data, 0x428ae, b"\t`MENU  OPTIONS\r", "\t`MENU  OPCOES\r", "MagesGuildModalTitle")
    patch_at(data, 0x429cd, b"\t`PICK  ITEM\r", "\t`PEGAR ITEM\r", "MagesGuildPickItemModalTitle")
    patch_at(data, 0x4295c, b"You already know what that is!",
             "Ja sabes o que isso e!", "MagesGuildItemAlreadyIdentified")
    patch_at(
        data, 0x4297b, b"I can tell you if that is magical, but it\r will cost you %lu gold.",
        "Posso dizer se isso e magico, mas\r vai custar %lu moedas.",
        "MagesGuildItemIdentifyCost",
    )

    patch_at(data, 0x42c3c, b"\t`MENU  OPTIONS\r", "\t`MENU  OPCOES\r", "TavernModalTitle")
    patch_at(data, 0x42d51, b"Rooms Available", "Quartos Livres", "TavernRoomsAvailable")
    patch_at(data, 0x42d61, b"You are unsuccessful...", "Nao tiveste sucesso...", "TavernSneakIntoRoomUnsuccessful")
    patch_at(data, 0x42d9e, b"How many days are you staying?         ",
             "Quantos dias vais ficar?", "TavernRoomRentNumberOfDays")
    patch_at(
        data, 0x42dc6, b"You successfully got into a room...\rThe %s is yours for the next 24 hours.",
        "Entraste no quarto com sucesso...\rO %s e teu pelas proximas 24 horas.",
        "TavernSneakIntoRoomSuccessful",
    )
    patch_at(data, 0x42e1e, b"\t\xfcThe cost is %d gold\rDo you accept?\r",
             "\t\xfcCusta %d moedas\rAceitas?\r", "TavernRoomRentalCost")
    patch_at(
        data, 0x42e44, b"\t`You only have %d remaining hours.\r\t`Rest this long?",
        "\t`So tens %d horas restantes.\r\t`Descansar assim?",
        "TavernRoomRentedRemainingHours",
    )
    patch_at(data, 0x42eaf, b"You finish the %s, thankful for a safe haven...",
             "Terminas %s, grato por um abrigo seguro...", "TavernConsumeDrink")
    patch_at(
        data, 0x42efb, b"Today you can have the room of your choice\rfree of charge for the next 24 hours.",
        "Hoje podes ter o quarto que quiseres\rde graca pelas proximas 24 horas.",
        "TavernFreeRoom",
    )

    patch_at(data, 0x42f54, b"\t`MENU  OPTIONS\r", "\t`MENU  OPCOES\r", "TempleModalTitle")
    patch_at(data, 0x42fa3, b"Receive our blessings...", "Recebe nossas bencaos...", "TempleReceiveBlessing")
    patch_at(data, 0x43026, b"Curing %s...", "Curando %s..", "TempleReceiveCuring")
    patch_at(data, 0x42fbc, b"%s, thou art healed...", "%s, estas curado...", "TempleReceiveHealing")
    patch_at(data, 0x42fd3, b"%s is in perfect condition...",
             "%s esta em otima forma...", "TemplePlayerIsFullHealth")
    patch_at(data, 0x42ff7, b"How much do you wish to donate?         ",
             "Quanto desejas doar?", "TempleDonationAmount")
    patch_at(data, 0x4306c, b"We humbly beg your forgivness for we cannot cure %s...",
             "Perdao, mas nao podemos curar %s...", "TemplePlayerIsNotDiseased")
    patch_at(data, 0x430a9, b"This service will cost %d gold. \rDo you accept?\r",
             "Este servico custa %d moedas. \rAceitas?\r", "TempleServiceCost")

    patch_at(data, 0x43f23, b"\t`ASK ABOUT ?\r", "\t`PERGUNTAR ?\r", "CitizenModalTitle")
    patch_at(data, 0x43f7b, b"\t`Rumor Type\r", "\t`Tipo Boato\r", "CitizenRumorsModalTitle")
    patch_at(data, 0x43fa9, b"I'm not sure. Try asking someone outside.",
             "Nao sei. Tenta perguntar la fora.", "CitizenRumorsModalWorkAskOutside")
    patch_at(data, 0x43eb0, b"I have no idea. Try asking in town.",
             "Nao faco ideia. Pergunta na cidade.", "CitizenRumorsModalWorkAskInTown")

    patch_at(data, 0x4050e, b"Gold left : ", "Moedas: ", "PlayerGoldRemaining")


def apply_item_actions(data: bytearray) -> None:
    """Drop/equip messages and the item-detail tooltip lines (weight,
    condition, damage, AR bonus, charges/uses left) - "AR" (Armor
    Rating, the game's own defense stat) kept untranslated as a game
    mechanic abbreviation, same treatment as e.g. "HP" would get."""
    patch_at(data, 0x36368, b"Do you wish to drop\rthe %s?\r", "Desejas largar\ro %s?\r", "DropItem")
    patch_at(data, 0x38184, b"This item will be lost here.\rDrop anyway?\r",
             "Perderas este item.\rLargar mesmo assim?\r", "DropItemPermanent")
    patch_at(data, 0x381af, b"There is no room to drop this here.\r",
             "Nao ha espaco para largar isto.\r", "DropItemNoRoom")
    patch_at(data, 0x3820e, b"This item can't be dropped.\r", "Nao podes largar isto.\r", "DropItemNotDroppable")
    patch_at(
        data, 0x38253, b"This item is needed to\rcomplete your quest...\rSee your logbook...\r",
        "Item necessario para\rcompletar tua missao...\rVe teu diario...\r",
        "DropItemRequiredByQuest",
    )
    patch_at(data, 0x381d4, b"You can only equip one %s.\r", "So podes equipar um %s.\r", "AlreadyEquippedItem")
    patch_at(data, 0x381f0, b"This item can't be equipped.\r", "Nao podes equipar isto.\r", "UnequippableItem")
    patch_at(data, 0x3634b, b"%ss cannot equip this item.\r", "%ss nao podem equipar isto.\r", "ClassForbiddenItem")

    patch_at(data, 0x39423, b"%d kgs\r", "%d kg\r", "ItemDetailWeight")
    patch_at(data, 0x3942b, b"Condition: %s\r", "Condicao: %s\r", "ItemDetailCondition")
    patch_at(data, 0x3943a, b"Damage: %d - %d  Weight: ", "Dano: %d - %d  Peso: ", "ItemDetailWeapon")
    patch_at(data, 0x39454, b"-%d to AR   Weight: ", "-%d a AR   Peso: ", "ItemDetailArmor")
    patch_at(data, 0x39487, b"-%d to AR   Weight: n/a\r", "-%d a AR   Peso: n/a\r", "ItemDetailArmorNoWeight")
    patch_at(data, 0x39469, b"%d charge(s) left\r", "%d carga(s)\r", "ItemDetailChargesLeft")
    patch_at(data, 0x3947c, b"+%d to %s\r", "+%d a %s\r", "ItemDetailStatBonus")
    patch_at(data, 0x394a0, b"%d use(s) left...\r", "%d uso(s)...\r", "ItemDetailUsesLeft")
    patch_at(
        data, 0x394b3, b"1 use left    Weight: n/a\rCondition: Fragile\r",
        "1 uso restante    Peso: n/a\rCondicao: Fragil\r",
        "ItemDetailPotion",
    )
    patch_at(
        data, 0x38296, b"You currently have\r%d piece(s) of the\rStaff of Chaos.\r",
        "Atualmente tens\r%d pedaco(s) do\rCajado do Caos.\r",
        "StaffPieceCount",
    )

    patch_at(data, 0x40736, b"%u gold piece", "%u moeda", "GoldPiece")
    patch_at(data, 0x40744, b"Bag of %u gold pieces", "Saco de %u moedas", "BagOfGoldPieces")


def apply_travel(data: bytearray) -> None:
    # LocationFormatTexts: 3 items, 69-byte combined span (ends 1 byte
    # before DayPrediction begins - that stray byte is unrelated,
    # non-string data, left untouched, same pattern as MonthNames).
    patch_array(
        data,
        ["%s in %s Province.\r", "The %s in the %s.\r", "The %s of %s\rin %s Province.\r"],
        69,
        ["%s na Provincia de %s.\r", "O %s no %s.\r", "O %s de %s\rna Provincia de %s.\r"],
        "LocationFormatTexts",
    )

    patch_at(data, 0x376f3, b"Based on the current weather,\r", "Com base no clima atual,\r", "DayPrediction")
    patch_at(data, 0x37738, b"The total distance is %d km.\r",
             "A distancia total e %d km.\r", "DistancePrediction")
    patch_at(data, 0x37756, b"You should arrive by\r", "Deves chegar por\r", "ArrivalDatePrediction")
    patch_at(data, 0x3776c, b"You are already in %s.\r", "Ja estas em %s.\r", "AlreadyAtDestination")
    patch_at(
        data, 0x37784, b"You can not travel until you have chosen\ra destination city, town, or village.\r",
        "Nao podes viajar sem escolher\ruma cidade, vila ou aldeia destino.\r",
        "NoDestination",
    )
    patch_at(
        data, 0x4251d,
        b"Considering your condition, you may not survive\rthis journey. Do you wish to attempt the journey?\r",
        "Dado teu estado, podes nao sobreviver\ra esta viagem. Desejas tentar mesmo assim?\r",
        "DiseaseRiskOfDeath",
    )
    patch_at(data, 0x40569, b"Yes\r", "Sim\r", "DiseaseRiskOfDeathYes")
    patch_at(data, 0x4056e, b"No\r", "N\r", "DiseaseRiskOfDeathNo")

    patch_at(data, 0x37665, b"You have arrived in ", "Chegaste em ", "ArrivalPopUpLocation")
    patch_at(data, 0x3767a, b"The date is\r", "A data e\r", "ArrivalPopUpDate")
    patch_at(data, 0x37688, b"It took %d days to reach your goal. ",
             "Levaste %d dias para chegar. ", "ArrivalPopUpDays")
    patch_at(data, 0x42642, b"the Imperial City. ", "a Cidade Imperial. ", "ArrivalCenterProvinceLocation")
    patch_at(data, 0x424d1, b"Enter the name of the city or press Enter key for a list.",
             "Digita o nome da cidade ou aperta Enter para uma lista.", "SearchTitleText")

    patch_at(data, 0x4170d, b"You cannot travel from here.", "Nao podes viajar daqui.", "NotAllowedToTravel")
    patch_at(data, 0x41756, b"You cannot travel from a boat...",
             "Nao podes viajar de barco...", "NotAllowedToTravelInBoat")
    patch_at(data, 0x4172a, b"You cannot travel when monsters are near...",
             "Nao podes viajar com monstros por perto...", "NotSafeToTravel")


def apply_thieving(data: bytearray) -> None:
    # 6 items, 100-byte combined span (ends where the binary
    # StaffDungeonSplashIndices table begins).
    patch_array(
        data,
        [
            "Failure...", "Success...", "Critical strike...",
            "Open locked chest ?", "Lock won't budge...", "The chest opens...",
        ],
        100,
        [
            "Falha", "Sucesso", "Golpe Critico",
            "Abrir bau trancado?", "Fechadura nao cede...", "O bau abre...",
        ],
        "Thieving",
    )


def apply_dialogue(data: bytearray) -> None:
    # Subject/Object/Possessive pronouns are used as %s-style
    # fill-ins in citizen dialogue templates - Portuguese doesn't have
    # a clean word-for-word substitute for English's he/it distinction
    # (and the fixed budgets here are extremely tight), so this uses
    # the closest practical stand-ins rather than "correct" grammar in
    # every possible sentence this could land in.
    patch_array(data, ["he", "she", "it"], 10, ["ele", "ela", "o"], "SubjectPronouns")
    patch_array(data, ["him", "her", "it"], 11, ["ele", "ela", "o"], "ObjectPronouns")
    patch_array(data, ["his", "her", "its"], 12, ["seu", "sua", "seu"], "PossessivePronouns")

    # CardinalDirections: 8 items, 62-byte combined span (ends exactly
    # where an unrelated quest-type word list - "deliver something"
    # etc - begins).
    patch_array(
        data,
        ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"],
        62,
        ["norte", "nordeste", "leste", "sudeste", "sul", "sudoeste", "oeste", "noroeste"],
        "CardinalDirections",
    )

    patch_at(data, 0x43e9a, b"That's in the city...", "Isso e na cidade...", "DirectionIsCityOnly")

    # Two loose Citizen-dialogue lines that were missed in the first
    # Services pass (apply_services_menus/apply_services_text) - found
    # during the full audit of what's left in the exe.
    patch_find(data, b"You see a %s...", 16, "Ves um %s...\x00", "InspectedEntityName")
    patch_find(data, b"I don't deal in rumors...\r", 27,
               "Nao lido com boatos...\r\x00", "CitizenRumorsModalWorkNoRumors")

    # CitizenWhereIsOptions: the "Where is...?" submenu place-type list,
    # two variants (city vs. wilderness) with their own fixed-array
    # budgets - "Guilda dos Magos" fits both (barely, in Wilderness,
    # hence the full "Trabalho" and "Covil" instead of "Masmorra" there
    # to make room - reviewed word-by-word with the user).
    patch_array(
        data,
        ["Inn", "Temple", "Equipment Store", "Mages Guild", "Palace",
         "City gates", "Nearest Inn", "Nearest Temple", "Nearest Store"],
        98,
        ["Pousada", "Templo", "Loja", "Guilda dos Magos", "Palacio",
         "Portao", "Pousada Perto", "Templo Perto", "Loja Perto"],
        "CitizenWhereIsOptionsCity",
    )
    patch_array(
        data,
        ["Inn", "Temple", "Equipment Store", "Mages Guild", "Palace",
         "Work", "Nearest Inn", "Nearest Temple", "Nearest Dungeon"],
        94,
        ["Pousada", "Templo", "Loja", "Guilda dos Magos", "Palacio",
         "Trabalho", "Pousada Perto", "Templo Perto", "Covil Perto"],
        "CitizenWhereIsOptionsWilderness",
    )


def apply_misc_text(data: bytearray) -> None:
    """Small leftover fields found during the full audit of the exe,
    each independent of the others - grouped here rather than shoved
    into a thematically-unrelated function."""
    # EffectNames: 8 items, 72-byte combined span (ends exactly where
    # DiseaseNames - already translated elsewhere - begins).
    patch_array(
        data,
        ["Diseased", "Poisoned", "Cursed", "Blessed", "Fortified", "Drunk",
         "Paralyzed", "Regenerating"],
        72,
        ["Doente", "Envenenado", "Maldito", "Bento", "Forte", "Bebado",
         "Paralisado", "Regenerando"],
        "EffectNames",
    )

    patch_at(data, 0x41830, b"Potion", "Pocao\x00", "UnidentifiedPotionName")
    patch_find(data, b"Staff Pieces (%u) ", 19, "Pecas Cajado (%u) \x00", "StaffPieces")

    # MagesGuildMenuName: the guild's own fixed display name - only a
    # 12-byte budget (was "Mages Guild"), too tight for the fuller
    # "Guilda dos Magos" used in CitizenWhereIsOptions above.
    patch_at(data, 0x42911, b"Mages Guild\x00", "Guilda Mago\x00", "MagesGuildMenuName")


def apply_status_flavor(data: bytearray) -> None:
    # LockDifficultyMessages: 14 items (13 flavor comments on the
    # lock-vs-skill gap, +1 special case for magically-held locks),
    # 568-byte combined span (there's one more trailing empty entry
    # after that - a genuine 569th byte of unused padding room, not
    # touched here since patch_array already zero-pads any leftover
    # span automatically).
    patch_array(
        data,
        [
            "This lock has nothing to fear from you...",
            "It'd be a miracle if you picked this lock...",
            "This lock looks to be beyond your skills...",
            "You doubt your ability to open this lock...",
            "This lock looks difficult...",
            "You would be challenged by this lock...",
            "This lock would prove a good challenge...",
            "You think you should be able to pick this lock...",
            "This lock seems relatively easy...",
            "You are amused by this lock...",
            "You laugh at the amateur quality of this lock...",
            "You see a pathetic excuse for a lock...",
            "This lock is an insult to your abilities...",
            "This is a magically held lock...",
        ],
        568,
        [
            "Esta fechadura nada teme de ti...",
            "Seria um milagre se abrisses esta fechadura...",
            "Esta fechadura parece alem de tuas habilidades...",
            "Duvidas de tua capacidade de abrir isto...",
            "Esta fechadura parece dificil...",
            "Serias desafiado por esta fechadura...",
            "Esta fechadura seria um bom desafio...",
            "Achas que consegues abrir esta fechadura...",
            "Esta fechadura parece bem facil...",
            "Estas divertido com esta fechadura...",
            "Ris da qualidade amadora desta fechadura...",
            "Ves uma fechadura patetica...",
            "Esta fechadura insulta tuas habilidades...",
            "Esta fechadura e presa por magia...",
        ],
        "LockDifficultyMessages",
    )

    patch_at(
        data, 0x434e0, b"You are so fatigued that you\rsimply drop where you stand.\r\nOne hour later....\r",
        "Estas tao exausto que\rsimplesmente caes onde estas.\r\nUma hora depois....\r",
        "StaminaExhaustedRecover",
    )
    patch_at(data, 0x4356a, b"You drop from exhaustion and\rquickly fall prey to monsters....\r",
             "Caes de exaustao e\rrapidamente viras presa de monstros....\r", "StaminaExhaustedDeath")
    patch_at(data, 0x4352f, b"Fatigue overcomes you and\rsends you to a watery grave....\r",
             "A fadiga te vence e\rte envia a um tumulo aquatico....\r", "StaminaDrowning")
    patch_at(
        data, 0x43327, b"Paralysis grips your body and\nand you succumb to the dark waters\nof your grave...",
        "Paralisia toma teu corpo e\ne sucumbes as aguas escuras\nde teu tumulo...",
        "StaminaDrowningParalyzed",
    )
    patch_at(data, 0x40670, b"The %s has nothing usable.", "O %s nao tem nada util.", "EnemyCorpseEmptyInventory")
    patch_at(data, 0x42128, b"On this body you find %d gold pieces.",
             "Neste corpo encontras %d moedas.", "CitizenCorpseGold")


def apply_citizen_rumor_generator(data: bytearray) -> None:
    """DISABLED - see main(), this function is no longer called.

    "NeighborWarPeace" (0x39B0C) turned out to be a 409-byte procedural
    NPC-description generator sitting at that address (6 word-groups
    separated by literal \\x08 bytes, 2 entries with a leading 2-byte
    control-code prefix - \\x05\\x02 before "figure", \\x03\\x05 before
    "Rogue" - whose meaning was never decoded), NOT the simple 2-item
    field its acdExeStrings.txt name suggests. Translating the whole
    409-byte block (same total size, same group/prefix structure,
    verified byte-for-byte against the pristine original before
    writing) crashed OpenTESArena during BinaryAssetLibrary init
    ("Buffer.h index >= 0" assertion) - confirmed by bisection
    (disabling just this call made the crash go away).

    Root cause: OpenTESArena's own ExeData.h declares this field as
    `std::string neighborWarPeace[2]` - it only ever reads the first 2
    null-terminated strings (war/peace) from this address and never
    looks at anything past them. Something else - not documented in
    acdExeStrings.txt, presumably a raw/hardcoded offset elsewhere in
    the executable - reads further into this same 409-byte region for
    the rest of that rumor-generator content, and this function's
    restructuring broke whatever assumption that other reader makes.
    Since OpenTESArena itself never surfaces this content to the
    player anyway (per its own 2-item struct), there's no payoff for
    the risk - left untranslated (English) rather than chasing down
    the undocumented reader just to reintroduce this crash. Kept here,
    disabled, in case a future session wants to dig further with more
    of the executable disassembled."""
    original = (
        b"war\x00peace\x00\x08\x00rather\x00very\x00slightly\x00highly\x00notably\x00remarkably\x00"
        b"surpassingly\x00singularly\x00\x08\x00mysterious\x00influential\x00impatient\x00aggressive\x00"
        b"peculiar\x00enigmatic\x00wealthy\x00well-known\x00\x05\x02figure\x00character\x00individual\x00"
        b"person\x00aristocrat\x00fellow\x00man\x00woman\x00lady\x00\x03\x05Rogue\x00Old\x00Mad\x00Lord\x00"
        b"Sir\x00Master\x00Brother\x00Father\x00Lady\x00Lady\x00Mistress\x00Sister\x00Mother\x00\x08\x00"
        b"The Wicked\x00The Dark\x00of %cn2\x00of the House of %dnl\x00of the %tem\x00the Warrior\x00"
        b"the Mage\x00the %ra\x00"
    )
    assert len(original) == 409, len(original)
    replacement = (
        "guerra\x00paz\x00\x08\x00meio\x00muito\x00levemente\x00muito\x00notavelmente\x00notavelmente\x00"
        "surpreendentemente\x00singularmente\x00\x08\x00misterioso\x00influente\x00impaciente\x00agressivo\x00"
        "peculiar\x00enigmatico\x00rico\x00famoso\x00\x05\x02figura\x00personagem\x00individuo\x00"
        "pessoa\x00aristocrata\x00sujeito\x00homem\x00mulher\x00dama\x00\x03\x05Ladino\x00Velho\x00Louco\x00"
        "Lorde\x00Sr\x00Mestre\x00Irmao\x00Padre\x00Dama\x00Dama\x00Senhora\x00Irma\x00Freira\x00\x08\x00"
        "O Perverso\x00O Sombrio\x00de %cn2\x00da Casa de %dnl\x00do %tem\x00o Guerreiro\x00"
        "o Mago\x00o %ra\x00"
    ).encode("latin-1")
    assert len(replacement) == 409, len(replacement)
    patch_at(data, 0x39B0C, original, replacement.decode("latin-1"), "CitizenRumorGenerator")


def apply_equipment(data: bytearray) -> None:
    start = data.find(b"Lord's Mail")
    end_needle = b"Potion of Free Action\x00"
    end = data.find(end_needle)
    if start == -1 or end == -1:
        raise ValueError("equipment region: anchors not found")
    end += len(end_needle)

    pos = start
    patched = 0
    while pos < end:
        nul = data.find(b"\x00", pos, end)
        if nul == -1:
            break
        run = data[pos:nul]
        try:
            text = run.decode("latin-1")
        except UnicodeDecodeError:
            text = None
        if text is not None and text in EQUIPMENT_TRANSLATIONS:
            budget = nul + 1 - pos
            new_text = EQUIPMENT_TRANSLATIONS[text]
            b = new_text.encode("latin-1") + b"\x00"
            if len(b) > budget:
                raise ValueError(f"equipment: {text!r} -> {new_text!r} needs {len(b)}, budget {budget}")
            b = b + b" " * (budget - len(b))
            data[pos:pos + budget] = b
            patched += 1
        pos = nul + 1
    print(f"  equipment region: patched {patched} entries")


def main() -> None:
    print("Building translated ACD.EXE...")

    original = (ORIG_DIR / "ACD.EXE").read_bytes()
    decompressed = bytearray(unpk.unpack(original))
    print(f"  decompressed: {len(decompressed)} bytes")

    apply_character_creation(decompressed)
    apply_status_and_locations(decompressed)
    apply_calendar_and_camping(decompressed)
    # DIAGNOSTIC: apply_entities still disabled (confirmed the crash is
    # somewhere in apply_entities+apply_races together); re-enabling
    # just apply_races to narrow it down further.
    apply_entities(decompressed)
    apply_races(decompressed)
    apply_city_generation(decompressed)
    apply_locations(decompressed)
    apply_services_menus(decompressed)
    apply_services_text(decompressed)
    apply_item_actions(decompressed)
    apply_travel(decompressed)
    apply_thieving(decompressed)
    apply_dialogue(decompressed)
    apply_misc_text(decompressed)
    apply_status_flavor(decompressed)
    # apply_citizen_rumor_generator(decompressed)  # temporarily disabled - see its own docstring
    apply_equipment(decompressed)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "ACD_unpacked.bin").write_bytes(decompressed)
    print(f"  wrote {WORK_DIR / 'ACD_unpacked.bin'} (patched, still decompressed)")

    new_exe = pk.rebuild_exe(original, bytes(decompressed))
    print(f"  recompressed: {len(new_exe)} bytes (original: {len(original)})")

    redecoded = unpk.unpack(new_exe)
    if redecoded != bytes(decompressed):
        raise RuntimeError("round-trip check failed: recompressed ACD.EXE doesn't decode back to the patched content")
    print("  round-trip verified: recompressed ACD.EXE decodes back to the patched content exactly")

    (WORK_DIR / "ACD.EXE").write_bytes(new_exe)
    print(f"  wrote {WORK_DIR / 'ACD.EXE'}")

    opentes_dir = BUILD_DIR / "opentes"
    opentes_dir.mkdir(parents=True, exist_ok=True)
    (opentes_dir / "ACD.EXE").write_bytes(new_exe)
    print(f"  wrote {opentes_dir / 'ACD.EXE'} (PKLITE-compressed, works only "
          f"in OpenTESArena - see pipeline-acd-exe.md)")

    unpacked_template = (ORIG_DIR / "ACD_UNPACKED_TEMPLATE.EXE").read_bytes()
    dosbox_exe = pk.rebuild_dosbox_exe(unpacked_template, bytes(decompressed))
    dosbox_dir = BUILD_DIR / "dosbox"
    dosbox_dir.mkdir(parents=True, exist_ok=True)
    (dosbox_dir / "ACD.EXE").write_bytes(dosbox_exe)
    print(f"  wrote {dosbox_dir / 'ACD.EXE'} (plain/uncompressed, works in "
          f"real DOSBox - PKLITE recompression hangs there, see pipeline-acd-exe.md)")

    print("Done.")


if __name__ == "__main__":
    main()
