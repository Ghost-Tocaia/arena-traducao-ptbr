#!/usr/bin/env python3
"""
Remove acentos e cedilha de todos os arquivos de uma pasta (1 nível, não
recursivo), detectando automaticamente se cada arquivo é texto puro ou
binário com strings embutidas (como .LST, .MNU de jogos DOS antigos).

Os arquivos processados são salvos em uma subpasta "build" criada dentro
da própria pasta de origem, mantendo os nomes originais. Os arquivos de
entrada nunca são alterados.

Uso: execute a partir da pasta "scripts":
    python3 build.py

Por padrão processa a pasta "Minha tradução", irmã da pasta deste script.
Para apontar outra pasta, edite a variável PASTA_ALVO abaixo.
"""
import unicodedata
from pathlib import Path

# Pasta a processar. None = pasta "Minha tradução" irmã da pasta deste script.
PASTA_ALVO = None
PASTA_DADOS = Path(__file__).resolve().parent.parent / "Minha tradução"
PASTA_RAIZ = Path(__file__).resolve().parent.parent

NOME_PASTA_BUILD = "build"
NOME_PROPRIO_SCRIPT = Path(__file__).name

# Arquivos de imagem cujo "texto" já foi desenhado como pixel art (via
# build_images.py), não como caracteres Latin-1 dentro do arquivo. Rodar o
# removedor de acentos neles seria perigoso: dados de imagem crua/comprimida
# são essencialmente aleatórios e podem coincidentemente cair na faixa de
# bytes "acentuados", corrompendo pixels ou o fluxo de compressão LZSS. Por
# isso são sempre copiados sem alteração.
ARQUIVOS_IMAGEM_BINARIOS = {
    "SCROLL03.IMG", "CHARSPEL.IMG", "TITLE.IMG", "TAMRIEL.MNU",
    # STARTGAM.MNU/MAPBTNS.MNU não têm texto (confirmado por análise de
    # pixels - ver inventario-arquivos.md seção 2.2), mas usam o mesmo
    # formato de imagem comprimida (LZSS) das telas acima — sofrem o
    # mesmo risco de corrupção e por isso também são sempre copiados
    # sem alteração.
    "STARTGAM.MNU", "MAPBTNS.MNU",
    # CHARSPEL.DAT é um dump de tela cru (sem cabeçalho) - mesmo risco
    # de corrupção do acentuador que os `.IMG`/`.MNU` acima.
    "CHARSPEL.DAT",
    # Arquivo (~16MB) já reconstruído por build_bsa_scrolls.py com
    # SCROLL01.IMG/SCROLL02.IMG traduzidos; contém ~2441 outros arquivos
    # binários que sofreriam o mesmo risco de corrupção do acentuador.
    "GLOBAL.BSA",
    # .INF de masmorra que existem como arquivo solto (fora do GLOBAL.BSA)
    # - já traduzidos e com acentos removidos por build_inf_loose.py, que
    # roda antes deste script; reprocessá-los aqui seria redundante e, como
    # têm um formato binário estruturado (texturas/posições/sons
    # misturados com o texto traduzido), arriscaria o mesmo tipo de
    # corrupção que os `.IMG` acima.
    "CRYSTAL3.INF", "IMPPAL1.INF", "IMPPAL2.INF", "IMPPAL3.INF", "IMPPAL4.INF",
    # ACD.EXE é comprimido com PKLITE (build_acd_exe.py já aplica suas
    # próprias traduções, sem acentos, direto no buffer descomprimido,
    # antes de recompactar) - o fluxo comprimido é essencialmente
    # aleatório e um único byte trocado corrompe a descompactação a
    # partir dali. Foi exatamente isso que aconteceu antes desta
    # entrada existir: o build completo (build_all.py) sobrescrevia o
    # ACD.EXE já correto de build_acd_exe.py com uma cópia corrompida,
    # travando o OpenTESArena ("Buffer.h index >= 0") mesmo com o script
    # de tradução do EXE funcionando perfeitamente sozinho. ACD_unpacked.bin
    # é só um artefato de depuração (buffer descomprimido, nunca lido
    # pelo jogo) mas corre o mesmo risco nas regiões de código/tabelas
    # binárias, por isso também fica de fora.
    "ACD.EXE", "ACD_unpacked.bin",
}

# Arquivos que build_acd_exe.py já escreve direto em build/opentes/ e
# build/dosbox/ (ACD.EXE precisa de uma versão diferente por
# plataforma - ver pipeline-acd-exe.md) - nunca devem ir pra build/
# raiz, nem sem alteração.
ARQUIVOS_SO_EM_SUBPASTA_PLATAFORMA = {"ACD.EXE", "ACD_unpacked.bin"}

# STARTGAM.MNU não tem texto (confirmado por análise de pixels - ver
# inventario-arquivos.md seção 2.2) - o jogo instalado simplesmente
# mantém o arquivo original intocado, então nem faz sentido colocar
# uma cópia idêntica em build/. (MAPBTNS.MNU, mesmo caso, nunca chegou
# a entrar em "Minha tradução/" pra começo de conversa - nem precisa
# constar aqui.) TAMRIEL.MNU saiu daqui em 30/09/2026: agora É
# traduzido (ver ARQUIVOS_IMAGEM_BINARIOS acima), então vai pra build/.
ARQUIVOS_MANTIDOS_ORIGINAIS_FORA_DO_BUILD = {"STARTGAM.MNU"}

# TEMPLATE.DAT tem versão diferente por plataforma (traduzido funciona
# no OpenTESArena; qualquer edição de byte quebra o sistema de diálogo
# no DOSBox real - ver o gotcha em pipeline-textos.md) - por isso não
# vai pra build/ raiz, e sim pra build/opentes/ (traduzido, processado
# normalmente por este script) e build/dosbox/ (original, cópia direta
# de Originais/, sem passar por processar_bytes).
ARQUIVOS_PLATAFORMA_TEMPLATE = {"TEMPLATE.DAT"}

# Bytes sempre considerados "texto" (ASCII imprimível + espaços/quebras de linha)
ASCII_IMPRIMIVEL = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}

# Mapeamento de caracteres acentuados/cedilha (Latin-1) -> equivalente ASCII.
# Mantém sempre 1 caractere -> 1 caractere, preservando o tamanho em bytes.
MAPA_ACENTOS = {
    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
    'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
    'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
    'ç': 'c', 'ñ': 'n',
    'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
    'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
    'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
    'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
    'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
    'Ç': 'C', 'Ñ': 'N',
}

# Bytes (em Latin-1) que os caracteres acima ocupam - também contam como "texto"
BYTES_ACENTUADOS = {ch.encode('latin-1')[0] for ch in MAPA_ACENTOS}

BYTES_TEXTO_VALIDOS = ASCII_IMPRIMIVEL | BYTES_ACENTUADOS


def remover_acentos_str(texto: str) -> str:
    """Troca cada caractere acentuado/cedilha pelo equivalente sem acento,
    mantendo o mesmo número de caracteres (1 para 1)."""
    return ''.join(MAPA_ACENTOS.get(c, c) for c in texto)


TAMANHO_MINIMO_RUN = 2


def encontrar_runs_de_texto(data: bytes):
    """Encontra sequências (runs) de bytes 'tipo texto' (ASCII imprimível
    ou acentuado) em qualquer posição do arquivo. Só aceita um run como
    texto de verdade se ele tocar um byte nulo (ou a borda do arquivo) em
    pelo menos um dos lados - isso é típico de strings null-terminated /
    null-padded dentro de arquivos binários, e evita mexer em sequências
    de bytes numéricos que por coincidência caem na faixa imprimível.
    Retorna lista de tuplas (inicio, fim) com fim exclusivo."""
    runs = []
    n = len(data)
    i = 0
    while i < n:
        if data[i] in BYTES_TEXTO_VALIDOS:
            j = i
            while j < n and data[j] in BYTES_TEXTO_VALIDOS:
                j += 1
            if j - i >= TAMANHO_MINIMO_RUN:
                toca_nulo_antes = (i == 0) or (data[i - 1] == 0)
                toca_nulo_depois = (j == n) or (data[j] == 0)
                if toca_nulo_antes or toca_nulo_depois:
                    runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def processar_bytes_binario(data: bytearray) -> bytearray:
    """Limpa acentos apenas dentro dos runs de texto identificados,
    deixando todo o resto do arquivo (dados numéricos/binários)
    exatamente como estava. Como a troca é sempre 1 caractere para 1
    caractere, o tamanho e os offsets do arquivo nunca mudam."""
    runs = encontrar_runs_de_texto(bytes(data))
    for inicio, fim in runs:
        texto = data[inicio:fim].decode('latin-1')
        texto_limpo = remover_acentos_str(texto)
        data[inicio:fim] = texto_limpo.encode('latin-1')
    return data


def processar_bytes(data: bytes) -> bytes:
    """Ponto de entrada: escolhe a estratégia certa dependendo do tipo
    de arquivo (texto puro vs. binário com strings embutidas).

    Arquivos de jogo antigos (.LST, .MNU) costumam ser de 1 byte por
    caractere (Latin-1/CP437) e quase sempre têm bytes nulos no meio
    (dados numéricos), então caem no modo binário. Arquivos de texto
    modernos (.md, .txt) normalmente não têm bytes nulos e podem estar
    em UTF-8 (padrão de editores atuais) - por isso tentamos UTF-8
    primeiro no modo texto, com Latin-1 como alternativa."""
    if eh_arquivo_binario(data):
        return bytes(processar_bytes_binario(bytearray(data)))

    try:
        texto = data.decode('utf-8')
        codificacao = 'utf-8'
    except UnicodeDecodeError:
        texto = data.decode('latin-1')
        codificacao = 'latin-1'

    texto_limpo = remover_acentos_str(texto)
    return texto_limpo.encode(codificacao)


def eh_arquivo_binario(data: bytes) -> bool:
    """Heurística simples: se o arquivo contém bytes nulos, é tratado como
    binário (pode ter strings embutidas em meio a dados numéricos)."""
    return b'\x00' in data


def main():
    pasta = Path(PASTA_ALVO) if PASTA_ALVO else PASTA_DADOS
    pasta_build = PASTA_RAIZ / NOME_PASTA_BUILD
    pasta_build.mkdir(exist_ok=True)
    pasta_opentes = pasta_build / "opentes"
    pasta_dosbox = pasta_build / "dosbox"
    pasta_opentes.mkdir(exist_ok=True)
    pasta_dosbox.mkdir(exist_ok=True)

    arquivos = [
        f for f in pasta.iterdir()
        if f.is_file() and f.name != NOME_PROPRIO_SCRIPT
    ]

    if not arquivos:
        print(f"Nenhum arquivo encontrado em: {pasta}")
        return

    for arquivo in arquivos:
        if arquivo.name in ARQUIVOS_SO_EM_SUBPASTA_PLATAFORMA:
            print(f"[plataforma] {arquivo.name} -> ignorado aqui, "
                  f"build_acd_exe.py escreve direto em build/opentes/ e build/dosbox/")
            continue

        if arquivo.name in ARQUIVOS_MANTIDOS_ORIGINAIS_FORA_DO_BUILD:
            print(f"[original] {arquivo.name} -> nao incluido no build "
                  f"(sem texto, instalacao mantem o arquivo original)")
            continue

        data = arquivo.read_bytes()

        if arquivo.name in ARQUIVOS_PLATAFORMA_TEMPLATE:
            original_data = (PASTA_RAIZ / "Originais" / arquivo.name).read_bytes()
            destino_dosbox = pasta_dosbox / arquivo.name
            destino_dosbox.write_bytes(original_data)
            print(f"[plataforma] {arquivo.name} -> {destino_dosbox.relative_to(PASTA_RAIZ)} "
                  f"(original em ingles, DOSBox real nao tolera edicao de byte)")

            novo_data = processar_bytes(data)
            destino_opentes = pasta_opentes / arquivo.name
            destino_opentes.write_bytes(novo_data)
            print(f"[plataforma] {arquivo.name} -> {destino_opentes.relative_to(PASTA_RAIZ)} "
                  f"(traduzido, {len(novo_data)} bytes, tamanho preservado: {len(data) == len(novo_data)})")
            continue

        destino = pasta_build / arquivo.name

        if arquivo.name in ARQUIVOS_IMAGEM_BINARIOS:
            destino.write_bytes(data)
            print(f"[imagem] {arquivo.name} -> {destino.relative_to(PASTA_RAIZ)} "
                  f"({len(data)} bytes, copiado sem alteração)")
            continue

        tipo = "binário" if eh_arquivo_binario(data) else "texto"

        novo_data = processar_bytes(data)

        destino.write_bytes(novo_data)

        print(f"[{tipo}] {arquivo.name} -> {destino.relative_to(PASTA_RAIZ)} "
              f"({len(data)} bytes, tamanho preservado: {len(data) == len(novo_data)})")


if __name__ == '__main__':
    main()