# Mistfall Reseller

Bot que observa a Casa de Leilão do jogo Mistfall e compra Itens-alvo quando o preço está no
valor desejado, para revendê-los com lucro.

## Como funciona

Entrada: um print da tela em 2560×1440. Saída: a decisão de qual Listagem comprar e, quando
ela existe, o envio dos comandos da Compra.

1. Confere que a tela é a lista do Leilão, em Material de Construção
2. No mesmo frame inicial, observa o Ouro e começa a varrer as Listagens. Em produção esses
   dois ramos rodam sequencialmente
3. Recorta os 12 slots por coordenada fixa e identifica o item de cada um por **template
   matching do ícone** — não por OCR do nome, que é fonte estilizada
4. Lê o **Preço-unitário** dos 12 slots por OCR, numa **chamada só**: os recortes vão
   empilhados numa folha, separados por faixas pretas, e cada número volta ao seu slot pela
   posição vertical
5. Entre as Listagens que estão **exatamente** no Preço-alvo, sorteia uma. Preço abaixo do
   Preço-alvo é leitura suspeita, não pechincha: vai para o `relatorio.json`, não gera Compra
6. Espera entre 50 e 150 ms, clica, espera entre 80 e 120 ms para a **Janela de
   Confirmação** abrir, e aperta **Espaço**
7. Registra `compra_enviada`: clique e Espaço foram enviados. Esse desfecho **não confirma**
   que a Compra aconteceu

**A Janela de Confirmação não é conferida.** Ela não é detectada, não é capturada e não é
lida — o passo 6 é uma espera e uma tecla. A conferência existia e foi desativada: ela nunca
pegou uma Compra ruim e derrubou Compras boas duas vezes, porque ler o modal é intermitente.
O porquê, o que isso deixa descoberto e o que continua cobrindo estão no
[ADR-0003](docs/adr/0003-nao-conferir-a-janela-de-confirmacao.md).

O que protege agora vive **antes** do clique: só é comprável o preço **exatamente** igual ao
Preço-alvo, e a conferência de ordenação invalida preço fora da ordem crescente. Depois do
Espaço não há nova captura nem conferência. O Ouro do frame inicial é telemetria
**observacional**: mesmo ilegível, ele nunca bloqueia a Volta nem muda a decisão de Compra.

As duas esperas do passo 6 são **sorteadas** a cada Compra para o ritmo não sair sempre
idêntico. `--espera-modal` ajusta o piso da espera entre o clique e o Espaço e conserva a
proporção de 1,5× até o teto. Depois de uma Compra enviada, o loop espera um valor sorteado
entre 650 e 750 ms para a lista se atualizar antes da próxima captura. Voltas sem Compra
mantêm a espera fixa de 150 ms, evitando desacelerar a varredura comum.

Os cliques da Compra não repetem uma coordenada fixa. A Listagem escolhida e as duas
Categorias usadas pelo Reset recebem pontos sorteados dentro de áreas centrais seguras.
Esse sorteio só muda o ponto dentro do mesmo alvo: não muda a Listagem escolhida, a
alternância Forja/Chave, as esperas ou as teclas Espaço/F3/F4.

### O Fluxo Completo

O que está acima é uma Volta de Compra, e é o que `mistfall-bot` faz em laço. O
`mistfall-completo` põe Compra e Venda no mesmo laço e decide sozinho quando trocar de
aba, sem ninguém entre uma coisa e outra.

A decisão é de ritmo, não de relógio. Ele conta **Intenções** — Listagens de Item-alvo no
Preço-alvo — e os Resets entre elas. Enquanto aparece Item-alvo, o regime é rápido e ele
só vende quando o jogo acusa Inventário cheio. Quando o mercado seca — três intervalos de
três Resets seguidos, ou cinco Resets sem nenhuma Intenção — o regime vira lento, e aí
vender 45 unidades acumuladas passa a valer mais que continuar varrendo.

Três coisas que valem saber antes de confiar nele por horas:

- O **Estoque estimado** é uma contagem interna, nunca relida do Armazém. Ele pode
  divergir do real quando o OCR do Ouro fica instável; isso é conhecido e não há
  reconciliação implementada.
- Um sinal ambíguo isolado — um toast não lido, um Ouro ilegível — nunca derruba a
  sessão. O que derruba é falha **persistente**: cinco Voltas abortadas seguidas, ou uma
  navegação que não confirma depois das retentativas.
- Quando ele encerra, grava `sessao.json` com desfecho e motivo, e sai com código 1. Um
  processo que terminou em silêncio com código 0 terminou porque você apertou F4.

## Onde roda

O jogo roda num PC **Windows**; o desenvolvimento acontece num **Mac**. Por isso existem três
fronteiras de IO — Tela, Mão e Interruptor — atrás de protocolos, com dublês. Todo o resto é
função pura de imagem → dado.

Consequência prática: **o bot inteiro é testável no macOS**, contra os prints em `images/`.
`src/mistfall/perifericos/windows.py` é o único arquivo que não roda aqui, e ele não tem
lógica nenhuma — só traduz chamada em syscall.

## Instalação

### No Mac, para desenvolver

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Precisa do binário do **tesseract**:

```bash
brew install tesseract
```

### No Windows, para rodar valendo

A máquina do jogo pode não ter nada além dele. São três coisas:

1. **Python 3.14** de [python.org](https://python.org), marcando *Add python.exe to PATH*
2. **tesseract**, o build do [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki),
   marcando a opção de adicionar ao PATH
3. O repositório, e então, na raiz dele:

```
python -m pip install -e .
```

O `-e` **não é opcional**: sem ele a busca pela pasta `templates/` quebra.

No fim, repare se o `pip` avisou que a pasta `Scripts` **não está no PATH**. No Python 3.14 do
python.org — que instala pelo *Python Install Manager* — ela costuma não estar, mesmo tendo
marcado *Add python.exe to PATH*: esse item põe no PATH um atalho para o `python.exe`, e não o
`Scripts` da instalação. O sintoma é o `mistfall-piloto` sair como "não é reconhecido" com tudo
instalado; o conserto está no [roteiro](docs/execucao-windows.md). Sem mexer no PATH, todo
`mistfall-piloto ...` abaixo funciona como `python -m ferramentas.piloto_cli ...`.

Confira que o tesseract responde antes de seguir:

```
tesseract --version
```

## Uso

Três comandos rodam a versão contínua do bot, todos com **F3** para iniciar e **F4**
para parar dentro do jogo:

- `mistfall-bot` — só Compra, roda até o Inventário e o Armazém acusarem cheios ou o
  operador parar.
- `mistfall-venda` — só Venda, processa o Baú aberto e avança somente para a direita.
- `mistfall-completo` — alterna Compra e Venda sozinho, adaptando o ritmo ao que
  encontra no Leilão.

`mistfall-piloto` continua sendo a ferramenta de uma Compra só, para calibrar e
depurar sem comprometer uma sessão inteira.

### Antes de qualquer execução

- Jogo em **2560×1440**, com a escala de exibição do Windows em **100%**
- Leilão aberto, aba **Comprar**, Categoria **Material de Construção**
- Pelo menos um **Item-alvo exatamente no Preço-alvo** visível na tela

### Simulado, sem risco

```
mistfall-piloto --simular --pasta execucao-simulada
```

Varre e decide ao vivo, e **não toca em mouse nem teclado**. Confira se o item e o preço que
ele diz que compraria batem com o que você vê. Se não baterem, pare aqui: a visão não está
lendo a tela real, e não adianta arriscar ouro.

### Valendo

Num terminal **como administrador**, a partir da raiz do repositório:

```
mistfall-piloto --pasta execucao-real
```

Durante a contagem de 5 segundos, dê **Alt+Tab para o jogo** — não clique nele, porque um
clique pode abrir um modal sozinho. O `SendInput` vai para a janela ativa.

**Sobre administrador.** É necessário — mas o motivo ficou mais claro do que a recomendação
original deixava parecer. Numa primeira execução na máquina do jogo, o clique falhava **igual
com e sem elevação**: o `SendInput` aceitava os eventos nos dois casos, e o cursor chegava até
a Listagem certa. A causa era outra — `LEFTDOWN` e `LEFTUP` viajavam no mesmo lote, o botão
ficava apertado por tempo zero, e o jogo amostra o mouse uma vez por quadro. Corrigido isso, o
clique passou a funcionar, e **só como administrador**. O UIPI do Windows — que impede um
processo de integridade menor de enviar input a uma janela de integridade maior, e o jogo roda
elevado — segue sendo a explicação mais provável, mas não é uma causa demonstrada, só a
hipótese que sobrou. Rode elevado de qualquer forma: é o que funciona.

Essa sequência tem um padrão que vale carregar para o próximo bug do gênero: **scancode em vez
de virtual-key, rodar elevado, e dar duração ao evento** — os três resolvem a mesma distância,
entre mandar o evento e o alvo perceber o evento, e nenhum deles aparece em teste, porque os
três vivem do lado de fora do processo. Detalhes no
[ADR-0001](docs/adr/0001-dev-mac-run-windows.md).

O roteiro completo, com a execução de diagnóstico que roda sem administrador de propósito,
está em [`docs/execucao-windows.md`](docs/execucao-windows.md).

### Rodar o laço

```
mistfall-bot --pasta sessao
```

Cada processo deve usar uma pasta nova de sessão; reutilizar uma pasta existente mistura os
JSONL, porque a numeração das Voltas e os relógios monotônicos relativos reiniciam em cada
processo.

Aperte **F3** dentro do jogo para começar e **F4** para parar. Cada Volta imprime uma linha
no console e guarda a própria pasta; as Voltas sem nada comprável descartam os prints e
mantêm só o relatório. O fecho informa `Compras enviadas`: cada uma significa apenas que o
clique e o Espaço foram enviados, não que o jogo confirmou a Compra.

Não há piso de Ouro: enquanto houver Listagem no Preço-alvo, o bot tenta; o único freio é o F4.
Ter saldo suficiente é uma limitação do jogo, não uma guarda do bot.

### Vender stacks de três

Abra o Leilão na aba **Vender**, selecione **Armazém** e deixe aberto o Baú de onde o
bot deve começar. Então rode:

```bash
mistfall-venda --pasta sessao-venda
# equivalente quando Scripts não está no PATH:
python -m ferramentas.venda_cli --pasta sessao-venda
```

Aperte **F3** dentro do jogo para começar e **F4** para parar. O comando identifica os
Itens-alvo no Baú atual e cria uma Listagem para cada stack cuja quantidade seja
exatamente `3`. Cada Baú é processado uma vez; depois ele avança somente para a direita
e encerra no último Baú.

Quantos Baús existem é **contado da tela**, uma vez por sessão, e não fica fixo em
lugar nenhum — o jogo é sazonal e o Armazém expande entre resets. O número contado vai
para o `sessao.json`: como a contagem acontece uma vez só, é lá que uma leitura errada
fica visível depois.

A Capacidade de Venda vem sempre de `X/Y` na tela. O bot relê os dois números depois de
cada Venda e para quando `X == Y`; não existe limite fixo nem opção de linha de comando
para substituí-lo.

Na Janela de Confirmação, o bot usa `Ctrl+A` para preencher o Preço de Venda configurado
e a Quantidade `3`, e clica em **Listar para Venda**. O clique é direto porque o campo
Quantidade continua focado e absorve o Espaço. Ele reconhece a abertura e o fechamento da
Janela, mas não relê os campos digitados nem usa a Tendência de Mercado.

Para evitar repetir exatamente o mesmo movimento, o clique no stack e o clique em
"Listar para Venda" variam dentro de áreas centrais seguras. Baús e campos de input
continuam com coordenadas fixas.

### Rodar o fluxo completo

```
mistfall-completo --pasta sessao-completa
```

O fluxo completo alterna sozinho entre Comprar e Vender, sem clique manual de aba. Ele
sempre começa na aba Comprar, Categoria **Item → Material de Construção**, garante o
filtro roxo e assume `estoque_estimado = 0` — comece sem stacks no Armazém, ou rode
`mistfall-venda` antes para esvaziá-lo.

Aperte **F3** dentro do jogo para começar e **F4** para parar, como nos outros modos
contínuos.

O coordenador começa no regime rápido e só entra em Venda voluntária no regime lento:
três intervalos de três Resets entre Intenções seguidos, ou cinco Resets seguidos sem
nenhuma Intenção. Uma Intenção é uma Listagem de Item-alvo no Preço-alvo; não depende
de a Compra ter sido enviada nem confirmada. Em qualquer regime, a mensagem "cheios" do
jogo dispara Venda na hora.

No regime lento contínuo, uma nova Venda dispara quando `estoque_estimado` atinge 45
unidades — 15 espaços de stacks de 3. A Venda é sempre parcial: começa no **segundo
Baú**, ignorando o primeiro, lista os stacks exatos de 3 que couberem na Capacidade de
Venda disponível naquele momento, relendo `X/Y` depois de cada Listagem, e volta para
Comprar sem tentar esvaziar o Armazém inteiro. Depois de cada Venda o fluxo restaura a
aba Comprar, a Categoria Material de Construção e o filtro roxo antes de continuar.

Na raiz da pasta de sessão, `eventos-do-fluxo.jsonl` registra cada transição do
coordenador: regime, Intenções e Resets desde a última, saldo estimado, unidades
listadas, o evento aplicado e o motivo da transição. As gravações são síncronas,
portanto um erro de I/O ainda pode encerrar a execução.

Ao terminar, a mesma pasta recebe um `sessao.json` com o desfecho, o motivo, as
Compras enviadas, as unidades listadas e o estado final do fluxo — escrito também
quando a sessão aborta. O `mistfall-completo` imprime esse desfecho no fecho e sai
com código `1` quando o desfecho é `abortou`.

`estoque_estimado` é uma contagem interna, nunca relida do Armazém depois do estado
inicial. Quando o Ouro sai ilegível com uma Compra pendente, o coordenador soma uma
unidade otimista para não perder o sinal, e essa soma nunca é revista depois. Em
sessões longas com OCR de Ouro instável, isso pode deixar `estoque_estimado` divergir
do Armazém real; não há reconciliação persistente implementada.

### Códigos de saída

| Código | Significado |
|--------|-------------|
| `0` | Correu como esperado: enviou a Compra, simulou, ou não havia nada comprável |
| `1` | Abortou por segurança — por exemplo, tela que ele não entendeu |
| `2` | Problema de ambiente: resolução errada, tesseract ausente, config inválida |

### O que fica na pasta de execução

Cada captura do caminho vira PNG numerado, mais um `relatorio.json` com tudo que o bot leu —
inclusive quando ele aborta, e inclusive se algo explodir no meio. O bloco `tempos`, em
milissegundos, separa `captura_pre_voo`, `gravacao_pre_voo`, `estado`, `ouro`,
`varredura_total`, `itens`, `preparo_folha`, `tesseract_precos`,
`analise_inicial_parede`, `conferencia_e_decisao`, `pausa_antes_do_clique`, `clique`,
`espera_modal` e `espaco`. `tempos` contém somente as etapas alcançadas pela Volta: abortos,
simulações e caminhos curtos têm um conjunto parcial.

Na raiz da sessão há ainda dois JSONL incrementais:

- `telemetria-ouro.jsonl` registra, em cada Volta cuja tela inicial é LISTA, o Ouro observado,
  inclusive `null`, com número da Volta, horário e instante monotônico;
- `tempos-do-laco.jsonl` registra a Volta encerrada, o instante do próximo início, a
  `espera_efetiva_ms` e o `intervalo_entre_inicios_ms`.

Esses arquivos servem para medir a sessão depois: não participam da decisão de Compra e não
criam uma espera exclusiva. As gravações são síncronas, portanto um erro de I/O ainda pode
encerrar a execução.

## Configuração

`config.toml` traz o **Preço-alvo** de cada Item-alvo: o preço exato pelo qual compramos.

```toml
trabalhadores = 4

[precos_alvo]
broche = 188
adaga = 199
lanterna = 234
dragao = 246
orbe = 253
rede = 260
codice = 281

[precos_venda]
broche = 226
adaga = 239
lanterna = 281
dragao = 295
orbe = 304
rede = 312
codice = 338
```

`[precos_venda]` traz o Preço de Venda fixo dos sete Itens-alvo. A Compra continua
usando `[precos_alvo]`; o comando de Venda exige os sete valores de `[precos_venda]`.

`trabalhadores` controlava quantos OCRs rodavam em paralelo. Hoje **não controla nada**: a chave
está dormente, e mexer nela não muda o comportamento do bot.

Ela perdeu os dois consumidores que tinha. A varredura dos 12 slots deixou de usar este número —
ela faz uma chamada só ao tesseract, com os doze recortes empilhados numa folha, e não há o que
paralelizar. E as três leituras da Janela de Confirmação saíram do caminho junto com a
conferência do modal, pelo [ADR-0003](docs/adr/0003-nao-conferir-a-janela-de-confirmacao.md).

A chave e o helper (`src/mistfall/paralelo.py`) continuam no código de propósito, não por
esquecimento. Há um modo experimental com duas threads, uma para observar Ouro e outra para
varrer Listagens, mas elas **não usam** `trabalhadores` e não dividem a folha em 12 OCRs. A
folha continua inteira numa única chamada ao tesseract. A
[#20](https://github.com/lavarini/mistfall-reseller/issues/20) decide se ele fica ou sai, e o
que o traria de volta.

Vale a pena saber por que a varredura o perdeu, porque foi o contrário do esperado: paralelizar
doze execuções do tesseract continua sendo doze execuções, e o custo real era criar processo —
5729 ms na máquina do jogo contra 477 ms no Mac, com o mesmo paralelismo ligado. Trocar doze
chamadas por uma levou a varredura de 503 ms para 221 ms no Mac, e de quebra subiu o acerto do
corpus de 79 para 84 slots em 84: empilhados, o tesseract compara altura de dígito e alinhamento
entre as linhas, onde antes julgava cada recorte sozinho.

## Desenvolvimento

```bash
.venv/bin/python -m pytest
```

Todos os testes rodam no Mac sem o jogo aberto.

### Benchmark da análise inicial

Com uma sessão que contenha `volta-*/00-pre-voo.png`:

```powershell
python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 3
```

O comando compara o modo sequencial com o modo experimental de duas threads e exige
`resultados_iguais: true`; também imprime mediana, p95 e máximo. O padrão de produção continua
`concorrente=False`. Somente o benchmark no Windows, com o jogo aberto, decide se a
concorrência ficará ativa; o resultado local no Mac não decide essa ativação.

### Ferramentas de bancada

```bash
# Desenha sobre um print o que a detecção enxergou — caixas, itens e preços
.venv/bin/python -m ferramentas.anotar images/algum.png saida.png

# Recorta os 7 templates de ícone a partir do print de referência
.venv/bin/python -m ferramentas.extrair_templates

# Propõe o arquivo de expectativa de cada print, para revisão humana
.venv/bin/python -m ferramentas.propor_esperado

# Gera os frames sintéticos usados nos testes do piloto
.venv/bin/python -m ferramentas.sintetizar_fixtures
```

A ferramenta de anotação é a forma de **ver** se a detecção funciona, em vez de confiar num
número de acurácia agregado.

### Uma coisa que este projeto aprendeu do jeito difícil

Verde não é evidência. A base já teve **doze** defeitos da família "teste que não testa" —
cinco só nesta branch —, testes que comparavam a saída consigo mesma, que importavam do
módulo sob teste a constante que iam afirmar, que buscavam uma string no código-fonte em vez
de exercitar comportamento. Nenhum apareceu como suíte vermelha: todos precisaram de alguém
quebrando o código de propósito.

Se você mexer numa proteção, **quebre-a e confirme que a suíte reclama.**

O Fluxo Completo trouxe uma variante nova da família, que vale reconhecer porque não se
parece com as outras. O teste que cobria a Venda de 45 unidades fazia `monkeypatch` do
Estoque inicial para 100 — um valor que produção nenhuma produz, já que o modo começa
assumindo zero. O caminho real levantava `ValueError` e matava a sessão, e o teste passava
verde porque tinha substituído justamente a condição que quebrava.

Nenhuma revisão por task pegou: cada uma via só o seu pedaço, e o defeito morava na junção
entre a política e o executor da Venda, onde todo colaborador é dublê. Precisou de uma
revisão do branch inteiro, rodando o cenário de produção à mão.

Moral: **um `monkeypatch` que troca o valor inicial troca o cenário.** Se o teste só passa
com o estado inicial substituído, ele não cobre a estreia — cobre um regime que o programa
nunca vive.

## Documentação

| Arquivo | O que traz |
|---------|------------|
| [`CONTEXT.md`](CONTEXT.md) | O glossário do domínio — Leilão, Listagem, Item-alvo, Compra, Reset |
| [`docs/execucao-windows.md`](docs/execucao-windows.md) | Roteiro operacional das execuções no Windows |
| [`docs/adr/`](docs/adr/) | Decisões arquiteturais e o porquê delas |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Designs, com as premissas que os moldaram |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | Planos de execução, task a task, ao lado das specs que os originaram |

Vale ler o [ADR-0002](docs/adr/0002-deteccao-slots-fixos-template.md) antes de mexer em
detecção: o acoplamento à resolução 2560×1440 é **deliberado**, não descuido. Se a resolução
ou o layout do Leilão mudarem, coordenadas e templates precisam ser recalibrados.
