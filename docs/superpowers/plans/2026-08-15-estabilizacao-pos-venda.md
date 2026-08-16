# Estabilização pós-venda Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Impedir que o cursor deixado sobre o botão `Listar` afete o painel direito e recuperar a aba Armazém sem perder a lista de candidatos do baú atual.

**Architecture:** A fronteira de mouse passa a expor movimento absoluto sem clique. A visão classifica o painel direito como Armazém, Inventário ou ilegível; a venda individual move o cursor a uma área neutra logo após confirmar e, se detectar Inventário, restaura Armazém antes de retornar sucesso. O ciclo permanece dono da lista em cache e continua no próximo candidato sem revarrer.

**Tech Stack:** Python 3.11+, pytest, OpenCV, NumPy, ctypes/SendInput confinado a `src/mistfall/perifericos/windows.py`.

## Global Constraints

- Resolução suportada: 2560x1440.
- Ponto neutro fixo: `(1620, 1100)`; mover sem clicar.
- Nunca enviar `Esc` durante a recuperação.
- No máximo um clique de recuperação em `Armazém` por venda.
- Não avançar baú nem chamar `varrer_armazem` durante a recuperação.
- Preservar preços, quantidade fixa `3` e randomização existente dos cliques.
- As pastas `sessao-venda*` permanecem fora dos commits.

---

### Task 1: Movimento de mouse sem clique

**Files:**
- Modify: `src/mistfall/perifericos/protocolos.py`
- Modify: `src/mistfall/perifericos/falso.py`
- Modify: `src/mistfall/perifericos/windows.py`
- Test: `tests/test_perifericos_falso.py`
- Test: `tests/test_perifericos_windows.py`

**Interfaces:**
- Consumes: coordenadas de tela `x: int`, `y: int` em 2560x1440.
- Produces: `Mao.mover(x: int, y: int) -> None`, implementado por `MaoFalsa` e `MaoWindows`.

- [ ] **Step 1: Escrever testes falhos para o dublê e o contrato Windows**

Em `tests/test_perifericos_falso.py`, estender o teste da ordem:

```python
def test_mao_falsa_grava_na_ordem():
    mao = MaoFalsa()
    mao.mover(30, 40)
    mao.clicar(10, 20)
    mao.apertar_espaco()
    mao.apertar_esc()
    assert mao.acoes == [
        ("mover", 30, 40),
        ("clicar", 10, 20),
        ("apertar_espaco",),
        ("apertar_esc",),
    ]
```

Em `tests/test_perifericos_windows.py`, incluir `mover` na asserção dos métodos e adicionar:

```python
def test_mover_emite_somente_movimento_absoluto(monkeypatch):
    chamadas = []
    monkeypatch.setattr(windows, "_enviar", lambda *entradas: chamadas.append(entradas))

    windows.MaoWindows().mover(2559, 1439)

    assert len(chamadas) == 1
    (evento,) = chamadas[0]
    assert evento.uniao.mi.dwFlags == 0x8001
    assert (evento.uniao.mi.dx, evento.uniao.mi.dy) == (65535, 65535)
```

- [ ] **Step 2: Executar os testes e confirmar a falha**

Run: `.venv/bin/pytest tests/test_perifericos_falso.py::test_mao_falsa_grava_na_ordem tests/test_perifericos_windows.py::test_windows_implementa_os_protocolos tests/test_perifericos_windows.py::test_mover_emite_somente_movimento_absoluto -v`

Expected: FAIL porque `MaoFalsa` e `MaoWindows` ainda não expõem `mover`.

- [ ] **Step 3: Implementar o movimento mínimo e reutilizá-lo no clique**

Adicionar ao protocolo:

```python
class Mao(Protocol):
    def mover(self, x: int, y: int) -> None: ...

    def clicar(self, x: int, y: int) -> None: ...
```

Adicionar ao dublê:

```python
def mover(self, x: int, y: int) -> None:
    self.acoes.append(("mover", x, y))
```

Em `MaoWindows`, centralizar a conversão no novo método e manter as esperas do clique:

```python
def mover(self, x: int, y: int) -> None:
    nx = x * 65535 // (LARGURA - 1)
    ny = y * 65535 // (ALTURA - 1)
    _enviar(_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny))

def clicar(self, x: int, y: int) -> None:
    self.mover(x, y)
    time.sleep(self._pausa_apos_mover)
    _enviar(_mouse(MOUSEEVENTF_LEFTDOWN))
    time.sleep(self._segundos_de_clique)
    _enviar(_mouse(MOUSEEVENTF_LEFTUP))
```

- [ ] **Step 4: Executar testes focados e a suíte dos periféricos**

Run: `.venv/bin/pytest tests/test_perifericos_falso.py tests/test_perifericos_windows.py -v`

Expected: PASS; o teste preexistente do clique ainda observa MOVE, LEFTDOWN e LEFTUP em três envios.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/perifericos/protocolos.py src/mistfall/perifericos/falso.py src/mistfall/perifericos/windows.py tests/test_perifericos_falso.py tests/test_perifericos_windows.py
git commit -m "Adiciona movimento neutro do mouse"
```

---

### Task 2: Estado selecionado do painel de itens

**Files:**
- Modify: `src/mistfall/venda_visao.py`
- Test: `tests/test_venda_visao.py`

**Interfaces:**
- Consumes: frame BGR 2560x1440.
- Produces: `PainelItens` com membros `INVENTARIO` e `ARMAZEM`; `ler_painel_itens(img) -> PainelItens | None`; `CENTRO_ABA_ARMAZEM = (1845, 215)`.

- [ ] **Step 1: Escrever testes falhos para classificação e ambiguidade**

Importar `PainelItens`, `ler_painel_itens` e testar a captura real já versionada do Armazém:

```python
def test_detecta_painel_armazem_selecionado(stash_2):
    assert ler_painel_itens(stash_2) is PainelItens.ARMAZEM


def test_painel_de_itens_ambiguo_e_recusado(monkeypatch, stash_2):
    monkeypatch.setattr(
        "mistfall.venda_visao._proporcoes_douradas_abas",
        lambda _: [0.16, 0.16],
    )
    assert ler_painel_itens(stash_2) is None


def test_detecta_inventario_quando_primeiro_titulo_esta_dourado(monkeypatch, stash_2):
    monkeypatch.setattr(
        "mistfall.venda_visao._proporcoes_douradas_abas",
        lambda _: [0.163, 0.110],
    )
    assert ler_painel_itens(stash_2) is PainelItens.INVENTARIO
```

Os valores `0.163/0.110` reproduzem as proporções medidas em
`sessao-venda-2/venda-0009/02-nao-fechou.png`, sem versionar a pasta da sessão.

- [ ] **Step 2: Executar os testes e confirmar a falha**

Run: `.venv/bin/pytest tests/test_venda_visao.py::test_detecta_painel_armazem_selecionado tests/test_venda_visao.py::test_painel_de_itens_ambiguo_e_recusado tests/test_venda_visao.py::test_detecta_inventario_quando_primeiro_titulo_esta_dourado -v`

Expected: FAIL de importação porque a interface ainda não existe.

- [ ] **Step 3: Implementar a classificação mínima**

Adicionar ao módulo de visão:

```python
from enum import Enum

REGIOES_ABAS_ITENS = (
    (1570, 190, 1755, 240),  # Inventario
    (1770, 190, 1940, 240),  # Armazem
)
LIMIAR_DOURADO_ABA = 0.14
MARGEM_DOURADA_ABA = 0.03
CENTRO_ABA_ARMAZEM = (1845, 215)


class PainelItens(Enum):
    INVENTARIO = "inventario"
    ARMAZEM = "armazem"


def _proporcoes_douradas_abas(img: np.ndarray) -> list[float]:
    conferir_resolucao(img)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    resultado = []
    for x0, y0, x1, y1 in REGIOES_ABAS_ITENS:
        recorte = hsv[y0:y1, x0:x1]
        dourado = (
            (recorte[:, :, 0] >= 10)
            & (recorte[:, :, 0] <= 35)
            & (recorte[:, :, 1] >= 50)
            & (recorte[:, :, 2] >= 80)
        )
        resultado.append(float(dourado.mean()))
    return resultado


def ler_painel_itens(img: np.ndarray) -> PainelItens | None:
    proporcoes = _proporcoes_douradas_abas(img)
    melhor = max(range(2), key=proporcoes.__getitem__)
    outro = 1 - melhor
    if (
        proporcoes[melhor] < LIMIAR_DOURADO_ABA
        or proporcoes[melhor] - proporcoes[outro] < MARGEM_DOURADA_ABA
    ):
        return None
    return PainelItens.INVENTARIO if melhor == 0 else PainelItens.ARMAZEM
```

- [ ] **Step 4: Executar a suíte de visão**

Run: `.venv/bin/pytest tests/test_venda_visao.py -v`

Expected: PASS, incluindo leitura de capacidade, baú e slots existentes.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/venda_visao.py tests/test_venda_visao.py
git commit -m "Identifica painel de itens da Venda"
```

---

### Task 3: Neutralização e recuperação após confirmar anúncio

**Files:**
- Modify: `src/mistfall/venda.py`
- Test: `tests/test_venda.py`

**Interfaces:**
- Consumes: `Mao.mover`, `ler_painel_itens`, `PainelItens`, `CENTRO_ABA_ARMAZEM`.
- Produces: `PONTO_NEUTRO_POS_VENDA = (1620, 1100)` e venda que só retorna `VENDEU` após restaurar Armazém.

- [ ] **Step 1: Escrever teste falho para mover imediatamente após Listar**

Fortalecer `test_executa_um_stack_com_cliques_dentro_das_areas_seguras`:

```python
indice_listar = max(
    indice for indice, acao in enumerate(mao.acoes)
    if acao[0] == "clicar" and dentro(acao[1:], AREA_SEGURA_BOTAO_LISTAR)
)
assert mao.acoes[indice_listar + 1] == ("mover", *PONTO_NEUTRO_POS_VENDA)
assert ("apertar_esc",) not in mao.acoes
```

- [ ] **Step 2: Escrever teste falho para recuperar Inventário uma única vez**

Adicionar teste com estados roteirizados, sem depender de OCR:

```python
def test_recupera_inventario_e_volta_ao_armazem(monkeypatch, tmp_path):
    estados = iter([PainelItens.INVENTARIO, PainelItens.ARMAZEM])
    monkeypatch.setattr("mistfall.venda.ler_painel_itens", lambda _: next(estados))
    monkeypatch.setattr("mistfall.venda.eh_tela_venda", lambda _: True)
    mao = MaoFalsa()

    resultado = executar_venda(
        TelaFalsa([STASH, MODAL, STASH, STASH]),
        mao,
        SLOT,
        226,
        tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )

    assert resultado.desfecho is DesfechoVenda.VENDEU
    assert mao.acoes.count(("clicar", *CENTRO_ABA_ARMAZEM)) == 1
    assert mao.acoes.count(("mover", *PONTO_NEUTRO_POS_VENDA)) == 2
    assert ("apertar_esc",) not in mao.acoes
```

- [ ] **Step 3: Escrever teste falho para estado persistentemente ilegível**

```python
def test_aborta_sem_esc_quando_painel_permanece_ilegivel(monkeypatch, tmp_path):
    monkeypatch.setattr("mistfall.venda.ler_painel_itens", lambda _: None)
    mao = MaoFalsa()
    resultado = executar_venda(
        TelaFalsa([STASH, MODAL, MODAL]), mao, SLOT, 226, tmp_path,
        ritmo=RitmoVenda.instantaneo(),
    )
    assert resultado.desfecho is DesfechoVenda.ABORTOU
    assert ("apertar_esc",) not in mao.acoes
    assert not any(
        acao == ("clicar", *CENTRO_ABA_ARMAZEM) for acao in mao.acoes
    )
```

- [ ] **Step 4: Executar os testes e confirmar as falhas**

Run: `.venv/bin/pytest tests/test_venda.py -v`

Expected: FAIL porque ainda não há movimento neutro nem recuperação da aba.

- [ ] **Step 5: Implementar a espera recuperável**

Importar as interfaces da Task 2, declarar o ponto e substituir a espera final
por um helper que permite somente um clique em Armazém:

```python
PONTO_NEUTRO_POS_VENDA = (1620, 1100)


def _esperar_retorno_armazem(tela, mao, ritmo):
    inicio = time.monotonic()
    clicou_armazem = False
    ultimo = None
    primeira = True
    while primeira or time.monotonic() - inicio < ritmo.teto_espera_fechamento:
        primeira = False
        ultimo = tela.capturar()
        painel = ler_painel_itens(ultimo)
        if painel is PainelItens.ARMAZEM and eh_tela_venda(ultimo):
            return ultimo, ultimo
        if painel is PainelItens.INVENTARIO and not clicou_armazem:
            mao.clicar(*CENTRO_ABA_ARMAZEM)
            mao.mover(*PONTO_NEUTRO_POS_VENDA)
            clicou_armazem = True
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None, ultimo
```

Logo após o clique em `AREA_SEGURA_BOTAO_LISTAR`:

```python
mao.clicar(*_sortear_ponto(AREA_SEGURA_BOTAO_LISTAR, sorteio))
mao.mover(*PONTO_NEUTRO_POS_VENDA)
depois, ultimo = _esperar_retorno_armazem(tela, mao, ritmo)
```

Preservar a gravação de `02-nao-fechou.png`, o relatório e o motivo de aborto.

- [ ] **Step 6: Executar testes de venda e ciclo**

Run: `.venv/bin/pytest tests/test_venda.py tests/test_ciclo_venda.py -v`

Expected: PASS. `test_processa_o_bau_uma_vez_e_vende_todos_os_stacks_tres`
continua provando uma única chamada a `varrer_armazem` e duas vendas a partir
da mesma lista.

- [ ] **Step 7: Commit**

```bash
git add src/mistfall/venda.py tests/test_venda.py
git commit -m "Recupera Armazem depois de anunciar item"
```

---

### Task 4: Verificação integrada

**Files:** Nenhum arquivo novo; esta tarefa valida os três commits anteriores.

**Interfaces:**
- Consumes: comportamento completo das Tasks 1–3.
- Produces: evidência de que a mudança não alterou os demais fluxos.

- [ ] **Step 1: Executar toda a suíte e verificações estáticas**

Run: `.venv/bin/pytest -v`

Expected: todos os testes PASS.

Run: `git diff --check`

Expected: nenhuma saída e exit code 0.

Run: `git status --short`

Expected: somente as pastas locais `sessao*/` aparecem; nenhuma captura da
sessão está staged e o código versionado está limpo.
