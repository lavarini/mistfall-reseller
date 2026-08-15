# Design do fluxo de Venda

Data: 2026-08-15

## Objetivo

Automatizar a criação de Listagens para os sete Itens-alvo já comprados pelo bot.
O operador abre previamente o Leilão na aba **Vender**, com o painel **Armazém**
selecionado. A partir daí, o bot vende todos os stacks de quantidade exatamente `3`,
respeita a capacidade `X/Y` mostrada na tela e percorre os baús somente para a direita.

O fluxo termina quando a capacidade está cheia ou quando o quarto e último baú não
contém mais candidatos.

## Vocabulário novo

**Venda** é a ação de criar uma Listagem a partir de um stack de `3` unidades de um
Item-alvo no Armazém. Uma Venda consome uma posição de `X/Y`. Ela começa
com o clique no slot, passa pela Janela de Confirmação "Listar para Venda" e termina
quando essa janela fecha após o Espaço.

**Preço de Venda** é o Preço-unitário fixo pelo qual um Item-alvo deve ser listado.
Ele vem da configuração e não é inferido da Tendência de Mercado nem relido da Janela
de Confirmação.

**Capacidade de Venda** é o par `X/Y` exibido em "Listar para Venda X/Y": `X` é o
número de Listagens ocupadas e `Y` é o limite atual do NPC. Os dois valores vêm da tela,
pois `Y` depende do nível do NPC e pode mudar entre seasons.

**Baú** é uma das quatro abas do Armazém, representadas pelos ícones abaixo do título
"Armazém". O bot começa no Baú selecionado pelo operador e só avança para a direita.

## Premissas

1. A resolução é fixa em 2560×1440, conforme o ADR-0002.
2. O operador abre a aba Vender e seleciona Armazém antes de apertar F2.
3. Qualquer um dos quatro Baús pode estar selecionado no início.
4. Os Itens-alvo continuam sendo Broche, Adaga, Lanterna, Dragão, Orbe, Rede e Códice.
5. Somente stacks cuja quantidade visível seja exatamente `3` são vendidos.
6. A Quantidade digitada na Janela de Confirmação é sempre `3`.
7. O conteúdo preenchido na Janela de Confirmação não é relido. Os valores digitados
   são autoritativos.

## Configuração

`config.toml` ganha uma seção obrigatória e independente de `[precos_alvo]`:

```toml
[precos_venda]
broche = 226
adaga = 240
lanterna = 281
dragao = 295
orbe = 304
rede = 312
codice = 338
```

Cada Preço de Venda deve ser um inteiro de Ouro maior que zero. O comando de Venda
recusa iniciar se faltar algum dos sete Itens-alvo, se houver nome desconhecido ou se
algum valor for inválido. O fluxo de Compra continua usando somente `[precos_alvo]`.

Não existe parâmetro de linha de comando para a Capacidade de Venda. A tela é a única
fonte autoritativa; o valor `12` das imagens é exemplo, não regra de produção.

## Fluxo

1. Espera F2. F3 solicita a parada.
2. Captura a tela e verifica resolução, aba Vender, painel Armazém e Baú selecionado.
3. Lê a Capacidade de Venda `X/Y`. Leitura ilegível ou incoerente aborta.
4. Se `X >= Y`, encerra com capacidade cheia, sem clicar em slot.
5. Varre os slots visíveis do Baú selecionado. Para cada slot, identifica o Item-alvo e
   lê a quantidade do stack.
6. Escolhe o primeiro candidato em ordem de cima para baixo e da esquerda para a direita:
   Item-alvo reconhecido com segurança e quantidade exatamente `3`.
7. Antes de começar a Venda, consulta F3. Se a parada foi pedida, encerra sem clicar no slot.
8. Clica no centro do slot e espera a Janela de Confirmação "Listar para Venda" abrir.
   Se ela não abrir dentro do teto, aborta sem digitar nem apertar Espaço.
9. Clica no campo Preço-unitário, usa `Ctrl+A` e digita o Preço de Venda configurado.
10. Clica no campo Quantidade, usa `Ctrl+A` e digita `3`.
11. Aperta Espaço uma vez para confirmar.
12. Espera a Janela de Confirmação fechar e a tela de Venda reaparecer. Se isso não
    acontecer dentro do teto, aborta sem repetir o Espaço.
13. Relê `X/Y`. Os dois números substituem a leitura anterior. Se estiverem ilegíveis
    ou incoerentes, aborta; se `X >= Y`, encerra com capacidade cheia.
14. Consome o próximo candidato da lista já extraída para o Baú atual. Os slots não se
    reorganizam depois de uma Venda, portanto a imagem não é processada novamente.
15. Quando a lista de candidatos do Baú atual acabar, consulta F3, avança exatamente um Baú à
    direita e espera a tela estabilizar.
16. Repete a partir do passo 3. Se o Baú atual já for o quarto, encerra automaticamente.

O bot nunca volta para um Baú à esquerda e nunca pula um Baú intermediário.

## Fronteiras e componentes

### Visão de Venda

Um módulo de visão puro recebe uma imagem e oferece operações independentes para:

- reconhecer a tela de Venda com Armazém aberto;
- ler `X/Y` da Capacidade de Venda;
- detectar qual Baú está selecionado pelo destaque dourado;
- recortar os slots fixos do Armazém;
- identificar Item-alvo usando os templates existentes;
- ler a quantidade visível do stack.

A geometria é medida nas três imagens de referência e permanece deliberadamente fixa em
2560×1440. Item ou quantidade ilegível torna o slot inelegível; não aborta a varredura.

### Uma Venda

Um orquestrador executa exatamente uma Venda. Ele conhece o slot, o Item-alvo, o Preço
de Venda e a Quantidade fixa, mas não conhece Baús nem decide quando a sessão termina.
Ele reconhece somente a abertura e o fechamento da Janela de Confirmação; não lê ícone,
Preço-unitário, Quantidade, ganhos estimados ou Tendência de Mercado dentro dela.

### Ciclo de Venda

Outro orquestrador controla a Capacidade de Venda, processa cada Baú uma vez, avança Baús e
encerra a sessão. Separar esse ciclo da Venda unitária preserva o mesmo limite usado no
MVP de Compra: uma operação de interface testável por vez e um laço que apenas a compõe.

O fluxo de Compra existente não é convertido em modo genérico. Compra e Venda têm telas,
decisões e estados distintos e permanecem em módulos separados.

### Periféricos

O protocolo `Mao` ganha operações para `Ctrl+A` e digitação numérica. A implementação
Windows continua sendo o único módulo dependente do sistema operacional. Os dublês
registram cliques, teclas e texto para que os testes verifiquem a sequência real de ações.

## Segurança e falhas

- Tela, Armazém, Baú selecionado ou `X/Y` irreconhecível: aborta sem adivinhar.
- `X > Y`, `X < 0` ou `Y <= 0`: leitura incoerente; aborta.
- Slot não alvo, quantidade diferente de `3` ou quantidade ilegível: ignora o slot.
- Janela de Confirmação não abriu: aborta sem digitar e sem Espaço.
- Janela não fechou depois do Espaço: aborta sem repetir a confirmação.
- F3 é consultado antes de começar uma Venda e antes de avançar de Baú. Depois do clique
  no slot, a Venda em andamento é concluída, inclusive os cliques nos dois campos, para
  não deixar a Janela parcialmente preenchida.
- O relatório registra Baú, slot, Item-alvo, Preço de Venda, Quantidade, leituras `X/Y`,
  capturas e desfecho. Nenhuma leitura interna da Janela influencia a decisão.

## Comando

`python -m ferramentas.venda_cli` executa o ciclo de Venda. Ele não recebe limite de
Listagens; carrega os Preços de Venda do `config.toml`, usa F2/F3 e recebe apenas opções
operacionais já compatíveis com o bot, como pasta de relatórios e tempos calibráveis.
O comando de Compra permanece `python -m ferramentas.bot_cli`.

## Testes

O desenvolvimento segue TDD. As três imagens fornecidas validam a visão real, e fixtures
sintéticas isolam transições que o corpus ainda não contém.

A suíte cobre:

- leitura de `0/12` e do Baú destacado nas imagens de Venda;
- reconhecimento de todos os Itens-alvo observáveis e de stacks `3`;
- rejeição de stacks `2`, `5`, ilegíveis e slots não alvo;
- validação completa de `[precos_venda]` sem mudar `[precos_alvo]`;
- sequência de clique, `Ctrl+A`, Preço de Venda, Quantidade `3` e Espaço;
- ausência de digitação e Espaço quando a Janela não abre;
- ausência de um segundo Espaço quando a Janela não fecha;
- uma única varredura por Baú e consumo dos candidatos já processados depois de cada Venda;
- avanço somente para a direita e parada no quarto Baú;
- releitura autoritativa de `X/Y` depois de cada Venda;
- parada quando `X == Y` e aborto para leituras ilegíveis ou incoerentes;
- parada por F3 antes de novos cliques;
- regressão completa do fluxo e do comando de Compra.

## Fora do escopo

- descobrir Preços de Venda pela Tendência de Mercado;
- vender quantidades diferentes de `3`;
- reler ou validar campos preenchidos na Janela de Confirmação;
- navegar para Baús à esquerda do selecionado inicialmente;
- alterar ou cancelar Listagens já criadas;
- adaptar a visão para resoluções diferentes de 2560×1440.
