"""Bakes the Portuguese translation into the "@TEXT" section of Arena's
.INF dungeon/location scripts bundled inside GLOBAL.BSA - the flavor
text shown while exploring (signs, notes, ambient descriptions,
riddles). The rest of an .INF (floor/wall textures, monster/item
placement) is left completely untouched.

Every .INF inside GLOBAL.BSA is XOR-"encrypted" with a fixed key (see
inf_codec.py) - trivially reversible, since XOR is its own inverse.

Many riddles rely on English wordplay that has no literal Portuguese
equivalent (a letter-riddle whose answer is "E" because of English
spelling; a compound-word riddle for "footstep" = foot + step). Those
are adapted into an equivalent Portuguese wordplay riddle with the same
narrative role (see DAGOTH3_RIDDLE and ELDEN2_FOOTSTEP_RIDDLE below) -
flagged clearly for the user to review, since this is a judgment call
rather than a literal translation.

Reads the pristine copies split_bsa.py already extracted into
"Minha tradução/GLOBAL_parts/" (run that first) and writes the
translated result as PLAIN, READABLE text (accents kept, not encrypted)
into "Minha tradução/GLOBAL_parts/legivel/<nome>". Accent-stripping and
XOR re-encryption both happen later, in compile_inf.py, the same way
every other translated text file in this project only loses its accents
at the very last "build" step (see build.py) - never before that. That
script also compiles the readable text back into the actual
"GLOBAL_parts/<nome>" (the same place split_bsa.py extracted it), which
merge_bsa.py then packs into a full GLOBAL.BSA.

Usage: python3 scripts/build_bsa_inf.py
"""
from pathlib import Path

from inf_codec import join_sections, parse_text_section, split_sections, xor_crypt

ROOT_DIR = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT_DIR / "Minha tradução" / "GLOBAL_parts"
LEGIVEL_DIR = PARTS_DIR / "legivel"

Translation = tuple[str | list[str] | None, list[str] | None]


def block_id(header: str) -> int:
    return int(header.strip().split()[-1])


# --- Blocks reused byte-for-byte (well, word-for-word) across several
# .INF files - translated once here and merged into each file's dict
# below, so the wording stays consistent everywhere it repeats. ---

RESTRICTED_AREA: dict[int, Translation] = {
    0: ("Área restrita! Somente pessoal autorizado...", None),
    1: ("O Salão Principal", None),
}

IMPERIAL_TOWER: dict[int, Translation] = {
    0: ("Os aposentos da Guarda Imperial.", None),
    1: ("O Salão Principal", None),
    2: ("Jagar Tharn te dá as boas-vindas, criança tola.", None),
    3: ("O Salão de Conferências", None),
}

# Shared by AGTEMPL.INF (blocks 1-7) and MGTEMPL1/2.INF (also 1-7).
TEMPLE_COMMON: dict[int, Translation] = {
    1: ("Uma placa sobre a escada diz: Privado! Somente membros!", None),
    2: ("O fedor de comida apodrecida enche o ar.", None),
    3: ("Uma pequena placa adverte: MANTENHA-SE À ESQUERDA - SIGA PELA DIREITA", None),
    4: ("Uma placa sobre a porta diz: DETENÇÃO", None),
    5: ("Um odor úmido e bafiento enche esta área.", None),
    6: ("O chão aqui tem um padrão estranho...", None),
    7: ("Claramente algum tipo de ritual desagradável estava planejado para esta capela...", None),
}

HALLS_INSCRIPTION: dict[int, Translation] = {
    0: ("Há uma inscrição gravada aqui na pedra coberta de musgo - Theodorus.", None),
    1: (
        "Você entra na passagem secreta para o Salão do Colosso. O chão aqui está "
        "coberto por um mofo fino, arranhado por garras grandes e afiadas, e o ar "
        "está quente e úmido.",
        None,
    ),
}

SPHINX_RIDDLE: dict[int, Translation] = {
    0: (
        [
            "Responda-me isto, e prove teu engenho, pois um verdadeiro "
            "desafio é raro.",
            "Eu tenho o dobro da idade de três vezes a idade da Esfinge de "
            "Gazia, Agamamnus, dividido por um nono da idade da Esfinge de "
            "Canus, Igon, que deixou este mundo há vinte e seis anos.",
            "Qual é então minha idade?",
            "Podes entrar livremente, criança. Mas fica avisado - há "
            "demônios lá dentro.",
            "Criança insolente, não podes entrar... Mas podes te juntar aos "
            "que vieram antes.",
        ],
        ["108", "cento e oito", "cento e 8"],
    ),
    1: (
        [
            "Eu sou o arquiteto deste inferno, cujo nome foi esquecido na "
            "poeira do tempo. Ainda assim, onde não há poeira, onde o rio "
            "falaria, ali está meu nome.",
            "Encontra este lugar e depois retorna, para me dizer meu nome. "
            "Só então poderás passar por esta porta.",
            "Qual é meu nome?",
            "Theodorus, Theodorus é meu nome. Passa, criança, e cuidado com "
            "os salões adiante.",
            "Esse não é meu nome. O homem mais sábio jamais adivinharia. "
            "Vasculha estes salões consagrados, purifica-te, mata aquilo "
            "que já está morto, então me dá o nome que é verdadeiro.",
        ],
        ["Theodorus"],
    ),
    2: (
        "Pedestais pairam no ar deste aposento, desafiando todas as leis. Teus "
        "sentidos ficam alertas ao cheiro acre de enxofre e ao zunido de asas de "
        "couro...",
        None,
    ),
}

STONEKEEP_PRISON: dict[int, Translation] = {
    0: ("As Prisões", None),
    1: ("O cheiro de mofo e decomposição sobe da masmorra inundada...", None),
    2: (
        "O baú está mofado, como se tivesse ficado submerso na água antes de ser "
        "trazido para cá.",
        None,
    ),
    3: (
        "Este cômodo, e outros próximos, já foram escritórios, mas a pilhagem e a "
        "decadência os deixaram meras cascas vazias...",
        None,
    ),
    4: (
        'Uma placa antiga e desbotada diz "O rei e o palácio estão perdidos. Nós, '
        'os últimos sobreviventes da corte de Stonekeep, seguimos rumo ao sul '
        'pelas cavernas dos goblins."',
        None,
    ),
    5: (
        'Uma placa antiga e desbotada diz "Estamos seguindo os túneis dos '
        'goblins rumo ao norte para fazer nossa última resistência."',
        None,
    ),
    6: (
        'Uma placa rachada, coberta de poeira, diz "Bem-vindo a Stonekeep. '
        'Entreguem todas as armas aos guardas, pois somos os guardiões da paz."',
        None,
    ),
    7: ("A Câmara Real", None),
}

GEMINI_PLACEHOLDER: dict[int, Translation] = {
    0: ("Olhe para esta linha. Elas podem ter várias linhas.", None),
    1: ("Aqui está um texto completamente diferente....", None),
    2: ("Texto final. Deixe uma linha em branco após a última entrada de texto. Seja breve.", None),
}


def T(prose: str | list[str], *answers: str) -> Translation:
    """prose is a single string for a block with one prose run, or a
    list with one entry per run (in order) for a block whose raw
    markers - '-', '`CORRECT'/'`WRONG', etc. - separate multiple
    distinct prose runs (see TextBlock._prose_run_spans in
    inf_codec.py). Passing one flat string for a multi-run block would
    silently misplace those markers relative to the translated text -
    build_one()'s call to block.render() raises ValueError if the
    counts don't match, precisely to catch that mistake."""
    return (prose, list(answers) if answers else None)


TRANSLATIONS: dict[str, dict[int, Translation]] = {
    "AGTEMPL.INF": {
        # The sign's original text is itself a garbled, torn-signage
        # joke that doesn't parse as real English either - kept as-is
        # rather than inventing a different-but-equally-meaningless
        # Portuguese scramble.
        0: ("Uma placa próxima, gasta e quase ilegível, diz: AGA  NU W LCO  S PI GRIMS ", None),
        **TEMPLE_COMMON,
        8: T(
            [
                "Responda este enigma e prossiga para dentro deste cofre,",
                "Eu estou todo dia em Elsweyr, e em Skyrim, às vezes exploro o "
                "mundo inteiro, desde o início dos tempos mantenho meu reinado, "
                "e assim será até o tempo não ser mais. Nunca em minha vida "
                "caminhei por jardim, campo ou parque, ainda assim todos eles "
                "ficam tristes e frios se eu não estiver lá e for noite...",
                "Resposta?",
                "Falaste bem. Entra...",
                "Nada acontece...",
            ],
            "sol", "o sol",
        ),
        9: (
            [
                "Você encontra um bilhete no corpo deste Cavaleiro,",
                "Você manterá esta fortaleza até meu retorno. Guarde bem os "
                "tesouros, ou perca sua vida... Sir Galandir...",
            ],
            None,
        ),
    },
    "BGATE2.INF": {
        0: T(
            [
                "Esta porta está lacrada. Uma pergunta está gravada acima dela. "
                "Que resposta você dá?",
                "O que é a coisa que vem em lençóis, mas não pode ser dobrada "
                "nem recolhida de novo?",
                "A porta agora está destrancada.",
                "Nada acontece.",
            ],
            "chuva", "a chuva",
        ),
    },
    "CASTLE.INF": RESTRICTED_AREA,
    "CRYPT1.INF": {
        0: (
            "Você está na Cripta dos Corações, um mundo de trevas e morte. O ar "
            "está parado, decomposto pelo tempo, e o cheiro de enxofre permeia o "
            "ambiente. Um vento quente parece vir de trás da esquina, ao sul...",
            None,
        ),
        1: (
            "Do outro lado do fluxo de lava há paredes de templo com inscrições "
            "que parecem torcer seus pensamentos mais básicos. O cheiro de morte "
            "paira no ar quente. Tambores podem ser ouvidos à distância...",
            None,
        ),
        2: (
            'Você está perto de um mausoléu. Uma inscrição rúnica diz, "Sir '
            'Culanthir - Que ele finalmente descanse." Os anos parecem ter '
            "enferrujado este portão de ferro. Até o chão está intocado. Seus "
            "passos levantam pequenas nuvens de poeira que pairam no ar parado e "
            "morto.",
            None,
        ),
        3: (
            "Este grande aposento está cheio de uma poça fervilhante de lava. À "
            "distância podem ser vistos vários blocos flutuantes, sustentados por "
            "algum tipo de magia. Talvez o campo de fogo possa, afinal, ser "
            "atravessado em segurança...",
            None,
        ),
        4: (
            "Você está perto das escadas que descem ainda mais nesta cripta dos "
            "mortos. Um ar frio sopra da abertura, trazendo consigo o cheiro de "
            "carne em decomposição...",
            None,
        ),
        5: (
            "Você depara com algo estranho. Humanos foram evidentemente mortos, "
            "cada um ao lado de uma pequena vela bruxuleante. No centro deste "
            "sacrifício bizarro há uma cripta fechada feita de pedra pesada...",
            None,
        ),
        6: (
            "No meio deste mar de lava há um templo. Você pode ver suas paredes "
            "gravadas com runas brilhando com o calor...",
            None,
        ),
    },
    "CRYPT3.INF": {
        0: (
            "Você entra no terceiro nível da Cripta dos Corações. As paredes "
            "estão cobertas por uma substância grudenta e fétida, parecida com "
            "muco. À distância podem ser ouvidos gritos de agonia...",
            None,
        ),
        1: ("Estas escadas parecem levar mais fundo na Cripta dos Corações...", None),
        2: ("Um vento fétido passa por você...", None),
        3: ("De algum lugar vem o cheiro de enxofre, e junto com ele uma rajada de ar quente...", None),
    },
    "CRYPT4.INF": {
        0: T(
            [
                "Poucos alcançaram estes salões sagrados, tolos corajosos que "
                "enfrentariam o enigma...",
                "Há algo, que nada é, mas tem um nome. Às vezes é alto e às "
                "vezes é baixo, ele tomba quando caímos, se junta à nossa "
                "brincadeira, e participa de todo jogo...",
                "Do que então eu falo?",
                "Estás correto, mortal. Prossiga ao teu destino...",
                "Pensa de novo, então fala com sabedoria...",
            ],
            "sombra", "tua sombra", "uma sombra", "minha sombra",
        ),
        1: (
            "Você está nos túmulos de heróis há muito mortos. Um gemido baixo "
            "pode ser ouvido por estes corredores abobadados...",
            None,
        ),
        2: ("Você vê a sexta peça do Cajado do Caos...", None),
        3: (
            "Você pode ver o que parece ser uma grande cripta ou templo bem no "
            "centro deste salão de abismos...",
            None,
        ),
    },
    "CRYSTAL1.INF": {
        3: ("Todos que entram aqui, abandonem a esperança...", None),
        4: (
            "Você entra nos salões da Torre de Cristal, recebido por sons e "
            "visões estranhas...",
            None,
        ),
    },
    "CRYSTAL3.INF": {
        0: ("Uma placa diz: O Bestiário - Seção 1", None),
        1: ("Uma placa diz: O Bestiário - Seção 2", None),
        2: ("Uma placa diz: O Bestiário - Seção 3", None),
        3: (
            "Um odor pesado e almiscarado flutua pelos corredores rústicos e "
            "esculpidos na rocha. À distância você pode ouvir o que soam como "
            "rosnados baixos...",
            None,
        ),
        4: (
            "O fedor de restos e excremento é quase insuportável. Perto dali você "
            "pode ouvir sons estranhos vindos do que parecem portas de cela...",
            None,
        ),
        5: ("Ratos", None),
        6: ("Goblins", None),
        7: ("Homem-Lagarto", None),
        8: (
            "Você de repente percebe que a garatuja ilegível pode ter sido um "
            "aviso em trollês...",
            None,
        ),
        9: ("Aviso de Lobo da Neve, o espécime tem ataque de sopro de gelo.", None),
        10: ("Orcs", None),
        11: ("Esqueleto", None),
        12: ("Minotauro", None),
        13: ("Aviso de Aranha, este espécime é altamente venenoso.", None),
        14: ("Aviso de Carniçal, altamente canibal. Não alimentar.", None),
        15: ("Aviso de Cão do Inferno, este espécime é altamente agressivo.", None),
        16: (
            "No corpo deste troll você encontra um mapa desenhado grosseiramente, "
            "obviamente deste nível. No canto SE há um grande 'x' vermelho. O "
            "mapa também mostra uma garatuja ilegível logo a NO deste aposento, "
            "marcando um local logo além da porta da cela...",
            None,
        ),
        17: ("Aviso de Zumbi, este espécime causa doenças.", None),
        18: ("Aviso de Espectro, o espécime tem habilidades de conjuração.", None),
        19: ("Aviso de Homúnculo, o espécime tem habilidades de conjuração.", None),
        20: ("Aviso de Golem de Gelo, este espécime tem uma aura de dano.", None),
        21: ("Aviso de Golem de Pedra, este espécime arremessa pedras.", None),
        22: ("Aviso de Demônio do Fogo, este guardião é extremamente perigoso.", None),
        23: ("Aviso de Medusa, ataque de olhar. Não encare.", None),
        24: (
            "Esta cela está vazia. Numa placa ao lado foi entalhado às pressas o "
            "seu nome. Parece que alguém estava esperando por você...",
            None,
        ),
        25: (
            "Você pode ver fossos atrás das criaturas. Deve ser isto que os "
            "guardiões trolls usam para alimentar os espécimes cativos...",
            None,
        ),
        29: ("Tubo de Alimentação 1. Cuidado: espécimes podem habitar estes túneis.", None),
        30: ("Tubo de Alimentação 2. Cuidado: espécimes podem habitar estes túneis.", None),
        31: ("Tubo de Alimentação 3. Cuidado: espécimes podem habitar estes túneis.", None),
        32: T(
            [
                "No chão há uma placa de pressão. Uma placa acima dela diz,",
                "Liberação de emergência das celas - Seções 1 e 2",
                "Pressionar a placa? (s/n)",
                "Pelos corredores você ouve o som de trancas se abrindo...",
                "Ocorre a você que liberar as trancas de todas as celas "
                "provavelmente seria uma péssima ideia...",
            ],
            "s", "sim",
        ),
        33: T(
            [
                "No chão há uma placa de pressão. Uma placa acima dela diz,",
                "Liberação de emergência das celas - Seção 3",
                "Pressionar a placa? (s/n)",
                "Pelos corredores você ouve o som de trancas se abrindo...",
                "Ocorre a você que liberar as trancas de todas as celas "
                "provavelmente seria uma péssima ideia...",
            ],
            "s", "sim",
        ),
    },
    "CRYSTAL4.INF": {
        3: (
            "Enquanto o ar gelado passa por você, congelando o próprio fôlego em "
            "seus pulmões, você percebe que só as mais poderosas magias "
            "poderiam sustentar os variados ambientes que você testemunhou "
            "nesta torre...",
            None,
        ),
        4: T(
            [
                "Para entrar lá dentro, deves encontrar, o significado desta "
                "passagem...",
                "Num salão de mármore branco como o leite, forrado com pele "
                "macia como seda, dentro de uma fonte cristalina, uma maçã "
                "dourada aparece, não há portas para esta fortaleza, ainda "
                "assim ladrões invadem para roubar o ouro...",
                "Qual é a tua resposta?",
                "Podes prosseguir, mortal, ao teu perigo...",
                "Rápido demais com tua resposta. Pensa, e tenta de novo...",
            ],
            "um ovo", "ovo",
        ),
        5: (
            "Você vê uma pequena chave no chão desta câmara gelada, mas outras "
            "coisas parecem chamar sua atenção...",
            None,
        ),
    },
    "DAGOTH1.INF": {
        1: (
            "Você entra na montanha de fogo, Dagoth-Ur. Ao seu redor o ar cintila "
            "com o calor. Até o chão de pedra está quente ao toque...",
            None,
        ),
        2: (
            "As passagens dentro deste vulcão estão cobertas de fuligem, e o "
            "cheiro de enxofre paira por toda parte.",
            None,
        ),
        3: ("Este aposento parece ser algum tipo de cripta...", None),
    },
    "DAGOTH2.INF": {
        5: ("Para passar pelo primeiro portal, deves encontrar a Chave de Rubi...", None),
        6: ("Para passar pelo segundo portal, deves encontrar a Chave de Safira...", None),
        7: ("Para passar pelo terceiro portal, deves encontrar a Chave de Cristal...", None),
        8: ("Para passar pelo quarto portal, deves encontrar a Chave de Ametista...", None),
        9: ("Para passar pelo portal final, deves encontrar a Chave de Diamante...", None),
        10: ("Este nível parece mais quente, como se um grande fogo ardesse sob seus pés...", None),
        11: (
            "Preso no centro desta poça de lava está um Golem de Ferro, e uma "
            "Chave de Rubi sobre um pedestal ao lado dele...",
            None,
        ),
        12: (
            "Nesta câmara você vê um Demônio do Fogo, e uma chave de Safira "
            "sobre um pedestal perto dele...",
            None,
        ),
        13: (
            "Atrás da porta da cela você vê uma Medusa, e uma chave de Cristal "
            "brilhando num pedestal à sua direita...",
            None,
        ),
        14: (
            "No centro desta câmara você vê um Vampiro, e uma chave de Ametista "
            "cintilando num pedestal a um canto...",
            None,
        ),
        15: (
            "Nesta câmara você vê um Lich, e uma chave de Diamante brilhando "
            "numa parede escurecida atrás dele...",
            None,
        ),
        16: (
            "Ouro reluz nas paredes quentes destas passagens, dando crédito às "
            "lendas de riqueza Anã lá embaixo...",
            None,
        ),
    },
    "DAGOTH3.INF": {
        # Adapted riddle: the English original is a spelling puzzle
        # whose answer is the letter "E" (eternity starts with E, time
        # and space end in E, "end" starts with E, place ends in E) -
        # that trick doesn't survive translation, so this is a newly
        # built Portuguese wordplay riddle with the same role (a
        # letter-of-the-alphabet answer needed to escape), using words
        # that make the SAME kind of trick work for the letter "O".
        0: T(
            [
                "Para escapar, um enigma deves responder...",
                "Está no início do Ocaso, e no fim de cada eco; está no início "
                "de todo obstáculo, e no fim de todo perigo...",
                "O que sou?",
                "És verdadeiramente digno. Vai em paz, e que teu destino seja "
                "escrito nos Elder Scrolls...",
                "Errado, mortal. Dagoth-Ur vai gostar de tua companhia, pelos "
                "milênios...",
                "Você percebe com desespero que a única saída é responder a "
                "pergunta corretamente...",
            ],
            "o", "letra o", "a letra o", "letra \"o\"",
        ),
        1: (
            "Uma rajada de calor te atinge ao ficar de pé no portal para um "
            "grande lago de fogo. Ao seu redor fogos ocasionais irrompem, e "
            "depois se apagam. No centro do lago você mal consegue distinguir "
            "algum tipo de estrutura...",
            None,
        ),
        2: (
            "Ao entrar neste nível uma onda de ar sulfuroso te atinge. Um som "
            "estrondoso pode ser ouvido, como se uma grande conflagração estivesse "
            "à frente. O ar ao seu redor cintila com o calor...",
            None,
        ),
    },
    "DEMO.INF": {
        0: (
            "Bem-vindo à demonstração jogável de Elder Scrolls! Esperamos que "
            "você se divirta nesta cripta dos mortos. Cuidado, pois todo tipo de "
            "criatura tentará impedi-lo de encontrar a única saída deste nível. "
            "Verifique seu inventário antes de continuar a aventura. Desejamos-lhe "
            "sorte nesta jornada...",
            None,
        ),
        1: (
            "Um odor fétido desce pelo corredor, trazendo consigo o cheiro de "
            "carne em decomposição...",
            None,
        ),
        2: (
            "Um vento quente flui por este corredor, e com ele você sente o "
            "cheiro de enxofre. Até o chão sob seus pés parece quente...",
            None,
        ),
        3: (
            "Você encontra um lago de fogo, sua superfície vermelha e quente "
            "borbulhando com violência. Um toque, e você certamente seria "
            "queimado até virar cinzas...",
            None,
        ),
        4: (
            "Do outro lado do fosso você vê o que parece ser uma espécie de "
            "altar. O corpo à sua frente obviamente é de alguém que não tomou as "
            "devidas precauções...",
            None,
        ),
        5: T(
            [
                "Responda isto corretamente e a porta de saída se destrancará. "
                "Responda errado, mortal, e sentirás a mão da morte se abater "
                "sobre você...",
                "O que não é peixe nem carne, nem penas nem osso, mas ainda "
                "assim tem dedos e polegares próprios?",
                "Qual é sua resposta?",
                "Sábio além da compreensão. Prossiga em paz para o mundo de "
                "Arena...",
                "Tolo mortal, pague o preço de tua loucura...",
            ],
            "luva", "luvas", "uma luva", "manopla", "uma manopla", "um par de luvas",
        ),
    },
    "ELDEN1.INF": {
        0: (
            "Você entra no Bosque de Elden, arrepiado pelas névoas que trazem "
            "escuridão perpétua a este lugar melancólico. Você pode ouvir coisas "
            "se arrastando pela vegetação, e um rosnado e gemido distantes que "
            "não soam nada humanos...",
            None,
        ),
    },
    "ELDEN2.INF": {
        0: T(
            [
                "Esta cova será teu túmulo, pois não há outra passagem para "
                "fora. Se responderes corretamente, estás livre. Se não, "
                "prepara-te para te juntar às almas perdidas do Bosque de "
                "Elden.",
                "Mitral élfico e prata argoniana, eu posso corroer. Mas "
                "primeiro, aprimoro tudo que o homem criou. Devoro todas as "
                "coisas, ave e fera, servos e reis. Embora meu passo seja "
                "constante, os homens amaldiçoam minha velocidade, desejando "
                "que eu fosse mais lento na hora da necessidade. Posso "
                "rastejar e me arrastar, ou correr, até voar. Sou tudo que "
                "tens. Diz-me, quem sou eu?",
                "Tempo é de fato a resposta. Considera o Bosque de Elden teu "
                "jardim. Vem e vai, à tua vontade.",
                "Não, não sou isso. Não estás livre para partir, embora "
                "quando eu escolher terminar, saberás. Posso te deixar muito "
                "em breve...",
            ],
            "tempo",
        ),
        # Adapted riddle: the English original is a compound-word
        # puzzle (foot + step = "footstep") that has no equivalent
        # Portuguese compound - rewritten as a plain descriptive riddle
        # with the same answer role (footprints/tracks).
        1: T(
            [
                "Resolve quem sou pelo enigma deste sinal, e todo bem e mal "
                "aqui dentro será teu.",
                "Sou feita pelo pé, mas não sou o pé, e dizem que, pelas "
                "minhas marcas, um ladrão pode ser capturado.",
                "Quem sou eu?",
                "Respondeste com verdade, então o portão se erguerá. "
                "Considera se tua sorte deve ser amaldiçoada ou louvada.",
                "Não sou isso. Podes retornar de novo e de novo, mas esta "
                "porta só se abre para os mais sábios dos homens.",
            ],
            "pegada", "pegadas", "a pegada", "as pegadas", "passo", "passos",
        ),
    },
    "FANG1.INF": {
        0: (
            "Você está em Covil da Presa. Suas passagens escavadas pelos Anões "
            "se estendem por quilômetros sob a terra...",
            None,
        ),
        5: (
            [
                "Deves provar teu valor para prosseguir ao Underdark. A "
                "resposta correta abrirá a cela com a chave de ouro, que "
                "abrirá o portal.",
                "Não te apresses em responder, mortal. A escolha errada "
                "abrirá as portas das celas para as aranhas...",
            ],
            None,
        ),
        6: T(
            [
                "Ao se aproximar, a própria porta fala:",
                "Ouve meu enigma, mortal tolo, e prova que és digno de meu "
                "serviço...",
                "Se a Cela 3 contém latão sem valor, a Cela 2 contém a chave "
                "de ouro. Se a Cela 1 contém a chave de ouro, a Cela 3 "
                "contém latão sem valor. Se a Cela 2 contém latão sem valor, "
                "a Cela 1 contém a chave de ouro.",
                "Sabendo disto, tolo corajoso, e sabendo que nem tudo que "
                "foi dito pode ser verdade, qual cela contém a chave de "
                "ouro?",
                "Estás correto, mortal. A chave dentro da cela 2 é tua...",
                "Você ouve o gemido do metal enquanto as portas das celas "
                "que prendem as aranhas se destrancam, e se abrem...",
            ],
            "cela 2", "2", "cela2", "a segunda cela", "a segunda", "c2",
        ),
        7: (
            "Você depara com algo estranho. Um aposento com celas dos dois "
            "lados. Em cada cela parece haver uma aranha faminta. Você vê mais "
            "três celas ao longo da parede sul. Ao lado delas há um portal "
            "escuro...",
            None,
        ),
        8: ("Cela 1", None),
        9: ("Cela 2", None),
        10: ("Cela 3", None),
        11: ("Poço de Mina A", None),
        12: ("Poço de Mina B", None),
        13: ("Poço de Mina C", None),
        14: ("Poço de Mina D", None),
        15: ("Poço de Mina E", None),
        16: ("Poço de Mina F", None),
        17: (
            "Estes túneis parecem se estender infinitamente, mas os trilhos que "
            "você encontra geralmente levam aos poços de mina...",
            None,
        ),
        18: ("De algum lugar próximo você pode ouvir raspados e cliques estranhos...", None),
        19: (
            "Você vê um templo, uma estrutura quase tão antiga quanto a rocha da "
            "qual foi esculpida...",
            None,
        ),
    },
    "FANG2.INF": {
        0: T(
            [
                "Uma pergunta simples para você,",
                "O que não é peixe nem carne, nem penas nem osso, mas ainda "
                "assim tem dedos e polegares próprios?",
                "Qual é sua resposta, mortal?",
                "Tens de fato o engenho para continuar. Podes prosseguir...",
                "Estás errado, mortal. Pensa com cuidado antes de tentar "
                "outra resposta.",
            ],
            "luva", "luvas", "uma luva", "manopla", "uma manopla", "um par de luvas",
        ),
    },
    "FORTI2.INF": {
        0: T(
            [
                "Toco teu rosto, estou em tuas palavras, sou a falta de "
                "espaço, e amado pelos pássaros... O que sou eu?",
                "A porta à tua frente se abre...",
                "Nada acontece.",
            ],
            "ar", "vento", "o ar", "o vento",
        ),
    },
    "GEMIN1.INF": GEMINI_PLACEHOLDER,
    "GEMIN2.INF": {
        **GEMINI_PLACEHOLDER,
        3: T(
            [
                "Responda isto, e passe -",
                "Eu saio da terra, sou vendida no mercado. Quem me compra "
                "corta minha cauda, tira minha roupa de seda, e chora ao meu "
                "lado quando estou morta...",
                "A porta à sua frente se destranca.",
                "Nada acontece...",
            ],
            "cebola", "uma cebola",
        ),
    },
    "HALLS1.INF": {
        **HALLS_INSCRIPTION,
        8: (
            "Neste corpo você encontra um bilhete rabiscado às pressas. Fala "
            "sobre encontrar seis chaves para abrir o segredo dos Salões. Estas "
            "chaves, segundo um mapa tosco, parecem estar espalhadas por este "
            "nível. Um 'X' vermelho está rabiscado num ponto diretamente ao "
            "norte daqui.",
            None,
        ),
    },
    "HALLS2.INF": {
        0: (
            "O ar parado no Salão do Colosso é seco e cheira a decadência. No "
            "silêncio da câmara, você pode ouvir o arrastar de muitos pés. Olhos "
            "vermelhos te encaram vindos da escuridão...",
            None,
        ),
        1: ("Esta fechadura parece ser feita de ferro...", None),
        2: ("Esta fechadura parece ser feita de ouro...", None),
        3: ("Esta fechadura está incrustada de rubis...", None),
        4: ("Esta é uma fechadura cravejada de diamantes...", None),
        5: ("Esta fechadura é adornada com safiras...", None),
    },
    "HALLS3.INF": SPHINX_RIDDLE,
    "IMPPAL1.INF": IMPERIAL_TOWER,
    "IMPPAL2.INF": IMPERIAL_TOWER,
    "IMPPAL3.INF": {
        0: ("EQUIPE VERMELHA", None),
        1: ("PORTA DA EQUIPE VERMELHA", None),
        2: ("EQUIPE AZUL", None),
        3: ("PORTA DA EQUIPE AZUL", None),
    },
    "IMPPAL4.INF": {
        1: (
            "Diante de você ergue-se uma grande porta de aço. Sua superfície "
            "está quente, como se atrás dela houvesse um grande fogo. O cheiro "
            "de enxofre e piche paira no ar parado e morto...",
            None,
        ),
    },
    "KHU1.INF": {
        0: (
            "O ar sulfuroso das Minas de Khuras te atinge como uma parede de "
            "calor, trazendo lágrimas aos seus olhos. Através do ar cintilante "
            "você pode ver vários fluxos e poços de lava espalhados pelo chão "
            "chamuscado, traiçoeiro e mortal...",
            None,
        ),
        1: (
            "Você supõe que este corpo seja de um aventureiro azarado. A carne "
            "parece rasgada, e talvez mastigada. Rabiscadas em sangue no chão ao "
            "lado estão as letras, 'SW'...",
            None,
        ),
        2: (
            "Marcas e arranhões na rocha aqui parecem indicar que algo grande "
            "passou por aqui há pouco tempo...",
            None,
        ),
        3: ("Você vê um poço que leva para outro nível...", None),
        4: (
            "Parece que os rumores de um tesouro Anão eram precisos. As pilhas "
            "de ouro e itens neste aposento brilham à luz trêmula das tochas...",
            None,
        ),
        5: (
            "Ao seu redor há poças de lava fervilhante, brotando de bem lá "
            "embaixo e liberando seus gases no ar, que parece contaminado mas "
            "respirável...",
            None,
        ),
        6: (
            [
                "Rabiscada na parede aqui há uma mensagem curta,",
                "'Cuidado com o Imperador. Seus lacaios me aguardam.",
                "Uma mensagem estranha de se encontrar nestas profundezas...",
            ],
            None,
        ),
        7: (
            [
                "Rabiscada na parede aqui há uma mensagem estranha,",
                "O segredo do Cajado é meu. Os perversos irã-",
                "A escrita termina abruptamente, como se quem escreveu "
                "tivesse sido interrompido de repente...",
            ],
            None,
        ),
    },
    "KHU2.INF": {
        0: (
            "Você entra nas entranhas das Minas, ciente de que ao seu redor há "
            "criaturas que vieram chamar este lugar amaldiçoado de lar...",
            None,
        ),
        1: (
            "Há uma ausência de luz nesta área, apenas somando à sensação "
            "melancólica de abandono...",
            None,
        ),
        2: (
            "Diante de você há uma porta secreta habilmente disfarçada, levando "
            "a outra seção das Minas...",
            None,
        ),
        3: (
            "Este corpo obviamente é do Irmão Barnabus. Seu corpo foi devastado "
            "pelos habitantes deste submundo e seu rosto marcado numa máscara de "
            "puro terror. Logo além do corpo você pode ver o que parece ser um "
            "mapa...",
            None,
        ),
        4: (
            [
                "No chão aqui você encontra um diário. O livro parece "
                "rasgado e gasto, com apenas uma página ainda legível,",
                "Os sonhos continuam. Não sei o que significam, mas algo "
                "precisa ser feito, ou o Império certamente perecerá. Talvez "
                "eu esteja louco, não sei. Vou começar a procurar o mapa na "
                "seção SE destas minas, e depois seguir a oeste ao longo da "
                "parede sul. Rezo para não ser tarde demais...",
                "Obviamente este diário foi escrito pelo Irmão Barnabus...",
            ],
            None,
        ),
    },
    "KHUTEST.INF": {
        0: (
            "Você entra nas entranhas das Minas, ciente de que ao seu redor há "
            "criaturas que vieram chamar este lugar amaldiçoado de lar...",
            None,
        ),
    },
    "LABRNTH1.INF": {
        0: (
            "Siga primeiro pelo caminho central, pois as pistas para resolver "
            "os segredos do Labyrinthian aguardam ali...",
            None,
        ),
        1: (
            "Esta é a história de dois irmãos, que buscaram o segredo da vida. "
            "Eles se aventuraram neste Labyrinthian, cansados da guerra e das "
            "dificuldades...",
            None,
        ),
        2: (
            "O primeiro era Kanen, o Ancião, um homem forte e astuto. Ele "
            "buscava riquezas e joias, mas descobriu que o Destino tinha outros "
            "planos...",
            None,
        ),
        3: (
            "O segundo era Mogrus, o Obtuso, e poucos sabiam seu real valor. "
            "Viam apenas o gigante desajeitado, não a criança que fora abençoada "
            "ao nascer...",
            None,
        ),
        4: (
            "Os poucos a quem contaram seus planos imploraram, de joelhos, que "
            "desistissem. Mas os irmãos testariam este enigma do Norte, pois até "
            "então não conheciam a derrota...",
            None,
        ),
        5: (
            "Esta é a história de dois irmãos, que falharam no segredo da vida. "
            "Presos para sempre por dois enigmas que levam ao prêmio, e a um "
            "engenho tão astuto e afiado quanto uma faca...",
            None,
        ),
        6: (
            "Mogrus, o Obtuso, embora seja um tédio, guarda a única chave que "
            "abre esta porta. Para achar o enigma, deves primeiro achar o "
            "filho, começa tua busca fatídica atrás da porta número um...",
            None,
        ),
        7: (
            "Kanen, o sábio, guarda mais a ser visto, uma chave e um enigma, e "
            "uma prova entre os dois. Para passar por este portal, feito por "
            "poucos, busca o irmão atrás da porta número dois...",
            None,
        ),
        8: (["Rabiscada no chão aqui está a palavra, ", "Porta 1"], None),
        9: (["Rabiscada no chão aqui está a palavra, ", "Porta 2"], None),
        10: T(
            [
                "Aqui está o portal final, a porta para a vida...",
                "O que a força e o vigor não conseguem atravessar, eu, com "
                "um toque suave, consigo; e muitos nestes salões torcidos "
                "ficariam de pé, se eu não estivesse, como um amigo, à "
                "mão...",
                "Resposta?",
                "És verdadeiramente digno do prêmio de Shalidor, a segunda "
                "peça do Cajado do Caos aguarda...",
                "Respondeste às pressas, e de fato erraste...",
            ],
            "chave", "uma chave",
        ),
        11: ("Para o Domínio de Mogrus", None),
        12: ("Para o Domínio de Kanen", None),
    },
    "LABRNTH2.INF": {
        0: T(
            [
                "Eu sou o irmão Mogrus, a sombra deste salão, Amaldiçoado "
                "por toda sua extensão, do início ao fim. Encontra-me a "
                "resposta, e uma porta eu abrirei. Falha uma vez sequer, e "
                "teu coração rasgarei...",
                "Mais bela que o rosto de teu Deus, ainda assim mais "
                "perversa que a língua bífida de um Demônio?",
                "Homens mortos a comem o tempo todo, Homens vivos que a "
                "comem morrem devagar...",
                "Qual é a resposta, mortal?",
                "Fui um tolo, talvez ferramenta de um mago louco. Ainda "
                "assim, após eras incontáveis, finalmente estou livre. Na "
                "cela ao lado desta está tua recompensa, a Chave de "
                "Diamante...",
                "Amaldiçoado sejas por um tolo, e agora provarás minha "
                "ira...",
            ],
            "nada",
        ),
        1: T(
            [
                "Eu sou o irmão Kanen, que guarda o segredo da vida. Não há "
                "enigmista mais astuto, entre o oceano e o feudo. "
                "Responde-me esta pergunta, ó mortal tolo lá de cima, ou te "
                "junta à minha tarefa eterna, nascida de dever e amor...",
                "Tenho dois corpos, Ainda que unidos em um só. Quanto mais "
                "paro, Mais rápido corro...",
                "Qual é tua resposta?",
                "Estou livre para voar com o vento, após uma eternidade de "
                "doença e pecado! Como recompensa por me libertares, a cela "
                "ao lado desta guarda tua Chave de Safira...",
                "Estás errado, mortal, agora tua alma tomarei para a "
                "eternidade...",
            ],
            "ampulheta", "uma ampulheta",
        ),
        4: ("Você está diante dos Salões de Mogrus...", None),
        5: ("Você está diante dos Salões de Kanen...", None),
    },
    "MAGE.INF": {
        0: ("Entrada absolutamente proibida!", None),
        1: ("Esta porta deve permanecer fechada em todos os momentos!", None),
    },
    "MGTEMPL1.INF": TEMPLE_COMMON,
    "MGTEMPL2.INF": {
        **TEMPLE_COMMON,
        8: (
            "Um bilhete no chão instrui alguém a mover coisas para a área de "
            'armazenamento segura no Nordeste, "antes que qualquer intrometido '
            'chegue"... De fato, o cômodo foi esvaziado.',
            None,
        ),
        9: T(
            [
                "A área acima da porta está inscrita com o seguinte:",
                "O que se acende E faz muito bem, E quando morre, É só um "
                "pedaço de madeira?",
                "A porta se move levemente enquanto a tranca se solta.",
                "Infelizmente, nada acontece.",
            ],
            "fósforo", "fósforos", "tocha", "tochas",
        ),
    },
    "MURK1.INF": {
        0: T(
            [
                "Para passar por este portal, responde meu enigma:",
                "Eu amarro e seguro, capturo e prendo, ainda assim tanto "
                "cavaleiros quanto vilões me desejam. Fielmente escravizo "
                "tudo ao meu alcance, queiram ou não me buscar. Ainda assim, "
                "aqueles que nunca sentiram minha mão impiedosa são "
                "lamentados por seus semelhantes...",
                "Encontraste a resposta. Prossegue ao coração de "
                "Murkwood...",
                "Responde de novo, mortal, pois foste apressado demais...",
            ],
            "amor",
        ),
        1: (
            "As névoas de Murkwood se enroscam ao seu redor, cegando você do "
            "perigo e confundindo seu senso de direção...",
            None,
        ),
        2: (
            "Você pode ouvir o que soa como respiração pesada através das "
            "névoas, mas a direção de onde veio é impossível de determinar...",
            None,
        ),
        3: ("De dentro das névoas vem o som de tambores...", None),
        4: (
            "Os pelos na nuca de seu pescoço se arrepiam enquanto figuras se "
            "materializam saindo das névoas...",
            None,
        ),
    },
    "MURK2.INF": {
        0: T(
            [
                "Um enigma simples para alguns, uma armadilha eterna para "
                "outros,",
                "Corro mais suave que qualquer rima, Adoro cair mas não "
                "consigo subir. Tremo a cada sopro de ar, E ainda assim "
                "posso carregar os fardos mais pesados...",
                "Qual é tua resposta?",
                "Verdadeiramente és digno do prêmio. Prossegue, mortal, e "
                "parte em paz...",
                "Estás errado, mortal. Enfrenta teus oponentes. Se "
                "vitorioso, podes tentar de novo...",
            ],
            "água", "a água",
        ),
        1: (
            "Você pode ver o que parece ser uma peça do Cajado bem à frente. Ao "
            "seu redor vêm sons estranhos de raspados, como ferro sendo torcido "
            "e dobrado, repetidamente...",
            None,
        ),
    },
    "NOBLE.INF": RESTRICTED_AREA,
    "NOBLE1.INF": RESTRICTED_AREA,
    "NOBLE2.INF": RESTRICTED_AREA,
    "NOBLE3.INF": RESTRICTED_AREA,
    "SD1.INF": GEMINI_PLACEHOLDER,
    "SD3.INF": {
        0: (
            "Você está em Covil da Presa. Suas passagens tortuosas se estendem "
            "por quilômetros sob a terra...",
            None,
        ),
    },
    "SELENE1.INF": {
        0: (
            "Este corredor úmido e mofado leva à Teia de Selene. O cheiro de "
            "terra molhada paira no ar.",
            None,
        ),
        1: (
            "Diante de você há uma pequena arena, cercada por água. Algo brilha "
            "nas pedras de uma das ilhas.",
            None,
        ),
        2: ("COVIS DE ACASALAMENTO! Sem Luz Nem Barulho!", None),
        3: ("Estranhamente, esta pequena passagem tem marcas de uso intenso.", None),
        5: ("Você vê uma porta com uma fechadura dourada.", None),
    },
    "SELENE2.INF": {
        0: ("PERIGO! ÁREA DE TREINAMENTO!", None),
        2: ("A porta à sua frente tem uma fechadura cravejada de diamantes.", None),
        3: (
            "Há pouca poeira aqui, e as pegadas que existem são de humanoides "
            "correndo em direção a esta parede e pulando...",
            None,
        ),
    },
    "SKEEP1.INF": STONEKEEP_PRISON,
    "SKEEP2.INF": {
        0: (
            "Talvez você encontre o pergaminho dentro dos depósitos "
            "abandonados ao seu redor...",
            None,
        ),
        1: ("Uma placa sobre a porta diz: QUARTEL DA GUARDA", None),
        2: (
            "A julgar pelas marcas de arrasto no chão, provavelmente houve uma "
            "luta aqui...",
            None,
        ),
        3: ("Você percebe um cheiro de umidade.", None),
        4: (
            "Ratos correm para fora de vista ao você se aproximar. Esta área "
            "provavelmente guardava gêneros secos, agora há muito decompostos.",
            None,
        ),
        5: ("Uma placa anuncia: ARSENAL", None),
        6: (
            "Um exame mais atento revela as marcas onde os suportes de armas "
            "estiveram presos às paredes...",
            None,
        ),
        7: T(
            [
                "Esmagada sob pés que pisoteiam, mantida na escuridão e no "
                "frio. Sou inútil se não sofri; mas tendo sofrido, meu "
                "temperamento é doce e forte para todos que participam. O "
                "que sou, no início?",
                "A porta se abre para um aposento estranho...",
                "Pensa de novo, mortal, então responda...",
            ],
            "uva", "uvas", "uma uva",
        ),
    },
    "START.INF": {
        1: (
            "Você desperta com o pingar de água vindo de algum lugar acima. As "
            "paredes da cela estão cobertas de limo, assim como as correntes "
            "que pendem do alto. Seu olhar, porém, vai imediatamente para um "
            "estranho brilho de rubi no canto de sua cela...",
            None,
        ),
        2: (
            "Os corredores aqui parecem tortuosos e confusos, mas as instruções "
            "de Ria eram ir a oeste, depois ao sul, para encontrar o Portão de "
            "Deslocamento...",
            None,
        ),
        3: (
            "O ruído de muitos pés com garras minúsculas pode ser ouvido nas "
            "pedras marrons e úmidas...",
            None,
        ),
        4: ("Olhos vermelhos parecem brilhar para você vindos da escuridão...", None),
        5: ("À frente você pode ver o campo cintilante do Portão de Deslocamento...", None),
        6: (
            "Parece seguro descansar nestes nichos. Você acha que os ratos ou "
            "outras criaturas podem não sentir seu cheiro com a corrente de ar "
            "que passa tão perto do chão...",
            None,
        ),
    },
    "STKEEP1.INF": STONEKEEP_PRISON,
    "TOWER.INF": IMPERIAL_TOWER,
    "TOWER1.INF": IMPERIAL_TOWER,
    "TOWER2.INF": RESTRICTED_AREA,
    "TOWER6.INF": HALLS_INSCRIPTION,
    "TOWER8.INF": SPHINX_RIDDLE,
    "VILPAL.INF": RESTRICTED_AREA,
}


def build_one(name: str) -> None:
    path = PARTS_DIR / name
    raw = path.read_bytes()
    text = xor_crypt(raw).decode("latin-1")
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
    print("Building translated .INF flavor text (GLOBAL_parts/legivel/)...")
    for name in TRANSLATIONS:
        build_one(name)
    print("Done.")


if __name__ == "__main__":
    main()
