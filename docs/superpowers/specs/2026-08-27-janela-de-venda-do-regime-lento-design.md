# Janela de Venda do regime lento

Data: 2026-08-27
Estado: aprovado, aguardando plano de implementação

## Problema

Numa sessão longa o Fluxo Completo gastou 100k, encheu o Armazém e ficou
resetando indefinidamente sem nunca ir vender. A investigação encontrou três
defeitos independentes, todos confirmados executando o código.

### Defeito 1 — no regime lento, um Reset nunca reavalia o Estoque

`_acao_por_saldo` (`fluxo.py`) só é consultado nos ramos de Compra. O ramo
`RESET_EXECUTADO` só devolve Venda na *aresta* da transição para lento; já
estando lento, devolve `CONTINUAR_COMPRA` incondicionalmente.

Com Estoque estimado 60 e limiar 45, sete Resets seguidos devolvem
`continuar_compra` nos sete. O gatilho por saldo é disparado por Compra, não
por nível: com o Armazém cheio e o Leilão seco, nada reavalia.

### Defeito 2 — a supressão do livelock engole a Venda da transição

`gatilho_por_saldo_suspenso` existe para impedir um ida-e-volta de aba a cada
Compra quando a Capacidade do NPC está cheia. Mas ela casa com a **ação**
`VENDER_POR_FLUXO_LENTO`, que é também a ação da transição para o regime lento.

Uma vez armada, ela só destrava com uma Venda que liste unidades — e nenhuma
Venda acontece para destravá-la. É um trinco, não um prazo.

### Defeito 3 — o Estoque estimado subconta e não é reconciliado

Compra real cujo Ouro está legível e não caiu soma **zero**. Sessenta Compras
reais podem virar Estoque estimado 30, que nunca cruza 45. `ESTOQUE_RECONCILIADO`
existe em `fluxo.py`, é testado, e não tem nenhum chamador.

### Causa provável a montante

O commit `305768f` (Detecta capacidade de Venda estagnada) descreve um bug do
jogo em que a leitura `X/Y` estagna. Com ela estagnada, `_esperar_vaga_parcial`
lê `ocupadas >= limite` indefinidamente, devolve `CAPACIDADE_CHEIA`, e o trinco
do defeito 2 arma. Esse commit ataca a causa; esta spec ataca as consequências.
Os dois são necessários: sem o trinco virar prazo, qualquer outra origem de
`CAPACIDADE_CHEIA` reproduz a falha.

## Desenho

### A Janela é um portão, não um gatilho

Depois de **qualquer** Venda, o regime lento não volta a vender por N segundos
(`config.intervalo_da_janela_s`, padrão 180). Enquanto a Janela está fechada,
nenhuma Venda do regime lento passa.

A Janela é nível e aresta ao mesmo tempo, e a distinção importa:

- **Nível** — `agora >= proxima_janela` é conferido a cada Volta e é o que
  autoriza a Venda vinda do gatilho de pressa, que nasce de um evento de
  Compra. `proxima_janela` só é reagendada quando uma Venda acontece; uma
  Janela que abre e não vende **continua aberta**.
- **Aresta** — na Volta em que a Janela passa de fechada a aberta, o
  coordenador emite `janela_de_venda_aberta` uma vez. É essa emissão que dá ao
  regime lento uma reavaliação que não depende de Compra nenhuma, e é ela que
  mata o defeito 1.

Reagendar a Janela na emissão em vez de na Venda seria erro: uma Compra que
cruzasse o limiar logo depois ficaria barrada por mais um intervalo inteiro,
sem nada ter sido vendido.

O relógio vive no coordenador, nunca em `fluxo.py`. É a porta que
`OURO_ABAIXO_DO_PISO` já usa: o número mora na configuração, a comparação é de
quem tem acesso ao mundo, e a política continua pura.

### As duas regras do regime lento, com a Janela aberta

| Condição | Ação | Papel |
|---|---|---|
| `estoque_estimado >= LOTE_DE_VENDA` | vende | a pressa: entrar em lento já sentado numa pilha |
| última Venda saiu por `CAPACIDADE_CHEIA` com lote cheio restante | vende | a retomada: drenagem cortada pela Capacidade |
| `ARMAZEM_ESGOTADO`, ou Capacidade cheia sem lote cheio | não vende | fim de lote: volta a acumular |

O portão vale para **as duas**. Sem isso o livelock volta pela porta dos fundos:
a Venda lista zero, uma Compra confirma, o saldo segue acima do limiar, e a
viagem se repete. Juntar um lote inteiro de Compras no regime lento leva bem
mais que a Janela, então o portão quase nunca segura a pressa.

### Um só número

O limiar de 45 unidades de `_acao_por_saldo` e os 15 stacks da varredura são a
mesma coisa em unidades diferentes. Viram uma constante só:

```
LOTE_DE_VENDA_EM_STACKS = 15          # 15 stacks de 3 = 45 unidades
```

Duas constantes divergem com o tempo; uma, não.

### A varredura de retomada

Ao sair por `CAPACIDADE_CHEIA`, a Venda precisa responder uma pergunta binária:
**resta um lote cheio no Armazém?** Ela varre os Baús contando slots com
`quantidade == 3` e **para assim que atingir 15**. No caso comum — Armazém
cheio — ela para quase de imediato; só fica cara quando resta pouco, que é
justamente quando a resposta importa.

`SessaoVenda` ganha `resta_lote_cheio: bool`. Um booleano, não uma contagem: é
o que a decisão precisa, e uma contagem que para nos 15 seria um número que
mente sobre si mesmo.

Valor por desfecho, sem caso indefinido:

| Desfecho da Venda | `resta_lote_cheio` |
|---|---|
| `CAPACIDADE_CHEIA` | resultado da varredura |
| `ARMAZEM_ESGOTADO` | `False` — não há stack nenhum |
| `ABORTOU` / `PAROU` | `False` |

`ABORTOU` é falha de visão, e religar a retomada a cada N segundos em cima de
uma falha de visão transformaria o defeito num laço silencioso. O Armazém cheio
continua coberto pelo gatilho de pressa, que não depende deste booleano.

Duas restrições vindas dos commits recentes:

- **Começa do `BAU_INICIAL`, não do Baú atual.** `305768f` introduziu
  `reiniciar_baus`, que volta ao primeiro Baú depois de detectar capacidade
  estagnada; e o motivo da estagnação é não saber se as Listagens registraram.
  Se não registraram, o stack continua num Baú anterior. A invariante "os Baús
  anteriores estão esgotados" não vale mais.
- **Leitura vazia não é prova de Baú vazio.** `7bca077` estabeleceu a releitura
  antes de acreditar num Baú vazio. A varredura precisa da mesma disciplina:
  contar um Baú transitoriamente vazio como zero subconta, desliga a Janela e
  faz o bot sentar em cima do estoque — exatamente a direção de erro do bug
  original. A varredura erra para cima ou não erra.

A varredura vive só no caminho parcial. O `mistfall-venda` usa `_esperar_vaga`,
que espera vaga indefinidamente e nunca sai por Capacidade cheia; ele fica
intacto.

### O que muda em `fluxo.py`

Um evento (`janela_de_venda_aberta`) e uma ação (`VENDER_POR_RETOMADA`). O
módulo continua puro: sem relógio, sem tela, sem clique.

`gatilho_por_saldo_suspenso` deixa de existir. O prazo substitui o trinco.

### O que não muda

**O regime rápido, em nada.** Continua vendendo só pelo toast de Inventário
cheio e pelo Ouro abaixo do piso. Nenhum gatilho por saldo, nenhuma Janela.

`mistfall-bot` e `mistfall-venda` não consomem `fluxo.py` nem o caminho parcial
da Venda. A suíte cobre o acoplamento; o comportamento e os defaults dos dois
ficam idênticos.

## Como cada defeito morre

| Defeito | Como morre |
|---|---|
| 1 — Reset não reavalia | A reavaliação deixa de estar amarrada a evento de Compra. O portão abre sozinho e pergunta de novo, com ou sem Compra. |
| 2 — trinco engole a transição | Prazo em vez de trinco. Nada fica suprimido para sempre. |
| 3 — Estoque estimado subconta | **Não morre.** Ver limitações. |

## Limitações aceitas

**O defeito 3 fica sem conserto de raiz.** A varredura dá verdade observada
onde importa — a decisão de retomada é independente da contagem feita na
Compra —, mas o `estoque_estimado` continua subcontando para o gatilho de
pressa. Reconciliação de verdade exige trabalho de visão que não está feito.
Registrado como limitação conhecida, não como esquecimento.

**`ARMAZEM_ESGOTADO` não significa Armazém vazio.** `_candidatos` só considera
slots com `quantidade == 3`, então podem restar até 2 unidades por slot. São
unidades não listáveis; para o fluxo de Itens é irrelevante.

**O toast de Inventário cheio continua sem Janela.** Ele tem o mesmo livelock
em potencial: Inventário cheio mais Capacidade cheia produz toast a cada Volta
e viagem a cada Volta. Existe hoje e não é regressão desta mudança. Fica fora
do escopo porque pôr Janela nele mudaria o regime rápido, que esta spec não
toca.

## Telemetria

`eventos-do-fluxo.jsonl` grava `modo`, `intencoes_desde_reset`,
`resets_desde_intencao` e `estoque_estimado`, mas **não** grava
`resets_consecutivos`, `intervalos_lentos_consecutivos` nem `pontos_de_pressa`.
Os contadores que decidem o regime só aparecem no `sessao.json`, no fim. Foi por
isso que este bug não pôde ser diagnosticado a partir dos registros.

A mudança acrescenta ao stream por Volta: os três contadores que faltam, o
estado da Janela, e `resta_lote_cheio` da última Venda.

## Configuração

```toml
intervalo_da_janela_s = 180
```

O `LOTE_DE_VENDA_EM_STACKS` fica como constante de código, não configuração:
ele descreve a mecânica do jogo (stack de 3, Capacidade do NPC), não uma
preferência de operação.
