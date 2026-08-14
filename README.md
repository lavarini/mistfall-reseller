# Mistfall Reseller

Bot que observa a Casa de Leilão do jogo Mistfall e compra Itens-alvo quando o preço está no
valor desejado, para revendê-los com lucro.

Hoje ele faz **uma Compra e para**. Loop, Reset de Categoria e guardrails são os próximos
passos — veja o [épico](https://github.com/lavarini/mistfall-reseller/issues/1).

## Como funciona

Entrada: um print da tela em 2560×1440. Saída: a decisão de qual Listagem comprar, e a Compra.

1. Confere que a tela é a lista do Leilão, em Material de Construção
2. Lê o Ouro
3. Recorta os 12 slots por coordenada fixa e identifica o item de cada um por **template
   matching do ícone** — não por OCR do nome, que é fonte estilizada
4. Lê o **Preço-unitário** de cada slot por OCR
5. Escolhe a Listagem de maior margem entre as que estão abaixo do Preço-alvo
6. Clica, espera a **Janela de Confirmação** ser detectada, e confere **quatro coisas** nela:
   o ícone, o Preço Unitário, a Quantidade e o Preço Total
7. Aperta **Espaço** e confirma que o Ouro caiu **exatamente** o Preço Total

**Na dúvida, não compra.** Qualquer divergência no passo 6 aperta **Esc** e aborta — inclusive
leitura ilegível, que conta como divergência e não como caso a tratar. É a proteção contra a
pior falha possível: comprar caro por leitura errada, sem ninguém olhando.

Velocidade não é requisito. Toda espera é generosa e toda conferência é paga.

## Onde roda

O jogo roda num PC **Windows**; o desenvolvimento acontece num **Mac**. Por isso existe uma
única fronteira de IO — captura de tela, clique e teclado — atrás de dois protocolos, com
dublês. Todo o resto é função pura de imagem → dado.

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
- Pelo menos um **Item-alvo abaixo do Preço-alvo** visível na tela

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

**Administrador não é frescura.** O UIPI do Windows impede um processo de integridade menor de
enviar input a uma janela de integridade maior, e o jogo roda elevado. Sem elevação, o input
tende a ser ignorado **em silêncio, sem erro nenhum**.

O roteiro completo, com a execução de diagnóstico que roda sem administrador de propósito,
está em [`docs/execucao-windows.md`](docs/execucao-windows.md).

### Códigos de saída

| Código | Significado |
|--------|-------------|
| `0` | Correu como esperado: comprou, simulou, ou não havia nada comprável |
| `1` | Abortou por segurança — divergência no modal, ou tela que ele não entendeu |
| `2` | Problema de ambiente: resolução errada, tesseract ausente, config inválida |
| `3` | Apertou Espaço e o **Ouro não se moveu** |

O `3` existe para não confundir "o Espaço não registrou" com uma Compra confirmada.

### O que fica na pasta de execução

Cada captura do caminho vira PNG numerado, mais um `relatorio.json` com tudo que o bot leu —
inclusive quando ele aborta, e inclusive se algo explodir no meio. Se der errado, é essa pasta
que diagnostica.

## Configuração

`config.toml` traz o **Preço-alvo** de cada Item-alvo: o máximo que você aceita pagar por
unidade.

```toml
fracao_sanidade = 0.25

[precos_alvo]
broche = 188
adaga = 199
lanterna = 234
dragao = 246
orbe = 253
rede = 260
codice = 281
```

`fracao_sanidade` é uma proteção contra OCR que perde um dígito: preço lido **abaixo** dessa
fração do Preço-alvo é tratado como leitura falha, não como pechincha. Um Broche de alvo 188
aparecendo a 19 é erro, não oportunidade.

## Desenvolvimento

```bash
.venv/bin/python -m pytest
```

São 226 testes, e todos rodam no Mac sem o jogo aberto.

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

Verde não é evidência. A base já teve **dez** defeitos da família "teste que não testa" —
testes que comparavam a saída consigo mesma, que importavam do módulo sob teste a constante
que iam afirmar, que buscavam uma string no código-fonte em vez de exercitar comportamento.
Nenhum apareceu como suíte vermelha: todos precisaram de alguém quebrando o código de
propósito.

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
