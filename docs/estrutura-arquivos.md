# Estrutura de arquivos e pastas

## Visão geral das pastas na raiz

```
Originais/          arquivos do jogo original em inglês, NUNCA editados
                     diretamente — são a fonte de verdade / fallback
  legivel/            espelho pristino, gerado/regenerável, em formato
                       aberto (PNG para imagens, texto puro decifrado
                       para os .INF com @TEXT) — ver "legivel/ vs.
                       formato do jogo" abaixo
Minha tradução/      resultado da tradução "de trabalho" (não a build
                     final) — o que os scripts de scripts/ leem e escrevem
  legivel/            PNGs/texto editáveis das imagens/`.INF` soltos
                       (CHARSPEL, TITLE, SCROLL03, CRYSTAL3.INF, IMPPAL*.INF)
  GLOBAL_parts/       cópias avulsas de cada arquivo de GLOBAL.BSA que
                       precisa de tradução (ver pipeline-imagens.md)
    legivel/           PNGs/texto editáveis de tudo que vive dentro do
                         GLOBAL.BSA — o que os scripts de build_bsa_*.py
                         realmente escrevem hoje
      empty/             versões "vazias" (texto apagado, nada desenhado
                           ainda) dos painéis INTRO/HISTORY, como PNG —
                           base reutilizável para desenhar a tradução
  TEMPLATE_parts/     partes de um arquivo de texto sendo traduzido no
                       momento (ver pipeline-textos.md) — conteúdo
                       descartável/temporário de trabalho
preview_imagens/     PNGs de pré-visualização (2x/4x, nearest-neighbor)
                     de toda imagem traduzida, gerados pelos scripts de
                     build para revisão visual — nunca editados à mão
                     (distinto de `legivel/`: é só para olhar, ampliado,
                     não é o arquivo de trabalho real)
build/               saída final do pipeline (scripts/build.py e
                     scripts/build_all.py), pronta para copiar para a
                     pasta de instalação do jogo
scripts/             todo o código Python do projeto (ver abaixo)
docs/                esta documentação
```

## Regra de ouro: `Originais/` é intocável

Nenhum script escreve em `Originais/` a partir do `GLOBAL.BSA`/arquivos
soltos do jogo em si. Todo fluxo de trabalho é: ler de `Originais/` (ou
de uma cópia extraída dele), escrever em `Minha tradução/`. Isso permite
reconstruir qualquer arquivo do zero a qualquer momento sem risco de ter
corrompido a fonte. A única exceção é `Originais/legivel/`, que É gerado
por um script (`gerar_legivel_originais.py`) — mas isso não viola a
regra, porque esse conteúdo é uma derivação 100% determinística do
`GLOBAL.BSA`/`.IMG` originais, nunca editado à mão, e sempre seguro de
regerar do zero a qualquer momento.

## `legivel/` vs. formato do jogo

Toda imagem `.IMG` e todo `.INF` empacotado no `GLOBAL.BSA` só existe em
formato binário do jogo (pixels comprimidos + paleta; texto cifrado por
XOR) na hora de instalar no jogo de verdade — **nunca** como arquivo de
trabalho. Enquanto a tradução está sendo feita/editada, o que existe em
disco é sempre uma pasta `legivel/` com:

- **PNG** (modo "P", com a paleta certa já embutida no próprio arquivo —
  abre com as cores corretas em qualquer visualizador/editor de imagem,
  sem precisar de nenhum contexto externo) para cada tela `.IMG`.
- **Texto puro** (Latin-1, com acento, já decifrado se for um `.INF`
  empacotado no `GLOBAL.BSA`) para cada `.INF` com seção `@TEXT`.

Isso significa que, se um `build_bsa_*.py` não acertar um detalhe visual
de primeira, dá para abrir o PNG correspondente num editor de imagem
comum e ajustar à mão — sem precisar mexer em compressão, cabeçalho ou
paleta.

A conversão para o formato binário do jogo só acontece na hora do
build, via dois scripts dedicados que leem QUALQUER coisa que estiver em
`legivel/` no momento (seja resultado de script ou edição manual) e
escrevem o binário final exatamente onde o `.IMG`/`.INF` pristino já
vivia:

- **`compile_images.py`** — usa `img_manifest.py` (tipo de compressão de
  saída e se deve embutir paleta, por arquivo) e `img_codec.py`
  (montagem do cabeçalho + compressão) para gerar cada `.IMG`.
- **`compile_inf.py`** — remove acento (`remover_acentos_str`, de
  `build.py` — mesma regra de todo outro arquivo de texto do projeto) e,
  só para os `.INF` empacotados no BSA, recifra com XOR
  (`inf_codec.xor_crypt`).

Ambos rodam depois de todo `build_bsa_*.py`/`build_images.py` e antes de
`merge_bsa.py`/`build.py` — já no lugar certo em `build_all.py`.

## `scripts/` — inventário

Formatos e codecs de baixo nível (sem estado, sem I/O de arquivo do
projeto — só codificam/decodificam bytes):

| Arquivo | O que é |
|---|---|
| `bsa_codec.py` | Leitor/escritor do formato de arquivo `GLOBAL.BSA` |
| `lzss_codec.py` | Codec da compressão "type 4" (LZSS) usada em vários `.IMG` |
| `huffman_codec.py` | Decodificador da compressão "type 8" (Huffman adaptativo + LZ77) — só leitura, ver [pipeline-imagens.md](pipeline-imagens.md#compressão-type-8-huffman-decode-only) |
| `img_codec.py` | Monta um `.IMG` binário (cabeçalho + compressão + paleta opcional) a partir de índices de pixel + paleta já resolvidos — usado só por `compile_images.py` |
| `inf_codec.py` | Cifra XOR e parsing de blocos `*TEXT N`/`@SECTION` de um `.INF` — ver [pipeline-inf.md](pipeline-inf.md) |

Pipeline de arquivos de texto (`.DAT`/`.TXT`/`.LST`) — ver
[pipeline-textos.md](pipeline-textos.md):

| Arquivo | Papel |
|---|---|
| `split_template.py` | Original → pedaços (`TEMPLATE_parts/*.DAT`) |
| `mount_template_part.py` | Aplica um dicionário de traduções (`*.py`) de volta em cima de um `*.DAT` |
| `merge_template.py` | Pedaços → arquivo único final |
| `reflow_template.py` | Correção pontual de `TEMPLATE.DAT`: reflui a quebra de linha física de cada parágrafo pra bater com o padrão irregular do original (não um wrap uniforme ~31 caracteres), suspeito de causar o bug de diálogo trocado no jogo real — ver [pipeline-textos.md](pipeline-textos.md) |
| `diagnostic_exact_length.py` | Ferramenta DESCARTÁVEL de diagnóstico (não é correção de tradução de verdade): força cada bloco de `TEMPLATE.DAT` a ter o mesmo tamanho em bytes do original em inglês, sacrificando qualidade da tradução, só pra testar se alinhamento byte-exato por si só resolve o bug de diálogo — ver [inventario-arquivos.md](inventario-arquivos.md#templatedat--arquivo-real-do-jogo-mas-não-é-seguro-traduzir-para-dosbox) |
| `build.py` | Remove acentos/cedilha de todo `Minha tradução/` (exceto imagens binárias e `.INF` já compilados), saída em `build/` |

Pipeline do arquivo `GLOBAL.BSA` e das imagens `.IMG`/`.INF` que ele
contém — ver [pipeline-imagens.md](pipeline-imagens.md) e
[pipeline-inf.md](pipeline-inf.md). Todo `build_bsa_*.py`/
`build_images.py`/`build_inf_loose.py` abaixo só produz PNG/texto em
`legivel/` — a conversão para o formato binário do jogo é sempre feita
depois, por `compile_images.py`/`compile_inf.py`:

| Arquivo | Papel |
|---|---|
| `split_bsa.py` | Extrai do `GLOBAL.BSA` original os arquivos-alvo, pristinos, para dentro de `GLOBAL_parts/` (cache interno/transitório — nunca é o "arquivo de trabalho") |
| `varredura_img_bruta.py` | Varredura bruta (paleta genérica, sem curadoria por arquivo) de todo `.IMG` do `GLOBAL.BSA` que ainda não está em `img_manifest.IMAGE_MANIFEST`, decodificado pra PNG só pra revisão visual humana em busca de texto escondido — é como as telas da seção 4 do inventário foram achadas. **Uso concluído em 30/09/2026**: os 946 `.IMG` do `GLOBAL.BSA` estão 100% analisados (ver [inventario-arquivos.md](inventario-arquivos.md#32-dentro-do-globalbsa)) — não sobrou nenhum pra varrer; o script fica no repositório como ferramenta histórica, só volta a ser útil se um dia aparecer um `.IMG` novo fora do manifesto atual |
| `blank_bsa_intro.py` | Gera as versões "vazias" (só apagadas) dos painéis INTRO/HISTORY, como PNG, em `GLOBAL_parts/legivel/empty/` |
| `build_bsa_intro.py` | Desenha a tradução dos 9 painéis INTRO*.IMG por cima de `legivel/empty/`, salva PNG em `GLOBAL_parts/legivel/` |
| `build_bsa_scrolls.py` | Traduz SCROLL01.IMG/SCROLL02.IMG (dentro do BSA) |
| `build_bsa_history.py` | Traduz HISTORY.IMG |
| `build_bsa_ui.py` | Traduz LOGBOOK.IMG / BUYSPELL.IMG / SPELLMKR.IMG |
| `build_bsa_menu.py` | Traduz MENU.IMG |
| `build_bsa_charstat.py` | Traduz CHARSTAT.IMG (ficha de atributos) |
| `build_bsa_yesno.py` | Traduz YESNO.IMG (Sim/Não/Cancelar) |
| `build_bsa_popup.py` | Traduz POPUP3.IMG/POPUP4.IMG (cabeçalhos de lista de arma/armadura) |
| `build_bsa_newmenu.py` | Traduz NEWMENU.IMG (Roubar/Sair) |
| `build_bsa_newold.py` | Traduz NEWOLD.IMG (Tarefa/Status/Cancelar) |
| `build_bsa_newequip.py` | Traduz NEWEQUIP.IMG (tela de saque de masmorra) |
| `build_bsa_labels2.py` | Traduz 5 rótulos pequenos achados na varredura: BONUS.IMG, EQUIPB.IMG, GOLD.IMG, PAGE2.IMG, SPELLBK.IMG |
| `build_bsa_equip.py` | Traduz EQUIP.IMG (variante de EQUIP/NEWEQUIP com Sair/Largar em ordem invertida) |
| `build_bsa_automap.py` | Traduz AUTOMAP.IMG (bússola N/S/L/O + Sair do mapa automático) |
| `build_bsa_slider.py` | Traduz SLIDER.IMG (tira de bússola da visão 3D, rola atrás do quadro fixo de COMPASS.IMG) — imagem crua sem cabeçalho de 12 bytes, não passa por `img_manifest.py`/`compile_images.py` |
| `build_bsa_quote.py` | Traduz QUOTE.IMG (citação de carregamento) |
| `build_bsa_op.py` | Traduz OP.IMG (tela de opções em jogo: Som/Música/Detalhe + Novo/Carregar/Salvar Jogo, Sair pro DOS, Continuar) |
| `build_bsa_forms.py` | Traduz os 17 FORM*.IMG (formulários de efeito de feitiço da Cria-Feitiços) |
| `build_bsa_accprejt.py` | Traduz ACCPREJT.IMG (botões Aceitar/Rejeitar de oferta/negociação) |
| `build_bsa_charspel.py` | Traduz a cópia de CHARSPEL.IMG dentro do GLOBAL.BSA (variante sem o botão "Delete Spell", inalcançável pelo jogo mas traduzida por segurança) - escreve o `.IMG` compilado direto, sem passar por `compile_images.py` |
| `build_bsa_scroll03.py` | Traduz a cópia de SCROLL03.IMG dentro do GLOBAL.BSA (variante sem ilustração, inalcançável pelo jogo mas traduzida por segurança) - escreve o `.IMG` compilado direto, sem passar por `compile_images.py` |
| `build_bsa_inf.py` | Traduz a seção `@TEXT` de cada `.INF` empacotado no BSA |
| `build_inf_loose.py` | Traduz os `.INF` que existem soltos, fora do BSA (`CRYSTAL3.INF`, `IMPPAL1-4.INF`) |
| `img_manifest.py` | Tabela por arquivo: tipo de compressão de saída e se deve embutir paleta — usada só por `compile_images.py` |
| `compile_images.py` | Compila todo PNG de `legivel/` para o `.IMG` binário do jogo |
| `compile_inf.py` | Compila todo texto de `legivel/*.INF` para o formato binário do jogo (acento removido, recifrado se for do BSA) |
| `merge_bsa.py` | Recombina `GLOBAL_parts/*` (já compilado) de volta num `GLOBAL.BSA` completo |
| `build_images.py` | Traduz as imagens que existem como arquivo solto (fora do BSA): `SCROLL03.IMG`, `CHARSPEL.IMG`, `TITLE.IMG`, `TAMRIEL.MNU` |
| `build_charspel_dat.py` | Traduz `CHARSPEL.DAT` (dump de tela cru, sem cabeçalho - bypass de `compile_images.py`, mesmo motivo do `build_bsa_slider.py`) |
| `gerar_legivel_originais.py` | Gera o espelho pristino `Originais/legivel/` (PNG/texto), a partir de `Originais/GLOBAL.BSA`/`.IMG` — regenerável, nunca editado à mão |

Pipeline do `ACD.EXE` (o executável principal do jogo, empacotado em
PKLITE) — ver [pipeline-acd-exe.md](pipeline-acd-exe.md). Único
pipeline que edita dados dentro de código de máquina compilado, não um
arquivo solto nem uma entrada do `GLOBAL.BSA`:

| Arquivo | Papel |
|---|---|
| `pklite_unpack.py` | Descompressor PKLITE (porta em Python do `ExeUnpacker.cpp` do OpenTESArena) |
| `pklite_pack.py` | Recompressor PKLITE + remontagem do `ACD.EXE` final — inclui a reconstrução direta usada pra `build/dosbox/` (`rebuild_dosbox_exe`, sem recompressão, ver [pipeline-acd-exe.md](pipeline-acd-exe.md#a-solução-real-nunca-recompactar-pklite-para-o-dosbox)) |
| `build_acd_exe.py` | Descompacta, aplica a tradução nas strings pelos offsets reais no buffer, e remonta o `ACD.EXE` |

Orquestração:

| Arquivo | Papel |
|---|---|
| `build_all.py` | Roda todo o pipeline de imagens/BSA na ordem certa, de ponta a ponta |

## Convenção de import/execução

Os scripts são feitos para rodar tanto de dentro de `scripts/` quanto da
raiz do projeto, sempre assim:

```bash
python3 scripts/build_bsa_intro.py
# ou, de dentro de scripts/:
python3 build_bsa_intro.py
```

Todos calculam `ROOT_DIR = Path(__file__).resolve().parent.parent` (ou
equivalente) em vez de depender do diretório de trabalho atual — ao criar
um script novo, siga o mesmo padrão.

## Padrão split → build → merge

Tanto o pipeline de texto quanto o de imagens seguem a mesma forma
geral, e vale manter esse padrão em qualquer script novo:

1. **split**: extrai/copia do original pristino para uma pasta de
   trabalho, sempre reproduzível (rodar de novo = resetar).
2. **build**: um ou mais scripts editam a pasta de trabalho *in loco*,
   cada um responsável por um subconjunto de arquivos (ou, no caso das
   imagens, por um subconjunto de *áreas* de um mesmo arquivo).
3. **merge**: recombina a pasta de trabalho no artefato final.

Isso existe porque vários desses arquivos (o `GLOBAL.BSA` inteiro, o
`TEMPLATE.DAT` de cada arquivo de texto) são grandes demais ou têm
formato binário demais para editar diretamente — trabalhar em pedaços
soltos e desconhecer o resto do arquivo é o que torna a tradução
possível e revisável.
