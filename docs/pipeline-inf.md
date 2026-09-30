# Pipeline de tradução dos `.INF` (texto de sabedoria de masmorra)

Além dos `.IMG` (pixel art) e dos arquivos de texto `.DAT`/`.TXT`/`.LST`
comuns, o `GLOBAL.BSA` também contém 93 arquivos `.INF` — scripts de
masmorra/localização (texturas de parede/chão, posição de monstros e
itens) que também carregam uma seção `@TEXT` com o texto de sabedoria
mostrado ao explorar: placas, bilhetes, descrições ambiente, enigmas.
57 deles têm conteúdo em `@TEXT`. Ver
[docs/pipeline-imagens.md](pipeline-imagens.md) e
[docs/pipeline-textos.md](pipeline-textos.md) para os outros dois
pipelines.

## Gotcha crítico: alguns `.INF` também existem como arquivo solto — e esse é o que vale

Cinco `.INF` (`CRYSTAL3.INF`, `IMPPAL1.INF`, `IMPPAL2.INF`, `IMPPAL3.INF`,
`IMPPAL4.INF` — os níveis do Palácio Imperial, confronto final com
Jagar Tharn) existem **duplicados**: uma cópia dentro do `GLOBAL.BSA` e
uma cópia solta direto na pasta do jogo, referenciada pelo `.MIF`
solto correspondente (`IMPPAL.MIF`). As duas cópias têm o mesmo texto
`@TEXT` (confirmado byte a byte).

**A cópia solta é a que o jogo realmente usa** — resolução de arquivo
clássica de DOS: um arquivo solto na pasta do jogo tem prioridade sobre
a mesma entrada dentro do arquivo `.BSA`. Traduzir só a cópia dentro do
`GLOBAL.BSA` (o que `build_bsa_inf.py` faz) deixa essas telas
aparecendo em inglês no jogo de verdade, mesmo com o `GLOBAL.BSA`
corretamente traduzido — foi exatamente isso que aconteceu numa
primeira rodada desta tradução, e só apareceu ao testar in-game.

A cópia solta também é estruturalmente diferente da de dentro do BSA:
**não é criptografada** (`INFFile.cpp` do OpenTESArena: `isEncrypted =
inGlobalBSA` — só arquivos vindos de dentro do BSA passam pelo XOR).
`scripts/build_inf_loose.py` cuida dela separadamente: lê texto puro
(sem `xor_crypt`), reaproveita as MESMAS entradas do dicionário
`TRANSLATIONS` de `build_bsa_inf.py` (para não duplicar o texto
traduzido em dois lugares), e salva o texto (com acento, ainda não
compilado) em `Minha tradução/legivel/<nome>` — `compile_inf.py` depois
remove o acento e grava o `.INF` final em `Minha tradução/<nome>` (sem
criptografar, já que é solto) — ver ["Acentuação"](#acentuação-removida-só-no-compile-inf-nunca-antes)
abaixo.

Se aparecer uma tela ainda em inglês mesmo depois de traduzida dentro
do `GLOBAL.BSA`, **sempre confira primeiro se existe uma cópia solta do
mesmo nome na pasta do jogo** antes de assumir que a tradução do
conteúdo está errada — o problema pode ser simplesmente qual cópia o
jogo está lendo. Um jeito rápido de checar: qual `.MIF` referencia
aquele `.INF` (`INFO` tag dentro do `.MIF`, ver
[pipeline-imagens.md](pipeline-imagens.md) para o formato de tags do
`.MIF`) — se aquele `.MIF` também é solto (não vem do `GLOBAL.BSA`), o
`.INF` que ele aponta quase certamente também precisa ser a cópia
solta.

## Descoberta e formato

Todo `.INF` dentro do `GLOBAL.BSA` é "criptografado" com XOR de chave
fixa de 8 bytes (`scripts/inf_codec.py`, confirmado contra
`INFFile.cpp` do OpenTESArena) — como XOR é a própria inversa, a mesma
função `xor_crypt()` cifra e decifra.

O texto decifrado é organizado em seções `@FLOORS`/`@WALLS`/`@FLATS`/
`@SOUND`/`@TEXT` etc. Só `@TEXT` é traduzido; todo o resto (nomes de
arquivo de textura, posições, sons) é preservado byte a byte.

Dentro de `@TEXT`, cada bloco começa com uma linha `*TEXT <id>` e
contém uma mistura de:
- **linhas de sabedoria (prosa)** — o texto traduzível.
- **linhas de resposta**, começando com `:` (ex.: `:sun`) — palavras-
  chave que o jogador digita para resolver um enigma.
- **linhas estruturais/de lógica de jogo**, preservadas ao pé da
  letra: uma linha em branco, um `-` sozinho (separador visual em
  enigmas/versos), uma linha começando com `^` (código de exibição,
  ex. `^255 0`), uma linha `+N` (referência numérica a outra tabela),
  ou um rótulo de ramificação `` `CORRECT``/`` `WRONG`` (em um arquivo,
  `DEMO.INF`, esse rótulo usa apóstrofo `'CORRECT`/`'WRONG` em vez de
  crase — `scripts/inf_codec.py`'s `classify_line()` trata as duas
  formas como equivalentes, por correspondência exata, não por
  prefixo, já que outros arquivos têm prosa legítima começando com
  apóstrofo, ex. `'Ware the Emperor`).

## Gotcha crítico: um bloco pode ter várias "sub-frases" de prosa

Um único bloco `*TEXT N` frequentemente intercala **várias prosas
separadas** com marcadores estruturais entre elas — por exemplo, um
enigma típico é: `[código de exibição]` `[frase de introdução]` `-`
`[corpo do enigma em verso]` `-` `[pergunta]` `[respostas]`
`` `CORRECT `` `[texto de sucesso]` `` `WRONG `` `[texto de falha]`.
Isso são **5 prosas distintas dentro do mesmo bloco**, não uma só.

A primeira versão deste pipeline juntava toda a prosa do bloco numa
única string, traduzia como um só texto, e distribuía o resultado de
volta nas linhas originais na ordem em que apareciam — isso
**recolocava os marcadores no lugar errado** em relação ao texto
traduzido (ex.: a resposta `:sol` acabava inserida no meio de uma
frase, ou a pergunta ficava depois da resposta) sempre que o número de
palavras do português não distribuía igual ao do inglês. A correção:
`TextBlock.prose_runs()`/`render()` tratam cada sub-frase de prosa como
uma unidade de tradução própria — a tradução de cada bloco é uma
**lista de strings**, uma por sub-frase, na mesma ordem; `render()`
levanta `ValueError` se a lista não tiver exatamente o mesmo número de
itens que o bloco tem de sub-frases, para pegar esse erro cedo.

```python
# UMA sub-frase (bloco sem marcadores no meio) - string simples aceita:
"NOBLE.INF": {1: ("O Salão Principal", None)}

# VÁRIAS sub-frases (enigma com introdução/corpo/pergunta/certo/errado)
# - lista obrigatória, uma entrada por sub-frase, na mesma ordem:
"BGATE2.INF": {
    0: T(
        [
            "Esta porta está lacrada... Que resposta você dá?",
            "O que é a coisa que vem em lençóis...?",
            "A porta agora está destrancada.",
            "Nada acontece.",
        ],
        "chuva", "a chuva",
    ),
},
```

Antes de escrever a tradução de um bloco novo, sempre confira quantas
sub-frases ele tem (`TextBlock.prose_runs()` num script descartável, ou
veja o `build_bsa_inf.py` já ter um audit script equivalente rodado
antes de cada build) — nunca assuma que "um bloco = uma frase".

## Enigmas com trocadilho intraduzível: adaptação, não tradução literal

Dois enigmas dependem de ortografia/estrutura do inglês sem equivalente
direto em português:

- **DAGOTH3.INF**: a resposta original é a letra "E" (eternity começa
  com E, time/space terminam em E, end começa com E, place termina em
  E) — reescrito como um enigma NOVO em português com a mesma função
  (abrir a porta dizendo uma letra), usando palavras que fazem o mesmo
  truque funcionar para a letra "O" (Ocaso/eco/obstáculo/perigo).
- **ELDEN2.INF (segundo enigma)**: a resposta original é uma palavra
  composta ("foot" + "step" = "footstep") sem equivalente em
  português — reescrito como um enigma descritivo comum cuja resposta
  é "pegada"/"pegadas".

Essas duas são **adaptações criativas**, não traduções literais —
sinalizadas com comentário no código (`build_bsa_inf.py`) para o
usuário revisar e, se quiser, substituir por algo diferente.

## Acentuação: removida só no `compile_inf.py`, nunca antes

`build_bsa_inf.py`/`build_inf_loose.py` decifram, traduzem, e salvam o
texto resultante **com acento**, sem criptografar, em
`Minha tradução/GLOBAL_parts/legivel/<nome>` (ou
`Minha tradução/legivel/<nome>` para os soltos) — o arquivo de trabalho
legível, editável à mão se precisar (ver
[pipeline-imagens.md](pipeline-imagens.md#legivel-vs-formato-do-jogo)
para o mesmo princípio aplicado às imagens).

`GLOBAL.BSA` inteiro é copiado sem alteração pelo `build.py` genérico
(está em `ARQUIVOS_IMAGEM_BINARIOS` — é binário comprimido/criptografado,
rodar o removedor de acentos nele corromperia dados), então o acento só
pode sair em algum ponto anterior a isso. Como esse texto é renderizado
pelo mesmo motor de texto do jogo (não é pixel art desenhada à mão),
`compile_inf.py` chama `remover_acentos_str()` (importado de
`scripts/build.py`) sobre o texto lido de `legivel/` — a mesma
transformação que todo outro arquivo de texto do projeto recebe (ver
[pipeline-textos.md](pipeline-textos.md#acentuação-e-cedilha-como-e-onde)),
só que aplicada aqui em vez de pelo `build.py` genérico — e só então,
para os `.INF` que vieram de dentro do `GLOBAL.BSA`, recriptografa com
`xor_crypt` antes de gravar em `GLOBAL_parts/<nome>` (o mesmo lugar onde
o pristino vivia). Os 5 `.INF` soltos não passam por `xor_crypt` nesse
ponto — nunca foram criptografados, dentro ou fora do jogo.

## Verificação

`compile_inf.py` (não `build_bsa_inf.py`/`build_inf_loose.py` — esses só
gravam texto legível, sem perda possível) faz o round-trip real: decifra
de volta o que acabou de gravar e confirma que é exatamente o texto que
tinha acabado de ler de `legivel/`, já sem acento
(`verify_text == text`). Além disso: (1) sem tradução aplicada,
`split_sections`/`parse_text_section`/`render(None, None)` devem
reproduzir o arquivo original **byte a byte** (checado uma vez ao
desenvolver o codec, cobrindo os 93 arquivos `.INF`, não só os 57
traduzidos); (2) um audit script à parte (não incluído no build normal)
confere, para cada bloco traduzido, que o número de sub-frases e de
respostas bate exatamente com o original antes de rodar o build de
verdade — rode-o sempre que adicionar uma tradução de bloco nova, para
pegar erros de contagem antes que virem `ValueError` no meio do build.
