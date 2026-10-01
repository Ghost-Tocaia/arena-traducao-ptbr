#!/usr/bin/env python3
"""
Monta os pacotes .zip prontos pra upload manual no Nexus Mods, um por
plataforma (DOSBox/Steam clássico e OpenTESArena), a partir do que já
está em "build/" (rode build_all.py antes, se "build/" estiver
desatualizado).

Cada pacote junta os arquivos comuns da raiz de "build/" com o
ACD.EXE/TEMPLATE.DAT certo daquela plataforma (de "build/dosbox/" ou
"build/opentes/") - o jogador só extrai e copia tudo pra pasta ARENA,
sem precisar entender a diferença entre as duas versões.

Saída: "nexus_release/Arena_Traducao_PTBR_<Plataforma>_v<VERSAO>.zip"
(pasta gitignorada - nunca é commitada, só existe localmente pra
preparar o upload). Não mexe em "nexus_release/texto-pagina-nexus.txt"
nem em "nexus_release/nexus-texto.html" - esses são mantidos à mão.

Uso: python3 scripts/build_nexus_release.py
"""
import zipfile
from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_BUILD = PASTA_RAIZ / "build"
PASTA_NEXUS = PASTA_RAIZ / "nexus_release"

VERSAO = "1.0"

PLATAFORMAS = {
    "DOSBox": PASTA_BUILD / "dosbox",
    "OpenTESArena": PASTA_BUILD / "opentes",
}


def montar_pacote(nome_plataforma: str, pasta_plataforma: Path) -> Path:
    arquivos_comuns = [
        f for f in PASTA_BUILD.iterdir()
        if f.is_file()
    ]
    arquivos_plataforma = [
        f for f in pasta_plataforma.iterdir()
        if f.is_file()
    ]

    destino = PASTA_NEXUS / f"Arena_Traducao_PTBR_{nome_plataforma}_v{VERSAO}.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in arquivos_comuns + arquivos_plataforma:
            zf.write(arquivo, arcname=arquivo.name)

    total = len(arquivos_comuns) + len(arquivos_plataforma)
    print(f"[{nome_plataforma}] {destino.relative_to(PASTA_RAIZ)} "
          f"({total} arquivos, {destino.stat().st_size / 1024 / 1024:.1f} MB)")
    return destino


def main() -> None:
    if not PASTA_BUILD.exists():
        print(f"'{PASTA_BUILD}' não existe - rode build_all.py primeiro.")
        return

    PASTA_NEXUS.mkdir(exist_ok=True)

    for nome_plataforma, pasta_plataforma in PLATAFORMAS.items():
        if not pasta_plataforma.exists():
            print(f"[{nome_plataforma}] pulado - '{pasta_plataforma}' não existe")
            continue
        montar_pacote(nome_plataforma, pasta_plataforma)


if __name__ == "__main__":
    main()
