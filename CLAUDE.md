# CLAUDE.md

Este arquivo orienta o Claude Code ao trabalhar neste repositório. As
instruções aqui e nos documentos referenciados **têm prioridade sobre o
comportamento padrão** — siga-as à risca.

## O projeto

Tradução para português brasileiro de *The Elder Scrolls: Arena* (1994,
DOS), feita por Ghost Tocaia (crédito no jogo). O trabalho
combina engenharia reversa dos formatos de arquivo do jogo com a
tradução propriamente dita — texto corrido, itens de menu e texto que é
pixel art desenhada em imagens.

Não existe suíte de testes automatizada. A verificação é: (1) round-trip
byte a byte na hora de compilar qualquer arquivo binário (`compile_images.py`/
`compile_inf.py` fazem isso, ver [docs/pipeline-imagens.md](docs/pipeline-imagens.md#verificação-de-round-trip-obrigatória-em-compile_imagespy)),
e (2) revisão visual humana de cada preview antes de considerar algo
pronto.

**Os arquivos de trabalho ficam sempre em formato aberto.** Toda imagem
traduzida vive como PNG (não `.IMG`) e todo `.INF` traduzido vive como
texto puro com acento (não cifrado/comprimido) numa pasta `legivel/` ao
lado de onde o arquivo original ficava — o `.IMG`/`.INF` binário do
jogo só é montado no fim, por `compile_images.py`/`compile_inf.py`. Ver
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#legivel-vs-formato-do-jogo).

## Publicação

O projeto está publicado publicamente no GitHub, sob a conta pessoal
do tradutor (**Ghost Tocaia** — separada de outras contas/organizações
que o usuário também usa): https://github.com/Ghost-Tocaia/arena-traducao-ptbr.
A identidade git (`user.name`/`user.email`) foi configurada **só
localmente neste repositório** (sem `--global`), propositalmente
diferente do e-mail pessoal do usuário — não assuma que a config
global da máquina é a identidade certa pra commits aqui.

`Originais/`, `varredura_imagens/` e `_dosbox_test/` nunca são
commitados (ver `.gitignore`) — são ativos do jogo original (Bethesda/
ZeniMax) ou cópias de trabalho/teste da instalação real, não trabalho
do projeto. Continuam no disco local, só fora do controle de versão.

`nexus_release/` (gitignorado, só local, não existe num clone novo)
guarda os pacotes `.zip` prontos pra upload manual no Nexus Mods (um
por plataforma — DOSBox e OpenTESArena — cada um já com o
`ACD.EXE`/`TEMPLATE.DAT` certo embutido, gerados a partir de `build/`)
e o texto da página do mod pronto pra copiar/colar
(`nexus-texto.html` — artifact publicado com botão de cópia
*formatada*, não Markdown nem tags HTML cruas, pro editor visual do
Nexus; `texto-pagina-nexus.txt` é a mesma cópia em texto puro).

`README.md` é o arquivo voltado ao público não técnico (como instalar,
estimativa de % traduzido por versão) — **mantenha os números de lá
(e os de `nexus_release/`) em sync** com qualquer novo arquivo
traduzido/revertido. Ver a entrada de 01/10/2026 no "Status conhecido"
mais abaixo pra como esse percentual deve ser calculado (nunca por
contagem de arquivos/impressão qualitativa).

## Comece por aqui

- **[docs/traducao-estilo.md](docs/traducao-estilo.md)** — regras de
  conteúdo: tom medieval/Elder Scrolls, quais nomes nunca traduzir,
  placeholders do motor do jogo, crédito do tradutor.
- **[docs/estrutura-arquivos.md](docs/estrutura-arquivos.md)** — mapa de
  pastas, inventário de todo script em `scripts/`, e o padrão geral
  split → build → merge usado no projeto inteiro.
- **[docs/pipeline-textos.md](docs/pipeline-textos.md)** — como
  traduzir um arquivo de texto do jogo (`.DAT`/`.TXT`/`.LST`): formato
  dos blocos `#hex`, o fluxo `TEMPLATE` genérico, o dicionário
  `translations`.
- **[docs/pipeline-imagens.md](docs/pipeline-imagens.md)** — como
  traduzir uma tela cujo texto é pixel art: formatos `GLOBAL.BSA`/
  `.IMG`, os dois codecs de compressão, o gotcha de paleta por arquivo,
  técnicas de apagar/desenhar/medir/posicionar texto, e o estado atual
  de cada tela.
- **[docs/pipeline-inf.md](docs/pipeline-inf.md)** — como traduzir o
  texto de sabedoria de masmorra (`.INF`, dentro do `GLOBAL.BSA`):
  cifra XOR, formato `@TEXT`, o gotcha de blocos com várias sub-frases
  de prosa, e enigmas adaptados por trocadilho intraduzível.
- **[docs/pipeline-acd-exe.md](docs/pipeline-acd-exe.md)** — como
  traduzir texto dentro do `ACD.EXE` (executável comprimido PKLITE):
  os três helpers de patch por offset/busca/array, os campos que
  travam o motor com qualquer edição (`AttributeNames`,
  `CitizenRumorGenerator`) e por quê, a técnica de inversão
  substantivo/adjetivo usada no gerador de nome de taverna — todo texto
  mapeado do `ACD.EXE` já está traduzido, nada pendente conhecido ali.
- **[docs/inventario-arquivos.md](docs/inventario-arquivos.md)** —
  catálogo de todo arquivo do jogo (solto na pasta de instalação ou
  empacotado dentro do `GLOBAL.BSA`), separado em traduzido / analisado
  sem necessidade de tradução / não analisado / confirmado com texto
  pendente de tradução. **Todas as categorias estão fechadas** (seção
  4, "candidatos pendentes", fica vazia permanentemente desde
  30/09/2026 — os 908 PNGs de `varredura_imagens/` foram revisados um a
  um pelo usuário e tudo que tinha texto já foi traduzido). Consulte
  antes de sair "procurando texto novo" — não deveria sobrar nenhum;
  se achar algo, é descoberta nova, não um candidato já catalogado.

## Regras que valem para qualquer tarefa aqui

1. **`Originais/` nunca é editado.** Todo fluxo lê de lá (ou de uma
   cópia extraída) e escreve em `Minha tradução/`.
2. **Nomes próprios do universo Elder Scrolls nunca são traduzidos**
   (Uriel Septim VII, Jagar Tharn, Tamriel, "The Elder Scrolls", etc.) —
   detalhes e exemplos em
   [docs/traducao-estilo.md](docs/traducao-estilo.md).
3. **Placeholders do motor do jogo** (`%t`, `%rf`, `%cn`, `%cn2`, `%ct`,
   `%st`, ...) são copiados literalmente, nunca traduzidos.
4. **Ao apagar texto de uma imagem**: uma caixa por linha (nunca um
   retângulo único cobrindo várias linhas), preenchida com uma única
   cor amostrada do fundo real ao redor — nunca apagamento seletivo
   pixel a pixel (isso recria a silhueta da letra como "fantasma" em
   outro tom). Ver
   [docs/pipeline-imagens.md](docs/pipeline-imagens.md#técnicas-de-apagamento-erase).
5. **Ao desenhar texto novo**: prefira diminuir a fonte e centralizar no
   ponto médio do espaço original (`draw_fitted`) a esticar/espremer as
   letras para caber num tamanho exato. Esticar só se justifica para o
   banner de título isolado das telas de feitiço. Ver
   [docs/pipeline-imagens.md](docs/pipeline-imagens.md#como-posicionardimensionar-texto-para-bater-com-o-original).
6. **`split_bsa.py` reseta TODOS os arquivos-alvo, não só um.** Depois
   de rodá-lo, sempre rode em seguida todo `build_bsa_*.py` cujo
   resultado você quer manter. Se também precisar regerar
   `GLOBAL_parts/legivel/empty/`, rode `split_bsa.py` **antes** de
   `blank_bsa_intro.py` — rodar `blank_bsa_intro.py` sozinho depois de
   `compile_images.py` já ter rodado apaga em cima do `.IMG` traduzido,
   não do pristino. Ver
   [docs/pipeline-imagens.md](docs/pipeline-imagens.md#o-arquivo-globalbsa-pipeline-split--build--merge).
7. **Todo `.IMG`/`.INF` compilado passa por verificação de round-trip**
   (decodificar de volta o que acabou de ser escrito e comparar byte a
   byte) antes de ser considerado pronto — isso acontece em
   `compile_images.py`/`compile_inf.py`, não nos `build_bsa_*.py`
   individuais (que só gravam PNG/texto, sem perda possível). Siga o
   mesmo padrão em qualquer script de compilação novo.
8. **Revisão é sempre visual e iterativa.** Gere preview (e, para ajuste
   fino de posição, preview com grade a cada 10px comparando original x
   traduzido), mostre, e espere aprovação explícita antes de seguir para
   o próximo arquivo. Não presuma que "ficou parecido" é suficiente.
9. **Uma tela ainda em inglês depois de "traduzida" pode ser um arquivo
   solto sobrepondo o do `GLOBAL.BSA`.** Alguns `.INF` (e possivelmente
   outros formatos) existem duplicados — uma cópia dentro do
   `GLOBAL.BSA`, outra solta na pasta do jogo — e a cópia solta tem
   prioridade. Antes de investigar mais a fundo um "ainda em inglês",
   confira se existe um arquivo solto de mesmo nome. Ver
   [docs/pipeline-inf.md](docs/pipeline-inf.md#gotcha-crítico-alguns-inf-também-existem-como-arquivo-solto--e-esse-é-o-que-vale).
10. **Os arquivos de trabalho são sempre `legivel/` (PNG/texto), nunca
    `.IMG`/`.INF` binário.** `build_bsa_*.py`/`build_images.py`/
    `build_inf_loose.py` só escrevem em `legivel/`; `compile_images.py`/
    `compile_inf.py` são os únicos que produzem o binário final. Se
    precisar ajustar manualmente um pixel/frase que um script não
    acertou, edite o PNG/texto em `legivel/` direto e rode só o
    `compile_*.py` correspondente de novo — não precisa re-rodar o
    `build_bsa_*.py`. Ver
    [docs/pipeline-imagens.md](docs/pipeline-imagens.md#legivel-vs-formato-do-jogo).

## Comandos mais usados

```bash
# Traduzir um arquivo de texto do jogo (ver pipeline-textos.md para o fluxo completo)
python3 scripts/split_template.py
python3 scripts/mount_template_part.py
python3 scripts/merge_template.py

# Resetar + retraduzir tudo que vive dentro de GLOBAL.BSA
python3 scripts/split_bsa.py
python3 scripts/build_bsa_scrolls.py
python3 scripts/build_bsa_intro.py
python3 scripts/build_bsa_history.py
python3 scripts/build_bsa_ui.py
python3 scripts/build_bsa_menu.py
python3 scripts/build_bsa_charstat.py
python3 scripts/build_bsa_yesno.py
python3 scripts/build_bsa_popup.py
python3 scripts/build_bsa_newmenu.py
python3 scripts/build_bsa_newold.py
python3 scripts/build_bsa_newequip.py
python3 scripts/build_bsa_labels2.py
python3 scripts/build_bsa_equip.py
python3 scripts/build_bsa_automap.py
python3 scripts/build_bsa_slider.py
python3 scripts/build_bsa_quote.py
python3 scripts/build_bsa_op.py
python3 scripts/build_bsa_forms.py
python3 scripts/build_bsa_accprejt.py
python3 scripts/build_bsa_charspel.py
python3 scripts/build_bsa_scroll03.py
python3 scripts/build_bsa_inf.py
python3 scripts/build_inf_loose.py
python3 scripts/compile_images.py
python3 scripts/compile_inf.py
python3 scripts/merge_bsa.py

# Pipeline completo, do zero
python3 scripts/build_all.py

# Regenerar o espelho legível pristino em Originais/legivel/
# (raro precisar rodar manualmente - só se estiver faltando ou em dúvida)
python3 scripts/gerar_legivel_originais.py
```

## Status conhecido (31/08/2026)

Todas as telas de imagem identificadas até agora estão traduzidas e
aprovadas: SCROLL01–03.IMG, TITLE.IMG, CHARSPEL.IMG, HISTORY.IMG,
INTRO01–09.IMG, LOGBOOK.IMG, BUYSPELL.IMG, SPELLMKR.IMG, MENU.IMG (a
última exigiu corrigir um bug no decoder Huffman "type 8" — faltava
pular 2 bytes de um campo de tamanho embutido logo após o cabeçalho —
documentado em
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#compressão-type-8-huffman-decode-only),
e recompressão para LZSS "type 4" ao gravar, já que não existe encoder
Huffman aqui).

Também traduzidas: **CHARSTAT.IMG** (ficha de atributos — introduziu o
alinhamento por coluna à direita + borda inferior, ver
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#draw_right_aligned--alinhar-por-coluna-à-direita--pela-borda-inferior-fichas-com-rótulos-label)),
**YESNO.IMG** (diálogo Sim/Não/Cancelar), **POPUP3.IMG**/**POPUP4.IMG**
(cabeçalhos de coluna das listas de armas/armaduras — Nome/Mãos-ou-
Protege/Peso/Custo), **NEWMENU.IMG** (Roubar/Sair, ao saquear um
contêiner), **NEWOLD.IMG** (Tarefa/Status/Cancelar, quadro de tarefas de
guilda) e **NEWEQUIP.IMG** (tela de saque de masmorra — "Nível:" e
Largar/Grimório/Sair). Essas últimas duas técnicas de apagamento (clone
de textura para fundo de alto contraste vs. preenchimento por moda
local para mármore liso) estão documentadas em
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#erase_box--clone-de-textura-fundo-com-alto-contraste-local).

Também traduzido: o texto de sabedoria (`@TEXT`) dos 57 arquivos
`.INF` de masmorra/localização dentro do `GLOBAL.BSA` (`scripts/
build_bsa_inf.py`, `scripts/inf_codec.py`) — placas, bilhetes,
descrições ambiente e enigmas. Ver
[docs/pipeline-inf.md](docs/pipeline-inf.md). Duas riddles usam
adaptação criativa (trocadilho de letra/palavra composta em inglês sem
equivalente em português) sinalizada no código para revisão do
usuário: `DAGOTH3.INF` (enigma da letra) e `ELDEN2.INF` (segundo
enigma, "footstep"/pegada).

Além disso, `CRYSTAL3.INF` e `IMPPAL1-4.INF` (níveis do Palácio
Imperial) existem **duplicados** como arquivo solto na pasta do jogo,
fora do `GLOBAL.BSA` — e é a cópia solta que o jogo realmente usa. Uma
primeira rodada traduziu só a cópia de dentro do BSA, então essas
telas continuavam em inglês no jogo de verdade; corrigido com
`scripts/build_inf_loose.py`, que reaproveita as mesmas traduções sem
duplicar texto. Ver a seção "gotcha crítico" em
[docs/pipeline-inf.md](docs/pipeline-inf.md).

**Rodada de 26 telas encontradas via varredura em massa (31/08/2026)**:
`scripts/varredura_img_bruta.py` (ver
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#4-confirmados-com-texto-pendentes-de-tradução))
achou 26 arquivos `.IMG` com texto nunca notado antes, todos já
traduzidos: `QUOTE.IMG` (citação de carregamento), `AUTOMAP.IMG`
(bússola N/S/L/O + Sair), `BONUS.IMG`/`EQUIPB.IMG`/`GOLD.IMG`/
`PAGE2.IMG`/`SPELLBK.IMG` (rótulos pequenos, `build_bsa_labels2.py`),
`EQUIP.IMG` (variante do `NEWEQUIP.IMG` com botões em ordem diferente),
`OP.IMG` (tela de opções do jogo, Sound/Music/Detail + New/Load/Save
Game/Drop to DOS/Continue) e os 17 `FORM1-15/4A/6A.IMG` (formulários de
efeito de feitiço da Cria-Feitiços — nunca notados porque
`SPELLMKR.IMG` não referencia esses nomes diretamente). Duas técnicas
novas usadas nesse lote: medir a posição do texto por **perfil de
coluna de tinta** (largura do "run" de pixels de tinta distingue letra
de borda de widget — muito mais confiável que ler visualmente um grid
ampliado) e **preenchimento por moda local em vez de clone de textura**
para o fundo alaranjado do `OP.IMG`/`FORM*.IMG` (clone de textura
plantava um retângulo visivelmente errado sempre que a busca por
deslocamento caía sobre a mancha de brilho do mármore). Ver
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#varredura-bruta-de-imagens-não-analisadas).

**Correção de paleta errada (31/08/2026)**: usuário reportou que
`SCROLL01.IMG`/`SCROLL02.IMG` (pergaminhos de abertura) e
`EQUIP.IMG`/`EQUIPB.IMG` saíram com a paleta errada mesmo depois de
traduzidos. Confirmado: `SCROLL01/02.IMG` usavam `DAYTIME.COL` (uma
suposição de sessão anterior nunca revalidada) e deveriam usar
`CHARSHT.COL` (agora um pergaminho de verdade, igual ao
`SCROLL03.IMG`/`HISTORY.IMG`); `EQUIP.IMG`/`EQUIPB.IMG` usavam
`PAL.COL` (aceito sem comparar alternativas na rodada de varredura) e
também deveriam usar `CHARSHT.COL` (fundo de pedra/azul-petróleo, igual
à ficha de atributos, em vez do mármore alaranjado). Corrigido em
`build_bsa_scrolls.py`, `build_bsa_equip.py` e `build_bsa_labels2.py`
(o índice de tinta 253/RGB(191,115,0) coincidentemente é igual nas duas
paletas, então só o arquivo de paleta carregado precisou mudar). Também
descoberto nesse processo: `EQUIP.IMG` tem seu próprio banner dourado
"EQUIPMENT" cravado nos pixels (diferente do `EQUIPB.IMG` solto) que
tinha passado batido — corrigido com uma técnica nova,
`erase_plaque_text()` (cura só os pixels escuros de cada linha,
copiando o pixel não-escuro mais próximo na mesma linha, em vez de
apagar a caixa inteira e perder o relevo dourado da placa). Lição
central, registrada em
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#gotcha-crítico-cada-paleta-é-única-e-não-é-uma-rampa-de-brilho):
"renderizou algo legível" não prova que a paleta está certa — sempre
comparar todas as paletas `.COL` candidatas lado a lado antes de
aceitar uma.

Instalado e testado na cópia Steam do jogo em
`~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/The Elder Scrolls Arena/ARENA/`
(cada arquivo tem seu `.original` de backup ao lado, já existente de
antes desta sessão).

Além das imagens acima, uma varredura por nome no `GLOBAL.BSA`
(`NBOX.IMG`, `SBOX.IMG`, `STAT11/13/15/21/23/25.IMG`, `BOOKS1/2.IMG`)
confirmou que são só sprites decorativos de objeto do mundo (baú,
estátua, livro), sem texto — não precisam de tradução. `DLGT.IMG`,
`TZDLGT.IMG`, `T_DLGT.IMG`, `DLGTD.IMG`, `XDLGTD.IMG` e `POPTALK.IMG`
têm cabeçalho `.IMG` corrompido/inválido (dimensões absurdas ao
decodificar) — provavelmente não são realmente arquivos `.IMG` apesar
do nome, e foram descartados sem mais investigação.

**Pendências conhecidas**: os 946 arquivos `.IMG` dentro do `GLOBAL.BSA`
já estão 100% analisados (fechado em 30/09/2026 - ver a entrada de
mesma data mais abaixo neste arquivo e
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#3-arquivos-não-analisados)
para o levantamento completo). Ainda soltos e nunca decodificados:
`STARTGAM.MNU`, `TAMRIEL.MNU`, `MAPBTNS.MNU`. Se surgir uma tela nova a
traduzir, seguir o padrão de `scripts/build_bsa_charstat.py`/
`build_bsa_newequip.py` (as mais recentes entre as imagens) como
referência mais próxima para um arquivo com fundo texturizado de alto
contraste, ou `scripts/build_bsa_popup.py` para fundo liso/mármore de
baixo contraste.

**Refactor de formato de trabalho (31/08/2026)**: todos os
`build_bsa_*.py`/`build_images.py`/`build_inf_loose.py` pararam de
gravar `.IMG`/`.INF` binário diretamente — agora só produzem PNG/texto
legível em `legivel/`. Dois scripts novos (`compile_images.py`,
`compile_inf.py`) fazem a conversão para o formato do jogo, só na hora
do build. Verificado que o `build/` resultante é byte-a-byte idêntico
ao de antes do refactor (única exceção: `INTRO08.IMG` mudou ~3,7% dos
pixels de fundo — texto idêntico, causa é uma `empty/` desatualizada de
sessão anterior que ficou obsoleta, não um efeito do refactor). Ver
[docs/pipeline-imagens.md](docs/pipeline-imagens.md#legivel-vs-formato-do-jogo).

**Tradução do `ACD.EXE` (03/09/2026)**: iniciada e testada ao vivo com o
usuário (instalação real do OpenTESArena 0.18.0). A maior parte do
texto do executável já está traduzida — ver
[docs/pipeline-acd-exe.md](docs/pipeline-acd-exe.md) para o inventário
completo. Dois achados importantes desta rodada: (1) `AttributeNames` e
o gerador procedural de boato do Citizen (`NeighborWarPeace`) travam o
motor com qualquer edição, por uma causa raiz nunca confirmada apesar
de bisecção ao vivo — ficam de propósito em inglês; (2) o gerador de
nome de taverna (`TavernPrefixes`/`TavernSuffixes`/
`TavernMarineSuffixes`) exigiu inverter qual tipo de palavra
(substantivo vs. adjetivo) mora em cada array do jogo, já que a ordem
de concatenação Adjetivo+Substantivo é hardcoded no motor e o
português quer Substantivo+Adjetivo. A mesma técnica (adaptada) foi
aplicada em seguida a Temple (construção genitiva "Ordem de X", não
precisou de inversão) e Equipment (convenção de nome de loja
"Nome+Categoria" + sufixo "-aria" sempre feminino, para não colidir
com os possessivos `%ef's`/`%n's`/`The Emperor's`) — com isso, todo
texto conhecido do `ACD.EXE` está traduzido, exceto o que fica de
propósito em inglês (`AttributeNames`, `CitizenRumorGenerator`, nomes
próprios). Ver [docs/pipeline-acd-exe.md](docs/pipeline-acd-exe.md)
para o detalhamento completo.

**`TEMPLATE.DAT` não é seguro traduzir para DOSBox (04-05/09/2026)**:
correção de uma suposição antiga — `TEMPLATE.DAT` é um arquivo real do
jogo (banco de falas de cidadão, 809 blocos `#hexid`), não lixo de
sessão. Corrigida a estrutura de linha (bug real, documentado em
[docs/pipeline-textos.md](docs/pipeline-textos.md)), mas mesmo assim
uma bisecção ao vivo isolou que o arquivo **não tolera nenhuma edição
de byte** ao rodar no DOSBox real (chegou a se testar 1 letra trocada,
mesmo tamanho de arquivo, e o bug de diálogo trocado persistiu) —
mesmo padrão do `AttributeNames` do `ACD.EXE`, provável checksum de
integridade não identificado. Decisão: manter a versão traduzida
instalada (funciona no OpenTESArena), aceitando que jogadores no
DOSBox real vão ver diálogo de cidadão ocasionalmente trocado. Ver
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#templatedat--arquivo-real-do-jogo-mas-não-é-seguro-traduzir-para-dosbox)
para o passo a passo completo da investigação.

**`ACD.EXE` traduzido nas duas plataformas: `build/dosbox/` vs.
`build/opentes/` (05/09/2026)**: investigação profunda (disassembly
real do stub PKLITE de 752 bytes via `objdump -m i8086`) achou e
corrigiu uma lacuna real em `pklite_pack.py` (faltava um token de
resincronização de ponteiro `0xFE` a cada ~40KB), mas isso sozinho
**não** destravou o `ACD.EXE` recompactado no DOSBox real — a causa
raiz exata nunca foi identificada, precisaria de um debugger x86 anexado
à execução real. A solução que funcionou: parar de recompactar PKLITE
para o DOSBox de vez. `Originais/ACD_UNPACKED_TEMPLATE.EXE` (um EXE já
descompactado por um expansor PKLITE de terceiros de verdade, gerado
uma única vez) recebe o buffer traduzido colado direto nele
(`pklite_pack.rebuild_dosbox_exe`) — sem stub, sem recompressão, sem o
bug. Confirmado funcionando no DOSBox real pelo usuário. `build/` agora
tem subpastas `dosbox/` (ACD.EXE plano + `TEMPLATE.DAT` original em
inglês) e `opentes/` (ACD.EXE PKLITE + `TEMPLATE.DAT` traduzido); o
resto dos ~201 arquivos é idêntico nas duas plataformas e a pasta do
OpenTESArena aponta pra eles via link simbólico na pasta do Steam. De
quebra, achado e corrigido um bug real: o `TEMPLATE.DAT` que estava
instalado no OpenTESArena não era a versão reflow-fixada (773/809
blocos com estrutura de linha errada) — nunca tinha sido reinstalado
depois do fix. Ver
[docs/pipeline-acd-exe.md](docs/pipeline-acd-exe.md#a-solução-real-nunca-recompactar-pklite-para-o-dosbox)
para a investigação completa.

**`ACCPREJT.IMG` traduzido (30/09/2026)**: achado pelo usuário via
revisão manual de `varredura_imagens/` (não fazia parte do lote de 26
telas nem de nenhuma lista anterior). 138x13, Huffman "type 8", sem
paleta embutida - `PAL.COL` confirmada certa comparando os 4 `.COL`
candidatos lado a lado (as outras 3 saem como ruído). Botões
"Accept"/"Reject" (resposta a oferta/negociação) traduzidos para
"Aceitar"/"Rejeitar" - fonte reduzida de tamanho 8 (padrão do
`NEWMENU.IMG`) para 7 já que as palavras em português são mais longas
e precisam continuar longe do divisor central. Novo script
`scripts/build_bsa_accprejt.py` (mesmo padrão de erase/redraw do
`build_bsa_newmenu.py`), registrado em `split_bsa.py`,
`img_manifest.py` e `build_all.py`. Verificado ponta a ponta: a entrada
em `build/GLOBAL.BSA` decodifica de volta corretamente após a
recompressão LZSS real.

**Varredura de `varredura_imagens/` concluída (30/09/2026)**: usuário
revisou manualmente, um por um, todos os 908 PNGs da pasta e confirmou
que os que não foram traduzidos não têm texto. 856 arquivos `.IMG`
movidos de "não analisados" para "sem tradução necessária" em
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#22-dentro-do-globalbsa)
(lista completa em `varredura_imagens/_sem_traducao.txt`). Isso deixa
só 13 arquivos `.IMG` genuinamente pendentes no `GLOBAL.BSA` - 11 que a
varredura em massa nunca conseguiu decodificar (`varredura_imagens/
_erros.txt`), e **2 achados nesta reconciliação, não relacionados à
varredura em si**: `CHARSPEL.IMG` e `SCROLL03.IMG` têm uma cópia
própria e ainda **não traduzida** dentro do `GLOBAL.BSA`, separada da
versão solta já traduzida - a varredura nunca as viu porque seu filtro
de exclusão é só por nome, e esses dois nomes já "existiam" no
manifesto de tradução (como arquivo solto), então a entrada do BSA foi
pulada sem checar se era o mesmo conteúdo. Mesma família do gotcha já
documentado para `CRYSTAL3.INF`/`IMPPAL1-4.INF` - ainda não confirmado
se o jogo de fato ignora a cópia do BSA aqui também. Ver
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#32-dentro-do-globalbsa)
para os detalhes completos e a lista dos 11+2.

**Os 13 `.IMG` restantes fechados - conta zerada (30/09/2026)**: os
dois casos abertos acima foram resolvidos direto no código-fonte do
OpenTESArena.

Os 11 que a varredura em massa nunca decodificou são todos imagens
cruas sem cabeçalho (mesma família do `SLIDER.IMG`) - `IMGFile.cpp`'s
`RawImgOverride` tem as dimensões reais hardcoded pra cada um
(`CITY.IMG` 16x11, `DITHER.IMG`/`DITHER2.IMG` 8x100, `DUNGEON.IMG`
14x8, `DZTTAV.IMG` 32x34, `NOCAMP.IMG`/`NOSPELL.IMG` 25x19, `P1.IMG`
320x53, `S2.IMG` 320x36, `TOWN.IMG` 9x10, `UPDOWN.IMG` 8x16).
Decodificados com essas dimensões (PAL.COL), nenhum tem texto:
`DITHER`/`DITHER2` são tiras de gradiente de dithering; `CITY`/
`DUNGEON`/`TOWN` são ícones de sprite pequenos; `DZTTAV` é a placa de
uma taverna (textura 64x64, tem seu próprio caso especial no
`IMGFile.cpp`); `NOCAMP`/`NOSPELL` são ícones de fogueira/estrela
mágica; `UPDOWN` é o ícone de escada acima/abaixo; `P1`/`S2` são barras
de ícones de menu (descansar/roubar), botões só com pictograma, sem
nenhuma palavra em inglês.

`CHARSPEL.IMG`/`SCROLL03.IMG`: confirmado que a cópia duplicada dentro
do `GLOBAL.BSA` é inalcançável pelo jogo. `VFS::Manager::open()`
(`components/vfs/manager.cpp` do OpenTESArena) sempre procura um
arquivo solto primeiro, em todas as raízes registradas, e só tenta o
`GLOBAL.BSA` se não achar - comportamento geral do motor, não
específico de `.INF`, então o mesmo raciocínio do gotcha documentado
pra `CRYSTAL3.INF`/`IMPPAL1-4.INF` se aplica aqui, agora confirmado
direto no código-fonte em vez de por analogia.

**Traduzidas mesmo assim, por segurança (30/09/2026)**: apesar de
inalcançáveis, o usuário pediu pra traduzir as duas cópias do BSA como
rede de segurança. Não são duplicatas bit-a-bit das versões soltas -
`CHARSPEL.IMG` (BSA) tem um layout com só 3 botões (sem "Delete
Spell"), e `SCROLL03.IMG` (BSA) não tem a ilustração de paisagem e usa
`CHARSHT.COL` como paleta externa em vez de paleta embutida - então
cada uma precisou da própria tradução, reaproveitando o mesmo texto e
estilo das versões soltas (`build_images.py`) adaptado ao layout real
de cada cópia. Novos scripts `scripts/build_bsa_charspel.py` e
`scripts/build_bsa_scroll03.py`, registrados em `split_bsa.py` e
`build_all.py` - escrevem o `.IMG` compilado direto (bypass de
`compile_images.py`, mesma razão do `build_bsa_slider.py`: o nome já é
chave do manifesto pela variante solta). Verificado ponta a ponta: as
duas entradas em `build/GLOBAL.BSA` decodificam de volta corretamente.

Com isso, os 946 arquivos `.IMG` do `GLOBAL.BSA` estão 100% analisados
e traduzidos onde fazia sentido: 53 traduzidos (51 + as 2 variantes do
BSA) + 20 já documentados antes + 856 da varredura manual + 11
recém-decodificados + 6 cabeçalhos inválidos = 946 - ver
[docs/inventario-arquivos.md](docs/inventario-arquivos.md#32-dentro-do-globalbsa)
pro fechamento completo da conta.

**Últimos candidatos soltos resolvidos: `TAMRIEL.MNU` e `CHARSPEL.DAT`
traduzidos, `STARTGAM.MNU`/`MAPBTNS.MNU`/`CLASSES.DAT` confirmados sem
texto (30/09/2026)**: os 5 "candidatos promissores" que restavam na
seção 3.1 do inventário foram todos decodificados.

- `TAMRIEL.MNU` (mapa "escolha sua província natal"): traduzido
  "Empire of"→"Império de" e "EXIT"→"SAIR" no banner/botão. Os 9 nomes
  de província (High Rock, Skyrim, Morrowind, ...) são nomes próprios
  preservados, igual já vale pro resto do jogo. Nova função
  `build_tamriel()` em `build_images.py`, registrada em
  `img_manifest.py` como `LOOSE` normal (tem cabeçalho de 12 bytes,
  passa pelo `compile_images.py` sem problema, só ".MNU" em vez de
  ".IMG" no nome - o pipeline não é IMG-específico apesar do nome do
  módulo).
- `CHARSPEL.DAT`: achado real, não lixo - **`charspel.dat` está
  referenciado de verdade dentro do `ACD.EXE` original** (junto com
  `charspel.img`, perto das strings de furto/confirmação de exclusão
  de feitiço). É um dump de tela cru 320x200 (sem cabeçalho, igual
  `SLIDER.IMG`) mostrando a tela de grimório/resistências de um
  personagem de exemplo ("Loviron Highorin", nome próprio preservado).
  Traduzido por segurança mesmo sem confirmar se é de fato alcançável
  em jogo normal (mesmo raciocínio do `CHARSPEL.IMG`/`SCROLL03.IMG`
  duplicados do BSA). Nomes de feitiço reaproveitam a tradução já
  estabelecida em `build_acd_exe.py` pros mesmos efeitos ("of Stamina"
  → "de Vigor" etc). Todas as 18 caixas de apagar/desenhar foram
  medidas por perfil de coluna/linha de tinta (mesma técnica do
  `ACCPREJT.IMG`) depois que uma primeira tentativa "no olho" deixou
  texto em inglês residual e errou a posição dos botões inteira (os
  três - Drop/Equipment/Exit - ficam dentro do painel esquerdo de
  160px, não espalhados pelos 320px da tela como pareciam num
  screenshot pequeno). Novo script `scripts/build_charspel_dat.py`
  (bypass de `compile_images.py`, mesmo motivo do `SLIDER.IMG`: não
  tem cabeçalho pra montar).
- `STARTGAM.MNU`: decodificado, confirmado só arte de fundo (cabana à
  noite), sem texto algum.
- `MAPBTNS.MNU`: decodificado, confirmado **100% preto** - um único
  índice de cor (0) nos 64000 pixels, checado programaticamente, não só
  "parece preto". Os 339 bytes finais do arquivo (além da imagem+
  paleta) parecem uma máscara de 1 bit (região de clique?), não texto.
- `CLASSES.DAT`: 216 bytes, zero strings (`strings -n 4` não acha
  nada) - tabela binária pura.

`scripts/build.py` tinha `TAMRIEL.MNU`/`CHARSPEL.DAT` faltando do
tratamento correto (`TAMRIEL.MNU` estava na lista de "nunca traduzido,
mantém original fora do build" - corrigido). Varredura por texto
também rodada nos 1402 arquivos `.MIF`/`.CFA`/`.SET`/`.DFA`/`.VOC`/
`.RMD`/`.CIF`/`.XFM`/`.XMI` dentro do `GLOBAL.BSA` (threshold de
10+ caracteres ASCII legíveis) - zero prosa real, só ruído binário e o
cabeçalho padrão dos `.VOC`. Ver
[docs/inventario-arquivos.md](docs/inventario-arquivos.md) seções 1.1,
2.1 e 3.2 para o detalhamento completo.

**Bug grave de pipeline encontrado e corrigido: "várias IMG sem
tradução no DosBox" (30/09/2026)**: depois de instalar a build no jogo
real (Steam/DOSBox) e também testar no OpenTESArena, várias telas que
já tinham sido traduzidas (QUOTE.IMG, SCROLL01/02.IMG, NEWMENU.IMG,
telas de inventário/armadura) apareceram em inglês nos dois motores.
Descartadas por evidência direta, nessa ordem: LZSS incompatível com o
motor real (refutado - POPUP3/4.IMG, sem compressão nenhuma, também
apareceram em inglês); Steam sobrescrevendo arquivo (refutado -
arquivo no disco continuava traduzido); pasta de instalação errada
(refutado - `libraryfolders.vdf`/`appmanifest_1812290.acf` confirmam
instalação única); cache de montagem de CD-ROM do DOSBox (refutado -
reiniciar o DOSBox via Steam não mudou nada). **A pista decisiva**: o
OpenTESArena (implementação própria, do zero, de BSA/LZSS) mostrava o
mesmo bug que o DOSBox real - isso descarta qualquer causa específica
de motor e aponta pra um problema no `GLOBAL.BSA` **gerado**, não em
como ele é lido.

Causa raiz, achada comparando timestamp de arquivo: `split_bsa.py` foi
rodado duas vezes nesta sessão (pra adicionar `ACCPREJT.IMG`, depois
`CHARSPEL.IMG`/`SCROLL03.IMG`) e, como documentado na regra 6 acima,
isso reseta **todos** os arquivos-alvo pro pristino em
`GLOBAL_parts/`, não só os dois novos. Só os scripts `build_bsa_*.py`
novos foram re-rodados depois, nunca o conjunto histórico inteiro.
`compile_images.py` (que varre o manifesto inteiro, lendo de
`legivel/` que nunca é resetado por `split_bsa.py`) rodou por acaso
durante o trabalho do `TAMRIEL.MNU` e consertou os `.IMG` de
raspão - mas `compile_inf.py` nunca rodou de novo, deixando os 57
`.INF` revertidos. E como `merge_bsa.py` tinha rodado **antes** desse
conserto acidental dos `.IMG`, nem esses estavam refletidos no
`GLOBAL.BSA` entregue. **Corrigido** rodando `compile_inf.py` (refaz
todos os 55 `.INF` do BSA + 5 soltos a partir de `legivel/`, todos
round-trip-verificados), confirmando por varredura binária que
`GLOBAL_parts/` tinha exatamente 108 entradas diferentes do pristino
(53 `.IMG` + 55 `.INF`, mais 2 `.INF` legitimamente idênticos ao
original - `CRYPT2.INF`/`CRYSTAL2.INF` não têm prosa real mesmo),
re-rodando `merge_bsa.py` + `build.py`, e reinstalando no Steam. **A
regra 6 já cobria a causa em abstrato; esta é a ocorrência real que a
originou** - releia a regra 6 sempre que rodar `split_bsa.py` fora de
um `build_all.py` do zero.

**Primeira instalação na cópia real do jogo (Steam/DOSBox) (30/09/2026)**:
`CHARSPEL.DAT`, `GLOBAL.BSA` e `TAMRIEL.MNU` copiados pra
`.../Steam/steamapps/common/The Elder Scrolls Arena/ARENA/`, com
`.original` criado antes da primeira sobrescrita de cada arquivo nunca
tocado. Só feito a pedido explícito do usuário - nunca escreva na
instalação real sem isso ser pedido na própria conversa.

**README.md criado e projeto publicado no GitHub, material do Nexus
Mods preparado (30/09/2026)**: ver a seção "Publicação" no topo deste
arquivo pro estado atual (link do repo, identidade git local, o que
fica de fora via `.gitignore`, o que tem em `nexus_release/`). Registro
à parte porque não é trabalho de tradução/engenharia reversa como o
resto deste arquivo, mas muda como qualquer sessão futura deve agir
(não recriar o repo, não recommitar `Originais/`/`varredura_imagens/`/
`_dosbox_test/`, saber que `nexus_release/` é local-only).

**Correção crítica do percentual de tradução da versão DOSBox: 90-93%
estava errado, o real é ~55% (01/10/2026)**: a estimativa original
(dada junto com o README) foi um chute qualitativo - "só falta um
arquivo" - sem medir quanto esse arquivo realmente pesa. O usuário
questionou certo: `TEMPLATE.DAT` (banco de falas de cidadãos, o único
arquivo não traduzido na versão DOSBox por causa do gotcha de edição
documentado em
[docs/pipeline-acd-exe.md](docs/pipeline-acd-exe.md)) tem **396 KB**,
contra **877 KB de texto no jogo inteiro** somando todos os arquivos
em formato texto puro (todos os `.INF` dentro e fora do `GLOBAL.BSA` +
`TEMPLATE.DAT` + o resto dos `.DAT`/`.TXT`/`.MNU` soltos tipo
`ARTFACT1/2.DAT`, `EQUIP.DAT`, `TAVERN.DAT` etc). Ou seja, sozinho ele
é **~45% de todo o texto do jogo** - a estimativa certa pra versão
DOSBox é **~55%**, não 90-93%. A versão OpenTESArena continua ~98-99%
(lá o `TEMPLATE.DAT` está traduzido).

**Lição pra qualquer estimativa de % futura**: nunca estime "% do jogo
traduzido" por contagem de arquivos ou impressão qualitativa ("é só um
arquivo que falta"). Meça o tamanho real em bytes de todo arquivo em
formato texto puro (os `.DAT`/`.TXT`/`.MNU`/`.INF` com prosa -
**não** `.IMG`, que é dado de pixel e não é comparável por tamanho de
arquivo dessa forma) e calcule a proporção de fato. `README.md` e
`nexus_release/texto-pagina-nexus.txt`/`nexus-texto.html` foram
corrigidos nessa mesma rodada - mantenha os três em sync se o quadro
mudar de novo (ex.: se algum dia o gotcha do `TEMPLATE.DAT` for
contornado e ele puder ser traduzido também na versão DOSBox).
