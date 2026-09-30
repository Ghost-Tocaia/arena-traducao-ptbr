# Pipeline de tradução de textos (`.DAT` / `.TXT` / `.LST`)

Para arquivos cujo texto é armazenado como caracteres de verdade (não
pixel art) — diálogos, descrições, menus baseados em texto. Ver
[pipeline-imagens.md](pipeline-imagens.md) para telas cujo texto é
desenhado como imagem.

## Formato do arquivo original

Os arquivos de texto do jogo (ex.: `JAGTEMP.DAT`) são Latin-1/CP437, 1
byte por caractere, quebra de linha `\r\n`, organizados em blocos assim:

```
#0000a
Você entra na câmara de
audiências do %t, notando os
belos ornamentos e móveis que
...
aos seus lábios.&

#0000b
próximo bloco...
```

- Uma linha começando com `#` seguido de dígitos hexadecimais é o
  cabeçalho/ID de um bloco de texto (usado pelo motor do jogo para achar
  aquele texto).
- As linhas seguintes até a próxima linha vazia/comentário/cabeçalho são
  o corpo do bloco, já pré-quebrado pelo jogo original em linhas curtas
  (a largura de uma caixa de diálogo do DOS).
- `%t`, `%rf`, `%cn`, `%cn2`, `%ct`, `%st` etc. são placeholders do motor
  — **nunca traduzir nem alterar**, ver
  [traducao-estilo.md](traducao-estilo.md#placeholders-variáveis-do-motor-do-jogo-nunca-alterar).
- Um `&` no fim do último caractere de texto de um bloco é um marcador
  de fim-de-registro do motor, não pontuação.
- Linhas começando com `;` são comentários e ficam como estão.

## O fluxo, passo a passo

Os scripts usam sempre o nome genérico **`TEMPLATE`** como
placeholder — para traduzir um arquivo real (ex.: `JAGTEMP.DAT`), copie-o
para `Minha tradução/TEMPLATE.DAT` antes de começar, e ao final copie o
`TEMPLATE.DAT` resultante de volta para o nome real.

1. **`python3 scripts/split_template.py`**
   Quebra `Minha tradução/TEMPLATE.DAT` em pedaços de ~1000 linhas
   (sempre cortando numa fronteira de bloco `#hex`, nunca no meio de um
   bloco), salvos em `Minha tradução/TEMPLATE_parts/TEMPLATE_part_NN.DAT`.
   Isso existe só para manter cada pedaço num tamanho confortável de
   revisar/traduzir de uma vez.

2. **Traduzir cada parte.** Para cada `TEMPLATE_part_NN.DAT`, crie um
   `TEMPLATE_part_NN.py` do lado com um dicionário `translations`
   mapeando o **índice sequencial do bloco de texto dentro daquele
   arquivo** (0, 1, 2, ... — não o `#hex` do jogo) para a string
   traduzida:

   ```python
   translations = {
       0: "Você entra na câmara de audiências do %t, notando os belos "
          "ornamentos e móveis que decoram o local. ...&",
       1: "Lá fora, o sol castiga sem trégua os cidadãos de %cn, ...&",
   }
   ```

   Observações sobre este dicionário:
   - A string é escrita **em uma linha só** (sem as quebras de linha
     curtas do original) — `mount_template_part.py` faz o reflow para
     largura fixa depois. Não precisa se preocupar em quebrar linha na
     mão.
   - Incluir o `&` final é opcional (o script tolera e remove antes de
     re-adicionar do jeito certo), mas é mais seguro incluir para deixar
     claro que aquele bloco tem fim-de-registro.
   - Todo bloco de texto do `.DAT` original recebe um índice, na ordem
     em que aparece; se algum índice não estiver no dicionário
     `translations`, aquele bloco é deixado no idioma original e um
     aviso é impresso (nunca falha silenciosamente).

3. **`python3 scripts/mount_template_part.py`**
   Para cada `TEMPLATE_part_NN.py` encontrado, lê o `.DAT` irmão de
   mesmo número, substitui o texto de cada bloco pela tradução
   correspondente (reflow para `LINE_WIDTH = 30` caracteres por linha,
   preservando cabeçalhos `#hex`/comentários/linhas em branco
   intocados), e **sobrescreve o próprio `.DAT`** com o resultado.

4. **`python3 scripts/merge_template.py`**
   Concatena `TEMPLATE_part_01.DAT`, `_02.DAT`, ... (nessa ordem
   numérica, avisando se faltar algum número no meio) de volta em
   `Minha tradução/TEMPLATE.DAT`.

5. Copie `Minha tradução/TEMPLATE.DAT` de volta para o nome real do
   arquivo (ex.: `Minha tradução/JAGTEMP.DAT`).

6. **`python3 scripts/build.py`** (ao final, para todos os arquivos de
   texto de uma vez) remove acentos/cedilha de tudo em `Minha tradução/`
   — exceto os arquivos de imagem binários listados em
   `ARQUIVOS_IMAGEM_BINARIOS` dentro do próprio script, que são copiados
   sem alteração — e escreve o resultado em `build/`. Essa é a etapa que
   realmente prepara os arquivos para irem para o jogo: o DOS original
   não é confiável para exibir todos os acentos, então a build final
   troca `á→a`, `ç→c`, etc., sempre 1 caractere por 1 caractere (nunca
   muda o tamanho do arquivo).

   `build.py` detecta sozinho se um arquivo é "texto puro" (tenta UTF-8,
   cai para Latin-1) ou "binário com strings embutidas" (quando há bytes
   nulos no meio — típico de `.DAT`/`.MNU` do DOS) e só mexe em
   sequências de bytes que claramente parecem texto encostado numa
   borda de byte nulo, para nunca corromper dados binários/numéricos
   coincidentemente na faixa de bytes imprimíveis.

## Por que essa indireção via "TEMPLATE"

Os scripts são genéricos e reaproveitados para qualquer um dos vários
arquivos de texto do jogo (`ARTFACT1.DAT`, `CITYINTR`, `DUNGEON.TXT`,
`EQUIP.DAT`, `JAGTEMP.DAT`, `MUGUILD.DAT`, `QUESTION.TXT`,
`SELLING.DAT`, `SPELLMKR.TXT`, `SPELLS.LST`, `TAVERN.DAT`, ...) — em vez
de duplicar o script para cada um, o arquivo sendo trabalhado no momento
é sempre renomeado para `TEMPLATE.DAT` e destrenomeado de volta ao
terminar. `TEMPLATE_parts/` é sempre conteúdo de trabalho descartável:
não guarde nada importante só lá — o que precisa persistir é o
`TEMPLATE.DAT` final (renomeado para o nome real) em `Minha tradução/`.

**Exceção**: um dos arquivos reais do jogo já se chama, de fato,
`TEMPLATE.DAT` (confirmado pelo usuário) — um banco de falas de
cidadão com 809 blocos `#hexid` (direção de prédio, "Who are you?",
conversa de profissão/posse de taverna, rumor de artefato único). Não
precisa (nem deve) ser renomeado pra outro nome ao final; é o próprio
nome real. Hoje é reconstruído direto num único passo por
`scripts/reflow_template.py`, sem passar por `TEMPLATE_parts/`/split/
merge (ver o gotcha abaixo sobre por que o fluxo genérico de linha
única de ~31 caracteres quebrava esse arquivo especificamente).

## Gotcha crítico: `TEMPLATE.DAT` não tolera nenhuma edição de byte no DOSBox real

Descoberto por bisecção ao vivo com o usuário (04-05/09/2026), em
ordem crescente de certeza:

1. **Tradução completa, linhas forçadas a ~31 caracteres** (o fluxo
   antigo de split/traduzir partes/merge quebrava cada linha nesse
   limite, mas o arquivo original **não segue essa regra** — alguns
   blocos, como os de resposta de direção, sempre ficam numa linha
   física só, não importa o tamanho) — resultado: perguntar "Where
   is...?" a um cidadão respondia com fala de outro contexto (dono de
   taverna, informante de artefato).
2. Corrigido o alinhamento de linha com `scripts/reflow_template.py`
   (usa o inglês original como molde de estrutura — mesma contagem de
   parágrafo/linha por bloco — e só reflui o português já existente
   pra caber, sem mudar uma palavra; verificado que o texto achatado
   antes/depois é idêntico) — **o bug persistiu**.
3. Arquivo 100% original + só a primeira palavra de um bloco de
   direção traduzida (8 substituições, +1 byte no total) — bug
   persistiu, mas manifestou num bloco *diferente* (~5,4KB adiante do
   bloco mexido), sugerindo não ser um problema local.
4. Arquivo 100% original + **uma única letra trocada, mesmo tamanho de
   arquivo** (`O`→`A`, sem mudar nem 1 byte de tamanho) — **o bug
   ainda apareceu**, agora num sistema de diálogo totalmente diferente
   ("Who are you?" respondeu só "man").

Conclusão: o arquivo não é sensível a tamanho nem a offset acumulado —
é sensível a **qualquer desvio do conteúdo binário exato**, em
qualquer posição. Mesmíssimo padrão do campo `entities.attributeNames`
do `ACD.EXE` (ver
[pipeline-acd-exe.md](pipeline-acd-exe.md#gotchas-descobertos-leia-antes-de-mexer-em-algo-novo)) —
indício forte de checksum/CRC de integridade calculado em algum lugar
não identificado (provavelmente dentro do próprio `ACD.EXE`), que só
o OpenTESArena (que nunca executa o `.EXE` de verdade) ignora. Sem
desmontar esse código, não dá pra confirmar o mecanismo nem contorná-lo.

**Solução (05/09/2026)**: já que `build/` agora separa arquivos por
plataforma (ver
[pipeline-acd-exe.md](pipeline-acd-exe.md#estrutura-final-builddosbox-e-buildopentes)),
`TEMPLATE.DAT` também virou platform-specific em vez de aceitar o
trade-off: `build/opentes/TEMPLATE.DAT` fica traduzido (funciona
perfeitamente lá) e `build/dosbox/TEMPLATE.DAT` fica **igual ao
original em inglês**, cópia direta de `Originais/TEMPLATE.DAT` sem
passar por `reflow_template.py` nem acentuação - já que qualquer edição
quebra o DOSBox real, a única versão seguramente segura ali é a que
nunca foi editada.
