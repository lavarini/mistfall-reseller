# Mistfall Reseller

Bot que observa a Casa de Leilão do jogo Mistfall e compra Itens-alvo quando o preço está no
valor desejado, para revendê-los com lucro.

## Como funciona

Entrada: um print da tela em 2560×1440. Saída: a decisão de qual Listagem comprar, e a Compra.

1. Confere que a tela é a lista do Leilão, em Material de Construção
2. Lê o Ouro
3. Recorta os 12 slots por coordenada fixa e identifica o item de cada um por **template
   matching do ícone** — não por OCR do nome, que é fonte estilizada
4. Lê o **Preço-unitário** dos 12 slots por OCR, numa **chamada só**: os recortes vão
   empilhados numa folha, separados por faixas pretas, e cada número volta ao seu slot pela
   posição vertical
5. Entre as Listagens que estão **exatamente** no Preço-alvo, sorteia uma. Preço abaixo do
   Preço-alvo é leitura suspeita, não pechincha: vai para o `relatorio.json`, não gera Compra
6. Clica, espera um tempo sorteado numa faixa curta para a **Janela de Confirmação**
   abrir, e aperta **Espaço**
7. Confirma que o Ouro caiu **exatamente** o Preço-unitário da Listagem escolhida

**A Janela de Confirmação não é conferida.** Ela não é detectada, não é capturada e não é
lida — o passo 6 é uma espera e uma tecla. A conferência existia e foi desativada: ela nunca
pegou uma Compra ruim e derrubou Compras boas duas vezes, porque ler o modal é intermitente.
O porquê, o que isso deixa descoberto e o que continua cobrindo estão no
[ADR-0003](docs/adr/0003-nao-conferir-a-janela-de-confirmacao.md).

O que protege agora vive **antes** do clique: só é comprável o preço **exatamente** igual ao
Preço-alvo, e a conferência de ordenação invalida preço fora da ordem crescente. Depois do
clique sobra uma conferência só, a do passo 7 — ela não impede a Compra errada, mas não deixa
ela passar calada.

Velocidade não era requisito enquanto era uma Compra e para. Com a conferência do modal fora
do caminho, a espera do passo 6 é o único tempo morto que restou. Ela é **sorteada** a cada
Compra, entre o valor calibrado e 1,5× ele, para o ritmo não sair sempre idêntico — o piso é
`--espera-modal`, e o sorteio vai só para cima dele: variar para baixo do calibrado perde
Compra.

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

Aperte **F2** dentro do jogo para começar e **F3** para parar. Cada Volta imprime uma linha
no console e guarda a própria pasta; as Voltas sem nada comprável descartam os prints e
mantêm só o relatório.

Não há piso de Ouro: o bot compra enquanto houver Listagem no Preço-alvo e Ouro na conta, e
o único freio é o F3.

### Códigos de saída

| Código | Significado |
|--------|-------------|
| `0` | Correu como esperado: comprou, simulou, ou não havia nada comprável |
| `1` | Abortou por segurança — tela que ele não entendeu, ou Ouro ilegível |
| `2` | Problema de ambiente: resolução errada, tesseract ausente, config inválida |
| `3` | Apertou Espaço e o **Ouro não se moveu** |

O `3` existe para não confundir "o Espaço não registrou" com uma Compra confirmada.

### O que fica na pasta de execução

Cada captura do caminho vira PNG numerado, mais um `relatorio.json` com tudo que o bot leu —
inclusive quando ele aborta, e inclusive se algo explodir no meio. Traz também o tempo de cada
etapa (`pre_voo`, `varredura`, `modal`, `confirmacao_do_ouro`), em milissegundos. Se der
errado, é essa pasta que diagnostica.

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
```

`trabalhadores` controlava quantos OCRs rodavam em paralelo. Hoje **não controla nada**: a chave
está dormente, e mexer nela não muda o comportamento do bot.

Ela perdeu os dois consumidores que tinha. A varredura dos 12 slots deixou de usar este número —
ela faz uma chamada só ao tesseract, com os doze recortes empilhados numa folha, e não há o que
paralelizar. E as três leituras da Janela de Confirmação saíram do caminho junto com a
conferência do modal, pelo [ADR-0003](docs/adr/0003-nao-conferir-a-janela-de-confirmacao.md).

A chave e o helper (`src/mistfall/paralelo.py`) continuam no código de propósito, não por
esquecimento: a leitura em folha única e a espera cega no modal são as duas experimentais, e
manter o paralelismo permite voltar atrás sem reconstruir nada. A
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

São 332 testes, e todos rodam no Mac sem o jogo aberto.

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

## Documentação

| Arquivo | O que traz |
|---------|------------|
| [`CONTEXT.md`](CONTEXT.md) | O glossário do domínio — Leilão, Listagem, Item-alvo, Compra, Reset |
| [`docs/execucao-windows.md`](docs/execucao-windows.md) | Roteiro operacional das execuções no Windows |
| [`docs/adr/`](docs/adr/) | Decisões arquiteturais e o porquê delas |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | Designs, com as premissas que os moldaram |

Vale ler o [ADR-0002](docs/adr/0002-deteccao-slots-fixos-template.md) antes de mexer em
detecção: o acoplamento à resolução 2560×1440 é **deliberado**, não descuido. Se a resolução
ou o layout do Leilão mudarem, coordenadas e templates precisam ser recalibrados.
