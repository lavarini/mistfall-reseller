# Design: leitura de preços em folha única

Data: 2026-08-14
Épico: [#1](https://github.com/lavarini/mistfall-reseller/issues/1)
Resolve: [#17](https://github.com/lavarini/mistfall-reseller/issues/17)

## O que provocou isto

A execução na máquina do jogo trouxe o tempo real de cada etapa, e a varredura dos 12 slots
custou **5729 ms** — contra 477 ms medidos no Mac com o mesmo paralelismo ativo. Doze vezes
mais lento.

A execução é posterior a todas as correções de paralelismo (o commit que faz `trabalhadores`
chegar na varredura é das 15:22; a execução, das 15:52), então o paralelismo estava ligado e
funcionando. A lentidão é da máquina, não de configuração perdida.

**A hipótese que os números sustentam é custo de criar processo.** O `pytesseract` não faz OCR
em Python: grava a imagem num arquivo temporário e executa o **binário do tesseract**. Cada
slot é uma execução. Criar processo no Windows é substancialmente mais caro que no Unix, e doze
execuções por varredura pagam esse custo doze vezes.

## A mudança

**Empilhar os doze recortes de preço numa imagem só, separados por faixas pretas, e fazer uma
única chamada ao tesseract**, com `--psm 6` — bloco de texto — em vez de doze chamadas com
`--psm 7` — linha isolada.

Medido no Mac, sobre `images/broche-dragao-orbe-codice-padrao.png`:

| Abordagem | Tempo | Acerto no corpus |
|-----------|-------|------------------|
| 12 chamadas, sequencial | 1512 ms | 79/84 |
| 12 chamadas, 4 trabalhadores (hoje) | 503 ms | 79/84 |
| **1 chamada, folha única** | **221 ms** | **84/84** |

**2,3× mais rápido que o paralelismo atual, e sem nenhum erro.** No Windows o ganho tende a ser
maior, porque lá o custo evitado — onze execuções de processo a menos — é justamente o que pesa.

### O separador é obrigatório, e o tamanho dele foi medido

Empilhar os recortes colados **não funciona**: dá 80/84, e o `227` continua saindo `297`. Os
recortes precisam de uma faixa preta entre eles para o `--psm 6` enxergar doze linhas em vez de
tentar costurar dígitos de slots vizinhos.

Varrendo o tamanho da faixa contra o corpus inteiro:

| separador | acerto no corpus |
|-----------|------------------|
| sem separador | 80/84 |
| 5 px | 82/84 |
| 10–20 px | 83/84 |
| **30–60 px** | **84/84** |
| 80 px | 83/84 |
| 120 px | 69/84 |
| 180 px | 65/84 |

**`SEPARADOR = 40`**, centro do platô 30–60. Não é número escolhido a olho, e não está na beira
de um precipício: erra por 10 px para qualquer lado sem mudar de resultado.

O degrau em 120 px tem explicação: faixa preta grande demais faz o `--psm 6` parar de ver um
bloco único e passar a tratar os pedaços como regiões separadas — que é exatamente o contexto
entre linhas que faz a folha única ler melhor. Separador de menos cola dígito; separador de
mais destrói o bloco.

### E ela corrige o OCR, não só o tempo

Os cinco erros que o corpus documenta em `ocr_lido_atual` **desaparecem**:

| print | slot | verdade | individual | folha única |
|-------|------|---------|-----------|-------------|
| `broche-dragao-orbe-codice-padrao` | (1,1) | 237 | `None` | **237** |
| `broche-dragao-orbe-codice-padrao` | (2,0) | 241 | 24 | **241** |
| `broche-tres-dragao-padrao` | (4,0) | 282 | 2892 | **282** |
| `lanterna-dragao-orbe-rede` | (0,1) | 223 | 293 | **223** |
| `rede-dois-dragao-padrao` | (3,0) | 249 | `None` | **249** |

E no print vindo da máquina do jogo, `images/sete-itens-ocr-227-como-297.png`, o slot (0,1) —
que a leitura individual erra como **297** e que fez a `conferir_ordenacao` derrubar a tela
inteira — passa a ler **227**. Isso **resolve a #17**.

**Por que lê melhor.** `--psm 7` trata cada recorte como uma linha solta, sem contexto. Com os
doze empilhados, `--psm 6` vê um bloco e usa a consistência entre linhas — altura de dígito,
alinhamento, espessura do traço — para decidir. É a mesma informação que faz um humano ler
`241` onde um dígito isolado pareceria `24`.

Vale notar que a #17 pedia investigar **por que aparece um `9`** antes de mexer em parâmetro. A
resposta é essa: o `9` aparece quando um dígito é julgado sem contexto. A correção não é ajustar
binarização — é dar contexto.

## Correspondência por posição, não por contagem

O jeito ingênuo de ler a folha é pegar os números na ordem em que saem. **Isso quebra em
silêncio:** um preço ilegível produz onze números em vez de doze, e a correspondência
slot↔preço se desloca inteira — o slot 6 passa a receber o preço do 7, e assim por diante. Um
erro num slot vira erro em todos.

Medido: apagando o recorte do slot 5, a leitura por ordem devolve onze valores e desalinha tudo.

**A solução é pedir ao tesseract onde cada número está.** `image_to_data` devolve a caixa de
cada palavra; como sabemos em que faixa vertical cada slot foi empilhado, cada número volta ao
seu slot pela posição. Slot sem número vira `None`, **no lugar certo**, e os outros onze não se
mexem.

Medido no mesmo teste: slot 5 vira `None`, os outros onze mantêm os valores corretos.

Isso elimina a necessidade de guarda de contagem e de queda para o caminho antigo.

## O que acontece com o paralelismo

O helper `src/mistfall/paralelo.py` **fica no código**. Com a folha única, a varredura passa a
fazer uma chamada só, e não há o que paralelizar ali — o helper deixa de estar no caminho da
varredura, mas continua servindo as três leituras do modal.

Isso é decisão explícita: ainda estamos experimentando, e manter o helper permite voltar atrás
sem reconstruir nada. A análise e a eventual remoção viram issue.

**A documentação precisa dizer isso.** `trabalhadores` continua no `config.toml` e continua
tendo efeito — no modal, não na varredura. Config que parece fazer uma coisa e faz outra é
exatamente o problema que esta base já cometeu uma vez, quando `trabalhadores` não chegava à
varredura e o README dizia que chegava.

## Arquitetura

Uma função nova em `src/mistfall/precos.py`:

```python
def ler_precos(recortes: list[np.ndarray]) -> list[int | None]
```

Recebe os recortes na ordem dos slots, devolve os valores na mesma ordem. `ler_preco`, que lê um
recorte só, **permanece** — é usada pelas leituras do modal, que não são doze e não formam
bloco. As duas compartilham o mesmo preparo de imagem — cinza, ampliação 4×, Otsu por recorte —
que hoje já vive dentro de `ler_preco` e passa a ser função própria.

`leilao.varrer_bruto` passa a chamar `ler_precos` uma vez em vez de `mapear(ler_preco, ...)`.

### O parâmetro `trabalhadores` sai da varredura

Com uma chamada só não há o que paralelizar, então `varrer` e `varrer_bruto` **perdem o
parâmetro `trabalhadores`**, e `piloto` para de repassá-lo à varredura. Manter um parâmetro que
não faz nada seria a mesma falha que esta base já cometeu — config que promete uma coisa e faz
outra.

Isso tem custo, e é melhor dizê-lo agora do que descobrir no review: **seis testes deixam de
fazer sentido** e saem junto — cinco em `tests/test_leilao.py` (equivalência paralelo/sequencial,
preservação de posição, o padrão do helper, o espião de repasse) e um em `tests/test_piloto.py`
(`test_a_varredura_repassa_os_trabalhadores_configurados_ao_helper`).

Esse último é o que merece atenção: ele nasceu de um achado de review real — `config.trabalhadores`
não chegava à varredura. Ele sai porque **o caminho que ele guardava deixa de existir**, não
porque incomoda. O que ele protegia continua protegido do outro lado: `config.trabalhadores`
agora alimenta só o modal, e `test_as_leituras_do_modal_passam_pelo_helper_de_paralelismo` já
guarda esse caminho.

A separação entre `varrer_bruto` e `conferir_ordenacao` não muda. A conferência de ordenação
**continua**: ela é a rede que pegou o `227→297`, e o fato de a folha única corrigir esse caso
não significa que não haverá outros.

## Testes

**Contra o corpus inteiro**, com a verdade humana: 84 slots, 7 prints, e a exigência é
**84/84**. Hoje a leitura individual acerta 79.

**O print da máquina do jogo** vira caso próprio: o slot (0,1) de
`sete-itens-ocr-227-como-297.png` tem de ler **227**.

**Slot ilegível**: apagar um recorte tem de produzir `None` **naquele índice**, com os outros
onze intactos. É o teste que guarda a correspondência por posição — sem ele, alguém troca por
leitura em ordem e a suíte não percebe.

**Uma chamada, não doze**: espiar `pytesseract` e afirmar que a varredura o invoca **uma vez**.
Comparar só resultado não distingue as duas implementações, e este projeto já teve **doze**
defeitos dessa família — cinco na branch anterior.

**Os cinco gaps do corpus mudam de estado.** `fixtures/esperado/*.json` marca cinco slots com
`ocr_lido_atual`, e `tests/test_regressao.py` tem um guarda afirmando que são exatamente cinco.
Com a folha única esses slots passam a ler certo: os campos `ocr_lido_atual` saem, e o guarda
passa a afirmar **zero**. Isso é resultado, não efeito colateral — mas precisa ser feito
explicitamente, senão a suíte fica vermelha sem que ninguém entenda por quê.

**A conferência de ordenação para de derrubar slots no corpus.** `DERRUBADOS_PELA_ORDENACAO`
lista hoje os slots que a ordenação invalida em três prints; com a leitura correta, ela não
derruba nada em nenhum dos sete, e o dicionário fica vazio.

Isso **não** é a regra virando letra morta, e o dicionário vazio não pode ser lido como teste
sem dentes: `tests/test_ordenacao.py` exercita `conferir_ordenacao` com listagens montadas à
mão, e é lá que o comportamento dela é provado. O que o corpus passa a dizer é outra coisa, e é
uma boa notícia: **nenhuma leitura do corpus viola mais a ordenação**. Se o OCR regredir, o
dicionário vazio quebra na hora.

**O tamanho do separador é medido, não escolhido.** Um teste percorre o corpus com separador de
30, 40 e 60 e exige 84/84 nos três — é o que prova que o 40 está num platô. Sem ele, alguém
"limpa" o número para 8 ou 100 e a suíte não reclama até a próxima execução no Windows.

## Documentação a atualizar

- **`README.md`** — descrever que os doze preços são lidos numa chamada só, e que
  `trabalhadores` afeta o modal, não a varredura.
- **`docs/superpowers/specs/2026-08-13-preco-exato-e-paralelismo-design.md`** — a seção de
  paralelismo descreve a varredura paralelizada. Ganha nota de que a varredura passou a folha
  única e que os números de lá valem para o modal.
- **A issue de remoção futura do helper** precisa existir antes do merge, para o "fica no
  código" ser decisão registrada e não esquecimento.

## O que fica de fora

- **Aplicar folha única ao modal.** São três leituras, não doze, e elas não formam bloco
  contíguo na tela. O ganho seria pequeno e o risco de desalinhamento, não.
- **Trocar o `pytesseract` por `tesserocr`**, que usa a API C++ e elimina a criação de processo
  de vez. Resolveria a causa raiz de forma mais completa, mas é dependência nova e mais difícil
  de instalar no Windows — exatamente a máquina onde a montagem já é o passo mais frágil. Se a
  folha única não bastar, é o próximo degrau.
- **Remover o helper de paralelismo.** Decisão do dono do projeto: fica, com issue.
