# Randomização de Todos os Cliques da Compra — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sortear pontos seguros para todos os cliques do fluxo de Compra sem alterar decisões, esperas, capturas, telemetria ou o fluxo de Venda.

**Architecture:** Um novo módulo puro `mistfall.cliques` sorteia pontos inclusivos usando um `random.Random` recebido. `mistfall.geometria` conhece os centros e constrói as áreas seguras; piloto e Reset apenas pedem um ponto e clicam. O ciclo cria uma única fonte de aleatoriedade por sessão e a compartilha com todas as Voltas e Resets.

**Tech Stack:** Python 3.14, `random.Random` da biblioteca padrão, pytest e os dublês `TelaFalsa`, `MaoFalsa` e `InterruptorFalso`.

## Global Constraints

- Randomizar todos e somente estes cliques da Compra: Listagem escolhida, Categoria alternativa do Reset e retorno para Material de Construção.
- A Listagem usa limites inclusivos `cx - 20 .. cx + 20` e `cy - 26 .. cy + 26`.
- Cada Categoria usa limites inclusivos `cx - 60 .. cx + 60` e `cy - 18 .. cy + 18`.
- Criar exatamente um `random.Random()` por sessão quando nenhum gerador for injetado.
- Repassar a mesma instância ao piloto e ao Reset em todas as Voltas.
- Chamadas standalone do piloto e do Reset criam uma instância local quando `sorteio=None`.
- O modo simulado não sorteia coordenada de clique.
- Preservar a alternância determinística Forja/Chave e todas as esperas, capturas, conferências, teclas e guardas existentes.
- Não adicionar configuração, opção de CLI, dependência ou persistência de coordenadas.
- Não alterar código, assinaturas ou testes do fluxo de Venda.
- Não usar o estado global de `random`.
- Preservar as pastas locais não versionadas `sessao/` e `sessao-venda/`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade nesta mudança |
| --- | --- |
| `src/mistfall/cliques.py` | Validar uma área e sortear um ponto inclusivo com o gerador recebido. |
| `tests/test_cliques.py` | Provar limites inclusivos, ordem das chamadas e rejeição de áreas invertidas. |
| `src/mistfall/geometria.py` | Construir as áreas seguras da Listagem e das Categorias a partir dos centros existentes. |
| `tests/test_geometria.py` | Provar os limites exatos das áreas sem envolver mouse ou aleatoriedade. |
| `src/mistfall/piloto.py` | Sortear o clique da Listagem imediatamente antes de uma Compra real. |
| `tests/test_piloto.py` | Provar área segura, diversidade, reprodução, isolamento global e modo simulado. |
| `src/mistfall/reset.py` | Sortear os dois cliques de Categoria de cada Reset. |
| `tests/test_reset.py` | Provar áreas, sequência, reprodução, falhas e uso do mesmo gerador. |
| `src/mistfall/ciclo.py` | Criar e compartilhar uma única instância de `Random` pela sessão. |
| `tests/test_ciclo.py` | Provar compartilhamento por Voltas/Resets e preservar a alternância. |
| `README.md` | Documentar quais cliques da Compra variam e o que continua inalterado. |

### Task 1: Criar o sorteio puro e as áreas seguras

**Files:**
- Create: `src/mistfall/cliques.py`
- Create: `tests/test_cliques.py`
- Modify: `src/mistfall/geometria.py`
- Modify: `tests/test_geometria.py`

**Interfaces:**
- Produces: `AreaClique = tuple[int, int, int, int]`.
- Produces: `sortear_ponto(area: AreaClique, sorteio: random.Random) -> tuple[int, int]`.
- Produces: `area_clique_slot(linha: int, coluna: int) -> AreaClique`.
- Produces: `area_clique_categoria(centro: tuple[int, int]) -> AreaClique`.
- Produces: `MEIA_LARGURA_CLIQUE_SLOT = 20`, `MEIA_ALTURA_CLIQUE_SLOT = 26`, `MEIA_LARGURA_CLIQUE_CATEGORIA = 60` e `MEIA_ALTURA_CLIQUE_CATEGORIA = 18`.

- [ ] **Step 1: Escrever testes vermelhos do helper puro**

Criar `tests/test_cliques.py`:

```python
import pytest

from mistfall.cliques import sortear_ponto


class SorteioControlado:
    def __init__(self, devolvidos):
        self.devolvidos = iter(devolvidos)
        self.chamadas = []

    def randint(self, minimo, maximo):
        self.chamadas.append((minimo, maximo))
        return next(self.devolvidos)


@pytest.mark.parametrize(
    "devolvidos, esperado",
    [([10, 20], (10, 20)), ([30, 40], (30, 40))],
)
def test_sorteia_x_e_y_com_os_quatro_limites_inclusivos(devolvidos, esperado):
    sorteio = SorteioControlado(devolvidos)
    assert sortear_ponto((10, 20, 30, 40), sorteio) == esperado
    assert sorteio.chamadas == [(10, 30), (20, 40)]


@pytest.mark.parametrize("area", [(2, 0, 1, 3), (0, 4, 3, 2)])
def test_rejeita_area_invertida(area):
    with pytest.raises(ValueError, match="area de clique invertida"):
        sortear_ponto(area, SorteioControlado([]))
```

- [ ] **Step 2: Rodar o teste e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_cliques.py -q
```

Expected: FAIL na coleta com `ModuleNotFoundError: No module named 'mistfall.cliques'`.

- [ ] **Step 3: Implementar o helper mínimo**

Criar `src/mistfall/cliques.py`:

```python
"""Sorteio puro de pontos dentro de areas seguras de clique."""

import random

AreaClique = tuple[int, int, int, int]


def sortear_ponto(
    area: AreaClique,
    sorteio: random.Random,
) -> tuple[int, int]:
    x0, y0, x1, y1 = area
    if x0 > x1 or y0 > y1:
        raise ValueError(f"area de clique invertida: {area}")
    return sorteio.randint(x0, x1), sorteio.randint(y0, y1)
```

- [ ] **Step 4: Rodar o teste do helper e confirmar que passa**

Run:

```bash
.venv/bin/python -m pytest tests/test_cliques.py -q
```

Expected: PASS.

- [ ] **Step 5: Escrever testes vermelhos para a geometria exata das áreas**

Acrescentar a `tests/test_geometria.py`:

```python
from mistfall.geometria import (
    CATEGORIA_CHAVE,
    CATEGORIA_MATERIAL_CONSTRUCAO,
    CATEGORIA_MATERIAL_FORJA,
    area_clique_categoria,
    area_clique_slot,
    caixa_slot,
)


def test_area_de_clique_do_slot_fica_ao_redor_do_centro():
    x0, y0, x1, y1 = caixa_slot(2, 1)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    assert area_clique_slot(2, 1) == (cx - 20, cy - 26, cx + 20, cy + 26)


@pytest.mark.parametrize(
    "centro",
    [CATEGORIA_MATERIAL_CONSTRUCAO, CATEGORIA_MATERIAL_FORJA, CATEGORIA_CHAVE],
)
def test_area_de_clique_da_categoria_fica_ao_redor_do_centro(centro):
    cx, cy = centro
    assert area_clique_categoria(centro) == (
        cx - 60, cy - 18, cx + 60, cy + 18,
    )
```

Se `pytest` ainda não estiver importado em `tests/test_geometria.py`, acrescentar `import pytest`.

- [ ] **Step 6: Rodar os testes de geometria e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_geometria.py -q
```

Expected: FAIL na coleta porque `area_clique_slot` e `area_clique_categoria` ainda não existem.

- [ ] **Step 7: Implementar os construtores de áreas**

Em `src/mistfall/geometria.py`, importar `AreaClique` e definir as margens junto às constantes de slot e Categoria:

```python
from mistfall.cliques import AreaClique

MEIA_LARGURA_CLIQUE_SLOT = 20
MEIA_ALTURA_CLIQUE_SLOT = 26
MEIA_LARGURA_CLIQUE_CATEGORIA = 60
MEIA_ALTURA_CLIQUE_CATEGORIA = 18
```

Depois de `caixa_slot`, acrescentar:

```python
def area_clique_slot(linha: int, coluna: int) -> AreaClique:
    x0, y0, x1, y1 = caixa_slot(linha, coluna)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    return (
        cx - MEIA_LARGURA_CLIQUE_SLOT,
        cy - MEIA_ALTURA_CLIQUE_SLOT,
        cx + MEIA_LARGURA_CLIQUE_SLOT,
        cy + MEIA_ALTURA_CLIQUE_SLOT,
    )


def area_clique_categoria(centro: tuple[int, int]) -> AreaClique:
    cx, cy = centro
    return (
        cx - MEIA_LARGURA_CLIQUE_CATEGORIA,
        cy - MEIA_ALTURA_CLIQUE_CATEGORIA,
        cx + MEIA_LARGURA_CLIQUE_CATEGORIA,
        cy + MEIA_ALTURA_CLIQUE_CATEGORIA,
    )
```

- [ ] **Step 8: Rodar os testes da infraestrutura de clique**

Run:

```bash
.venv/bin/python -m pytest tests/test_cliques.py tests/test_geometria.py -q
```

Expected: PASS.

- [ ] **Step 9: Commitar o helper e a geometria**

```bash
git add src/mistfall/cliques.py src/mistfall/geometria.py tests/test_cliques.py tests/test_geometria.py
git commit -m "Adiciona areas seguras de clique"
```

### Task 2: Randomizar o clique da Listagem escolhida

**Files:**
- Modify: `src/mistfall/piloto.py`
- Modify: `tests/test_piloto.py`

**Interfaces:**
- Consumes: `area_clique_slot(linha: int, coluna: int) -> AreaClique` da Task 1.
- Consumes: `sortear_ponto(area: AreaClique, sorteio: random.Random) -> tuple[int, int]` da Task 1.
- Preserva: `executar(..., sorteio: random.Random | None = None, ...) -> Resultado`.

- [ ] **Step 1: Trocar a asserção de centro exato por uma área segura**

Em `tests/test_piloto.py`, importar `area_clique_slot` e substituir `test_caminho_feliz_clica_no_slot_certo` por:

```python
from mistfall.geometria import area_clique_slot


def _dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_caminho_feliz_clica_na_area_segura_do_slot_certo(tmp_path):
    mao = MaoFalsa()
    resultado = executar(
        roteiro_feliz(), mao, cfg(), tmp_path,
        ritmo=JA, sorteio=random.Random(1),
    )
    ponto = mao.acoes[0][1:]
    assert _dentro(
        ponto,
        area_clique_slot(resultado.listagem.linha, resultado.listagem.coluna),
    )
```

- [ ] **Step 2: Acrescentar testes vermelhos para variação, reprodução e modo simulado**

Ainda em `tests/test_piloto.py`:

```python
def _clique_com_semente(tmp_path, semente):
    mao = MaoFalsa()
    executar(
        roteiro_feliz(), mao, cfg(), tmp_path / str(semente),
        ritmo=JA, sorteio=random.Random(semente),
    )
    return mao.acoes[0][1:]


def test_sementes_variadas_produzem_mais_de_um_ponto_de_listagem(tmp_path):
    pontos = {_clique_com_semente(tmp_path, s) for s in range(10)}
    assert len(pontos) > 1


def test_mesma_semente_reproduz_o_clique_da_listagem(tmp_path):
    assert _clique_com_semente(tmp_path / "a", 91) == _clique_com_semente(
        tmp_path / "b", 91,
    )


def test_clique_injetado_independe_do_random_global(tmp_path):
    random.seed(1)
    primeiro = _clique_com_semente(tmp_path / "a", 73)
    random.seed(999)
    segundo = _clique_com_semente(tmp_path / "b", 73)
    assert primeiro == segundo


def test_modo_simulado_nao_sorteia_coordenada(tmp_path, monkeypatch):
    def falhar(*_args):
        raise AssertionError("nao deveria sortear clique simulado")

    monkeypatch.setattr("mistfall.piloto.sortear_ponto", falhar)
    resultado = executar(
        roteiro_feliz(), MaoFalsa(), cfg(), tmp_path,
        simular=True, ritmo=JA, sorteio=random.Random(1),
    )
    assert resultado.desfecho is Desfecho.SIMULOU
```

- [ ] **Step 3: Rodar os testes focados e confirmar as falhas**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py -q
```

Expected: FAIL porque o clique continua no centro e `mistfall.piloto.sortear_ponto` ainda não existe.

- [ ] **Step 4: Aplicar o sorteio somente ao clique real da Listagem**

Em `src/mistfall/piloto.py`, substituir a importação de `caixa_slot` e importar o helper:

```python
from mistfall.cliques import sortear_ponto
from mistfall.geometria import area_clique_slot
```

Remover o cálculo de `x0, y0, x1, y1`. Manter a pausa exatamente onde está e substituir somente o clique:

```python
inicio = time.monotonic()
mao.clicar(*sortear_ponto(
    area_clique_slot(escolhida.linha, escolhida.coluna), sorteio,
))
r.tempos["clique"] = (time.monotonic() - inicio) * 1000
```

Não mover esse bloco para antes do retorno de `simular`; isso garante que a simulação não sorteie coordenadas.

- [ ] **Step 5: Rodar os testes do piloto**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py -q
```

Expected: PASS, inclusive os testes preexistentes de decisão, esperas, ações e telemetria.

- [ ] **Step 6: Commitar o clique da Listagem**

```bash
git add src/mistfall/piloto.py tests/test_piloto.py
git commit -m "Randomiza clique da Listagem na Compra"
```

### Task 3: Randomizar os dois cliques do Reset

**Files:**
- Modify: `src/mistfall/reset.py`
- Modify: `tests/test_reset.py`

**Interfaces:**
- Consumes: `area_clique_categoria(centro: tuple[int, int]) -> AreaClique` da Task 1.
- Consumes: `sortear_ponto(area: AreaClique, sorteio: random.Random) -> tuple[int, int]` da Task 1.
- Produces: `resetar_categoria(..., categoria_alternativa: CategoriaAlternativa = CategoriaAlternativa.FORJA, sorteio: random.Random | None = None) -> bool`.

- [ ] **Step 1: Adaptar os testes de Forja e Chave para as áreas seguras**

Em `tests/test_reset.py`, importar `random` e `area_clique_categoria`. Trocar as asserções de coordenadas exatas por:

```python
import random

from mistfall.geometria import area_clique_categoria


def _dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_reset_clica_forja_e_depois_material_em_areas_seguras():
    mao = MaoFalsa()
    assert resetar_categoria(
        TelaFalsa([FORJA, LISTA]), mao, JA, sorteio=random.Random(1),
    ) is True
    assert len(mao.acoes) == 2
    assert _dentro(mao.acoes[0][1:], area_clique_categoria(CATEGORIA_MATERIAL_FORJA))
    assert _dentro(
        mao.acoes[1][1:], area_clique_categoria(CATEGORIA_MATERIAL_CONSTRUCAO),
    )


def test_reset_pode_usar_chave_como_categoria_alternativa():
    mao = MaoFalsa()
    assert resetar_categoria(
        TelaFalsa(["images/reset-chave.png", LISTA]),
        mao,
        JA,
        categoria_alternativa=CategoriaAlternativa.CHAVE,
        sorteio=random.Random(1),
    ) is True
    assert len(mao.acoes) == 2
    assert _dentro(mao.acoes[0][1:], area_clique_categoria(CATEGORIA_CHAVE))
    assert _dentro(
        mao.acoes[1][1:], area_clique_categoria(CATEGORIA_MATERIAL_CONSTRUCAO),
    )
```

- [ ] **Step 2: Acrescentar testes vermelhos da sequência e do gerador**

Ainda em `tests/test_reset.py`:

```python
class SorteioEspiao(random.Random):
    def __init__(self, semente):
        super().__init__(semente)
        self.chamadas = []

    def randint(self, minimo, maximo):
        self.chamadas.append((minimo, maximo))
        return super().randint(minimo, maximo)


def _cliques_do_reset(semente):
    mao = MaoFalsa()
    resetar_categoria(
        TelaFalsa([FORJA, LISTA]), mao, JA,
        sorteio=random.Random(semente),
    )
    return [acao[1:] for acao in mao.acoes]


def test_os_dois_cliques_usam_a_mesma_instancia_injetada():
    sorteio = SorteioEspiao(42)
    resetar_categoria(TelaFalsa([FORJA, LISTA]), MaoFalsa(), JA, sorteio=sorteio)
    assert sorteio.chamadas == [
        (160, 280), (759, 795),
        (160, 280), (687, 723),
    ]


def test_sementes_variadas_produzem_sequencias_diferentes_no_reset():
    sequencias = {tuple(_cliques_do_reset(s)) for s in range(10)}
    assert len(sequencias) > 1


def test_mesma_semente_reproduz_os_dois_cliques_do_reset():
    assert _cliques_do_reset(91) == _cliques_do_reset(91)


def test_reset_injetado_independe_do_random_global():
    random.seed(1)
    primeiro = _cliques_do_reset(73)
    random.seed(999)
    segundo = _cliques_do_reset(73)
    assert primeiro == segundo
```

Manter o teste parametrizado de falha e acrescentar `mao = MaoFalsa()` nele, afirmando `len(mao.acoes) == 2`. Isso prova que o retorno a Material de Construção continua sendo tentado mesmo quando a primeira transição falha.

- [ ] **Step 3: Rodar os testes e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_reset.py -q
```

Expected: FAIL porque `resetar_categoria` ainda não aceita `sorteio` e ainda clica nos centros.

- [ ] **Step 4: Injetar o gerador e sortear os dois pontos**

Em `src/mistfall/reset.py`, importar `random`, `sortear_ponto` e `area_clique_categoria`:

```python
import random

from mistfall.cliques import sortear_ponto
from mistfall.geometria import area_clique_categoria
```

Acrescentar o argumento ao final da assinatura para preservar chamadas posicionais existentes:

```python
sorteio: random.Random | None = None,
```

No começo da função:

```python
if sorteio is None:
    sorteio = random.Random()
```

Substituir somente os dois cliques:

```python
mao.clicar(*sortear_ponto(
    area_clique_categoria(COORDENADA_POR_CATEGORIA[categoria_alternativa]),
    sorteio,
))
```

```python
mao.clicar(*sortear_ponto(
    area_clique_categoria(CATEGORIA_MATERIAL_CONSTRUCAO), sorteio,
))
```

Não alterar a ordem de cliques, capturas ou `time.sleep`, nem condicionar o segundo clique ao resultado da primeira captura.

- [ ] **Step 5: Rodar os testes do Reset**

Run:

```bash
.venv/bin/python -m pytest tests/test_reset.py -q
```

Expected: PASS.

- [ ] **Step 6: Commitar os cliques do Reset**

```bash
git add src/mistfall/reset.py tests/test_reset.py
git commit -m "Randomiza cliques de Categoria no Reset"
```

### Task 4: Compartilhar o gerador pela sessão e documentar

**Files:**
- Modify: `src/mistfall/ciclo.py`
- Modify: `tests/test_ciclo.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `executar(..., sorteio: random.Random | None = None, ...) -> Resultado`.
- Consumes: `resetar_categoria(..., sorteio: random.Random | None = None) -> bool` da Task 3.
- Preserva: `executar_ciclo(..., sorteio: random.Random | None = None) -> Sessao`.

- [ ] **Step 1: Fazer os dublês do ciclo registrarem o gerador recebido**

Em `tests/test_ciclo.py`, importar `random`. Estender `_PilotoFalso`:

```python
self.sorteios = []
```

No `__call__`, antes de devolver o resultado:

```python
self.sorteios.append(kwargs.get("sorteio"))
```

Estender `_ResetFalso`:

```python
self.sorteios = []
```

E aceitar/registrar o novo argumento:

```python
def __call__(
    self, tela, mao, ritmo=None, categoria_alternativa=None, sorteio=None,
) -> bool:
    self.categorias.append(categoria_alternativa)
    self.sorteios.append(sorteio)
    return self.funcionou
```

- [ ] **Step 2: Escrever teste vermelho para uma única instância por sessão**

Acrescentar a `tests/test_ciclo.py`:

```python
def test_compartilha_um_sorteio_com_todas_as_voltas_e_resets(monkeypatch, tmp_path):
    sorteio = random.Random(42)
    piloto = _PilotoFalso([
        Resultado(Desfecho.NADA_COMPRAVEL),
        Resultado(Desfecho.COMPRA_ENVIADA),
        Resultado(Desfecho.NADA_COMPRAVEL),
    ])
    reset = _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)

    executar_ciclo(
        tela=None,
        mao=None,
        config=None,
        pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=4),
        ritmo=Ritmo.instantaneo(),
        sorteio=sorteio,
    )

    assert piloto.sorteios == [sorteio, sorteio, sorteio]
    assert reset.sorteios == [sorteio, sorteio]
    assert reset.categorias == [CategoriaAlternativa.FORJA, CategoriaAlternativa.CHAVE]
```

- [ ] **Step 3: Escrever teste vermelho para a criação única quando omitido**

Acrescentar:

```python
def test_cria_um_unico_sorteio_quando_a_sessao_nao_recebe_um(monkeypatch, tmp_path):
    criados = []

    class RandomFalso(random.Random):
        def __init__(self):
            super().__init__(42)
            criados.append(self)

    piloto = _PilotoFalso([Resultado(Desfecho.NADA_COMPRAVEL)] * 2)
    reset = _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.random.Random", RandomFalso)
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)

    executar_ciclo(
        tela=None,
        mao=None,
        config=None,
        pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=3),
        ritmo=Ritmo.instantaneo(),
    )

    assert len(criados) == 1
    assert piloto.sorteios == [criados[0], criados[0]]
    assert reset.sorteios == [criados[0], criados[0]]
```

- [ ] **Step 4: Rodar os testes focados e confirmar as falhas**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo.py -q
```

Expected: FAIL porque o ciclo ainda repassa `None` ao piloto, não repassa gerador ao Reset e não cria uma instância própria.

- [ ] **Step 5: Criar e compartilhar o gerador no ciclo**

Em `src/mistfall/ciclo.py`, imediatamente no começo de `executar_ciclo`, antes de `interruptor.esperar_inicio()`:

```python
if sorteio is None:
    sorteio = random.Random()
```

Manter `sorteio=sorteio` na chamada de `executar` e acrescentá-lo por nome à chamada de Reset:

```python
if resetar_categoria(
    tela,
    mao,
    ritmo,
    categoria_alternativa=proxima_categoria,
    sorteio=sorteio,
):
```

- [ ] **Step 6: Rodar os testes integrados da Compra**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_cliques.py tests/test_geometria.py tests/test_piloto.py \
  tests/test_reset.py tests/test_ciclo.py -q
```

Expected: PASS.

- [ ] **Step 7: Documentar o comportamento operacional**

Em `README.md`, junto à explicação do fluxo de Compra, acrescentar:

```markdown
Os cliques da Compra não repetem uma coordenada fixa. A Listagem escolhida e as duas
Categorias usadas pelo Reset recebem pontos sorteados dentro de áreas centrais seguras.
Esse sorteio só muda o ponto dentro do mesmo alvo: não muda a Listagem escolhida, a
alternância Forja/Chave, as esperas ou as teclas Espaço/F2/F3.
```

Não documentar opção de configuração ou CLI, pois as margens são internas e fixas nesta etapa.

- [ ] **Step 8: Rodar a suíte completa e as verificações de diff**

Run:

```bash
.venv/bin/python -m pytest -q
git diff --check
git status --short
```

Expected: toda a suíte PASS; `git diff --check` sem saída; somente os arquivos desta mudança aparecem como modificados, além das pastas não versionadas `sessao/` e `sessao-venda/`.

- [ ] **Step 9: Commitar ciclo e documentação**

```bash
git add src/mistfall/ciclo.py tests/test_ciclo.py README.md
git commit -m "Compartilha sorteio pelos cliques da Compra"
```

- [ ] **Step 10: Verificar o estado final antes da integração**

Run:

```bash
.venv/bin/python -m pytest -q
git log -4 --oneline
git status --short
```

Expected: suíte completa PASS; quatro commits da implementação no topo; nenhuma alteração versionada pendente; `sessao/` e `sessao-venda/` continuam não versionadas e preservadas.
