# Pipeline de tradução de imagens (`.IMG`, `GLOBAL.BSA`)

Para telas cujo texto é pixel art desenhada na própria imagem — não há
string para editar, o "texto" tem que ser apagado da imagem e outro
texto desenhado por cima. Ver [pipeline-textos.md](pipeline-textos.md)
para arquivos de texto de verdade.

## Formatos de arquivo

### `GLOBAL.BSA`

Arquivo de arquivo (archive) simples, decodificado/recodificado por
`scripts/bsa_codec.py`. **Não** é o formato BSA usado por jogos
Bethesda posteriores (Morrowind em diante) — é um formato próprio, bem
mais simples:

```
offset 0:  uint16 LE            NumFiles
offset 2:  dados de todos os arquivos, um atrás do outro, na MESMA
           ordem em que o diretório abaixo os lista
fim do arquivo:  NumFiles entradas de diretório, 18 bytes cada:
    14 bytes  nome do arquivo, ASCII, terminado/preenchido com \0
     4 bytes  uint32 LE  tamanho do arquivo
```

`bsa_codec.rebuild()` reescreve o arquivo inteiro trocando só as
entradas indicadas por `replacements`, preservando a ordem e copiando
todo o resto sem alteração — mesmo que o arquivo substituto tenha um
tamanho diferente do original (o BSA não usa offsets fixos, é sempre
recalculado a partir dos tamanhos).

### Cabeçalho `.IMG`

Todo `.IMG` do jogo (dentro ou fora do `GLOBAL.BSA`) começa com um
cabeçalho fixo de 12 bytes:

```
uint16 LE xoff, yoff, width, height, flags, length
```

- `flags & 0xFF` = **tipo de compressão** dos dados de pixel logo a
  seguir:
  - `0` = cru, sem compressão (`length` = `width*height` bytes)
  - `4` = LZSS ("type 4") — ver `lzss_codec.py`
  - `8` = Huffman adaptativo + LZ77 ("type 8") — ver `huffman_codec.py`
    (só decodificação, ver [abaixo](#compressão-type-8-huffman-decode-only))
- `flags & 0x100` = se ligado, um **palette embutida** de 768 bytes (256
  cores × 3 canais, valores VGA de 6 bits) vem logo depois dos dados de
  pixel (comprimidos ou não). Quando essa flag está desligada, o arquivo
  não carrega paleta própria — o jogo desenha usando qualquer paleta que
  esteja ativa na hora (ver `SCROLL01.IMG`/`SCROLL02.IMG` abaixo).
- `length` = tamanho em bytes dos dados de pixel logo após o cabeçalho
  (já comprimidos, se houver compressão) — **não** inclui os 768 bytes
  de paleta, se houver.

### Conversão de paleta: 6 bits → 8 bits

Uma paleta embutida de `.IMG` guarda cada canal de cor em 6 bits (DAC de
VGA, 0–63), não 8 bits. Toda vez que ler uma paleta embutida de `.IMG`,
expanda assim antes de usar com Pillow (que espera 0–255):

```python
def s6(v: int) -> int:
    return (v << 2) | (v >> 4)
```

**Cuidado**: isso vale só para paletas *embutidas em `.IMG`*. Arquivos
`.COL` (ex.: `CHARSHT.COL`, usado por `SCROLL01.IMG`/`SCROLL02.IMG`/
`EQUIP.IMG`) já guardam os 768 bytes em 8 bits diretos, sem essa
conversão — não aplique `s6()` numa paleta `.COL`, ou as cores saem
erradas.

### Gotcha crítico: cada paleta é única e NÃO é uma rampa de brilho

Cada `.IMG` com paleta embutida tem sua **própria** paleta,
independente de qualquer outro arquivo. E dentro de uma mesma paleta, o
**número do índice não indica brilho** — o índice 15 pode ser quase tão
claro quanto o índice 1, e o índice 19 (vizinho) pode ser quase preto.
Dois arquivos diferentes também podem mapear o mesmo número de índice
para cores completamente diferentes.

Consequência prática: **nunca** decida "isso é tinta" ou "isso é mais
escuro que aquilo" comparando números de índice de paleta diretamente.
Sempre:

1. Converta a paleta inteira para luminância perceptual real (a partir
   do RGB, não do índice) — ver `luminance_table()` em
   `build_bsa_intro.py`:
   ```python
   luminance = 0.299*r + 0.587*g + 0.114*b
   ```
2. Para descobrir a cor de tinta/contorno *daquele arquivo específico*,
   amostre um pixel que você sabe visualmente ser texto (olhando um
   preview ampliado) e leia o índice/RGB real ali — nunca assuma que um
   índice descoberto num arquivo vale para outro arquivo. Esse método
   (amostra pontual → descobre o índice real → escaneia só por aquele
   índice exato) foi o que resolveu erros de detecção em `BUYSPELL.IMG`/
   `SPELLMKR.IMG`/`LOGBOOK.IMG` depois que um limiar genérico não
   funcionou.

**Gotcha irmão, sobre a PALETA em si (não só a tinta)**: "renderizou
algo legível" não é o mesmo que "é a paleta certa". `SCROLL01.IMG`/
`SCROLL02.IMG` (paleta `DAYTIME.COL`) e `EQUIP.IMG`/`EQUIPB.IMG`
(paleta `PAL.COL`) foram aceitos assim por já mostrarem texto legível
num preview — mas eram a paleta ERRADA (a certa, `CHARSHT.COL`, só foi
descoberta quando o usuário reportou "a paleta está errada" depois de
ver no jogo de verdade). Sempre que um arquivo sem paleta embutida for
tratado, **renderize com TODAS as paletas `.COL` disponíveis lado a
lado antes de aceitar uma** — não pare na primeira que "funciona", a
pergunta certa é "faz sentido temático/visual comparado às outras telas
da mesma sequência?" (nesse caso: um pergaminho de abertura deveria
parecer pergaminho, não papel azul-marinho).

### Compressão "type 4" (LZSS)

`scripts/lzss_codec.py` — buffer circular de 4096 bytes inicializado com
`0x20`, correspondências de tamanho 3–18, byte de controle consumido
LSB-first (1 bit = 1 literal segue / 0 bit = 1 par de bytes de
correspondência segue). Tem **encoder e decoder** (`encode_type04` /
`decode_type04`) — é o formato usado para (re)gravar toda imagem
traduzida comprimida deste projeto.

Ao gravar um `.IMG` comprimido, sempre verifique que o resultado cabe no
campo `length` de 16 bits:
```python
assert len(compressed) < 65536, f"{name}: compressed size overflowed 16-bit length field"
```

### Compressão "type 8" (Huffman, decode-only)

`scripts/huffman_codec.py` — Huffman adaptativo combinado com
referências estilo LZ77 (família "LZHUF"), portado do
`Compression::decodeType08` do OpenTESArena. **Só tem decoder, não
encoder** (nunca precisa gravar type 8 — ver o plano de recompressão
abaixo).

> **Pegadinha de chamada (resolvida em 30/08/2026)**: um arquivo type 8
> tem, logo após o cabeçalho de 12 bytes, **2 bytes extras** com o
> tamanho descomprimido esperado (little-endian, igual a `width*height`)
> **antes** do stream Huffman de verdade começar. Esses 2 bytes contam
> dentro do campo `length` do cabeçalho, mas não são dados Huffman.
> Esquecer de pular esses 2 bytes não dá erro nenhum — o decoder roda
> normalmente e produz lixo a partir de pouco depois do início, porque o
> estado da árvore de Huffman adaptativa desvia a partir do primeiro bit
> lido do lugar errado. Chamada correta:
> ```python
> xoff, yoff, width, height, flags, length = struct.unpack_from("<HHHHHH", data, 0)
> pixels = decode_type08(data, 12 + 2, 12 + length, width * height)
> ```
> Confirmado contra `Compression::decodeType08`/`IMGFile.cpp` do
> OpenTESArena (`srcPtr + HeaderSize + 2` é exatamente o `src` passado
> para `decodeType08` lá) e validado decodificando `MENU.IMG` por
> inteiro sem ruído.

Arquivos conhecidos usando type 8: `MENU.IMG`, `YESNO.IMG`,
`NEWMENU.IMG`, `NEWOLD.IMG`, e provavelmente outros — sempre cheque
`flags & 0xFF` antes de assumir o tipo de compressão de um arquivo
novo, e sempre lembre do `+2` acima.

**MENU.IMG (feito, `scripts/build_bsa_menu.py`)**: como não existe
encoder Huffman aqui, o arquivo é decodificado com `decode_type08` (com
o `+2`), editado normalmente, e então **recomprimido como LZSS type 4**
(`encode_type04`, que já existe e funciona) trocando o byte baixo de
`flags` de `8` para `4` antes de gravar. O arquivo final não precisa
continuar Huffman — só precisa que o jogo consiga descomprimir o que
for gravado, e o motor original entende type 4 perfeitamente.

Essa tela (o menu principal - "Load Saved Game"/"Start New Game"/"Exit"
→ "Carregar Jogo"/"Novo Jogo"/"Sair") também deixou um gotcha de
posicionamento novo: a moldura ornamentada nos quatro cantos usa a
**mesma cor de tinta** do texto, então um scan automático por cor de
tinta detecta os floreios decorativos como se fossem texto. As caixas
de apagamento de `build_bsa_menu.py` foram por isso medidas à mão contra
um recorte ampliado (8x) com régua de grade, mantendo distância segura
de onde cada floreio mais se aproxima da linha de texto.

Além disso, centralizar o texto traduzido no **centro geométrico da
caixa de apagamento** não bate com onde o texto original realmente
fica: essa fonte estilo blackletter tem uma caixa delimitadora
(bounding box) cujo "peso visual" real senta mais baixo do que o centro
geométrico sugere, e a caixa de apagamento em si tem margens
assimétricas (para escapar dos floreios). A solução foi desacoplar as
duas coisas - `draw_two_tone` recebe um `draw_center = (x, y)` **medido
separadamente**, direto num recorte com régua do texto original, e
centraliza o texto ali, independente da caixa de apagamento. Esse é o
mesmo princípio do `draw_top`/`draw_left` manual dos painéis INTRO (ver
["Separando 'onde apagar' de 'onde desenhar'"](#separando-onde-apagar-de-onde-desenhar)
acima) — vale a pena revisitá-lo sempre que a posição "óbvia" (centro da
caixa) não bater com a posição visual real após a primeira tentativa.

## O arquivo `GLOBAL.BSA`: pipeline split → build → merge

Vários arquivos `.IMG` traduzíveis vivem **dentro** de `GLOBAL.BSA`, não
soltos (`SCROLL01/02.IMG`, `INTRO01-09.IMG`, `HISTORY.IMG`, `MENU.IMG`,
`LOGBOOK.IMG`, `BUYSPELL.IMG`, `SPELLMKR.IMG`, `CHARSTAT.IMG`,
`YESNO.IMG`, `POPUP3.IMG`, `POPUP4.IMG`, `NEWMENU.IMG`, `NEWOLD.IMG`,
`NEWEQUIP.IMG`). O fluxo:

1. **`python3 scripts/split_bsa.py`** — extrai cada arquivo-alvo listado
   em `TARGET_FILES`, pristino (bytes idênticos aos do `GLOBAL.BSA`
   original), para `Minha tradução/GLOBAL_parts/<nome>.IMG`.

   ⚠️ **Isso reseta TODOS os alvos, não só um.** Rodar `split_bsa.py`
   para "resetar" um único arquivo apaga a tradução já aplicada nos
   outros também (eles voltam a ser cópias pristinas em `GLOBAL_parts/`
   até algum `build_bsa_*.py` rodar de novo). Sempre que rodar
   `split_bsa.py`, rode em seguida **todos** os scripts
   `build_bsa_*.py` relevantes para restaurar as traduções dos arquivos
   que você não queria mexer:
   ```bash
   python3 scripts/split_bsa.py
   python3 scripts/build_bsa_scrolls.py
   python3 scripts/build_bsa_intro.py
   python3 scripts/build_bsa_history.py
   python3 scripts/build_bsa_ui.py
   ```
   (`GLOBAL_parts/legivel/empty/` não é afetado por `split_bsa.py` — só
   `blank_bsa_intro.py` regrava aquela pasta.)

2. **Cada `build_bsa_*.py`** lê de `GLOBAL_parts/` (bytes pristinos do
   jogo, exatamente como sempre), edita os pixels, e **salva o resultado
   como PNG em `GLOBAL_parts/legivel/<nome>.png`** — nunca escreve um
   `.IMG` binário diretamente. Cada script cuida de um subconjunto fixo
   de arquivos: `build_bsa_scrolls.py` (SCROLL01/02), `build_bsa_intro.py`
   (INTRO01–09), `build_bsa_history.py` (HISTORY), `build_bsa_ui.py`
   (LOGBOOK/BUYSPELL/SPELLMKR), e por aí afora — ver a tabela completa em
   [estrutura-arquivos.md](estrutura-arquivos.md).

3. **`python3 scripts/compile_images.py`** — lê todo PNG de `legivel/`
   (o que estiver lá no momento, seja saída de script ou ajuste manual
   feito num editor de imagem), monta o `.IMG` binário correspondente
   (`img_codec.py`, com o tipo de compressão/paleta de cada arquivo
   vindo de `img_manifest.py`) e grava de volta **no mesmo lugar onde
   o pristino vivia** em `GLOBAL_parts/` — substituindo-o.

4. **`python3 scripts/merge_bsa.py`** — lê o `GLOBAL.BSA` original de
   `Originais/`, troca cada entrada que tem um arquivo correspondente em
   `GLOBAL_parts/` (o que estiver lá agora, seja pristino ou já
   compilado pelo passo 3) pelo conteúdo daquele arquivo, copia todo o
   resto do BSA sem alteração, e grava `Minha tradução/GLOBAL.BSA`.

`scripts/build_all.py` roda esse pipeline inteiro (mais `build_images.py`,
`compile_inf.py` e o `build.py` de acentos) na ordem certa, de ponta a
ponta — use-o para uma reconstrução completa depois de mexer em
qualquer coisa.

## Por que existe um passo de "compilar" separado

`legivel/` — PNG de verdade, com a paleta certa embutida — é o arquivo
que de fato existe em disco enquanto a tradução está sendo feita ou
ajustada; o `.IMG` binário do jogo só é montado no fim, por
`compile_images.py`. Isso foi um pedido explícito do usuário: **poder
abrir e ajustar manualmente** um PNG num editor de imagem comum quando
um script não acerta um detalhe de primeira, sem precisar entender
compressão/cabeçalho/paleta para isso. Consequência prática: se você
editar um PNG de `legivel/` à mão, rode só `compile_images.py` de novo
(não precisa re-rodar o `build_bsa_*.py` daquele arquivo) para que a
edição vá para o `.IMG` final.

## Padrão "split → blank → draw" (empty/)

Para telas com arte ao redor do texto (os painéis `INTRO01-09.IMG`, e o
mesmo padrão vale para `HISTORY.IMG`), apagar e desenhar são duas
preocupações bem separadas — revisar cada uma isoladamente evita
confundir "o apagamento tocou a arte?" com "o texto novo ficou bom?".

1. **`python3 scripts/blank_bsa_intro.py`** apaga só o texto original
   (nunca desenha nada no lugar) e salva o resultado como PNG em
   `GLOBAL_parts/legivel/empty/<nome>.png`, mais um preview
   `*_vazio.png`. Revise esse preview sozinho primeiro: a arte
   (pergaminho, ilustração) deve estar 100% intacta, e a área de texto
   deve estar preenchida de forma lisa, sem fantasma/silhueta das
   letras antigas.
2. **`python3 scripts/build_bsa_intro.py`** lê de
   `GLOBAL_parts/legivel/empty/` (nunca reapaga), desenha a tradução por
   cima, e salva o resultado final como PNG em `GLOBAL_parts/legivel/`.

Uma vez que uma versão `empty/` está aprovada, ela nunca mais precisa
ser regerada — só rodar de novo o passo de desenho é seguro e barato.
Isso significa que iterar no *texto* (posição, fonte, quebra de linha)
nunca arrisca reintroduzir um erro de apagamento.

⚠️ **Cuidado de ordem**: `blank_bsa_intro.py` lê o `.IMG` pristino que
estiver em `GLOBAL_parts/` NAQUELE MOMENTO. Se você já rodou
`compile_images.py` (que sobrescreve `GLOBAL_parts/INTRO0N.IMG` com a
versão traduzida/compilada), rodar `blank_bsa_intro.py` de novo sem
resetar primeiro com `split_bsa.py` vai apagar em cima do texto
*traduzido*, não do original em inglês — corrompendo silenciosamente a
base `empty/`. Sempre `split_bsa.py` → `blank_bsa_intro.py`, nessa
ordem, se precisar regerar `empty/`.

Para telas simples de UI sem arte ao redor (`LOGBOOK.IMG`,
`BUYSPELL.IMG`, `SPELLMKR.IMG` — fundo de pergaminho plano e
uniformemente iluminado), esse cuidado extra não é necessário: apagar é
um preenchimento plano de cor única (`erase_flat` em
`build_bsa_ui.py`/`build_bsa_history.py`), e não existe pasta
`empty/` própria para elas — apagar e desenhar acontecem no mesmo
script, na mesma passada.

## Técnicas de apagamento (erase)

Duas técnicas distintas, escolha pela presença ou não de arte ao redor:

### `erase_flat` — preenchimento plano (fundo liso)

Para fundos de pergaminho lisos e uniformemente iluminados
(`build_bsa_ui.py`, `build_bsa_history.py`): simplesmente preenche a
caixa inteira com um único índice de cor de fundo conhecido
(`BG_INDEX`), amostrado uma vez do próprio arquivo. Simples, e correto
sempre que não há gradiente/textura relevante dentro da caixa.

### `erase_box` — preenchimento pelo modo local (fundo com textura/sombra)

Para os painéis INTRO, onde a "cor de fundo" varia sutilmente por
sombra/textura do pergaminho ao redor de cada legenda
(`build_bsa_intro.py`): a caixa inteira é preenchida com **uma única
cor** (não pixel a pixel) — mas essa cor é a **mais comum (moda)**
encontrada num anel de amostragem ao redor da caixa (raio 6 a 40px, o
raio cresce até achar amostras suficientes), restrita a amostras que:

- Sejam claramente "claras/pergaminho" (luminância ≥ 100) — isso
  descarta tanto o vazio fora da borda rasgada do pergaminho (índice de
  cor bem escuro) quanto uma sombra de ilustração vizinha.
  - Removido/rejeitado: um limiar `lum < 15` isolado (insuficiente —
    deixava passar sombras médias); a solução final que pegou foi exigir
    `lum >= 100` (só parchment/claro conta).
- Não sejam tinta (checado via contraste local, não limiar global — ver
  `is_ink()`/`INK_CONTRAST`).
- Não estejam dentro da borda decorativa do painel (`BORDER = 20px` do
  topo/base) nem dentro da caixa de nenhuma outra legenda do mesmo
  painel (parâmetro `exclude`).

Esta é a técnica que resolveu, nessa ordem, três problemas encontrados
ao vivo: (1) "fantasma" das letras antigas (apagamento seletivo pixel a
pixel recriava a silhueta da letra em outro tom — resolvido indo para
"apagar a caixa inteira com 1 cor"); (2) manchas pretas (amostras
pegando o índice 0 "vazio" fora da borda rasgada — resolvido excluindo
amostras escuras); (3) remendo escuro errado (a moda ocasionalmente
escolhia um tom localmente comum mas errado, tipo uma sombra próxima —
resolvido exigindo `lum >= 100`).

**Instrução original do usuário que gerou essa técnica**: "Não precisa
apagar pixel a pixel, pode apagar a área inteira, mas só a área do
texto, sem mexer nas imagens." — ou seja: **uma caixa, uma cor**,
delimitada com precisão à área real do texto original, nunca ao
formato irregular das letras.

### `erase_box` — clone de textura (fundo com alto contraste local)

Para fundos marmorizados/manchados de **alto contraste local**
(`CHARSTAT.IMG`, `YESNO.IMG`, `NEWMENU.IMG`, `NEWOLD.IMG`,
`NEWEQUIP.IMG` — pedra, lava, grama/madeira), um preenchimento plano
(mesmo com a cor de moda local) fica visível como um retângulo, porque
a variação de tom dentro da própria textura é maior que a diferença
entre "moda" e qualquer pixel real vizinho. A técnica que resolveu isso
é **clonar um recorte do mesmo tamanho** de outra posição da própria
imagem, escolhida por tentativa:

1. Tenta deslocamentos horizontais primeiro (`±largura`, `±2×largura`),
   depois verticais (`±altura`, `±2×altura`), alternando direção.
2. Um candidato só é aceito se a região correspondente estiver "limpa"
   (sem nenhum pixel do índice de tinta, e fora de qualquer outra caixa
   de apagamento da mesma tela via parâmetro `exclude`).
3. Se nenhum deslocamento candidato ficar limpo, cai de volta no
   preenchimento por moda local (mesmo algoritmo do `erase_box`
   original dos painéis INTRO).

Essa é a técnica-padrão para qualquer novo fundo texturizado de alto
contraste — comece por ela em vez de preenchimento plano.

**Contraponto importante**: em `POPUP3.IMG`/`POPUP4.IMG`, cujo fundo é
um mármore escuro **liso, de baixo contraste** (mas com um gradiente
sutil de brilho ao longo da largura do painel), o clone de textura
**piorou** o resultado — a nuvem clara/escura do mármore tem brilho
médio ligeiramente diferente em cada ponta do painel, então colar um
recorte de uma ponta na outra deixa uma costura retangular visível
(mais sutil que um preenchimento plano errado, mas ainda visível).
`build_bsa_popup.py` resolveu isso **voltando** ao preenchimento por
moda local (mesmo algoritmo do "estilo INTRO"). Regra prática: **fundo
ruidoso de alto contraste → clonar; fundo liso com gradiente suave →
moda local**, e sempre conferir visualmente as duas antes de decidir
(a diferença só aparece ampliando o preview, não é óbvia a olho nu no
tamanho real do jogo).

## Medindo a caixa do texto original (por linha, não por bloco)

Regra permanente do projeto (instrução original do usuário): "tentar
manter o texto na mesma área do texto original, sem tocar a borda dos
pergaminhos e não deve ser um quadrado, deve desenhar linha a linha,
para garantir que fique a mesma área do texto original."

Ou seja: **cada linha do texto original tem sua própria caixa
retangular**, nunca uma caixa única cobrindo o bloco inteiro (que
tipicamente sobraria para dentro da arte nas linhas mais curtas). Ver a
classe `Caption` e o dicionário `PANELS` em `build_bsa_intro.py` para o
formato consolidado: `original_lines: list[Box]`, uma tupla
`(x0, y0, x1, y1)` por linha.

Duas formas de medir essa caixa, dependendo do que está disponível:

1. **A olho, sobre um render ampliado (3–4x, nearest-neighbor)** do
   painel pristino — é como toda caixa de `PANELS` em
   `build_bsa_intro.py` foi obtida originalmente. Bom para arte com
   texto sobre fundo irregular, onde um scan automático teria muitos
   falsos positivos vindos da própria ilustração.
2. **Scan de pixels por um conjunto de índices de tinta conhecidos**
   (descoberto por amostragem pontual, ver o gotcha de paleta acima),
   quando o fundo é limpo o bastante para não gerar ruído. Duas
   variantes usadas neste projeto, ambas em Python simples sobre a
   lista de pixels pristina:
   - **Bandas por linha**: varra as linhas (`y`) e agrupe em "bandas"
     contíguas de `y` que contenham pelo menos um pixel de tinta — cada
     banda contígua tende a ser uma linha de texto.
   - **Grupos por coluna** (para textos numa única linha, como um
     botão): varra as colunas (`x`) dentro de uma banda de `y` já
     conhecida, e agrupe colunas próximas (com um "gap" de tolerância,
     tipicamente 8–14px, calibrado por inspeção visual) em grupos —
     cada grupo tende a ser uma palavra/frase.
   - Nas duas variantes, é normal ter que **inspecionar visualmente**
     (crop + grade de régua a cada 5–10px, com as coordenadas
     desenhadas) para descartar bandas/grupos espúrios vindos de
     textura/decoração incidental, antes de confiar nos números.

Para overlays de conferência lado a lado (original vs. traduzido, com
grade verde a cada 10px), ver o padrão usado nas revisões deste projeto:
renderizar os dois num só PNG empilhado, escala 3x, linha de grade a
cada 10px do espaço de coordenadas da imagem original — isso é o que
permite ao usuário conferir pixel a pixel se início/fim de cada rótulo
bate com o original.

## Separando "onde apagar" de "onde desenhar"

Quando a tradução em português precisa de mais linhas ou mais largura
que o inglês original, apagar e desenhar usando exatamente a mesma caixa
força uma escolha ruim: ou a caixa de apagamento fica larga demais (e
some com a arte), ou o texto novo fica espremido demais. A classe
`Caption` (`build_bsa_intro.py`) resolve isso com campos independentes:

- `original_lines` — caixas **apertadas**, medidas contra o inglês;
  usadas **só para apagar**. Nunca alargar isso "para caber mais texto"
  — isso é o que garante nunca tocar a arte.
- `draw_lines` — caixas **mais largas** (remedidas contra os limites
  reais da arte, não do texto original), usadas **só para decidir a
  largura de quebra de linha** do texto traduzido. Por padrão (se não
  informado) é igual a `original_lines`.
- `draw_top` / `draw_left` — quando o ponto de partida natural para o
  texto redesenhado não é o mesmo canto de `original_lines` (por
  exemplo, depois de apertar a caixa de apagamento, sobrou espaço que
  faz mais sentido usar). Por padrão, usa o canto de `original_lines`.
- `line_height` — usado só quando `draw_top` está definido (posição
  manual); sem `draw_top`, o espaçamento é `altura_total_do_bloco //
  número_de_linhas`, para o bloco desenhado nunca ultrapassar o espaço
  vertical que o bloco original ocupava, não importa quantas linhas o
  texto traduzido acabe usando.

Ao ajustar uma legenda que está estourando ou sobrando espaço, o
primeiro instinto deve ser mexer em `draw_lines`/`draw_top`/`draw_left`
— não em `original_lines`, que deve continuar refletindo fielmente onde
o texto em inglês estava.

## Escolha de fonte de apagamento/desenho

| Fonte | Onde é usada | Por quê |
|---|---|---|
| `NotoSerif-Italic.ttf` | Painéis INTRO, HISTORY.IMG, SCROLL01/02/03.IMG | Corpo de texto narrativo/pergaminho — itálico serifado lê como caligrafia de manuscrito |
| `Montserrat-Black.otf` | Títulos grandes de UI (banner "GRIMÓRIO"/"CRIA-FEITIÇOS"), CHARSPEL.IMG | Peso bem grosso, adequado só para títulos estilo rúnico/banner — **grosso demais para rótulos pequenos**, ver abaixo |
| `Montserrat-Bold.otf` | Rótulos e botões de BUYSPELL.IMG/SPELLMKR.IMG | Peso mais fino que Black — necessário depois que Black em rótulos pequenos ficou "muito grosso e grande" comparado ao original (feedback direto do usuário) |
| `NotoSans-Bold.otf` | Rótulos/botões de CHARSPEL.IMG | Sans-serif direto, bom para UI pequena |

**Lição registrada**: a fonte "Black" (peso mais pesado) só deve ser
usada onde o original também é claramente um traço grosso/bloco (um
banner de título estilo rúnico). Para rótulos de campo e texto de botão
pequenos, ela lê como grande e grosso demais — prefira `Bold` normal, e
ajuste o tamanho para casar com a altura de caixa (cap height) real
medida no original (nas telas de feitiço, ~7–9px).

## Como posicionar/dimensionar texto para bater com o original

Três técnicas distintas foram desenvolvidas, cada uma para um problema
diferente — não são intercambiáveis, escolha pela situação:

### `draw_at` — posição fixa, tamanho natural

A técnica padrão para qualquer rótulo/botão cujo comprimento em
português é parecido com o original: desenha o texto no tamanho de
fonte natural, com o canto superior-esquerdo da caixa do texto
(`textbbox`) alinhado exatamente ao ponto medido no original. Contorno
opcional é um único deslocamento de 1px na diagonal (`(x+1, y+1)`), não
um anel completo de 8 direções — um anel completo dobra a espessura
visual da letra e faz o texto ler como muito mais grosso/grande do que
é, o que foi justamente uma reclamação do usuário resolvida trocando
para esse contorno de 1 canto só.

### `draw_title` — esticar para caber numa caixa fixa (uso restrito)

Usada só para o banner-título estilo rúnico de BUYSPELL/SPELLMKR
("GRIMÓRIO"/"CRIA-FEITIÇOS"): renderiza o texto grande e nítido, corta
para a caixa delimitadora real dos pixels desenhados, e então
**redimensiona (esticando, via LANCZOS) para uma largura E altura
exatas**, definidas de antemão para bater com a região que o título
original ocupava (medida excluindo o índice de cor de fundo liso: no
caso de BUYSPELL/SPELLMKR, x:80–239, y:0–19, ambas as telas idênticas).
A altura também precisa ser controlada explicitamente aqui porque o
banner fica bem perto da primeira linha de rótulos logo abaixo — sem
isso, o título esticado verticalmente colide com "Saldo:"/"Nome:".

Essa técnica **distorce as letras** (esticar/espremer) e por isso só
deve ser usada quando a palavra em português tem comprimento parecido
com o original (esticar ~1.4x, como "GRIMÓRIO" precisou, ainda fica
legível; um fator muito maior não fica).

### `draw_fitted` — diminuir a fonte e centralizar (técnica preferida para rótulos/botões)

Quando o texto traduzido é **bem mais longo ou mais curto** que o
espaço horizontal que o original ocupava (ex.: "Comprar Feitiço" no
lugar de "Buy Spell", um espaço bem mais estreito no SPELLMKR), **não
esprema as letras** — isso foi tentado primeiro (esticar/espremer a
largura para bater exatamente com o x0/x1 original) e o usuário rejeitou
o resultado ("Está bem ruim, textos muito grossos e grandes" /
depois "o Comprar Feitiço que está espremido"). A técnica correta,
registrada em `draw_fitted` (`build_bsa_ui.py`):

1. Comece no tamanho de fonte "base" desejado (calibrado para bater com
   a altura de caixa do original).
2. Se a largura natural (sem distorção) do texto nesse tamanho
   ultrapassar `(x1 - x0) * overflow` (uma folga de ~10%), **diminua o
   tamanho da fonte** (nunca estique/esprema) até caber dentro dessa
   folga, ou até um tamanho mínimo de segurança.
3. Desenhe centralizado no **ponto médio** `(x0+x1)/2` do espaço
   original — não alinhado à esquerda em `x0` — para que o centro do
   texto traduzido bata com o centro do texto original mesmo quando o
   resultado transborda um pouco os dois lados.

Isso foi explicitamente pedido pelo usuário como regra geral: "diminuir
a fonte e pode passar um pouquinho, desde que o centro esteja
alinhado" — ou seja, largura aproximada é aceitável e preferível a
letras distorcidas, desde que o **centro** continue no mesmo lugar.

**Ordem de preferência recomendada para texto de rótulo/botão daqui pra
frente: `draw_fitted` (diminuir+centralizar) é o padrão; `draw_title`
(esticar) só se justifica quando as duas palavras têm comprimento bem
parecido E a região é um banner de título isolado, sem linha de rótulo
colada embaixo.**

### `draw_right_aligned` — alinhar por coluna à direita + pela borda inferior (fichas com rótulos "label:")

Para telas onde o original já organiza rótulos "Nome:"/"For:"/etc. em
**colunas alinhadas à direita** (todo ":" de uma coluna termina no mesmo
`x`) — `CHARSTAT.IMG` (ficha de atributos) e os cabeçalhos de coluna de
`POPUP3.IMG`/`POPUP4.IMG` são exemplos — replique exatamente esse
alinhamento em vez de usar `draw_fitted`/centralização:

1. Meça, por coluna, o `x` onde o original termina (a borda direita
   compartilhada) — não o `x` onde cada rótulo individual começa.
2. Desenhe cada rótulo traduzido com a borda **direita** da sua própria
   caixa de texto (`textbbox`) alinhada exatamente a esse `x` da coluna
   — `anchor_x1 - (bbox[2]-bbox[0])`, nunca esticar/espremer para
   caber.
3. Para a posição vertical, **não** centralize no meio geométrico da
   caixa de apagamento. Use a **borda inferior** (baseline) de cada
   rótulo original, medida individualmente — texto com descendentes
   (`g`, `p`) empurra visualmente para baixo, então alinhar pelo centro
   geométrico deixa alguns descendentes tocando a linha seguinte mesmo
   quando o espaçamento médio entre linhas parece correto.
   `CHARSTAT.IMG` precisou, além disso, de pequenos ajustes manuais
   nessa borda inferior por linha (`Res:`/`Sor:` tiveram vizinhos
   desigualmente espaçados no original) — meça, não assuma
   espaçamento uniforme.

Esse padrão foi estabelecido depois que a primeira tentativa em
`CHARSTAT.IMG` (alinhamento à esquerda, depois centralização vertical)
recebeu feedback direto do usuário: "alinhas pelo centro vertical e
pela direita na horizontal... Alinhe as colunas pela direita, igual ao
original", e depois "Invés de alinhar pelo centro, experimentar alinhar
pela borda inferior."

## Telas de UI: BUYSPELL.IMG / SPELLMKR.IMG / LOGBOOK.IMG

Essas três são `.IMG` cru (sem compressão), com paleta embutida, fundo
de pergaminho plano — tratadas por `scripts/build_bsa_ui.py`.

- **BUYSPELL.IMG** ("Grimório") e **SPELLMKR.IMG** ("Cria-Feitiços")
  compartilham exatamente o mesmo layout de campo (`SPELLSCREEN_LABELS`,
  `SPELLSCREEN_ERASE`): Nome/Nível/Feitiço/Alvo/Efeitos à esquerda,
  Saldo/Custo/Resist./Conjuração à direita — mesmos rótulos, mesmas
  coordenadas x0/x1/y0 medidas uma vez e reaproveitadas para as duas
  telas. Só o título do banner e os botões de ação (que têm textos
  diferentes: "Escolher Outro Feitiço"/"Comprar Feitiço"/"Sair" vs.
  "Novo Feitiço"/"Comprar Feitiço"/"Sair") mudam por tela.
- O título do banner usa um esquema de cor **diferente** do resto dos
  rótulos — não reaproveite `GOLD`/`OUTLINE` para ele. Medido por
  amostragem direta da paleta pristina: preenchimento ≈ RGB(174,101,0),
  contorno ≈ RGB(77,40,16) (índices de paleta 147 e 73 no arquivo
  original). Os rótulos de campo usam `GOLD = (235,190,32)` /
  `OUTLINE = (85,44,20)`.
- **LOGBOOK.IMG** ("Diário") é mais simples: tinta quase-preta
  (`LOGBOOK_INK = (24,24,24)`), sem o esquema dourado, um único título e
  dois rótulos de rodapé (imprimir/sair).

## Verificação de round-trip (obrigatória em `compile_images.py`)

Como todo `build_bsa_*.py`/`build_images.py` grava só um PNG (sem perda
possível), a verificação de round-trip que importa de verdade —
confirmar que a compressão/cabeçalho binário do jogo foi montado
corretamente — acontece uma vez só, dentro de `compile_images.py`
(`img_codec.verify_roundtrip`): relê o `.IMG` recém-gravado, decodifica
de volta, e compara byte a byte com os índices de pixel que vieram do
PNG — se não bater, lança `RuntimeError` imediatamente em vez de deixar
passar um arquivo corrompido silenciosamente. Ao adicionar um novo
arquivo traduzível, não é preciso reimplementar essa verificação — só
adicionar a entrada certa em `img_manifest.py`.

## Varredura bruta de imagens não analisadas

`scripts/varredura_img_bruta.py` decodifica, de uma vez, TODO `.IMG` do
`GLOBAL.BSA` que ainda não está em `img_manifest.IMAGE_MANIFEST` (ou
seja, tudo que nunca foi individualmente investigado) para PNG em
`varredura_imagens/` (raiz do projeto, fora do pipeline de build) — sem
cuidado nenhum de paleta por arquivo (paleta embutida se tiver, senão
`PAL.COL` de chute) e sem nenhuma validação. O objetivo não é qualidade
de imagem, é permitir uma passada visual rápida (humana, num
visualizador de imagens com miniaturas) para achar arquivos com texto
escondido — mesmo com a paleta errada, o desenho da tinta geralmente
ainda aparece como algo visualmente distinto do fundo.

Duas descobertas ao rodar isso pela primeira vez:

1. Muitas texturas de piso/parede de masmorra (referenciadas em `.INF`,
   ex. `caspit.img`, `bluerug.img`, a família `BS_*.IMG`) não têm o
   cabeçalho `.IMG` de 12 bytes comum ao resto do projeto — são um
   bloco cru **quadrado** sem compressão (mais comum: 64×64 = 4096
   bytes). O script detecta isso por descarte: se o cabeçalho de 12
   bytes render dimensões absurdas E o tamanho do arquivo for um
   quadrado perfeito (`math.isqrt`), trata como textura crua. Isso
   sozinho fez a taxa de conversão saltar de 450/921 para 908/921.
2. Um punhado (13) de arquivos pequenos e de tamanho incomum
   (`SLIDER.IMG`, `UPDOWN.IMG`, `DITHER.IMG`, `NOCAMP.IMG`, ...) não se
   encaixa em nenhum dos dois formatos — ficam listados em
   `varredura_imagens/_erros.txt`, não vale o esforço de decifrar esse
   formato ainda dado o volume pequeno.

Arquivos confirmados com texto por essa varredura entram na [seção 4 de
inventario-arquivos.md](inventario-arquivos.md#4-confirmados-com-texto-pendentes-de-tradução)
como pendentes — a tradução de verdade de cada um segue o processo
normal (medir posição/cor de tinta, escolher paleta certa por trial,
escrever um `build_bsa_*.py` dedicado) quando for a vez de fazer.

## Medindo posição por perfil de coluna (telas com widgets no meio do texto)

Para telas como `OP.IMG`/`FORM*.IMG`, onde cada linha mistura rótulo +
caixa numérica + spinner de seta + outro rótulo, ler a posição num grid
ampliado visualmente é pouco confiável — é fácil confundir onde o
rótulo termina e o widget começa, ou vice-versa (isso já causou
retrabalho nesta sessão: posições erradas por >10px, texto original
"fantasma" sobrando ao lado da tradução). A técnica que resolveu isso:

1. Para uma faixa `(y0, y1)` de uma linha, calcule por coluna `x` a
   **fração de linhas** naquele intervalo que têm o índice de tinta
   conhecido: `perfil[x] = contagem_de_tinta(x, y0, y1) / (y1 - y0)`.
2. Classifique cada coluna: `'W'` (parede) se a fração > 0.5 — uma
   borda VERTICAL de caixa atravessa quase toda a altura da linha, then
   `'t'` (texto) se `0 < fração <= 0.5` — um traço de letra ou a borda
   HORIZONTAL de uma caixa (que só toca 1–2 das ~13 linhas da faixa) —
   e `'e'` (vazio) se não há tinta ali.
3. Agrupe em "runs" contíguos do mesmo tipo. Um run `'t'` **largo**
   (>9px) é quase sempre a borda superior/inferior de uma caixa numérica
   (ocupa toda a largura da caixa numa única linha fina); runs `'t'`
   **estreitos** (2–5px) são letras individuais de um rótulo.

Isso separa com precisão "onde termina o rótulo" de "onde começa o
widget" sem depender de leitura visual. Gotcha descoberto ao aplicar
isso: os spinners (setas para cima/baixo) ficam **só do lado esquerdo**
do primeiro widget de uma linha — o vão entre duas caixas na mesma
linha (o "para"/"a" de um intervalo X–Y) é limpo, mas o vão **depois**
da última caixa de uma linha (antes de um sufixo como "Níveis") quase
sempre tem a seta direita de um segundo spinner que se estende bem além
da própria caixa — sempre confira o pixel real ali antes de assumir uma
margem de segurança fixa.

## `erase_box` por moda local vs. clone: mancha de brilho grande

`OP.IMG` e os 17 `FORM*.IMG` compartilham um fundo alaranjado/lava com
uma mancha de brilho suave e grande (um "blob" mais claro no meio do
painel). Nessas telas, clonar um recorte do mesmo tamanho de outra
posição (a técnica que funciona bem em `CHARSTAT.IMG`/`NEWEQUIP.IMG`)
frequentemente planta um retângulo visivelmente errado, porque o
deslocamento tentado cai numa parte do blob com brilho médio diferente
do ponto original. A correção foi voltar ao preenchimento por moda
local (estilo painéis INTRO/POPUP3-4) para essas telas — mesmo
sendo um fundo "texturizado", o gradiente de larga escala do blob pesa
mais que o ruído fino da textura na hora de escolher a técnica certa.
Regra prática revisada: **textura de alto contraste E sem gradiente de
brilho em larga escala → clonar; qualquer coisa com uma mancha de
brilho suave visível a olho nu (mesmo que a textura em si seja
"ruidosa") → moda local.**

## Fluxo de revisão com o usuário

Este projeto usa um ciclo de revisão bem iterativo e visual — ao
implementar qualquer mudança de imagem, siga este padrão em vez de
assumir aprovação:

1. Gere/atualize o preview PNG do arquivo mexido (`preview_imagens/`,
   2–4x nearest-neighbor — nunca com suavização, isso borraria os
   pixels que estão sendo conferidos).
2. Para conferência de posição/tamanho fina, gere uma versão com **grade
   verde a cada 10px** sobreposta, empilhando original e traduzido no
   mesmo PNG para comparação lado a lado (ver função `add_grid` usada
   nas revisões deste projeto).
3. Mostre o(s) preview(s) e pergunte pontualmente o que aprovar/ajustar
   (via pergunta de múltipla escolha quando fizer sentido) — não
   prossiga para o próximo arquivo/tela sem confirmação explícita.
4. Só depois de aprovado, esse arquivo é considerado estável — mudanças
   posteriores em outro arquivo não devem reabrir esse a menos que o
   usuário peça.
