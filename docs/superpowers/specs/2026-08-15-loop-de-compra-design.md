# Design: loop de Compra com F2 e F3

Data: 2026-08-15
Épico: [#1](https://github.com/lavarini/mistfall-reseller/issues/1)
Issues: [#6](https://github.com/lavarini/mistfall-reseller/issues/6),
[#7](https://github.com/lavarini/mistfall-reseller/issues/7),
[#8](https://github.com/lavarini/mistfall-reseller/issues/8) (só a tecla de pânico)

Nenhuma das três fecha só com este trabalho. A #6 tem critérios que o ADR-0003 tornou
obsoletos e um que exige a máquina do jogo ("o loop completa pelo menos uma Compra de ponta a
ponta"); a #7 fecha inteira no código, mas seu critério de Reset confirmado só é observável
de verdade rodando; a #8 fica com dois terços em aberto por decisão. Ver "Documentação a
atualizar junto".

## O que provocou isto

O `piloto.py` faz uma Compra e para. O docstring dele diz isso na primeira linha e aponta
para as duas fatias que faltam: "Sem loop, sem Reset — esses sao a #6 e a #7". O Reset
standalone chegou em `reset.py` e foi exercitado na máquina do jogo. Falta costurar os dois
num laço que rode sozinho, e um jeito de ligar e desligar esse laço sem largar o teclado do
jogo.

O pedido do dono do projeto: **F2 começa, F3 para, feedback no PowerShell**, e o laço
completo presumindo que a tela já está em Material de Construção — analisa, reseta se
precisar, clica, Espaço, recomeça.

## De onde partimos, com evidência

Vale registrar porque muda o risco do que vem a seguir.

**O clique funciona.** O ADR-0001 termina dizendo que o clique não acontecia na máquina do
jogo e que a correção — `LEFTDOWN` e `LEFTUP` em lotes separados, com espera entre eles —
saiu por eliminação e ainda não tinha sido confirmada. Ela foi: a correção está em
`perifericos/windows.py:130-132`, e `execucao-real/` guarda o `01-janela.png`, isto é, o bot
clicou numa Listagem e a Janela de Confirmação abriu. A seção "O que ainda não foi
observado" do ADR-0001 está desatualizada nesse ponto.

**O Espaço nunca foi confirmado.** Aquela mesma execução abortou com `"Preco Unitario
ilegivel no modal"` — a #18, que gerou o [ADR-0003](../../adr/0003-nao-conferir-a-janela-de-confirmacao.md)
e tirou a conferência da Janela do caminho. Nenhuma Compra jamais completou. A
[#9](https://github.com/lavarini/mistfall-reseller/issues/9) segue aberta e o desfecho
`OURO_NAO_CAIU` existe exatamente para essa pergunta.

Consequência para este design: **a primeira execução real deste loop é também a primeira
chance de uma Compra completar.** O laço não está sendo construído sobre um caminho provado;
está sendo construído sobre um caminho provado até o penúltimo passo.

## Decisões tomadas no brainstorm

Quatro, todas do dono do projeto, registradas porque restringem o desenho:

1. **A Categoria do Reset alterna a cada Reset**: Forja, Chave, Forja, Chave. Não é sorteio e
   não tem relação com hora do relógio.
2. **Da #8 entra só a tecla de pânico.** Piso de Ouro e log estruturado de Compras ficam de
   fora. Ver "Riscos aceitos".
3. **Só o F3 para o laço.** Nenhuma falha o encerra, por mais que se repita.
4. **O F3 interrompe de forma cooperativa**, checado nos pontos que importam — não entre
   Compras apenas, e não matando thread.

## O Interruptor

Um terceiro protocolo em `perifericos/protocolos.py`, ao lado de `Tela` e `Mao`:

```python
class Interruptor(Protocol):
    def esperar_inicio(self) -> None:
        """Bloqueia até o operador apertar F2."""

    def pediram_parada(self) -> bool:
        """F3 foi apertado desde a última pergunta?"""
```

A fronteira é a mesma dos outros dois, e pela mesma razão do
[ADR-0001](../../adr/0001-dev-mac-run-windows.md): a lógica fica testável no macOS e só a
tradução para syscall mora no Windows.

**`InterruptorWindows`** em `perifericos/windows.py`, usando `GetAsyncKeyState` por
`ctypes.windll.user32` — a mesma porta que o `SendInput` já usa, sem dependência nova.
`VK_F2` é `0x71` e `VK_F3` é `0x72`.

O detalhe que dispensa uma thread: `GetAsyncKeyState` devolve, no bit `0x0001`, se a tecla
foi pressionada **desde a chamada anterior**. Isso é um trinco, não uma leitura instantânea:
uma tecla apertada e solta durante um `time.sleep` de 2 s continua registrada na pergunta
seguinte. Sem isso o F3 só pegaria se você o segurasse no instante exato da checagem.

Esse comportamento do trinco é a única parte deste design que **não pode ser verificada no
macOS** e precisa ser confirmada na máquina do jogo. Se ele se mostrar instável, o plano B é
uma thread de fundo enquetando a mesma API e guardando o flag — mesma interface, mesmos
testes, nenhuma mudança fora de `windows.py`.

**`InterruptorFalso`** em `perifericos/falso.py`, roteirizado: para na enésima pergunta.
É o que torna o laço inteiro exercitável sem jogo e sem Windows.

## O ciclo e a Volta

Módulo novo, `src/mistfall/ciclo.py`. O `piloto.py` **não** ganha o laço: ele é
deliberadamente "uma Compra e para", e o ciclo compõe as peças que já existem sem duplicar
nenhuma.

```
interruptor.esperar_inicio()                      # bloqueia no F2
enquanto não interruptor.pediram_parada():
    resultado = piloto.executar(..., interruptor=interruptor)
    imprimir_a_linha_da_volta(resultado)
    se resultado.desfecho é NADA_COMPRAVEL:
        reset.resetar_categoria(..., próxima_categoria())
    dormir(ritmo.espera_entre_voltas)
imprimir_o_fecho()
```

**Reset só no `NADA_COMPRAVEL`.** É o critério da #7, e a razão está no `CONTEXT.md`: uma
Compra, ou mesmo uma tentativa, já recarrega a lista sozinha. `COMPROU`, `OURO_NAO_CAIU` e
`ABORTOU` não resetam — o último porque abortar não chegou a mexer na tela.

**`espera_entre_voltas`, campo novo no `Ritmo`.** Não é cosmético. Como só o F3 para o laço,
uma tela que não seja `LISTA` faz o pré-voo abortar imediatamente, e sem essa espera o laço
gira em rotação máxima capturando a tela inteira dezenas de vezes por segundo. A espera
transforma "queima CPU e disco" em "reclama devagar".

Padrão: 1,0 s, o mesmo valor que `espera_categoria_carregar` já usa para o redesenho da
lista. É palpite calibrável, não medida — como todo tempo deste projeto, só se acerta na
máquina do jogo. `Ritmo.instantaneo()` o zera junto com os outros.

### Duas mudanças no que já existe

**`piloto.executar` ganha `interruptor: Interruptor | None = None`.** O default `None`
preserva o comportamento atual, e é o que impede os 286 testes existentes de precisarem
mudar. Quando presente, é consultado em dois pontos:

- **Antes do clique.** Este é o ponto que justifica a abordagem cooperativa: sem ele, apertar
  F3 durante uma varredura ainda deixa o bot completar mais uma Compra.
- **Dentro de `_esperar_o_ouro_cair`.** Encurta a enquete de até 5 s em vez de cumpri-la.

Não há checagem entre o clique e o Espaço. Com o ADR-0003, essa janela encolheu para
80-120 ms, e depois do Espaço não há mais nada para abortar: a Compra já aconteceu.

**`SEGUNDOS_DE_CONTAGEM` não vai para o bot.** A contagem regressiva de 5 s existia para dar
tempo de Alt+Tab; o F2 resolve isso melhor, porque é apertado de dentro do jogo. O
`piloto_cli` mantém a contagem — ele continua sendo a ferramenta de uma Compra só.

## O Reset alternante

Um `itertools.cycle([FORJA, CHAVE])` guardado pelo ciclo. Determinístico de propósito: o
teste afirma a sequência exata em três Resets seguidos, sem sorteio para atrapalhar.

**A alternância escolhe qual Categoria alternativa usar naquele Reset — uma só.** Cada Reset
continua sendo dois cliques, e nunca toca nas duas alternativas no mesmo disparo:

```
Reset nº1:  clica Forja  →  clica Material de Construção
Reset nº2:  clica Chave  →  clica Material de Construção
Reset nº3:  clica Forja  →  clica Material de Construção
```

O segundo clique não é opcional: sem ele a lista fica exibindo Chave ou Forja, que não é
onde os Itens-alvo estão. É a definição de Reset no `CONTEXT.md` e o que o `reset.py` já
confirma, exigindo as duas transições antes de devolver sucesso.

Isto é a única coisa que o ciclo sabe sobre Categorias. O `reset.resetar_categoria` já aceita
`categoria_alternativa` e já confirma as duas transições antes de devolver verdadeiro; o
ciclo só escolhe qual passar.

## O diário: só as Voltas interessantes

O `_Diario` do piloto grava no mínimo um PNG de pré-voo (~1 MB) e um `relatorio.json` por
execução. Foi desenhado para execução única, onde o relatório **é** o produto. Num laço de
mil Voltas isso vira mais de um giga e mil pastas.

Decisão: **a Volta guarda a pasta completa quando o desfecho é `COMPROU`, `OURO_NAO_CAIU` ou
`ABORTOU`; descarta os PNGs quando é `NADA_COMPRAVEL`.** O caso comum é também o que não
carrega informação nenhuma — uma tela sem Item-alvo no Preço-alvo é exatamente o que se
espera na maioria das Voltas.

Cada Volta escreve em `<pasta>/volta-NNNN/`, onde `<pasta>` é o `--pasta` da execução e a
numeração recomeça em 1 a cada sessão do bot. O descarte é do ciclo, não do piloto: o piloto
continua gravando tudo, e quem sabe que a Volta foi rotina é quem viu o desfecho. Isso mantém
o `piloto.executar` ignorante do laço.

O `relatorio.json` **não** é descartado nem nas Voltas de rotina. Ele é pequeno e é o que
permite reconstruir a sessão depois.

## Feedback no PowerShell

Uma linha por Volta, com `flush=True`:

```
[001] 23:47:12  comprou      Broche  200g   Ouro 59227 -> 59027
[002] 23:47:19  nada         -> Reset (forja)
[003] 23:47:26  nada         -> Reset (chave)
[004] 23:47:33  OURO NAO CAIU  apertamos Espaco e o Ouro nao se moveu
[005] 23:47:40  abortou      pre-voo viu janela_confirmacao, esperava lista
```

Cabeçalho antes do laço: `aperte F2 no jogo para comecar, F3 para parar`. Fecho depois do
F3: total de Voltas, quantas Compras, Ouro gasto na sessão.

**Sem acentos e sem cor.** O projeto inteiro já escreve saída de console sem acento
(`"comecando em..."`, `"prints e relatorio em"`), quase certamente por causa da página de
código do console do Windows. Seguir o padrão custa nada; quebrá-lo arrisca um `mojibake` na
única superfície que o operador vê enquanto o bot roda.

## CLI

Ferramenta nova, `ferramentas/bot_cli.py`, com entry point `mistfall-bot` no
`pyproject.toml`. O `mistfall-piloto` fica intocado: uma Compra, um relatório, para depurar.
São ferramentas diferentes e misturá-las numa flag esconderia isso.

Argumentos: `--pasta`, `--config` e `--espera-modal`, os mesmos do piloto e pelo mesmo
motivo — a espera do modal só se calibra na máquina do jogo.

## Testes

Todos no macOS, com `Ritmo.instantaneo()`, `TelaFalsa` servindo um roteiro de PNGs,
`MaoFalsa` gravando o que lhe pediram e `InterruptorFalso` roteirizado:

- F3 antes de uma Volta nova encerra o laço, e a `MaoFalsa` não registra clique depois disso
- `NADA_COMPRAVEL` dispara Reset; `COMPROU` e `OURO_NAO_CAIU` não disparam
- Três Resets seguidos saem Forja, Chave, Forja
- Volta `NADA_COMPRAVEL` não deixa PNG no disco; Volta `COMPROU` deixa a pasta inteira
- O `relatorio.json` sobrevive em toda Volta, inclusive nas descartadas
- F3 durante a enquete do Ouro encurta a espera em vez de cumprir o teto
- `piloto.executar` sem `interruptor` se comporta exatamente como hoje

O último é o que protege os 286 testes existentes.

Fora de alcance dos testes automatizados, e portanto explicitamente uma pergunta para a
máquina do jogo: se o trinco `0x0001` do `GetAsyncKeyState` pega uma tecla apertada durante
um `time.sleep`.

## O que foi considerado e recusado

**Matar a thread do worker no F3.** Python não interrompe thread com segurança, e cortar
entre `LEFTDOWN` e `LEFTUP` deixaria o botão do mouse pressionado dentro do jogo. O estado
que sobra é pior do que o que se queria evitar.

**Checar o F3 apenas entre Voltas.** Mais simples e sem tocar no `piloto.py`, mas deixa o bot
começar uma Compra inteira depois de você já ter mandado parar, e cumpre até 7 s de espera de
Ouro antes de perceber.

**Pôr o laço dentro do `piloto.py`.** O módulo declara na primeira linha que é de uma Compra
só, e as funções estacionadas do ADR-0003 já moram lá. Somar um laço a isso faz do arquivo
duas coisas.

**Guardar uma linha por Volta em JSONL e nenhum PNG.** É mais barato e vira insumo do log da
#8, mas hoje, com a #9 ainda sem resposta, uma Volta que der errado no Windows sem imagem
nenhuma é um diagnóstico que não volta da viagem.

## Riscos aceitos

Decisões do dono do projeto, registradas para não parecerem esquecimento:

**Sem piso de Ouro.** O laço compra enquanto houver Listagem no Preço-alvo e Ouro na conta.
O único freio é o F3. A #8 nomeia esse risco — "para o bot não zerar a conta" — e ele fica
em aberto por ora.

**Nenhuma falha para o laço.** Um `ABORTOU` que se repita para sempre, por exemplo se o jogo
sair da tela do Leilão, vira um laço que captura, aborta, espera e recomeça indefinidamente.
Ele reclama em toda linha do PowerShell, mas não desiste sozinho.

**`OURO_NAO_CAIU` não para.** Se o Espaço não estiver registrando, o bot clica em Listagens
sem comprar, indefinidamente. Como o Espaço nunca foi confirmado (#9), esse é o desfecho mais
provável da primeira execução real — e o operador vai precisar ler o PowerShell e apertar F3.

## Documentação a atualizar junto

- **`CONTEXT.md`**: entrada para **Volta** (uma iteração do laço: varredura, e então Compra
  ou Reset; *avoid*: Iteração, Ciclo, Rodada) e para **Interruptor** (o par F2/F3 visto pelo
  bot; *avoid*: Hotkey, Atalho, Tecla de pânico).
- **ADR-0001**: a seção "O que ainda não foi observado" afirma que o clique com duração não
  foi confirmado. Foi. Corrigir com a evidência de `execucao-real/`.
- **Issue #6**: os critérios de aceite exigem conferência dupla do preço e espera pela Janela
  detectada antes do Espaço — as duas coisas que o ADR-0003 removeu. Ajustar a issue ao ADR
  antes de fechá-la, ou ela será fechada mentindo.

## O que fica de fora

Piso de Ouro, log estruturado de Compras (#8), Quantidade diferente de 1, qualquer uso da
Tendência de Mercado, e a estratégia de revenda.
