# Tradução PT-BR de The Elder Scrolls: Arena

Tradução, feita por fãs, do primeiro jogo da série The Elder Scrolls
("Arena", 1994) para português do Brasil — telas, menus, itens,
diálogos, feitiços e a maior parte do texto do jogo.

Compatível com as duas formas de jogar o Arena hoje em dia:

- **A versão clássica**, rodando em DOSBox (é o que a Steam entrega
  quando você instala "The Elder Scrolls: Arena").
- **[OpenTESArena](https://github.com/afritz1/OpenTESArena)**, um motor
  moderno e gratuito, feito por fãs, que recria o Arena original pra
  rodar direto no Windows/Linux/Mac sem emulação de DOS — com tela
  maior, mouse livre, e outras conveniências modernas.

---

## Quanto do jogo está traduzido?

| | Versão OpenTESArena | Versão DOSBox (Steam clássica) |
|---|---|---|
| **Estimativa** | ~98-99% do texto do jogo | ~55% do texto do jogo |

A base do jogo é **idêntica** nas duas versões — menus, itens, diário
de masmorra, criação de personagem, telas de interface, feitiços,
praticamente todo o executável do jogo, e todo o texto dos encontros
em masmorra/templo/taverna (arquivos `.INF`). A diferença entre as
duas vem de **um único arquivo**, o `TEMPLATE.DAT` (banco de falas dos
cidadãos nas cidades — conversa de rua, rumores, "onde fica tal
lugar?") — mas esse arquivo sozinho é **quase metade de todo o texto
do jogo** (cerca de 396 KB dos ~877 KB de texto no total, medindo pelo
tamanho real dos arquivos de texto do jogo), então deixá-lo em inglês
pesa proporcionalmente muito mais do que o nome "um arquivo" sugere.
Esse arquivo específico não tolera nenhuma alteração quando roda no
DOSBox de verdade — qualquer edição, por menor que seja, embaralha os
diálogos do jogo. Por segurança, mantivemos esse arquivo em inglês só
na versão DOSBox; na versão OpenTESArena ele está traduzido
normalmente, já que o motor moderno não tem essa limitação.

O que fica de propósito em inglês nas duas versões: nomes próprios
(dias da semana, nomes de província, nome do imperador) e dois campos
bem específicos do executável que travam o jogo se forem editados.

---

## Como instalar

⚠️ **Antes de começar**, faça uma cópia de segurança da pasta do jogo
inteira, pra poder voltar atrás se quiser. É só copiar a pasta pra
outro lugar antes de mexer em qualquer coisa.

### Versão DOSBox (Steam)

1. Instale **The Elder Scrolls: Arena** na Steam, se ainda não
   tiver.
2. Ache a pasta de instalação do jogo:
   - Na Steam, clique com o botão direito no jogo → **Gerenciar** →
     **Procurar arquivos locais**.
   - Dentro da pasta que abrir, entre na subpasta chamada **`ARENA`**
     — é aqui que os arquivos do jogo de verdade ficam.
3. Copie **todos os arquivos da pasta `build/`** deste pacote de
   tradução pra dentro dessa pasta `ARENA`, substituindo os arquivos
   existentes quando o sistema perguntar.
4. Além disso, copie os dois arquivos de dentro de **`build/dosbox/`**
   (`ACD.EXE` e `TEMPLATE.DAT`) pra essa mesma pasta `ARENA`,
   substituindo também.
5. Pronto — inicie o jogo pela Steam normalmente.

### Versão OpenTESArena

1. Baixe e instale o [OpenTESArena](https://github.com/afritz1/OpenTESArena)
   (ele é gratuito, mas **precisa dos arquivos originais do jogo** —
   ou seja, você ainda precisa ter o Arena original, da Steam ou do
   GOG, instalado em algum lugar).
2. Configure o OpenTESArena pra apontar pra pasta `ARENA` do jogo
   original (normalmente isso é pedido na primeira vez que você abre
   o programa, ou fica num arquivo de opções — consulte as instruções
   do próprio OpenTESArena se tiver dúvida).
3. Copie **todos os arquivos da pasta `build/`** deste pacote de
   tradução pra dentro dessa mesma pasta `ARENA` que o OpenTESArena
   está usando, substituindo os arquivos existentes.
4. Além disso, copie os dois arquivos de dentro de **`build/opentes/`**
   (`ACD.EXE` e `TEMPLATE.DAT`) pra essa mesma pasta, substituindo
   também.
5. Pronto — abra o OpenTESArena e jogue.

> **Importante**: os arquivos `ACD.EXE`/`TEMPLATE.DAT` são diferentes
> entre as duas versões (um pra DOSBox, outro pro OpenTESArena) — não
> troque um pelo outro, ou o jogo pode não abrir / os diálogos podem
> ficar bagunçados.

---

## Problemas conhecidos

- Diálogo de cidadão (conversa de rua nas cidades, arquivo
  `TEMPLATE.DAT`) continua em inglês **só na versão DOSBox**, pelo
  motivo explicado acima — é a maior lacuna da tradução nessa versão.
- Alguns nomes próprios (dias da semana, províncias, nome do
  imperador) continuam em inglês de propósito, seguindo a mesma
  convenção usada nos outros jogos traduzidos da série.

---

## Créditos

Tradução: **Ghost Tocaia**

Repositório: [github.com/Ghost-Tocaia/arena-traducao-ptbr](https://github.com/Ghost-Tocaia/arena-traducao-ptbr)
