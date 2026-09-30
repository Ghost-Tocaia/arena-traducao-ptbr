"""Faz uma varredura BRUTA (sem validação, sem escolha cuidadosa de
paleta por arquivo) de todo `.IMG` do `GLOBAL.BSA` que ainda não tem
uma versão legível em `Originais/legivel/` - ou seja, todo `.IMG` fora
de `img_manifest.IMAGE_MANIFEST` - decodificando cada um para PNG só
para permitir revisão visual humana rápida em busca de texto escondido.

Diferente de `gerar_legivel_originais.py` (que resolve a paleta certa,
por arquivo, com cuidado), este script usa uma regra única e rápida:
paleta embutida se o arquivo tiver uma, senão PAL.COL como chute padrão
(a paleta externa mais comum encontrada neste projeto). Puramente
best-effort - muitos sprites de mundo (masmorra, criatura, item) quase
certamente vão sair com cores erradas/ruído, mas o objetivo aqui não é
acertar a cor, é permitir identificar rapidamente qual arquivo tem
pixels de texto (formas de letra reconhecíveis) mesmo que a paleta
esteja errada, já que o "desenho" da tinta ainda aparece como algo
visualmente distinto do fundo na maioria dos casos.

Muitas texturas de piso/parede de masmorra (referenciadas em `.INF`,
ex. `caspit.img`, `bluerug.img`) NÃO têm o cabeçalho de 12 bytes comum
ao resto do projeto - são um bloco cru quadrado (mais comumente 64x64 =
4096 bytes) sem compressão, sem paleta própria. Detectado por
descarte: se o cabeçalho de 12 bytes produzir dimensões absurdas E o
tamanho do arquivo for um quadrado perfeito, trata como textura crua.

Arquivos que não se encaixam em nenhum dos dois formatos (cabeçalho
normal ou textura quadrada crua) são pulados e listados em `_erros.txt`
dentro da pasta de saída, não travam a varredura inteira.

Escreve em "varredura_imagens/" (raiz do projeto) - pasta de uso único
para revisão, não faz parte do pipeline de build.

Usage: python3 scripts/varredura_img_bruta.py
"""
import math
import struct
from pathlib import Path

from PIL import Image

from bsa_codec import offsets_by_name, read_index
from huffman_codec import decode_type08
from img_manifest import IMAGE_MANIFEST
from lzss_codec import decode_type04

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT_DIR / "Originais"
OUT_DIR = ROOT_DIR / "varredura_imagens"

MAX_PIXELS = 2_000_000  # descarta cabeçalhos claramente corrompidos


def s6(v: int) -> int:
    return (v << 2) | (v >> 4)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    bsa_data = (ORIG_DIR / "GLOBAL.BSA").read_bytes()
    entries = read_index(bsa_data)
    offsets = offsets_by_name(entries)

    default_pal_raw = (ORIG_DIR / "PAL.COL").read_bytes()
    default_palette = list(default_pal_raw[8:8 + 768])

    ja_legivel = set(IMAGE_MANIFEST.keys())
    alvos = [(name, offsets[name]) for name, _ in entries if name.endswith(".IMG") and name not in ja_legivel]

    print(f"Total .IMG no GLOBAL.BSA: {sum(1 for n, _ in entries if n.endswith('.IMG'))}")
    print(f"Já com legivel/ (pulados): {len(ja_legivel)}")
    print(f"A converter agora: {len(alvos)}")

    erros = []
    ok_count = 0
    for i, (name, (off, size)) in enumerate(alvos, 1):
        filedata = bsa_data[off:off + size]
        try:
            pixels = None
            width = height = 0
            palette_flat = default_palette

            if len(filedata) >= 12:
                xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", filedata, 0)
                if width and height and width * height <= MAX_PIXELS:
                    comp_type = flags & 0xFF
                    if comp_type == 0:
                        pixels = filedata[12:12 + width * height]
                    elif comp_type == 4:
                        pixels, _ = decode_type04(filedata, 12, 12 + length, width * height)
                    elif comp_type == 8:
                        pixels = decode_type08(filedata, 12 + 2, 12 + length, width * height)
                    else:
                        pixels = None  # tipo de compressão desconhecido - tenta textura crua abaixo

                    if pixels is not None and (flags & 0x100):
                        pal_region = filedata[12 + length:12 + length + 768]
                        if len(pal_region) >= 768:
                            palette_flat = [s6(b) for b in pal_region]

            if pixels is None:
                # Fallback: textura de piso/parede sem cabeçalho - bloco
                # cru quadrado (ex. 4096 bytes = 64x64), sem compressão.
                side = math.isqrt(len(filedata))
                if side * side == len(filedata) and side > 0:
                    width = height = side
                    pixels = filedata
                else:
                    raise ValueError(
                        f"não é um cabeçalho .IMG válido nem uma textura quadrada crua (tamanho {len(filedata)} bytes)"
                    )

            im = Image.new("P", (width, height))
            im.putpalette(palette_flat)
            im.putdata(bytes(pixels))
            stem = name.rsplit(".", 1)[0]
            im.save(OUT_DIR / f"{stem}.png")
            ok_count += 1
        except Exception as exc:  # noqa: BLE001 - varredura best-effort, nunca deve travar
            erros.append(f"{name}: {exc}")

        if i % 100 == 0:
            print(f"  {i}/{len(alvos)}...")

    (OUT_DIR / "_erros.txt").write_text("\n".join(erros), encoding="utf-8")
    print(f"Convertidos: {ok_count}. Falharam: {len(erros)} (ver {OUT_DIR / '_erros.txt'})")


if __name__ == "__main__":
    main()
