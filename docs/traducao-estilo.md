# Estilo de tradução

Este documento fixa as regras de conteúdo/estilo da tradução — o "o quê" e
"como escrever" — independente de qual arquivo ou formato está sendo
mexido. Para a mecânica de arquivos, ver [estrutura-arquivos.md](estrutura-arquivos.md),
[pipeline-textos.md](pipeline-textos.md) e [pipeline-imagens.md](pipeline-imagens.md).

## Registro medieval / Elder Scrolls

Arena se passa em Tamriel, o mesmo mundo dos jogos posteriores da série
The Elder Scrolls. A tradução deve soar como um texto de fantasia
medieval formal, não como português coloquial moderno:

- Prefira formas mais formais e "arcaicas" quando soarem naturais:
  "Império", "trono", "Conselho dos Anciãos", "Guarda Imperial", "Mago de
  Batalha Imperial", "Feiticeiro Imperial", em vez de equivalentes
  genéricos ou modernos.
- Evite gírias, abreviações de internet, ou construções muito coloquiais.
  O tom é o de um pergaminho/crônica, não o de um app.
- Mantenha a cadência de frase original quando possível (frases um pouco
  mais longas e descritivas são normais no gênero).
- Isso vale tanto para texto corrido (parágrafos, diários, itens de menu)
  quanto para rótulos curtos de UI — mesmo um rótulo de botão deve soar
  como parte do mundo do jogo, não como um app genérico traduzido.

## Nomes próprios: NUNCA traduzir

Nomes próprios do universo Elder Scrolls/Tamriel permanecem exatamente
como no original em inglês. Isso inclui, mas não se limita a:

- **Nomes de personagens**: Uriel Septim VII, Jagar Tharn, Talin
  Warhaft, Ria Silmane.
- **Topônimos**: Tamriel, Cyrodiil, e nomes de cidades/províncias em
  geral.
- **Título da franquia**: "The Elder Scrolls" nunca vira "Os
  Pergaminhos Anciãos" nem qualquer outra tradução — mesmo no meio de
  uma frase em português. Exemplo já traduzido e aprovado
  (`scripts/build_images.py`, `build_scroll03()`):

  > "...pois como os Elder Scrolls profetizaram, é aqui que sua aventura
  > começa..."

- **Nomes de itens/artefatos únicos e termos de jogo com grafia
  própria** (verificar caso a caso; na dúvida, não traduzir e perguntar).

O que **é** traduzido normalmente: títulos genéricos/comuns (Imperador,
líder da Guarda Imperial), termos de jogo genéricos (feitiço, nível,
alvo, saldo), e todo o texto narrativo ao redor dos nomes próprios.

## Placeholders/variáveis do motor do jogo: NUNCA alterar

Os arquivos de texto do jogo (`.DAT`/`.TXT`/`.LST`, ver
[pipeline-textos.md](pipeline-textos.md)) contêm tokens que o motor do
jogo substitui em tempo de execução por nomes/dados gerados
proceduralmente. Exemplos vistos em `TEMPLATE.DAT`: `%t`, `%rf`, `%cn`,
`%cn2`, `%ct`, `%st`.

- Esses tokens devem ser copiados **literalmente**, byte a byte, para a
  tradução — nunca traduzidos, nunca com espaço extra inserido dentro
  deles, nunca reordenados de um jeito que quebre o token.
- É esperado (e correto) que a ordem das palavras ao redor de um token
  mude entre inglês e português para a frase continuar gramatical — só o
  próprio token não pode mudar.
- O caractere `&` no fim de um bloco de texto é um marcador de
  fim-de-registro do motor do jogo (ver `mount_template_part.py`), não
  pontuação a ser traduzida ou removida do sentido — ele é
  automaticamente reanexado à última linha após o reflow, então ao
  escrever a tradução no dicionário `translations` normalmente nem
  precisa se preocupar em digitá-lo de novo (ver
  [pipeline-textos.md](pipeline-textos.md)).

## Crédito do tradutor

O jogo tem um crédito de tradução assinado embutido como pixel art em
`TITLE.IMG` (tela de título), logo abaixo de "Chapter One: The Arena",
dentro da silhueta da torre do coliseu (`scripts/build_images.py`,
`build_title()`):

```
Traduzido por:
Ghost Tocaia
```

Esse é o crédito oficial do projeto. Não remover nem alterar o nome sem
pedido explícito do usuário.

## Acentuação e cedilha: como e onde

A tradução em si é escrita normalmente, com todos os acentos e cedilhas
do português. A **remoção** de acentos só acontece em uma etapa de build
específica (`scripts/build.py`), porque os arquivos do DOS original são
Latin-1/CP437 de 1 byte por caractere e o motor do jogo pode não
renderizar corretamente certos acentos — ver
[pipeline-textos.md](pipeline-textos.md) para os detalhes de quais
arquivos passam por essa etapa e quais são copiados sem alteração (as
imagens, cujo "texto" já é pixel art e não caracteres).

## Consistência entre telas irmãs

BUYSPELL.IMG (Grimório) e SPELLMKR.IMG (Cria-Feitiços) compartilham
exatamente o mesmo layout de campos (Nome/Nível/Feitiço/Alvo/Efeitos à
esquerda, Saldo/Custo/Resist./Conjuração à direita) — os mesmos rótulos
em português devem ser usados nas duas telas, só os botões de ação e o
título mudam. Ver [pipeline-imagens.md](pipeline-imagens.md#telas-de-ui-buyspellimg-spellmkrimg-logbookimg)
para os detalhes de layout compartilhado.
