# Otimiza Venda pós-resgate e leitura do Armazém Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir o retorno pós-Venda quando há Ouro a resgatar e reduzir o tempo de leitura do Armazém sem perder a ordem nem a segurança dos candidatos.

**Architecture:** A Venda unitária continuará responsável por restaurar a aba Armazém, mas o ciclo manterá a lista de candidatos já extraída porque o Armazém não se reorganiza sozinho. A visão paralelizará o trabalho independente dos slots usando quatro trabalhadores, preservando a ordem visual com `executor.map`.

**Tech Stack:** Python, pytest, OpenCV, NumPy, pytesseract, `ThreadPoolExecutor`.

## Global Constraints

- Resolução suportada: 2560x1440.
- Quantidade vendável continua exatamente `3`.
- O Preço de Venda e os cliques da Janela de Confirmação não mudam.
- O Armazém só é considerado reorganizado após ação explícita; retorno pelo Inventário não dispara nova varredura.
- Pastas locais `sessao*`, imagens já existentes e demais alterações do usuário permanecem preservadas.

---

### Task 1: Cobrir telas com resgate e retorno sem revarredura

**Files:**
- Modify: `tests/test_venda_visao.py`
- Modify: `tests/test_ciclo_venda.py`

**Interfaces:**
- Consumes: `ler_painel_itens`, `eh_tela_venda`, `eh_janela_venda`, `executar_ciclo_venda`.
- Produces: regressões para as novas imagens e para a lista de candidatos persistente.

- [ ] **Step 1: Add failing test for the two new visual fixtures**

Assert `ARMAZEM`, tela de Venda válida and Janela válida for `tela-venda-resgatar.png` and `modal-venda-resgatar.png`.

- [ ] **Step 2: Run the focused vision tests and verify the expected failure**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: the new fixture assertions fail until they are added with the exact current behavior documented.

- [ ] **Step 3: Add failing cycle test for keeping cached candidates after Inventário recovery**

Make the first sale return `armazem_reaberto=True`, provide a second candidate only if the cached list is used, and assert `varrer_armazem` is called once.

- [ ] **Step 4: Run the focused cycle test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py::test_rele_candidatos_depois_de_reabrir_armazem -q`

Expected: FAIL because the current cycle rescans after `armazem_reaberto`.

---

### Task 2: Fix the cycle state after returning from Inventário

**Files:**
- Modify: `src/mistfall/ciclo_venda.py`
- Modify: `tests/test_ciclo_venda.py`

**Interfaces:**
- Consumes: `ResultadoVenda.armazem_reaberto` as a recovery observation only.
- Produces: cached candidate list consumed continuously after successful recovery.

- [ ] **Step 1: Remove the post-recovery candidate rescan**

Keep the frame and capacity reread, but do not replace `candidatos` when `resultado.armazem_reaberto` is true.

- [ ] **Step 2: Run the focused regression test**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py::test_rele_candidatos_depois_de_reabrir_armazem -q`

Expected: PASS.

- [ ] **Step 3: Add and run a regression for initial non-Armazém panel**

Assert that a valid Venda screen with `PainelItens.INVENTARIO` aborts before scanning or clicking.

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py -q`

Expected: the new test passes and existing cycle tests remain green.

---

### Task 3: Parallelize Armazém slot processing

**Files:**
- Modify: `src/mistfall/venda_visao.py`
- Modify: `tests/test_venda_visao.py`

**Interfaces:**
- Consumes: fixed 7×8 Armazém grid, `_identificar_item_do_slot`, `_ler_quantidade`.
- Produces: `varrer_armazem(img) -> list[SlotArmazem]` with unchanged order and values, using four workers.

- [ ] **Step 1: Add an order-and-value regression around `varrer_armazem`**

Compare the returned `(linha, coluna, item, quantidade)` sequence against the existing expected fixtures for both normal Armazém images and the resgate screen.

- [ ] **Step 2: Run the vision regression before implementation**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: the behavior test passes before optimization, proving it constrains semantics rather than implementation.

- [ ] **Step 3: Extract one slot worker and map it with four threads**

Create a worker that receives `(linha, coluna, recorte)`, identifies the Item-alvo, reads quantity only when identified, and returns `SlotArmazem`. Use `ThreadPoolExecutor(max_workers=4).map` over slots in row-major order.

- [ ] **Step 4: Run the vision suite and compare results**

Run: `.venv/bin/python -m pytest tests/test_venda_visao.py -q`

Expected: all vision tests pass with identical values and order.

- [ ] **Step 5: Measure before and after**

Measure five complete scans of `images/tela-venda-resgatar.png`; record median sequential baseline and parallel result in the final report.

---

### Task 4: Full verification

**Files:**
- Verify only; no additional production files.

- [ ] **Step 1: Run focused Venda tests**

Run: `.venv/bin/python -m pytest tests/test_venda.py tests/test_ciclo_venda.py tests/test_venda_visao.py -q`

- [ ] **Step 2: Run the complete suite**

Run: `.venv/bin/python -m pytest -q`

- [ ] **Step 3: Check formatting and worktree scope**

Run: `git diff --check` and `git status --short`; confirm session folders and user-provided images remain uncommitted unless explicitly requested.
