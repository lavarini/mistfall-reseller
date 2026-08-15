# Randomização dos Cliques da Venda — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sortear pontos seguros para clicar no Item-alvo e em "Listar para Venda", sem variar os demais cliques nem tocar no fluxo de Compra.

**Architecture:** A unidade de uma Venda recebe um `random.Random` injetável e usa uma função pura para sortear coordenadas inclusivas em dois retângulos seguros. O ciclo cria uma única instância por sessão e a repassa a todas as Vendas, preservando variação real e reprodutibilidade em testes.

**Tech Stack:** Python 3.14, `random.Random` da biblioteca padrão, pytest e os dublês `TelaFalsa`/`MaoFalsa`.

## Global Constraints

- Alterar somente o fluxo de Venda; nenhum arquivo ou comportamento da Compra entra no escopo.
- Randomizar somente o clique no stack do Item-alvo e no botão "Listar para Venda".
- Manter fixos os cliques nos Baús, no Preço de Venda e na Quantidade.
- O slot usa limites inclusivos `cx - 20 .. cx + 20` e `cy - 26 .. cy + 26`.
- O botão usa X `1500..1900` e Y `1010..1040`, ambos inclusivos.
- Não adicionar configuração, dependência, captura de tela ou randomização de tempo.
- Não persistir as coordenadas sorteadas no relatório.
- Não depender do estado global de `random`.
- Preservar as pastas locais não versionadas `sessao/` e `sessao-venda/`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade nesta mudança |
| --- | --- |
| `src/mistfall/venda.py` | Definir áreas seguras, sortear pontos e aplicá-los aos dois cliques da unidade de Venda. |
| `tests/test_venda.py` | Provar limites, diversidade, reprodução por semente, isolamento do `random` global e cliques fixos. |
| `src/mistfall/ciclo_venda.py` | Criar/repassar uma única fonte de aleatoriedade por sessão. |
| `tests/test_ciclo_venda.py` | Provar que todas as Vendas recebem a mesma instância e que Baús continuam fixos. |
| `README.md` | Explicar brevemente quais cliques da Venda variam e quais permanecem fixos. |

### Task 1: Sortear os dois cliques seguros de uma Venda

**Files:**
- Modify: `src/mistfall/venda.py`
- Modify: `tests/test_venda.py`

**Interfaces:**
- Consumes: `centro_slot_armazem(slot: SlotArmazem) -> tuple[int, int]` e `random.Random.randint(a, b)`.
- Produces: `_sortear_ponto(area: tuple[int, int, int, int], sorteio: random.Random) -> tuple[int, int]`.
- Produces: `executar_venda(..., ritmo: RitmoVenda = RITMO_VENDA_PADRAO, sorteio: random.Random | None = None) -> ResultadoVenda`.
- Produces: constantes `MEIA_LARGURA_CLIQUE_SLOT = 20`, `MEIA_ALTURA_CLIQUE_SLOT = 26` e `AREA_SEGURA_BOTAO_LISTAR = (1500, 1010, 1900, 1040)`.

- [ ] **Step 1: Escrever testes vermelhos para os limites e para os cliques que ficam fixos**

Em `tests/test_venda.py`, importar `random`, trocar asserções de centros exatos nos dois cliques variáveis por limites e manter igualdade exata para os inputs:

```python
import random

from mistfall.venda import AREA_SEGURA_BOTAO_LISTAR


def dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_executa_um_stack_com_cliques_dentro_das_areas_seguras(tmp_path):
    tela = TelaFalsa([STASH, MODAL, STASH])
    mao = MaoFalsa()
    resultado = executar_venda(
        tela, mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(), sorteio=random.Random(42),
    )

    cliques = [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]
    cx, cy = centro_slot_armazem(SLOT)
    assert dentro(cliques[0], (cx - 20, cy - 26, cx + 20, cy + 26))
    assert cliques[1:3] == [CENTRO_PRECO_VENDA, CENTRO_QUANTIDADE_VENDA]
    assert dentro(cliques[3], AREA_SEGURA_BOTAO_LISTAR)
    assert resultado.desfecho is DesfechoVenda.VENDEU
```

Atualizar também os cenários de aborto: quando a Janela não abre, afirmar que existe um único clique e que ele está na área segura do slot; quando não fecha, contar exatamente um clique pertencente a `AREA_SEGURA_BOTAO_LISTAR`, sem exigir o centro antigo.

- [ ] **Step 2: Rodar o teste e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_venda.py -q
```

Expected: FAIL porque `AREA_SEGURA_BOTAO_LISTAR` e o parâmetro `sorteio` ainda não existem e os cliques continuam nos centros fixos.

- [ ] **Step 3: Implementar o sorteio mínimo e aplicá-lo aos dois cliques**

Em `src/mistfall/venda.py`:

```python
import random

MEIA_LARGURA_CLIQUE_SLOT = 20
MEIA_ALTURA_CLIQUE_SLOT = 26
AREA_SEGURA_BOTAO_LISTAR = (1500, 1010, 1900, 1040)


def _sortear_ponto(
    area: tuple[int, int, int, int], sorteio: random.Random,
) -> tuple[int, int]:
    x0, y0, x1, y1 = area
    return sorteio.randint(x0, x1), sorteio.randint(y0, y1)
```

Remover `CENTRO_BOTAO_LISTAR`, que deixa de ter consumidor, e substituir sua importação nos
testes por `AREA_SEGURA_BOTAO_LISTAR`.

Acrescentar `sorteio` ao fim da assinatura de `executar_venda`. No começo da função, depois das validações e antes de qualquer sorteio:

```python
if sorteio is None:
    sorteio = random.Random()
```

Substituir somente os dois cliques variáveis:

```python
cx, cy = centro_slot_armazem(slot)
area_slot = (
    cx - MEIA_LARGURA_CLIQUE_SLOT,
    cy - MEIA_ALTURA_CLIQUE_SLOT,
    cx + MEIA_LARGURA_CLIQUE_SLOT,
    cy + MEIA_ALTURA_CLIQUE_SLOT,
)
mao.clicar(*_sortear_ponto(area_slot, sorteio))
```

```python
mao.clicar(*_sortear_ponto(AREA_SEGURA_BOTAO_LISTAR, sorteio))
```

Não alterar os cliques em `CENTRO_PRECO_VENDA` e `CENTRO_QUANTIDADE_VENDA`.

- [ ] **Step 4: Rodar os testes da unidade de Venda**

Run:

```bash
.venv/bin/python -m pytest tests/test_venda.py -q
```

Expected: PASS.

- [ ] **Step 5: Acrescentar testes de diversidade, reprodução e isolamento do estado global**

Adicionar helpers que executem uma Venda com uma semente e devolvam apenas os quatro cliques. Cobrir:

```python
def cliques_com_semente(tmp_path, semente):
    mao = MaoFalsa()
    executar_venda(
        TelaFalsa([STASH, MODAL, STASH]), mao, SLOT, 226,
        tmp_path / str(semente), ritmo=RitmoVenda.instantaneo(),
        sorteio=random.Random(semente),
    )
    return [acao[1:] for acao in mao.acoes if acao[0] == "clicar"]


def test_sementes_variadas_produzem_mais_de_um_ponto(tmp_path):
    sequencias = [cliques_com_semente(tmp_path, s) for s in range(10)]
    assert len({seq[0] for seq in sequencias}) > 1
    assert len({seq[3] for seq in sequencias}) > 1


def test_mesma_semente_reproduz_os_cliques(tmp_path):
    assert cliques_com_semente(tmp_path, 91) == cliques_com_semente(tmp_path, 91)


def test_sorteio_injetado_independe_do_random_global(tmp_path):
    random.seed(1)
    primeira = cliques_com_semente(tmp_path, 73)
    random.seed(999)
    segunda = cliques_com_semente(tmp_path, 73)
    assert primeira == segunda
```

- [ ] **Step 6: Rodar novamente os testes da unidade**

Run:

```bash
.venv/bin/python -m pytest tests/test_venda.py -q
```

Expected: PASS.

- [ ] **Step 7: Commitar a unidade de Venda**

```bash
git add src/mistfall/venda.py tests/test_venda.py
git commit -m "Randomiza cliques seguros da Venda"
```

### Task 2: Compartilhar o gerador pela sessão sem variar outros cliques

**Files:**
- Modify: `src/mistfall/ciclo_venda.py`
- Modify: `tests/test_ciclo_venda.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `executar_venda(..., sorteio: random.Random | None = None) -> ResultadoVenda` da Task 1.
- Produces: `executar_ciclo_venda(..., ritmo: RitmoVenda = RITMO_VENDA_PADRAO, sorteio: random.Random | None = None) -> SessaoVenda`.
- Preserva: `centro_bau(bau) -> tuple[int, int]` e todos os cliques de Baú exatos.

- [ ] **Step 1: Escrever teste vermelho para uma única instância em toda a sessão**

Em `tests/test_ciclo_venda.py`, importar `random`. No teste que vende dois candidatos, criar uma instância e fazer o dublê receber o novo argumento:

```python
sorteio = random.Random(42)
sorteios_recebidos = []


def vender(tela, mao, slot, preco, pasta, ritmo, recebido):
    vendidos.append(slot)
    sorteios_recebidos.append(recebido)
    return sucesso(slot)


monkeypatch.setattr("mistfall.ciclo_venda.executar_venda", vender)
sessao = executar_ciclo_venda(
    TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
    InterruptorFalso(), RitmoVenda.instantaneo(), sorteio=sorteio,
)
assert sorteios_recebidos == [sorteio, sorteio]
```

Manter `test_avanca_somente_um_bau_a_direita` inalterado: sua asserção exata em `(1851, 286)` e `(1915, 286)` é a prova de que Baús não foram randomizados.

- [ ] **Step 2: Rodar o teste e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo_venda.py::test_processa_o_bau_uma_vez_e_vende_todos_os_stacks_tres -q
```

Expected: FAIL porque `executar_ciclo_venda` ainda não aceita nem repassa `sorteio`.

- [ ] **Step 3: Criar e repassar o gerador da sessão**

Em `src/mistfall/ciclo_venda.py`, importar `random`, acrescentar `sorteio` ao fim da assinatura e inicializá-lo uma única vez antes de `interruptor.esperar_inicio()`:

```python
if sorteio is None:
    sorteio = random.Random()
```

Passar a instância como último argumento de cada `executar_venda`:

```python
resultado = executar_venda(
    tela,
    mao,
    slot,
    config.precos_venda[slot.item],
    pasta / f"venda-{sessao.vendas + 1:04d}",
    ritmo,
    sorteio,
)
```

Adaptar somente os dublês com assinatura posicional explícita em `tests/test_ciclo_venda.py`; os dublês `*args, **kwargs` não precisam mudar.

- [ ] **Step 4: Rodar os testes do ciclo e da CLI**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo_venda.py tests/test_venda_cli.py -q
```

Expected: PASS. A CLI continua usando o padrão não determinístico sem receber nova opção.

- [ ] **Step 5: Documentar o comportamento operacional**

No trecho da Venda em `README.md`, acrescentar:

```markdown
Para evitar repetir exatamente o mesmo movimento, o clique no stack e o clique em
"Listar para Venda" variam dentro de áreas centrais seguras. Baús e campos de input
continuam com coordenadas fixas.
```

Não adicionar opção de configuração ou mencionar mudança na Compra.

- [ ] **Step 6: Rodar verificação completa**

Run:

```bash
.venv/bin/python -m pytest -q
git diff --check
```

Expected: todos os testes passam e `git diff --check` não produz saída.

- [ ] **Step 7: Revisar o diff contra o escopo**

Run:

```bash
git status --short
git diff --stat
git diff -- src/mistfall/venda.py src/mistfall/ciclo_venda.py tests/test_venda.py tests/test_ciclo_venda.py README.md
```

Confirmar que nenhum módulo da Compra foi alterado e que `sessao/`/`sessao-venda/` seguem não versionadas.

- [ ] **Step 8: Commitar integração e documentação**

```bash
git add src/mistfall/ciclo_venda.py tests/test_ciclo_venda.py README.md
git commit -m "Compartilha sorteio na sessao de Venda"
```
