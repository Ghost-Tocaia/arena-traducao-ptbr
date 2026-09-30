# Inventário de arquivos do jogo

Catálogo de **todos** os arquivos relevantes do jogo — tanto os soltos na
pasta de instalação quanto os que vivem empacotados dentro de
`GLOBAL.BSA` — organizados em 4 categorias:

1. **Traduzidos** — já têm tradução aplicada e aprovada.
2. **Analisados, mas sem tradução necessária** — foram abertos/inspecionados
   e não contêm texto para o jogador (dado binário puro, ou moldura
   decorativa sem rótulo, ou arquivo vazio).
3. **Não analisados** — ainda não foram abertos/verificados individualmente.
   Agrupados por extensão com uma nota do que a extensão provavelmente
   representa (inferido de convenções conhecidas do formato Arena/DOS,
   **não confirmado arquivo por arquivo**).
4. **Confirmados com texto, pendentes de tradução** — já abertos/vistos
   visualmente (via `varredura_imagens/`, ver
   [pipeline-imagens.md](pipeline-imagens.md#varredura-bruta-de-imagens-não-analisadas)),
   confirmado que têm texto de jogador, mas a tradução ainda não foi
   feita. Esta lista cresce conforme mais arquivos de `varredura_imagens/`
   são revisados — bem menor que a categoria 3 por enquanto, já que a
   varredura em massa ainda não foi 100% revisada manualmente.

A pasta de referência para "todos os arquivos soltos" é a instalação real
do jogo (Steam), não `Originais/` deste repositório — `Originais/` guarda
só uma cópia pristina dos arquivos que o projeto já mexeu ou usa como
referência de paleta, não o jogo inteiro. Contagens totais nesta página:
**159 arquivos soltos** na pasta do jogo + **2441 arquivos** dentro de
`GLOBAL.BSA` (ver [pipeline-imagens.md](pipeline-imagens.md#global-bsa) para
o formato do archive).

---

## 1. Arquivos traduzidos

### 1.1 Soltos na pasta do jogo (28 arquivos + o container `GLOBAL.BSA`)

| Arquivo | Tipo | Fluxo/script | Observação |
|---|---|---|---|
| `ARTFACT1.DAT` | texto (`#hex` blocks) | `split_template.py`/`mount_template_part.py` | descrições de artefatos |
| `ARTFACT2.DAT` | texto (`#hex` blocks) | idem | descrições de artefatos (parte 2) |
| `CITYINTR` | texto (`#hex` blocks) | idem | texto de chegada em cidade |
| `CITYTXT` | texto (`#hex` blocks) | idem | textos gerais de cidade |
| `DUNGEON.TXT` | texto (`#hex` blocks) | idem | textos de masmorra |
| `EQUIP.DAT` | texto (`#hex` blocks) | idem | textos de equipamento |
| `HELP.TXT` | texto (`#hex` blocks) | idem | tela de ajuda in-game |
| `JAGTEMP.DAT` | texto (`#hex` blocks) | idem | falas de Jagar Tharn |
| `MUGUILD.DAT` | texto (`#hex` blocks) | idem | textos da Guilda dos Magos |
| `QUESTION.TXT` | texto (`#hex` blocks) | idem | perguntas de criação de personagem |
| `SELLING.DAT` | texto (`#hex` blocks) | idem | textos de venda/loja |
| `SPELLMKR.TXT` | texto (`#hex` blocks) | idem | textos da Cria-Feitiços |
| `SPELLS.LST` | texto (`#hex` blocks) | idem | lista/descrições de feitiços |
| `TAVERN.DAT` | texto (`#hex` blocks) | idem | textos de taverna |
| `TEMPLATE.DAT` | texto (`#hex` blocks, 809 blocos) | `split_template.py`/`mount_template_part.py`/`merge_template.py` + `reflow_template.py` | banco de falas de cidadão; **não é seguro traduzir para DOSBox real** (funciona no OpenTESArena) — ver [nota completa](#templatedat--arquivo-real-do-jogo-mas-não-é-seguro-traduzir-para-dosbox) |
| `ACD.EXE` | executável DOS, comprimido PKLITE | `build_acd_exe.py` (pipeline própria, fora do padrão split/build/merge) | todo texto mapeado já traduzido, nada pendente conhecido; ver [pipeline-acd-exe.md](pipeline-acd-exe.md#o-que-fica-de-propósito-em-inglês) pro que fica de propósito em inglês (trava o motor) e nomes próprios |
| `READ.ME` | texto solto (não `#hex`) | tradução manual | leia-me do patch 1.05 |
| `README.TXT` | texto solto (não `#hex`) | tradução manual | leia-me da versão CD-ROM 1.07 |
| `CRYSTAL3.INF` | `.INF` solto, **não** cifrado | `build_inf_loose.py` | sobrepõe a cópia dentro do `GLOBAL.BSA` — ver [gotcha crítico](pipeline-inf.md#gotcha-crítico-alguns-inf-também-existem-como-arquivo-solto--e-esse-é-o-que-vale) |
| `IMPPAL1.INF`–`IMPPAL4.INF` (4) | `.INF` solto, **não** cifrado | `build_inf_loose.py` | idem — níveis do Palácio Imperial |
| `CHARSPEL.IMG` | pixel art | `build_images.py` | tela de criação de feitiço |
| `SCROLL03.IMG` | pixel art | `build_images.py` | pergaminho de abertura (3º) |
| `TITLE.IMG` | pixel art | `build_images.py` | tela de título |
| `TAMRIEL.MNU` | pixel art (LZSS, achado via revisão manual, 30/09/2026) | `build_images.py` | mapa "escolha sua província natal" — só "Empire of"→"Império de" e "EXIT"→"SAIR"; os 9 nomes de província são nomes próprios preservados |
| `CHARSPEL.DAT` | pixel art crua, sem cabeçalho (achado via revisão manual, 30/09/2026) | `build_charspel_dat.py` | dump de tela — grimório/resistências de um personagem de exemplo; referenciado de verdade dentro do `ACD.EXE` original (`charspel.dat`), traduzido por segurança mesmo com reachability incerta |
| `GLOBAL.BSA` | container/archive | `merge_bsa.py` | ver detalhamento interno na seção 1.2 |

### 1.2 Dentro do `GLOBAL.BSA`

#### Imagens (pixel art) — 53 arquivos

| Arquivo | Tela | Script |
|---|---|---|
| `SCROLL01.IMG`, `SCROLL02.IMG` | pergaminhos de narração de abertura | `build_bsa_scrolls.py` |
| `INTRO01.IMG`–`INTRO09.IMG` (9) | painéis da visão do golpe de Jagar Tharn | `build_bsa_intro.py` |
| `HISTORY.IMG` | parágrafo de contexto antes da visão | `build_bsa_history.py` |
| `LOGBOOK.IMG` | diário | `build_bsa_ui.py` |
| `BUYSPELL.IMG` | Grimório (comprar feitiço) | `build_bsa_ui.py` |
| `SPELLMKR.IMG` | Cria-Feitiços | `build_bsa_ui.py` |
| `MENU.IMG` | menu principal | `build_bsa_menu.py` |
| `CHARSTAT.IMG` | ficha de atributos | `build_bsa_charstat.py` |
| `YESNO.IMG` | diálogo Sim/Não/Cancelar | `build_bsa_yesno.py` |
| `POPUP3.IMG` | cabeçalho de lista de armas (Nome/Mãos/Peso/Custo) | `build_bsa_popup.py` |
| `POPUP4.IMG` | cabeçalho de lista de armaduras (Nome/Protege/Peso/Custo) | `build_bsa_popup.py` |
| `NEWMENU.IMG` | botões Roubar/Sair (saque de contêiner) | `build_bsa_newmenu.py` |
| `NEWOLD.IMG` | botões Tarefa/Status/Cancelar (quadro de guilda) | `build_bsa_newold.py` |
| `NEWEQUIP.IMG` | tela de saque de masmorra (Nível:/Largar/Grimório/Sair) | `build_bsa_newequip.py` |
| `BONUS.IMG`, `EQUIPB.IMG`, `GOLD.IMG`, `PAGE2.IMG`, `SPELLBK.IMG` | rótulos pequenos: "Bônus:", "Equipamento", "Ouro", "Próxima", "Grimório" | `build_bsa_labels2.py` |
| `EQUIP.IMG` | variante do saque de masmorra (Sair/Grimório/Largar em ordem diferente do `NEWEQUIP.IMG`) | `build_bsa_equip.py` |
| `AUTOMAP.IMG` | mapa automático — bússola N/S/L/O + Sair | `build_bsa_automap.py` |
| `SLIDER.IMG` | tira de bússola da visão 3D (N/NE/L/SE/S/SO/O/NO, rola atrás do quadro fixo do `COMPASS.IMG`) — imagem crua sem cabeçalho, não passa pelo `compile_images.py` | `build_bsa_slider.py` |
| `QUOTE.IMG` | citação de carregamento (Gaiden Shinji, Mestre-Espadachim) | `build_bsa_quote.py` |
| `OP.IMG` | tela de opções (Som/Música/Detalhe + Novo/Carregar/Salvar Jogo, Sair para DOS, Continuar) | `build_bsa_op.py` |
| `FORM1.IMG`–`FORM15.IMG`, `FORM4A.IMG`, `FORM6A.IMG` (17) | formulários de efeito de feitiço da Cria-Feitiços (Alcance/Chance/Duração/Aumento/Força/etc. + Custo do Feitiço/Sair) | `build_bsa_forms.py` |
| `ACCPREJT.IMG` | botões Aceitar/Rejeitar (resposta a uma oferta/negociação) | `build_bsa_accprejt.py` |
| `CHARSPEL.IMG` (cópia do BSA) | variante do Grimório sem o botão "Delete Spell" (3 botões, não 4) — mesma tela já traduzida como arquivo solto (acima), mas o jogo nunca lê esta cópia (`VFS::Manager::open()` sempre prioriza o arquivo solto - ver seção 3.2); traduzida por segurança mesmo assim | `build_bsa_charspel.py` |
| `SCROLL03.IMG` (cópia do BSA) | variante do 3º pergaminho de abertura sem a ilustração de paisagem (só textura de pergaminho) e sem paleta embutida (usa `CHARSHT.COL`) — mesmo texto da versão solta (acima), mesma situação de cópia inalcançável, traduzida por segurança | `build_bsa_scroll03.py` |

Duas telas (`DAGOTH3.INF`, `ELDEN2.INF`, ver abaixo) usam **adaptação
criativa** em vez de tradução literal para enigmas de trocadilho em
inglês sem equivalente direto em português — sinalizado no código para
revisão do usuário. Ver
[pipeline-inf.md](pipeline-inf.md#enigmas-intraduzíveis).

#### Arquivos `.INF` com texto de sabedoria (`@TEXT`) — 55 arquivos

Placas, bilhetes, descrições ambientais e enigmas de masmorra/localização,
todos via `scripts/build_bsa_inf.py` + `scripts/inf_codec.py`. Ver
[pipeline-inf.md](pipeline-inf.md) para o formato/cifra.

```
AGTEMPL.INF   BGATE2.INF   CASTLE.INF   CRYPT1.INF   CRYPT3.INF
CRYPT4.INF    CRYSTAL1.INF CRYSTAL3.INF CRYSTAL4.INF DAGOTH1.INF
DAGOTH2.INF   DAGOTH3.INF  DEMO.INF     ELDEN1.INF   ELDEN2.INF
FANG1.INF     FANG2.INF    FORTI2.INF   GEMIN1.INF   GEMIN2.INF
HALLS1.INF    HALLS2.INF   HALLS3.INF   IMPPAL1.INF  IMPPAL2.INF
IMPPAL3.INF   IMPPAL4.INF  KHU1.INF     KHU2.INF     KHUTEST.INF
LABRNTH1.INF  LABRNTH2.INF MAGE.INF     MGTEMPL1.INF MGTEMPL2.INF
MURK1.INF     MURK2.INF    NOBLE.INF    NOBLE1.INF   NOBLE2.INF
NOBLE3.INF    SD1.INF      SD3.INF      SELENE1.INF  SELENE2.INF
SKEEP1.INF    SKEEP2.INF   START.INF    STKEEP1.INF  TOWER.INF
TOWER1.INF    TOWER2.INF   TOWER6.INF   TOWER8.INF   VILPAL.INF
```

(`CRYSTAL3.INF` e `IMPPAL1-4.INF` aparecem tanto aqui — a cópia de
dentro do `GLOBAL.BSA`, traduzida por `build_bsa_inf.py` — quanto na
tabela 1.1 como arquivo solto, traduzido por `build_inf_loose.py`. As
duas cópias existem no jogo de verdade; a solta é a que prevalece.)

---

## 2. Arquivos analisados, mas sem tradução necessária

### 2.1 Soltos na pasta do jogo

| Arquivo | Motivo |
|---|---|
| `EXTRA` | arquivo vazio (0 bytes) |
| `ARENA.BAT`, `INSTALL.CFG`, `CONFIG.CPY`, `BOOTEXEC.CPY`, `ULTRAMID.INI` | scripts/config de instalação e boot DOS (comandos, caminhos, parâmetros técnicos) — nunca aparecem como texto de jogo para o jogador |
| `steam_autocloud.vdf` | metadado da Steam Cloud, não é conteúdo original do jogo de 1994 |
| `GLOBAL.BSA.MOD` | artefato de outra ferramenta/mod, não é um arquivo original do jogo |
| `STARTGAM.MNU` | pixel art (LZSS) — decodificado e revisado visualmente (30/09/2026): só a arte de fundo (cabana à noite), nenhum texto |
| `MAPBTNS.MNU` | pixel art crua (mesma família do `SLIDER.IMG`) — decodificada e confirmada **100% preta** pixel a pixel (um único índice de cor, 0, em todos os 64000 pixels), sem nenhum conteúdo visível |
| `CLASSES.DAT` | 216 bytes, zero strings legíveis (`strings` não encontra nada) — tabela binária pura (provavelmente valores numéricos de definição de classe) |
| `DISKS.BAK` | script batch do instalador DOS (`del a.exe`/`move arena.exe a.exe`/...), não é texto de jogo |

### 2.2 Dentro do `GLOBAL.BSA`

| Arquivo(s) | Motivo |
|---|---|
| `NBOX.IMG`, `SBOX.IMG` | sprites decorativos de objeto (baú/caixa), sem texto |
| `STAT11.IMG`, `STAT13.IMG`, `STAT15.IMG`, `STAT21.IMG`, `STAT23.IMG`, `STAT25.IMG` | sprites de estátua (golem), sem texto |
| `BOOKS1.IMG`, `BOOKS2.IMG` | sprites de livro (fechado/aberto), sem texto legível — só linhas decorativas simulando texto |
| `POPUP.IMG`, `POPUP2.IMG`, `POPUP5.IMG`, `POPUP7.IMG`, `POPUP8.IMG`, `POPUP11.IMG`, `NEWPOP.IMG` | molduras decorativas vazias — mesma família visual de `POPUP3.IMG`/`POPUP4.IMG`, mas sem nenhum rótulo desenhado |
| `EQUIPMEN.IMG` | sprite decorativo (ícone de elmo/arma/livro), sem texto |
| `LOADSAVE.IMG` | tela de salvar/carregar — só 10 linhas vazias de slot, sem texto baked-in (o jogo desenha os nomes dos saves dinamicamente) |
| `DLGT.IMG`, `TZDLGT.IMG`, `T_DLGT.IMG`, `DLGTD.IMG`, `XDLGTD.IMG`, `POPTALK.IMG` | cabeçalho `.IMG` inválido (dimensões absurdas ao decodificar, ex. 28527×28527) — provavelmente não são `.IMG` de verdade apesar do nome/extensão; nenhum conteúdo visualizável foi obtido |
| `NOEXIT.IMG` | tela pequena (43×13, comprimida "type 8") sem paleta embutida — renderizada nas 4 paletas `.COL` do jogo (`PAL`, `CHARSHT`, `DAYTIME`, `DREARY`) para revisão visual; nenhuma mostra letras reconhecíveis, e o usuário confirmou que a imagem não parece conter texto algum. Revisão anterior desta página (baseada só numa forma fraca vista em escala de cinza) tinha marcado como "tem texto real, bloqueado por paleta errada" — corrigido |
| 856 arquivos `.IMG` (lista completa em [`varredura_imagens/_sem_traducao.txt`](../varredura_imagens/_sem_traducao.txt)) | revisão visual manual, arquivo por arquivo, de todos os 908 PNGs em `varredura_imagens/` pelo usuário (30/09/2026) — confirmado sem texto/tradução necessária. Cobre praticamente todo o restante da varredura bruta; os poucos nomes que sobraram fora dessa lista (não revisados) estão na seção 3 |
| `CITY.IMG`, `DITHER.IMG`, `DITHER2.IMG`, `DUNGEON.IMG`, `DZTTAV.IMG`, `NOCAMP.IMG`, `NOSPELL.IMG`, `P1.IMG`, `S2.IMG`, `TOWN.IMG`, `UPDOWN.IMG` | imagens cruas sem cabeçalho (mesma família do `SLIDER.IMG`), por isso a varredura em massa nunca conseguiu decodificá-las — dimensões reais achadas no `RawImgOverride` do `IMGFile.cpp` do OpenTESArena e decodificadas com elas (30/09/2026). Todas confirmadas sem texto: `DITHER`/`DITHER2` são tiras de gradiente de dithering; `CITY`/`DUNGEON`/`TOWN` são ícones de sprite pequenos; `DZTTAV` é o desenho de uma placa de taverna (textura 64×64, ver o caso especial no próprio `IMGFile.cpp`); `NOCAMP`/`NOSPELL` são ícones de fogueira/estrela mágica; `UPDOWN` é o ícone de escada acima/abaixo; `P1`/`S2` são barras de ícones de menu (descansar/roubar) — botões só com pictograma, sem nenhuma palavra em inglês |
| `CRYPT2.INF`, `CRYSTAL2.INF` | têm seção `@TEXT`, mas ela só contém marcadores de motor (`*TEXT N` / `+N`), nenhuma prosa real |
| 36 arquivos `.INF` sem `@TEXT`: `BGATE1`, `BS1`, `CAS`, `DCN`, `DCR`, `DCW`, `DWN`, `DWR`, `EQUIP`, `FORTI1`, `GENERAL`, `GUARD`, `INT`, `MCN`, `MCR`, `MCS`, `MCW`, `MWN`, `MWR`, `MWS`, `NEWTAV`, `RD1`, `RD2`, `SD2`, `TAVERN`, `TCN`, `TCR`, `TCS`, `TCW`, `TEMPLE`, `TOWER3`, `TWN`, `TWR`, `TWS`, `WCRYPT`, `WCRYPT8` | blocos de masmorra/edifício genéricos e reaproveitados (layout de piso/parede/sons), sem nenhuma seção `@TEXT` no arquivo — confirmado por varredura decodificando os 93 `.INF` do `GLOBAL.BSA` e checando a presença literal de `"@TEXT"` |

Isso fecha a verificação dos **93 arquivos `.INF`** do `GLOBAL.BSA`: 55
traduzidos + 2 com `@TEXT` vazio + 36 sem `@TEXT` = 100% analisados.

---

## 3. Arquivos não analisados

### 3.1 Soltos na pasta do jogo

**Candidatos promissores**: todos os 5 que havia aqui (`STARTGAM.MNU`,
`TAMRIEL.MNU`, `MAPBTNS.MNU`, `CLASSES.DAT`, `CHARSPEL.DAT`) foram
decodificados e resolvidos em 30/09/2026 — `TAMRIEL.MNU`/`CHARSPEL.DAT`
traduzidos (seção 1.1), os outros 3 confirmados sem texto (seção 2.1).
Esta subseção fica vazia até aparecer um novo candidato.

**Provavelmente sem texto de jogador** (dados binários de assets —
sprites, animações, som, música, fontes bitmap, tabelas numéricas;
verificado apenas por extensão/convenção conhecida do formato Arena/DOS,
**nenhum arquivo individual desta lista foi aberto**):

| Extensão(ões) | Qtde | O que provavelmente é |
|---|---|---|
| `.FLC` | 17 | vídeos de animação (Autodesk Animator FLIC) — cinemáticas |
| `.ADV` | 19 | drivers/config de placa de som (Sound Blaster, AdLib, Gravis, etc.) |
| `.MIF` | ~18 (soltos, além dos ~533 dentro do BSA) | dados de layout de masmorra/exterior (geometria de blocos) |
| `.64` / `.65` | 6 + 5 | pares de arquivo de dados por resolução/config, provável tabela numérica |
| `.$$$` / `.$$2` | 5 + 1 | arquivos de estado/cache temporário do instalador ou do próprio jogo |
| `.DAT` (fontes/dados) | `ARENAFNT`, `CHARFNT`, `FONT4`, `FONT_A-D`, `FONT_S`, `TEENYFNT`, `NAMECHNK`, `NAMES`, `RAND`, `POINTER1`, `GUARD` | fontes bitmap, fragmentos de nome para geração procedural de NPC, tabelas de aleatoriedade — formato binário puro confirmado (sem strings legíveis) em `CLASSES`/`NAMES`/`RAND`; `GUARD.DAT` também é binário puro (não é texto apesar do que a ferramenta `file` sugere) |
| `.COL` | 4 | paletas de cor (`PAL`, `CHARSHT`, `DAYTIME`, `DREARY`) — já usadas como referência de paleta por vários scripts deste projeto, nunca como fonte de texto |
| `.CIF` | 1 (`ARROWS.CIF`) | sprite/quadro de imagem comprimido |
| `.CEL` | 2 (`MAGE.CEL`, `WARRIOR.CEL`, `ROGUE.CEL`) | sprite de personagem |
| `.RCI` | 2 (`LAVAANI.RCI`, `WATERANI.RCI`, `SPPARTS.RCI`) | quadros de animação de textura (lava, água) |
| `.LGT` | 2 (`FOG.LGT`, `NORMAL.LGT`) | tabela de iluminação/sombra |
| `.BNK` | 4 (`GM1`, `GM2`, `MT1`, `MT2`) | banco de instrumentos MIDI |
| `.VOC` | 2 (`FANFARE1`, `FANFARE2`) | efeito sonoro digitalizado |
| `.XFM` | 1 (`WINGAME.XFM`) | dados de conversão/patch MIDI |
| `.EMS`, `.NTZ`, `.GLD`, `.CLR` | 1 cada | formatos não documentados neste projeto; nomes sugerem memória expandida, "notas"(?), "gold"(?) e cores de nome |
| `.ICO` | 1 (`ARENA.ICO`) | ícone do executável |
| `.EXE` (`ULTRAMID.EXE`, `INSTALL.EXE`) | 2 | utilitários de terceiros (MIDI, instalador) — não são o motor do jogo |
| `FOG.TXT` | 1 | apesar do nome `.TXT`, o conteúdo é binário (dados de fog/iluminação, não texto) |
| `SOUND.CFG` | 1 | verificado (30/09/2026): tem texto real — lista de placas de som pro utilitário de configuração de áudio original da instalação DOS ("No Sound"/"No Music" + nomes de marca como "Sound Blaster", a maioria nome próprio). Não usado pelo OpenTESArena (áudio via SDL) nem, na prática, pelo DOSBox real (que emula um Sound Blaster fixo, sem rodar o utilitário de detecção original) — prioridade baixa por reachability, não por falta de texto |

### 3.2 Dentro do `GLOBAL.BSA`

**Varredura por texto legível feita em 30/09/2026** (script ad-hoc,
não faz parte do pipeline): os 1402 arquivos das 9 extensões abaixo
foram lidos e checados por sequências de texto ASCII legível
(threshold de 10+ caracteres). Zero prosa real encontrada — só ruído
binário (dados de animação/textura comprimidos que por acaso caem na
faixa ASCII imprimível) e o cabeçalho padrão "Creative Voice File" dos
`.VOC` (identificador de formato, não texto de jogador). Nenhum
arquivo individual foi aberto/decodificado visualmente — a varredura
só confirma "sem sequência de texto óbvia", não decodifica o conteúdo
como as imagens acima.

| Extensão | Qtde | O que provavelmente é | Prioridade |
|---|---|---|---|
| `.IMG` | 0 restantes | ver seção 2.2 — os 946 `.IMG` do BSA já estão 100% analisados | — |
| `.MIF` | 533 | dados de layout de masmorra/exterior (geometria) | baixa |
| `.CFA` | 340 | quadros de animação de criatura/personagem comprimidos | baixa |
| `.SET` | 180 | conjuntos de sprite/textura agrupados | baixa |
| `.DFA` | 79 | quadros de animação de porta/objeto | baixa |
| `.VOC` | 76 | efeito sonoro digitalizado | baixa |
| `.RMD` | 70 | metadado de bloco de masmorra aleatória | baixa |
| `.CIF` | 58 | sprite/quadro de imagem comprimido (ex.: variações de equipamento por raça, como `0EQUIP.CIF`/`1EQUIP.CIF`) | baixa |
| `.XFM` | 33 | dados de conversão/patch MIDI | baixa |
| `.XMI` | 33 | trilha musical (eXtended MIdi) | baixa |
| `.INF` | 0 restantes | ver seção 2.2 — os 93 `.INF` do BSA já estão 100% analisados | — |

**Nota histórica** (recontado por diff binário real entre
`Originais/GLOBAL.BSA` e `build/GLOBAL.BSA`, não por contagem manual):
os 946 `.IMG` do `GLOBAL.BSA` foram completamente fechados em duas
etapas em 30/09/2026. Primeiro, revisão visual manual de todos os 908
PNGs de `varredura_imagens/` (51 traduzidos, seção 1.2 + 876
confirmados sem tradução necessária, seção 2.2). Isso deixou 13 sem
resolver: 11 que a varredura em massa nunca conseguiu decodificar
(cabeçalho inválido e não são textura quadrada crua) e 2 achados na
própria reconciliação (`CHARSPEL.IMG`/`SCROLL03.IMG`, duplicados
dentro do BSA). Os dois casos foram resolvidos investigando o código-
fonte do OpenTESArena: os 11 são todos imagens cruas sem cabeçalho
(mesma família do `SLIDER.IMG`) com dimensões hardcoded em
`IMGFile.cpp`'s `RawImgOverride` - decodificados com as dimensões
certas, nenhum tem texto (ver seção 2.2 para o que cada um é). Os 2
duplicados foram confirmados inalcançáveis pelo jogo - `VFS::Manager::
open()` sempre prioriza o arquivo solto sobre a mesma entrada dentro
do `GLOBAL.BSA` (mesmo princípio do gotcha do `.INF`, aqui confirmado
direto no código-fonte) - mas traduzidos mesmo assim por segurança (são
variantes de layout genuinamente diferentes das versões soltas, não
bytes idênticos - ver seção 1.2). 53 + 876 + 11 + 6 (cabeçalhos
inválidos) = 946 - conta fechada.

---

## 4. Confirmados com texto, pendentes de tradução

Encontrados via `scripts/varredura_img_bruta.py` (ver
[pipeline-imagens.md](pipeline-imagens.md#varredura-bruta-de-imagens-não-analisadas)) —
908 PNGs em `varredura_imagens/` (raiz do projeto, fora do pipeline de
build) para revisão visual manual. **Revisão completa dos 908 concluída
em 30/09/2026** (usuário revisou cada arquivo manualmente). Todos os 28
que continham texto já foram traduzidos — os 26 do primeiro lote
(`QUOTE.IMG`, `AUTOMAP.IMG`, `BONUS.IMG`, `EQUIP.IMG`, `EQUIPB.IMG`,
`GOLD.IMG`, `OP.IMG`, `PAGE2.IMG`, `SPELLBK.IMG`, os 17 `FORM*.IMG`)
mais `ACCPREJT.IMG`, achado numa rodada de revisão posterior — ver
seção 1.2 acima. Esta tabela fica vazia permanentemente: não há mais
`.IMG` não analisado no `GLOBAL.BSA` (ver seção 3.2).

---

## `TEMPLATE.DAT` — arquivo real do jogo, mas não é seguro traduzir para DOSBox

Correção de uma nota antiga desta página: `TEMPLATE.DAT` **não é**
nome de trabalho genérico nem lixo — é o **nome real** de um arquivo
grande do jogo (confirmado pelo usuário), um banco de falas de cidadão
com 809 blocos `#hexid` (diálogo de "Where is...?"/direção, "Who are
you?", conversa de fundo sobre profissão/posse de taverna, rumor de
artefato único, etc — ver [pipeline-textos.md](pipeline-textos.md)
para o formato `#hexid`). Segue o mesmo fluxo split → traduzir partes
→ merge descrito ali, só que hoje é reconstruído direto num único
passo por `scripts/reflow_template.py` (sem `TEMPLATE_parts/`, que foi
removido).

**Achado crítico (04-05/09/2026)**: `TEMPLATE.DAT` **não tolera
nenhuma edição de byte**, por menor que seja, quando rodado no DOSBox
real (via Steam/Proton) — só no OpenTESArena que ele funciona editado.
Isolado por bisecção ao vivo com o usuário, testes em ordem crescente
de certeza:

1. Tradução completa (linhas quebradas em ~31 caracteres por um bug do
   pipeline antigo) — diálogos trocados (pedia direção de prédio,
   recebia fala de "sou dono da taverna com meus sócios" ou de
   informante de artefato).
2. Mesma tradução, mas com `scripts/reflow_template.py` corrigindo a
   estrutura de linha pra bater exatamente com o original (cada bloco
   com a mesma contagem de parágrafo/linha do inglês, nenhuma palavra
   alterada, só a posição da quebra) — **o bug persistiu**.
3. Arquivo 100% original + só a primeira palavra de um bloco de
   direção traduzida (8 substituições, arquivo cresceu **1 byte no
   total**) — bug persistiu, mas num bloco *diferente* do que se
   esperava (`#0289`, ~5,4KB adiante do bloco mexido).
4. Arquivo 100% original + **uma única letra trocada, sem alterar o
   tamanho do arquivo em nada** (`O`→`A` em "Oh, you'll find", byte
   384312 igual nos dois arquivos, só a posição 192568 diferente) —
   **o bug ainda apareceu** ("Who are you?" respondeu só "man", um
   sistema de diálogo completamente diferente do byte alterado).

Conclusão: não é sensível a *tamanho* de arquivo nem a offset
acumulado — é sensível a **qualquer desvio do conteúdo exato**, mesmo
1 byte em qualquer posição, independente de onde. Isso é o mesmo
padrão do campo `entities.attributeNames` do `ACD.EXE` (ver
[pipeline-acd-exe.md](pipeline-acd-exe.md)): fortíssimo indício de uma
validação de integridade (checksum/CRC) do conteúdo exato do arquivo,
calculada em algum lugar não identificado (provavelmente dentro do
próprio `ACD.EXE`) — sem desmontar esse código, não dá pra confirmar
o mecanismo exato nem contorná-lo.

**Decisão do usuário**: manter a versão traduzida e com a estrutura
corrigida instalada (funciona perfeitamente no OpenTESArena, que não
impõe essa validação) — jogadores no DOSBox real vão ocasionalmente
ver um diálogo de citizen "trocado" (a fala certa de outro contexto
aparecendo no lugar da esperada) até (se algum dia) a validação for
identificada e neutralizada via engenharia reversa do `ACD.EXE`.
`ARTFACT1.DAT`/`ARTFACT2.DAT` (que também usam o mesmo formato
`#hexid`, mas são arquivos separados) não mostraram esse problema nos
testes desta sessão e continuam traduzidos normalmente.
