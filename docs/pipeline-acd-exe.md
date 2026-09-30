# Pipeline do ACD.EXE (executável principal)

`ACD.EXE` é o executável DOS do jogo, comprimido com **PKLITE v1.12**.
Ao contrário de todo outro arquivo traduzido neste projeto, o texto aqui
vive dentro de dados de um binário compactado, não num arquivo solto nem
numa entrada do `GLOBAL.BSA` — por isso tem seu próprio script e sua
própria lógica, fora do padrão split → build → merge usado no resto do
projeto.

## Scripts

- **`scripts/pklite_unpack.py`** — descompacta o PKLITE (stub de 752
  bytes, bitstream LSB-first) num buffer linear de 305520 bytes.
- **`scripts/pklite_pack.py`** — recompacta o buffer patchado de volta
  num `.EXE` válido (`rebuild_exe`), reaproveitando o stub original.
- **`scripts/build_acd_exe.py`** — o script principal: lê
  `Originais/ACD.EXE`, descompacta, aplica uma cadeia de funções
  `apply_*(data)` (cada uma responsável por uma área temática do jogo),
  recompacta, e escreve em `Minha tradução/ACD_unpacked.bin` (buffer
  descomprimido, só para depuração) e `Minha tradução/ACD.EXE` /
  `build/ACD.EXE` (o `.EXE` final).

Rodar sozinho: `python3 scripts/build_acd_exe.py` (a partir da raiz do
projeto ou da pasta `scripts/`). Não faz parte de `build_all.py` como um
passo separado explícito — **na verdade não está incluído em
`build_all.py`**; rode manualmente sempre que mexer em algo do EXE, e
confirme que `build/ACD.EXE` foi atualizado antes de instalar.

`ACD.EXE` (e o `ACD_unpacked.bin` de depuração) estão na lista
`ARQUIVOS_IMAGEM_BINARIOS` de `scripts/build.py`, então nunca passam
pelo removedor de acentos genérico — todo texto em português escrito
aqui já sai **sem acento** (o removedor de acentos do resto do projeto
não toca neste arquivo; a responsabilidade de não usar acento é do
próprio `build_acd_exe.py`).

## Verificação obrigatória

Toda execução de `build_acd_exe.py` faz o mesmo round-trip que os outros
compiladores binários do projeto: recompacta e descompacta de novo,
comparando byte a byte com o buffer patchado antes de aceitar o
resultado. Ver regra 7 do [CLAUDE.md](../CLAUDE.md).

## Os três helpers de patch

- **`patch_find(data, needle, budget, text, label)`** — busca por texto,
  exige ocorrência única, sobrescreve `budget` bytes a partir do match
  preenchendo com **espaços**. Uso: strings soltas fáceis de achar por
  conteúdo.
- **`patch_at(data, offset, expected, text, label)`** — offset absoluto
  (tirado do `acdExeStrings.txt` do OpenTESArena, cruzado com a saída do
  `pklite_unpack.py`), valida os bytes originais ali antes de escrever.
  `budget = len(expected)` — **se o campo termina em `\x00`, `expected`
  precisa incluir esse `\x00`**, senão o budget fica 1 byte curto e a
  tradução (que também deve embutir seu próprio `\x00` de terminação)
  estoura por 1 byte. Uso: strings curtas/genéricas demais para busca
  única ("Select", "Male").
- **`patch_array(data, original_items, span, items, label)`** — array
  sequencial de strings null-terminated (ex. `ClassNames`). A agulha de
  busca é o **conteúdo completo original juntado**, não só o primeiro
  item (um primeiro item curto/genérico como `"Strength\x00"` já
  colidiu com dado não relacionado em outro lugar do arquivo). Corrige
  **todas** as ocorrências encontradas, não só a primeira — alguns
  campos (`ClassNames`, `AttributeNames`) existem duplicados em dois
  endereços diferentes com conteúdo idêntico, e as duas cópias precisam
  bater. Preenche o restante do `span` com bytes **nulos**.
- **`patch_button(data, offset, original, new_word, label, highlight_idx)`**
  — para botões de menu com tecla de atalho destacada (formato
  `\t\xc0<letra>\t\xd4<resto>`). Sempre por offset absoluto (o mesmo
  texto de botão, tipo "Exit", se repete em várias telas). Corrige um
  bug real encontrado nesta sessão: se a tradução for mais curta que o
  original e não for preenchida com espaço até o tamanho exato, a
  atribuição de fatia do Python **encolhe o buffer inteiro**,
  corrompendo tudo que vem depois.

## Gotchas descobertos (leia antes de mexer em algo novo)

1. **Alguns campos do `acdExeStrings.txt` são maiores/mais complexos do
   que o nome sugere.** `NeighborWarPeace` parecia um array de 2 itens
   (guerra/paz) só pelo nome e pelo struct C++ do OpenTESArena
   (`std::string neighborWarPeace[2]`) — na prática é um bloco de 409
   bytes com 6 grupos de palavras e bytes de controle, usado por um
   gerador procedural de descrição de NPC. O motor só lê os 2 primeiros
   itens documentados, mas **algo não documentado lê mais adiante** —
   traduzir o bloco inteiro (mesmo preservando span e estrutura)
   trava o jogo (`Buffer.h index >= 0` na inicialização). Fica
   **desativado** (função `apply_citizen_rumor_generator` existe mas não
   é chamada) — ver o docstring da função para detalhes completos.

2. **Campos que travam o motor mesmo com edição mínima.**
   `AttributeNames` (nomes dos atributos: Strength/Intelligence/...) —
   qualquer edição, mesmo um único caractere, mesmo só preenchendo com
   espaço, trava o OpenTESArena 0.18.0 entre a confirmação de raça e a
   tela de distribuição de pontos (`KeyValuePool.h index -1`). Bisectado
   ao vivo com o usuário (4 variações testadas: as duas ocorrências, só
   uma com padding de espaço, só uma com padding nulo, e uma troca de 1
   byte só) — todas travam igual. Revisão do código-fonte do
   OpenTESArena não achou motivo óbvio (os dois pontos de leitura,
   `PrimaryAttribute::init` e o tooltip de acessório em
   `CharacterEquipmentUiState.cpp`, parecem seguros por inspeção). Causa
   raiz nunca confirmada — deixado em inglês. É visível ao jogador só no
   tooltip de item que dá bônus de atributo ("+5 to Strength") — não
   aparece na tela de distribuição de pontos nem na ficha (esses usam
   uma imagem já traduzida separadamente, o nome do atributo ali é só
   uma chave interna de UI, nunca renderizado como texto).

3. **Orçamento de bytes é sempre absoluto e por vezes tem "buracos".**
   Vários arrays têm alguns bytes de dado não-string intercalados entre
   o último item real e o campo seguinte (ex. `MonthNames`: 12 itens
   somam 136 bytes, mas o próximo campo documentado só começa 150 bytes
   depois — os 14 bytes do meio são dado binário não relacionado, nunca
   tocado). Sempre calcule o span pela **soma real dos itens
   originais**, nunca por "distância até o próximo campo documentado".

4. **Inverter o papel semântico de um array (ex. transformar array de
   substantivos em array de adjetivos) muda o orçamento de bytes
   necessário**, porque o span de bytes foi dimensionado para o
   *tamanho típico* do tipo de palavra original, não para o conceito.
   Isso apareceu ao reestruturar o gerador de nome de taverna (ver
   seção própria abaixo): um array pensado para caber substantivos
   ingleses curtos (`Mug`, `Ship`, 5-7 bytes/palavra) não cabe
   adjetivos portugueses típicos (particípios como "Enferrujado",
   "Assombrado" correm 10-12 bytes) — descoberto só na hora de
   implementar, não author antes.

5. **`patch_find`/`patch_after` com `budget` maior que o `needle` exige
   que a tradução embuta seu próprio `\x00`.** Se o `needle` de busca
   não inclui o `\x00` final do campo mas o `budget` passado é 1 byte
   maior que o `needle` (pra "cobrir" esse terminador), `patch_find`
   preenche esse último byte com **espaço** (é assim que ele
   completa qualquer sobra de orçamento) — nunca com `\x00`. Isso
   destrói o terminador original e o jogo passa a ler direto através
   do campo seguinte inteiro, só parando no próximo `\x00` de
   verdade que encontrar pela frente (às vezes vários campos depois).
   Bug real, veio de um relato do usuário em jogo (mensagens de
   status/acampamento aparecendo coladas umas nas outras, tipo
   "Inimigos perto!!Nao acampa aqui.Nao p...") — afetava **21 campos**,
   todos em `apply_calendar_and_camping`/o fim de `apply_entities`,
   onde o `budget` tinha sido escrito como `len(texto visível) + 1` por
   engano. Corrigido reduzindo cada `budget` para `len(needle)` exato
   (o padrão seguro usado em todo o resto do arquivo, onde o `\x00`
   fica fora da janela de escrita e nunca é tocado). Auditado com um
   script que roda a pipeline inteira com `patch_find`/`patch_at`/
   `patch_after` "encapsulados" comparando, pra cada chamada, se o
   trecho de dado pristino entre `needle` e `needle+budget` contém um
   `\x00` sem que o texto traduzido tenha um `\x00` embutido — reveste
   qualquer novo campo desse tipo antes de confiar nele.

6. **`ACD.EXE` recompactado (`pklite_pack.py`) não roda no DOSBox
   real, só no OpenTESArena.** Ver a seção sobre isso mais abaixo
   ("O EXE traduzido só funciona no OpenTESArena") para a investigação
   completa e a solução adotada (builds separadas por plataforma).

## Gerador de nome de estabelecimento (CityGeneration) — a virada de substantivo/adjetivo

O jogo monta o nome de toda taverna do mundo concatenando, sempre nessa
ordem fixa (hardcoded em `MapGeneration.cpp::createTavernName` do
OpenTESArena, não editável — só os dados são editáveis):

```cpp
tavernPrefixes[prefixIndex] + ' ' + (coastal ? tavernMarineSuffixes : tavernSuffixes)[suffixIndex]
```

`TavernPrefixes` no original guarda **adjetivos** (Green, Black,
Haunted...) e os dois arrays de sufixo guardam **substantivos** (Griffin,
Dragon... / Sailor's, Ship, Anchor... para cidade costeira) — por isso
o inglês lê natural como Adjetivo+Substantivo ("Green Griffin"). Em
português o natural é Substantivo+Adjetivo. Como a ordem de concatenação
é fixa no motor, a solução (decidida com o usuário) foi **inverter qual
tipo de palavra mora em cada array**: os substantivos traduzidos vão
para o endereço de `TavernPrefixes` (sempre lido primeiro,
independente de cidade costeira), e os adjetivos vão para os dois
endereços de sufixo (lidos em segundo, escolhidos por costeira/não-
costeira).

Consequência: a distinção costeira, que no original mora do lado do
substantivo (Ship/Anchor vs. Griffin/Dragon), passa a morar do lado do
adjetivo — por isso `TavernMarineSuffixes` recebeu um conjunto **novo,
inventado** de adjetivos com tema marítimo/praiano (Salgado,
Tempestuoso, Bravio, Marulhante...), já que os substantivos marítimos
originais não sobrevivem à inversão (só existe um array de prefixo
compartilhado, sem variação costeira).

Os 6 substantivos originalmente femininos (Mug→Caneca, Dagger→Adaga,
Skull→Caveira, Sword→Espada, Dungeon→Masmorra, Eagle→Águia) foram todos
trocados por equivalentes **masculinos** (Cálice, Garfo, Esqueleto,
Martelo, Covil, Urubu) por sugestão do usuário — com isso os 23
substantivos ficam 100% masculinos, eliminando de vez qualquer problema
de concordância de gênero com os adjetivos (que sempre usam a forma
masculina).

**Estado: implementado e aplicado** (`apply_city_generation()` em
`build_acd_exe.py`) para **Tavern, Temple e Equipment** — as três
famílias de nome procedural do jogo. Arrays finais:

- `TavernPrefixes` (0x36416, 167 bytes) — substantivos: Grifo, Dragao,
  Golem, Goblin, Ogro, Gigantes, Djinn, Lobo, Cacador, Calice, Copo,
  Garfo, Esqueleto, Martelo, Guarda, Covil, Poco, Elmo, Abismo, Castelo,
  Jarro, Urubu, Passaro.
- `TavernSuffixes` (0x36557, 138 bytes, cidade do interior) —
  adjetivos: Verde, Preto, Rubro, Azul, Belo, Branco, Alvo, Quente,
  Sujo, Feio, Voador, Bom, Baixo, Seco, Real, Real, Sedento, Infeliz,
  Sortudo, Mal, Negro, Uivante, Alto. ("Seco"↔Restless e "Baixo"↔Laughing
  são substituições puramente por orçamento, não carregam o sentido
  original — aceito porque é texto de ambientação, não UI traduzida.)
- `TavernMarineSuffixes` (0x364BD, 154 bytes, cidade costeira) —
  adjetivos marítimos inventados: Bravio, Rugente, Salgado, Marinho,
  Abissal, Salobre, Insular, Aqueo, Salino, Aquoso, Turvo (x2), Largo
  (x2), Aberto, Morto, Vivo (x3), Sereno, Gelido, Tepido, Areno.

**Temple** não precisou da inversão substantivo/adjetivo — é uma
construção genitiva (`templePrefixes[model] + templeSuffix`, **sem**
espaço explícito na concatenação, o espaço mora dentro de cada prefixo:
`"Order of the "`) que já lê certo em português como "Ordem de X".
`model` (0-2) escolhe ao mesmo tempo o prefixo e qual dos 3 arrays de
sufixo (de tamanhos diferentes) é usado — cada prefixo só é pareado com
seu próprio array, não um pool compartilhado como a Tavern.

- `TemplePrefixes` (0x365E1, 43 bytes, 3 itens) — Ordem de, Irmandade
  de, Conclave de.
- `Temple1Suffixes` (0x3660C, 61 bytes, 5 itens, só com "Ordem de") —
  Rosa Rubra, Profeta Uno, Tumulo Ouro, Esperanca, Mao Gentil.
  ("Knights of Hope" virou só "Esperanca" — orçamento muito apertado,
  ~12 bytes/palavra em média, não cabia por extenso.)
- `Temple2Suffixes` (0x36649, 63 bytes, 9 itens, só com "Irmandade
  de") — Piedade, Fe, Caridade, Guerra, Justica, Temperanca, Uno
  (`the One` sem artigo embutido, para não colidir com a preposição
  "de" do prefixo), Seth, Gideon (nomes próprios).
- `Temple3Suffixes` (0x36688, 73 bytes, 10 itens, só com "Conclave
  de") — Piedade, Fe, Caridade, Justica, Temperanca, Uno, Verdade,
  Solidao, Baal, Riana (nomes próprios).

**Equipment** tem uma estrutura mais complicada que a Tavern: 20
prefixos vs. só 10 sufixos (não simétrico, não dá pra fazer a mesma
troca completa de arrays), 5 dos 20 prefixos são possessivos com
placeholder dinâmico (`%ef's`, `%n's`, `The Emperor's`, `The Wyrm's`,
`The Adventurer's` — "[nome]'s [loja]"), e os sufixos já comiam quase
todo o orçamento de bytes no original (122 bytes pros 10 itens, folga
zero). Solução: em vez de inverter os arrays, usei a convenção real de
nome de loja em português — nome/adjetivo justaposto ao tipo de loja,
sem "de"/"da" no meio (tipo "Silva Ferragens") — e o sufixo de loja
"-aria" (Mercearia, Ferraria, Armaria...), que é **sempre feminino**,
então todo adjetivo do prefixo pôde usar uma forma feminina fixa sem
nenhum conflito de gênero, sem precisar da técnica "todo substantivo
masculino" da Tavern. `%ct`/`%ef`/`%n` (tipo de cidade / nome de NPC
gerado) viram substituição literal dentro da string já concatenada,
então a posição deles no prefixo ou sufixo não importa para a
substituição funcionar.

- `EquipmentPrefixes` (0x366D1, 205 bytes, 20 itens) — %ef, %n, %ct,
  Essencial, Usada, Pratica, Aventureira, Rara, "%ef Fina", Nova,
  Desenterrada, Vintage, Imperial, Elite, Barata, "%ef Geral", Basica,
  Draconica, "%ef Profissional", "%ef de Qualidade".
- `EquipmentSuffixes` (0x3679E, 122 bytes, 10 itens) — Mercearia,
  Selaria, Armaria, Bugigangaria, Espadaria, Ferramentaria, Correaria,
  Provisoes, Mercancia, Panoplia.

`MagesGuildMenuName` (o nome fixo "Mages Guild", budget de só 12
bytes) foi traduzido separadamente como "Guilda Mago" — orçamento
apertado demais para o "Guilda dos Magos" usado em
`CitizenWhereIsOptions`.

## O que já está traduzido

Calendário e opções de acampamento, criação de personagem completa
(escolha de classe/raça/nome/gênero/atributos, incluindo os 4 textos de
confirmação de raça ConfirmedRace1-4), `ClassNames` (duas cópias),
raças (nome singular/plural — Bretao/Redguard/Nordico/Dunmer/Altmer/
Bosmer/Khajiit/Argoniano, nomes próprios preservados por regra do
projeto), `CreatureNames`, `DiseaseNames`, `RulerTitles` (com
Czar/Czarina no lugar de Emperor/Empress por restrição de bytes — ver
histórico da sessão para a negociação completa), `ItemConditionNames`,
`MainQuestItemNames`, todos os menus e textos de Serviços (Equipment/
Mages Guild/Tavern/Temple/Citizen — botões fortemente abreviados por
orçamento zero de folga: Buy→Cmp, Repair→Reparo, Steal→Furto sempre),
ações de item (largar/equipar/tooltip de item), viagem, furto,
diálogo/pronomes/direções cardeais, textos de status (fadiga, cadáver,
dificuldade de fechadura), gerador de nome de taverna (ver seção
acima), `EffectNames`, `CitizenWhereIsOptions` (cidade e selvagem, com
"Guilda dos Magos"), e um conjunto de textos soltos residuais
("Ves um %s...", "Nao lido com boatos...", "Pocao", "Pecas Cajado
(%u)").

## O que fica de propósito em inglês

- `AttributeNames` — trava o motor com qualquer edição (item 2 dos
  gotchas acima).
- `CitizenRumorGenerator` (`NeighborWarPeace`) — trava o motor, motor
  não usa a maior parte do conteúdo mesmo (item 1 dos gotchas acima).
- Nomes próprios: dias da semana (Morndas, Tirdas...), nomes de
  província, nomes de cidade-capital de província (Rihad, Winterhold,
  Ebonheart...), nome do imperador ("Uriel Septim").

## O que ainda falta

Nada conhecido no momento — todo texto do `ACD.EXE` mapeado até agora
(via `acdExeStrings.txt` do OpenTESArena + auditoria manual) está
traduzido, exceto os itens listados em "O que fica de propósito em
inglês" acima. Se surgir mais texto para traduzir, conferir primeiro
se já não está coberto por alguma das funções `apply_*` de
`build_acd_exe.py` antes de reabrir uma área.

## O EXE traduzido só funciona no OpenTESArena, não no DOSBox real (05/09/2026)

**Sintoma**: qualquer `ACD.EXE` recompactado por `pklite_pack.py`
(mesmo um "identity repack" sem nenhuma mudança de conteúdo, só
recompressão) trava o carregamento no DOSBox real/Steam — tela do
DOSBox congelada, nunca chega ao jogo. O mesmo arquivo, executado pelo
OpenTESArena (que nunca roda o `.EXE` de verdade — só lê os bytes
comprimidos e os descomprime em software com `pklite_unpack.py`/seu
próprio `ExeUnpacker.cpp`), funciona perfeitamente.

**Investigação** (usando `_dosbox_test/UNP.EXE` — um descompactador
PKLITE de terceiros de 1993, rodado via DOSBox nativo, como oráculo
rápido de segundos em vez de esperar o jogo completo carregar):

1. **Descartado, via disassembly real do stub de 752 bytes
   (`objdump -m i8086`)**: não existe checksum/CRC do conteúdo
   comprimido em lugar nenhum do stub — hipótese inicial (por analogia
   com o gotcha do `AttributeNames`/`TEMPLATE.DAT`) revisada.
2. **Achado real via disassembly**: o stub só resincroniza os
   ponteiros de leitura/escrita (`SI`/`DS` e `DI`/`ES`) de volta para
   dentro de uma janela de 16 bits em UM único ponto de código —
   tratando um byte de escape `0xFE` (ou o terminador `0xFF`) do modo
   "Duplication". Um valor de comprimento normal (2-24 direto, ou
   25-277 via extensão) **nunca** passa por esse ponto. Sem
   resincronizar, `DI`/`SI` estouram 64KB silenciosamente (a imagem
   descompactada tem ~305KB, a comprimida ~166-177KB) e corrompem a
   memória. Confirmado instrumentando `pklite_unpack.py` contra o
   `ACD.EXE` original: ele contém exatamente 7 tokens `0xFE` "keep
   -alive", espaçados a ~40960 bytes descompactados um do outro — um
   mecanismo real do formato PKLITE que `pack_lz`/`pack_literal` nunca
   reproduziam.
3. **Corrigido** (`pklite_pack.py`, `RESYNC_INTERVAL`/
   `_write_keepalive`): `pack_lz` agora insere um token `0xFE` a cada
   32768 bytes (descompactados ou comprimidos, o que vier primeiro)
   desde o último resync. Round-trip e alinhamento de splice
   continuam corretos — **mas isso sozinho não resolveu o travamento**
   (testado com `RESYNC_INTERVAL` tão agressivo quanto 500 bytes,
   ainda trava idêntico).
4. **Validado exaustivamente que os primitivos de codificação estão
   corretos**: "reproduzir" os tokens exatos do arquivo original
   através do nosso próprio `BitWriter`/`_write_duplication` produz um
   arquivo **byte-a-byte idêntico** ao `ACD.EXE` original — inclusive
   passando pelo pipeline completo de `rebuild_exe` (trim + splice +
   correção de header). Isso prova que `BitWriter`, as tabelas
   `_D1_RAW`/`_D2_RAW`/`_COUNT_TO_BITS`/`_MSB_TO_BITS` e a lógica de
   splice/relocation estão **todas corretas** — nenhum valor que
   `pack_lz` usa é diferente de algum já usado (e validado) pelo
   arquivo original.
5. **Bisseção por hibridização** (tokens originais para um prefixo do
   arquivo + busca gulosa `pack_lz` fresca só para o sufixo): 95%/85%
   original funcionam no UNP.EXE; 75%/50% falham — mas com um erro
   **diferente** ("FATAL ERROR - Not enough memory to store relocation
   items"), não mais um travamento silencioso. Confirmado que a
   tabela de relocation está **byte-a-byte correta e no offset certo**
   em ambos os casos (simulação da própria rotina ASM de aplicar
   relocations bate 100% com o original) — então o erro não é
   estrutural, é algo interno ao próprio `UNP.EXE` (ou ao stub real)
   que não conseguimos identificar sem um disassembler/debugger de
   verdade anexado à execução real.

**Causa raiz exata do travamento do PKLITE recompactado**: nunca
identificada — precisaria de um debugger x86 real (ex. rodar sob
DOSBox com o debugger interno habilitado) para inspecionar registradores
no momento exato da falha, ferramenta não disponível neste ambiente. O
achado do token `0xFE` é real e foi mantido em `pack_lz`
(`RESYNC_INTERVAL`/`_write_keepalive`) - é uma condição necessária do
formato, mesmo não sendo suficiente sozinha para destravar o DOSBox
real.

## A solução real: nunca recompactar PKLITE para o DOSBox

O usuário lembrou de uma versão antiga, funcional no DOSBox, que **não
adicionava bytes no início/fim do arquivo** - ou seja, nunca passava
pela recompressão PKLITE. Reproduzindo essa ideia: em vez de tentar
consertar `pack_lz`, o `ACD.EXE` do DOSBox agora é montado **sem
nenhuma recompressão PKLITE**:

1. `Originais/ACD_UNPACKED_TEMPLATE.EXE` (321728 bytes, checado no
   repo) é uma cópia do `ACD.EXE` original **já descompactada por um
   expansor PKLITE de terceiros de verdade** (`_dosbox_test/UNP.EXE`,
   UNP V3.01 de Ben Castricum, rodado uma única vez dentro do DOSBox
   real contra o `Originais/ACD.EXE` pristino) - um EXE plano, sem
   stub de descompressão, com cabeçalho MZ padrão e tabela de
   relocation nativa do DOS já pronta (`e_crlc=4044`, header de 16208
   bytes antes dos dados).
2. `pklite_pack.rebuild_dosbox_exe()` simplesmente **substitui os
   16208:16208+305520 bytes** desse template pelo buffer descomprimido
   já traduzido (`ACD_unpacked.bin`) - mesma técnica de substituição
   de mesmo tamanho usada em todo o resto do projeto, só que aplicada
   direto num EXE já plano em vez de precisar recompactar.
3. Os últimos 8 bytes da imagem descompactada (305510-305515,
   305518-305519) são espaço de pilha/BSS não-inicializado no arquivo
   original - `pklite_unpack.py` (um `bytearray` zerado) nunca escreve
   ali, mas o template real (produzido pelo UNP.EXE de verdade) tem
   valores reais nessa posição; `rebuild_dosbox_exe()` preserva os
   bytes do template ali em vez de zerar, por segurança.
4. Testado direto no DOSBox real via Steam: **carrega o jogo
   normalmente, sem travar** - confirmado pelo usuário. Isso não
   precisa mais do `UNP.EXE`/DOSBox em todo build: o template já
   descompactado fica fixo no repo, só o buffer traduzido muda.

Isso não corrige a causa raiz do bug do PKLITE (que continua
desconhecida), só a torna irrelevante: o DOSBox real nunca mais vê um
`ACD.EXE` recompactado por este projeto.

## Estrutura final: `build/dosbox/` e `build/opentes/`

Como o `ACD.EXE` (PKLITE comprimido vs. plano) e o `TEMPLATE.DAT`
(traduzido vs. original - ver o gotcha em
[pipeline-textos.md](pipeline-textos.md)) precisam de conteúdo
diferente por plataforma, `build/` tem duas subpastas:

- **`build/opentes/ACD.EXE`** - PKLITE comprimido, traduzido
  (`pklite_pack.rebuild_exe`, escrito por `build_acd_exe.py`). Só
  funciona no OpenTESArena.
- **`build/opentes/TEMPLATE.DAT`** - traduzido (`build.py`, mesmo
  processamento de sempre).
- **`build/dosbox/ACD.EXE`** - plano/descompactado, traduzido
  (`pklite_pack.rebuild_dosbox_exe`, escrito por `build_acd_exe.py`).
  Funciona no DOSBox real.
- **`build/dosbox/TEMPLATE.DAT`** - **original em inglês**, cópia
  direta de `Originais/TEMPLATE.DAT` (escrito por `build.py` - real
  DOSBox não tolera nenhuma edição de byte nesse arquivo).
- **`build/` (raiz)** - todo o resto, idêntico nas duas plataformas.

**Instalação** (os dois motores usam pastas de dados fisicamente
diferentes neste ambiente):

- **DOSBox real / Steam** (`.../The Elder Scrolls Arena/ARENA/`):
  `ACD.EXE` e `TEMPLATE.DAT` vêm de `build/dosbox/`; todo o resto vem
  de `build/` raiz.
- **OpenTESArena** (`OpenTESArena/build/data/ARENA/` - cópia própria
  em disco, independente da pasta do Steam; **não** é a pasta
  `OpenTESArena/data/ARENA`, que é só um symlink pro Steam e não é
  usada pelo binário real `build/otesa`): `ACD.EXE` e `TEMPLATE.DAT`
  vêm de `build/opentes/`; **todo o resto é link simbólico apontando
  pra pasta do Steam** (201 arquivos) - assim uma atualização na pasta
  do Steam já reflete automaticamente ali, sem copiar de novo. Só
  `ACD.EXE`/`TEMPLATE.DAT` exigem atualização manual em dobro daqui pra
  frente.

**Bug real encontrado e corrigido nesta mesma rodada**: o
`TEMPLATE.DAT` instalado no OpenTESArena (417985 bytes) **não** era a
versão reflow-fixada - 773 dos 809 blocos tinham contagem de linha
diferente do original (a versão antiga, de quebra forçada em ~31
caracteres, nunca tinha sido substituída de fato após o fix). A versão
correta (`Minha tradução/TEMPLATE.DAT`, 408042 bytes, só 1/809 blocos
divergentes do original) estava certa na origem o tempo todo, só nunca
tinha sido reinstalada - `build/opentes/TEMPLATE.DAT` agora reflete
ela corretamente.

**`STARTGAM.MNU`/`TAMRIEL.MNU` removidos do `build/`**: nunca foram
decodificados/traduzidos (ver
[inventario-arquivos.md](inventario-arquivos.md) seção 3.1) - `build.py`
agora nem copia eles pra `build/`, a instalação simplesmente mantém o
arquivo original do jogo intocado.
