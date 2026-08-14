# Design da primeira Compra real

Data: 2026-08-12
Issue: [#9](https://github.com/lavarini/mistfall-reseller/issues/9)
Épico: [#1](https://github.com/lavarini/mistfall-reseller/issues/1)

## O que muda em relação à #9

A #9 foi escrita como um spike de coordenada chumbada: capturar, clicar num ponto fixo,
apertar Espaço, sem visão nenhuma. O objetivo era isolar captura e injeção da complexidade
da detecção.

**Isso foi descartado.** O que vai ser construído é o caminho vertical inteiro rodando
sozinho: varre a lista, decide pelos Preços-alvo reais, clica na Listagem escolhida, espera a
Janela de Confirmação, confere o que está nela e aperta Espaço. Uma Compra, e para.

O trade que essa escolha faz: junta o risco desconhecido (injeção de input) com a parte
complexa (visão em tela ao vivo). Se falhar, há mais variáveis para isolar. Em compensação,
uma única execução prova o sistema inteiro em vez de um pedaço, e reaproveita a camada de
visão que já existe com 148 testes.

O modo simulado (abaixo) recupera boa parte do isolamento perdido, de graça.

## Premissas

1. **A máquina Windows não tem nada além do jogo.** Todo requisito de stack é trabalho de
   instalação antes do experimento começar.
2. **O cenário é garantido por humano.** O usuário abre o Leilão em Material de Construção
   com um Item-alvo comprável na tela e então dispara o bot. O bot mesmo assim não assume
   isso — verifica e aborta se não for verdade.
3. **Delay não importa.** Toda espera é generosa; toda conferência é paga sem hesitação.
4. **Uma Compra e para.** Loop e Reset vêm depois, na #6 e na #7, confirmados estes.

## Fluxo

1. **Pré-voo.** Contagem de 5 segundos para o usuário tirar a mão. Captura e confere:
   resolução 2560×1440 e estado `LISTA`. Qualquer outra coisa aborta sem tocar em nada.
2. **Ouro inicial.** Ilegível aborta — sem ele não há como confirmar a Compra.
3. **Varre** os 12 slots e monta as Listagens.
4. **Decide** pelos Preços-alvo do `config.toml`. Nenhuma comprável sai limpo, sem clicar.
5. **Clica** no centro da Listagem escolhida, após uma pausa aleatória entre 200 e 600 ms.
   Numa execução única isso quase não importa; o valor está em o código nascer com o hábito,
   já que o loop da #6 herda esse ritmo e é lá que timing metronômico destoaria.
6. **Espera a Janela de Confirmação ser detectada** — pergunta a cada 100 ms, desiste em 10 s.
   Não abriu, aborta sem apertar nada.
7. **Confere quatro coisas dentro da Janela:** o ícone bate com o Item-alvo decidido; o Preço
   Unitário bate com o lido na Listagem; a Quantidade é exatamente 1; e o Preço Total fecha
   com 1 × Preço Unitário. **Leitura ilegível é divergência**, não caso a tratar. Qualquer
   divergência → **Esc**, salva o print, aborta.
8. **Espaço.**
9. **Confirma pelo Ouro.** Espera 2 s e então enquete por até 5 s, **até a queda bater com o
   Preço Total** — guardando sempre a última leitura legível. Como a Janela mostra o Preço
   Total, a conferência é exata: o Ouro deve cair **exatamente** esse valor, não apenas
   "diminuir". Parar na primeira leitura legível não serve: o Ouro quase sempre é legível, e
   ler antes de o jogo debitar reportaria Compra com queda zero.
10. **Relatório e sai.**

`--simular` executa 1 a 4 e o relatório, sem tocar em mouse ou teclado. O desfecho dele é
`simulou`, e não `nada_compravel`: uma simulação bem-sucedida achou uma Listagem, e o roteiro
usa `nada_compravel` como portão de "pare aqui".

### Saídas de erro

| Situação | Ação |
|----------|------|
| Resolução ≠ 2560×1440 | Aborta antes de tudo |
| Estado ≠ `LISTA` no pré-voo | Aborta, salva print |
| Ouro inicial ilegível | Aborta |
| Nenhuma Listagem comprável | Sai limpo, sem clicar — não é erro |
| Clique não abriu a Janela | Aborta **sem apertar nada** |
| Ícone na Janela ≠ item decidido, ou irreconhecível | **Esc**, salva, aborta |
| Preço na Janela ≠ preço da Listagem, ou ilegível | **Esc**, salva, aborta |
| Quantidade ≠ 1, ou ilegível | **Esc**, salva, aborta |
| Preço Total ilegível, ou ≠ 1 × Preço Unitário | **Esc**, salva, aborta |
| Ouro final ilegível | Reporta **indeterminado** — não afirma nada |
| **Ouro não se moveu** | Desfecho próprio `ouro_nao_caiu` — não é Compra |
| Ouro caiu ≠ Preço Total, mas se moveu | Reporta divergência com os dois números |

Código de saída: `0` correu como esperado (comprou, simulou, ou nada havia comprável), `1`
abortou por segurança, `2` problema de ambiente, `3` apertou Espaço e o Ouro **não se moveu**.

O `3` existe porque `0` deixaria "o Espaço não registrou" indistinguível de uma Compra
confirmada — e essa é a primeira pergunta que a execução no Windows existe para responder.

**Sem tecla de pânico.** Numa execução de uma Compra, com contagem regressiva e dez saídas
automáticas, ela é complexidade sem retorno. Entra na #8, junto com o loop.

## Arquitetura

### A fronteira de IO

Em `src/mistfall/perifericos/` — o nome evita colisão com o módulo `io` da stdlib.

```python
class Tela(Protocol):
    def capturar(self) -> np.ndarray: ...

class Mao(Protocol):
    def clicar(self, x: int, y: int) -> None: ...
    def apertar_espaco(self) -> None: ...
    def apertar_esc(self) -> None: ...
```

`apertar_esc` é caminho de execução, não detalhe: é como o passo 7 desfaz o que começou.

**Duas implementações.** `perifericos/windows.py` usa `mss` para captura e `ctypes` puro para
input. `perifericos/falso.py` traz `TelaFalsa`, que serve uma sequência roteirizada de PNGs, e
`MaoFalsa`, que grava o que lhe pediram.

**O input vai por `SendInput` com `KEYEVENTF_SCANCODE`, não com virtual-key.** Jogos costumam
ler scancode de hardware e ignorar evento de tecla virtual — é a razão clássica de um script
funcionar no Bloco de Notas e não no jogo. Espaço é `0x39`, Esc é `0x01`. É provavelmente o
que o Mini Mouse Macro faz, e o que explica ele ter funcionado.

### Visão dentro do modal

`src/mistfall/janela.py`, módulo novo: `ler_item_da_janela`, `ler_preco_da_janela`,
`ler_quantidade_da_janela`. É visão pura — imagem → dado — e não vai em `perifericos`.

Regiões já medidas contra `images/janela.png`, com o mesmo pipeline de OCR do resto
(cinza → 4× `INTER_CUBIC` → Otsu → `--psm 7` com whitelist de dígitos):

| Campo | Região | Lido |
|-------|--------|------|
| Preço Unitário | `(1500, 628, 1900, 674)` | 237 |
| Quantidade | `(1500, 730, 1900, 776)` | 1 |
| Preço Total | `(1500, 826, 1900, 872)` | 237 |
| Ícone do item | `(1390, 448, 1518, 564)` | 116×128 |

O recorte do ícone tem **exatamente as dimensões da região de busca da lista**, então os sete
templates existentes servem sem adaptação. Em `janela.png` o modal mostra Espelho Adornado,
que não é Item-alvo, e o melhor match fica em **0,365** — bem abaixo do limiar de 0,70.

**Limitação conhecida:** é uma amostra só, e negativa. Não existe print de modal com Item-alvo
dentro, então o casamento de ícone não pode ser provado no sentido positivo antes da execução
no Windows. Essa execução gera o print que falta.

**Varredura de escala.** Ninguém confirmou que o modal desenha o ícone no mesmo tamanho da
lista, de onde os templates saíram, e o casamento não perdoa: medido sobre um Dragão real,
1,000× dá 0,9358 e identifica, 0,950× cai para 0,7818 e devolve `None`. Por isso
`ler_item_da_janela` tenta sete escalas (0,85× a 1,15×) e decide pela melhor delas.

A varredura vive em `janela.py` e **não** em `itens.identificar_item`, que é compartilhado com
a detecção da lista — validada em 84/84 slots e sem dúvida de escala nenhuma. Ela não afrouxa
o único negativo real: em `janela.png` o Espelho Adornado fica em 0,4047 com margem 0,0027 na
melhor das sete escalas, longe dos limiares de 0,70 e 0,25.

Os sete scores e a escala vencedora vão para o `relatorio.json`, em todos os desfechos: abortar
por ícone é o desfecho mais provável da primeira execução, e sem esses números o operador volta
só com "o modal mostra None".

### O orquestrador

`src/mistfall/piloto.py`:

```python
def executar(tela: Tela, mao: Mao, config: Config,
             pasta: Path, simular: bool = False) -> Resultado
```

Não sabe se fala com o Windows ou com um dublê. O registro é parâmetro, não global: `pasta`
recebe os PNGs numerados e um JSON por captura com o que o bot leu. Nos testes é `tmp_path`;
no Windows é a pasta que volta para diagnóstico.

`perifericos/windows.py` é o **único** arquivo do projeto que não roda no macOS, e não tem
lógica nenhuma — só traduz chamada em syscall. Toda decisão vive em código testável no Mac.

## Testes

**`janela.py` contra `janela.png`:** Preço Unitário 237, Quantidade 1, Preço Total 237, ícone
não casa com nenhum Item-alvo.

**`piloto.executar` contra os dublês**, com a `TelaFalsa` roteirizada:

- caminho feliz — clica, Janela abre, confere, Espaço, Ouro cai pelo valor exato
- **preço na Janela diverge → `MaoFalsa` registra Esc e nunca Espaço**
- **ícone na Janela diverge → idem**
- **Quantidade ≠ 1 → idem**
- clique não abriu a Janela → aborta sem registrar tecla nenhuma
- nada comprável → sai limpo, `MaoFalsa` vazia
- pré-voo com estado errado → aborta
- `--simular` → `MaoFalsa` completamente vazia

Os três em negrito são o coração da suíte: vermelho ali significa bot apertando Espaço quando
não devia.

**Fixtures.** Para o caminho feliz é preciso um frame "depois" com o Ouro exatamente
`inicial − preço total`, e não existe print assim. Esse frame será **sintetizado**, colando o
número esperado na região do Ouro de um print real, e o teste dirá isso explicitamente. O caso
"Ouro caiu por valor inesperado" usa dois prints reais (65234 → 64735).

**Não testável no Mac:** `perifericos/windows.py`. Só é exercitado na máquina Windows — razão
pela qual ele não tem lógica.

## Montagem no Windows

Com nada instalado: Python, o binário do **tesseract**, o repositório, e um `pip install` de
opencv, numpy, pillow, pytesseract e `mss`.

Isso torna a issue [#14](https://github.com/lavarini/mistfall-reseller/issues/14) —
`pip install -e .` — **pré-requisito de fato**. Sem ela, sobra briga com `PYTHONPATH` na
máquina onde menos se quer isso.

## O que a execução tem de devolver

O produto real desta issue não é o código, é a evidência:

1. **Funcionou?** Clique abriu a Janela; Espaço acionou Comprar; Ouro caiu pelo valor certo.
2. **O tempo da Janela de Confirmação, medido** — não estimado. É o número que a #6 precisa e
   que hoje ninguém tem. É um **teto**: o relógio começa antes do clique e só para depois de
   uma captura e de um `identificar_estado`, então inclui o custo de perguntar.
3. **Sem administrador, falha em silêncio?** Uma execução não-elevada. Se o clique for
   ignorado sem erro, confirma o diagnóstico de UIPI e vira nota no ADR-0001.
4. **A pasta de prints**, para diagnóstico remoto se algo der errado.
5. **Um print do modal com Item-alvo dentro** — hoje inexistente. Fecha a lacuna de evidência
   que nenhum trabalho no Mac consegue fechar, e vira fixture permanente.

## Mudanças em documentos existentes

- **Issue #9** — o corpo dela descreve o spike de coordenada chumbada, que foi descartado.
  Precisa ser reescrito para este desenho, e os critérios de aceitação trocados. Ainda não
  aplicado.
- **Issue #14** (`pip install -e .`) — deixa de ser dívida diferida e passa a bloquear a #9.
  A relação precisa ficar registrada no tracker.
- **ADR-0001** — ganha nota sobre o resultado da execução: qual método de captura e de
  injeção funcionou, e se a falha sem administrador é mesmo silenciosa (UIPI).

## Definições que o plano precisa fechar

- **`Resultado`** — o tipo que `executar` devolve. Precisa carregar, no mínimo: o desfecho
  (comprou / Ouro não caiu / nada comprável / simulou / abortado, com o motivo), o Ouro antes e
  depois, a Listagem escolhida, **tudo que foi lido dentro da Janela** (item, Preço Unitário,
  Quantidade, Preço Total, os sete scores do ícone e a escala vencedora), e o tempo medido
  entre o clique e a Janela aparecer. Ele é gravado em `relatorio.json` **sempre**, inclusive
  quando uma exceção inesperada sobe depois de o bot já ter clicado.

## Fora do escopo

- **Loop de Compra** e **Reset de Categoria** — #6 e #7, depois desta confirmada.
- **Tecla de pânico, piso de Ouro e log estruturado** — #8.
- **Tendência de Mercado** — o painel de Menor Preço / Preço Médio aparece na Janela e
  continua sem influenciar decisão nenhuma.
- **Comprar mais de uma unidade** — a Quantidade é conferida como 1 e nunca alterada.
