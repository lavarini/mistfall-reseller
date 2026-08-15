# Design: preço exato, sorteio e paralelismo

> **Nota de 2026-08-14.** A seção de paralelismo desta spec descreve a varredura dos 12 slots
> rodando OCR em paralelo. Isso mudou: a varredura passou a ler os doze preços numa chamada só
> — ver `2026-08-14-leitura-de-precos-em-folha-unica-design.md`.
>
> Os números medidos aqui continuam válidos como medição, mas **não descrevem mais nenhum
> caminho vivo**. `trabalhadores` ficou sem consumidor: a varredura deixou de usá-lo, e as três
> leituras da Janela de Confirmação saíram com o
> [ADR-0003](../../adr/0003-nao-conferir-a-janela-de-confirmacao.md). A
> [#20](https://github.com/lavarini/mistfall-reseller/issues/20) decide se o helper fica ou sai.

Data: 2026-08-13
Épico: [#1](https://github.com/lavarini/mistfall-reseller/issues/1)

## O que provocou isto

Duas observações do dono do projeto, ambas verificadas antes de virarem desenho.

**A Janela de Confirmação não faz request.** Ela reexibe dados que o cliente já tinha. A
evidência: deixando uma Listagem na tela por alguns segundos — tempo de outra pessoa
comprá-la —, clicando e apertando Comprar muito rápido, o jogo responde *"item já foi
vendido"*. A recusa vem do **servidor**, no momento da Compra. O modal em si não sabia de nada.

E a lista do Leilão **fica congelada até uma ação**. Não recarrega sozinha.

Junte as duas e a conclusão é firme: **o modal mostra exatamente a mesma Listagem que o bot
varreu**. A conferência do modal, portanto, **nunca poderá detectar "o preço mudou" ou "alguém
comprou"** — isso é papel do servidor, e ele o cumpre. O que ela detecta é **erro de OCR
nosso**, e só.

**Os Itens-alvo nunca ficam abaixo do corte.** Os valores em `config.toml` são chão de
mercado, não teto. Conferido contra o corpus rotulado: em **49 observações de Item-alvo, zero
abaixo do corte** — 16 exatamente nele, 33 acima.

## O que foi medido

Tudo num Mac de 12 núcleos ocioso. Os números do Windows serão outros; ver "O que fica para a
execução da #9".

| Etapa | Custo |
|-------|-------|
| `identificar_estado` | 7 ms |
| 12 casamentos de ícone | 49 ms |
| **12 OCRs de preço** | **1725 ms** |
| `ler_ouro` | 126 ms |
| Conferência do modal (4 leituras) | 397 ms |
| — só o ícone | 38 ms |
| — só os 3 números | 341 ms |

**96% da varredura é OCR de preço.** A conferência do modal, que era a suspeita inicial, custa
menos de um quarto disso.

## As três mudanças

### 1. Preço exato substitui "menor ou igual"

`Preço-unitário == Preço-alvo`. Preço **abaixo** do corte é leitura suspeita: vai para o
`relatorio.json` da execução, não gera Compra, e a varredura segue. (Log estruturado de
Compras é a #8; aqui é o relatório que já existe.)

Isso é **mais seguro** que a regra anterior, não menos. Antes, um OCR que lesse qualquer valor
abaixo do alvo disparava Compra; agora ele precisa acertar **exatamente** o número do corte. A
janela de erro perigoso encolheu de "todo o intervalo abaixo" para "um único valor".

**Remove `fracao_sanidade`.** Ela existia para rejeitar preço absurdamente baixo. Com a regra
nova, qualquer valor abaixo do corte já é rejeitado, e a fração vira config inalcançável.
Config que parece proteção e não protege é pior que config nenhuma — alguém no futuro ajusta
aquele `0.25` achando que está mudando comportamento.

### 2. Sorteio uniforme entre os candidatos

Com igualdade exata **toda margem é zero**: todos os candidatos empatam. O critério de
desempate atual é ordem de leitura, e a lista é ordenada por preço crescente — o que premia
sistematicamente os cortes mais baratos.

Medido no corpus, com a regra de desempate atual:

| Item | Corte | Vezes no corte | Vezes escolhido |
|------|-------|----------------|-----------------|
| Broche | 188 | 1 | 1 |
| Adaga | 199 | 1 | 1 |
| Lanterna | 234 | 3 | 2 |
| Dragão | 246 | 4 | 2 |
| Orbe | 253 | 2 | **0** |
| Rede | 260 | 4 | **1** |
| Códice | 281 | 1 | **0** |

Orbe e Códice nunca seriam comprados; a Rede, uma vez em quatro oportunidades.

**O sorteador é injetado, não global.** `escolher` passa a receber um `random.Random`. Mesmo
padrão do `Ritmo`: sem injeção os testes viram loteria, e teste que às vezes passa é pior que
teste nenhum. Com semente fixa a escolha é determinística e afirmável; o piloto passa um
sorteador sem semente.

**O que o sorteio não resolve, e está aceito.** Ele elimina o viés de posição na tela, não o de
oferta: se o Broche estiver no corte com muito mais frequência que o Códice, mais Broches serão
comprados. **Isso é decisão explícita** — comprar na proporção do que o mercado oferece está
correto. Escolha ciente do estoque, se um dia fizer falta, depende do log de Compras da
[#8](https://github.com/lavarini/mistfall-reseller/issues/8) e se decide com dado real.

### 3. OCR em paralelo

`pytesseract` não faz OCR em Python: grava a imagem em arquivo temporário e roda o **binário do
tesseract como subprocesso**. O GIL não é o gargalo, e por isso `ThreadPoolExecutor` escala.

| Threads | 12 OCRs |
|---------|---------|
| 1 (hoje) | 1725 ms |
| 2 | 1080 ms |
| **4 (padrão)** | **578 ms** |
| 8 | 461 ms |
| 12 | 413 ms |

Resultado **idêntico ao sequencial** em 2, 4, 6, 8 e 12 threads.

**Padrão 4, configurável.** Com 4 o ganho já é 3× e sobra CPU para o jogo — que roda na mesma
máquina e precisa desenhar a tela que o bot vai capturar. Ir a 12 rende mais 165 ms e disputa
tudo.

Dois pontos de aplicação: os 12 OCRs de preço da varredura (1725 → 578 ms) e os 3 números do
modal (341 → 160 ms). O casamento de ícone fica sequencial — 49 ms para os doze, não há o que
ganhar.

**Um helper compartilhado**, não `ThreadPoolExecutor` solto nos dois lugares. A
[#13](https://github.com/lavarini/mistfall-reseller/issues/13) já registra pipeline de OCR
duplicado em três arquivos; não faz sentido criar a quarta duplicação no mesmo movimento.

Três garantias do desenho:

- **Ordem preservada.** `map` devolve na ordem da entrada; o slot 3 continua sendo o slot 3.
- **`trabalhadores=1` roda sequencial de verdade** — saída para depurar e para isolar a
  paralelização de qualquer suspeita futura.
- **O relatório passa a registrar o tempo de cada etapa**, para a execução no Windows dizer
  qual número usar em vez de a gente chutar duas vezes.

### Ciclo resultante

Com o padrão de **4 trabalhadores**, que é o que vai rodar:

| Etapa | Hoje | Depois |
|-------|------|--------|
| `identificar_estado` | 7 ms | 7 ms |
| 12 casamentos de ícone | 49 ms | 49 ms |
| 12 OCRs de preço | 1725 ms | 578 ms |
| `ler_ouro` | 126 ms | 126 ms |
| Conferência do modal | 397 ms | 198 ms |
| **Total** | **2304 ms** | **958 ms** |

Com 12 trabalhadores o total cairia para ~793 ms, mas disputando a CPU com o jogo. A diferença
entre 958 e 793 não paga esse risco — e é justamente o tipo de número que a execução no
Windows vai corrigir.

## O que foi considerado e recusado

**Cortar a conferência do modal.** Era a pergunta original. Economiza 400 ms e é a única guarda
específica sobre o número que decide o gasto. Com o paralelismo, os 400 ms deixam de ser
relevantes — e a conferência sai barateada junto (198 ms).

> **Revisto durante a execução.** A decisão acima segurava as quatro leituras porque o tempo
> deixou de importar — mas tempo não era a única variável, e essa parte ficou de fora. A
> [#18](https://github.com/lavarini/mistfall-reseller/issues/18) mostrou que a conferência do
> ícone dá **100% de falso negativo** na máquina real: `_esperar_janela` devolve o primeiro
> frame em que o *estado* já é detectável, e a detecção de estado precisa de menos pixels
> estáveis que o casamento de ícone, então o modal ainda está desenhando quando o ícone é
> lido. E, olhando os seis erros de OCR conhecidos do corpus, nenhum teria sido pego só pela
> conferência do ícone — os nulos já são ignorados por `decisao` e os absurdos são pegos pela
> ordenação. Uma guarda que erra 100% das vezes que dispara e não pega nenhum dos casos reais
> não estava protegendo nada, só abortando à toa. O ícone **saiu do portão**: continua sendo
> lido e vai para o `relatorio.json` com os sete scores — é o que permitiu diagnosticar a #18
> a distância —, mas deixou de abortar a Compra. Preço Unitário, Quantidade e Preço Total
> continuam conferindo, porque são baratos, estáveis, e cobrem o caminho que a regra de preço
> exato deixa aberto (um 250 lido como 246 compraria por 250).

**Enxugar a conferência, mantendo só ícone e Preço Unitário.** Economizaria 260 ms. A
Quantidade cobre um cenário real que aparece na
[#6](https://github.com/lavarini/mistfall-reseller/issues/6): se o modal lembrar a quantidade
de uma Compra anterior, o loop compraria N unidades. Hoje o risco é nulo — com uma Compra e
para — mas o loop chega logo, e a proteção estaria faltando exatamente quando passar a
importar.

**Ler OCR só dos slots que são Item-alvo.** Economizaria 538 ms, ao custo de rodar a
conferência de ordenação sobre ~7 pontos em vez de 12. Com o paralelismo, ler os 12 custa
578 ms — a economia deixa de compensar a perda.

**Saída antecipada: comprar no primeiro candidato encontrado.** Pararia no 3º de 7 alvos em
média (~43% dos OCRs), o que sequencialmente custaria ~430 ms. Com o paralelismo, ler os **doze**
custa 578 ms — praticamente o mesmo. A saída antecipada perde a razão de existir — e com ela some o viés de
posição que ela introduziria.

**Inverter a autoridade do preço**, decidindo pelo valor lido no modal em vez do da lista. O
modal renderiza o número maior e em fundo limpo, então *pode* ser a leitura mais confiável.
**Fica pendente de medição:** existe uma única amostra real de modal, e ela é negativa. A
execução da #9 traz o primeiro print de modal com Item-alvo dentro; com ele e mais alguns, dá
para comparar as duas leituras do mesmo preço em dezenas de casos e decidir com dado.

## Testes

**Preço exato** reaproveita o corpus rotulado: os 7 prints já têm os preços verdadeiros, então
dá para afirmar quantas Listagens qualificam em cada um — 2, 4, 3, 1, 1, 4 e 1.

**Sorteio**, dois testes que provam coisas diferentes: um com semente fixa afirmando **qual**
Listagem sai, e outro rodando muitos sorteios e exigindo que **todos** os candidatos apareçam.
O segundo pega a implementação que "sorteia" e devolve sempre o mesmo.

**Paralelismo**: comparar paralelo contra sequencial sobre os prints reais, exigindo resultado
idêntico; e um teste com `trabalhadores=1` provando que o caminho sequencial continua vivo.

**Prova por mutação**, como o resto do projeto exige:

- trocar `==` por `<=` na regra de preço → suíte vermelha
- devolver sempre o primeiro candidato em vez de sortear → suíte vermelha
- fazer o paralelo devolver fora de ordem → suíte vermelha

## Documentação a atualizar junto

Sem isso, os documentos que definem o projeto passam a mentir.

- **`CONTEXT.md`** — Preço-alvo deixa de ser "o preço unitário máximo que aceitamos pagar" e
  vira o preço **exato**. É o glossário; é o que mais importa acertar.
- **`README.md`** — o passo 5 de "Como funciona" descreve "maior margem entre as que estão
  abaixo do Preço-alvo", e a seção de configuração documenta a `fracao_sanidade`.
- **`config.toml`** — sai a `fracao_sanidade`.
- **`docs/superpowers/specs/2026-08-11-mvp-bot-leilao-design.md`** — registra a regra `≤`;
  ganha nota de que foi superada.

## O que fica para a execução da #9

Os 785 ms foram medidos num Mac de 12 núcleos ocioso. Na máquina Windows o jogo disputa CPU, e
ninguém sabe o efeito disso. Como o relatório passa a registrar o tempo de cada etapa, a
execução volta dizendo qual valor de `trabalhadores` usar.

Junto com o que a #9 já devia trazer: o tempo real da Janela de Confirmação, o comportamento
sem administrador, e o primeiro print de modal com Item-alvo dentro — que também destrava a
decisão sobre inverter a autoridade do preço.
