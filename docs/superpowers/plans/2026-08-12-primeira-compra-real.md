# Primeira Compra Real — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um comando que, com o Leilão aberto, varre a tela, decide, clica, confere a Janela de Confirmação e aperta Espaço — fazendo **uma** Compra real e parando.

**Architecture:** A camada de visão já existe e não muda. Entra uma fronteira de IO com dois protocolos (`Tela`, `Mao`), duas implementações (Windows real e dublê), um módulo de visão novo para ler dentro do modal, e um orquestrador que só fala com os protocolos. Tudo exceto o arquivo do Windows é testável no macOS.

**Tech Stack:** Python 3.14, opencv-python-headless, numpy, pytesseract sobre tesseract 5.5, `mss` (captura, só Windows), `ctypes` da stdlib (input, só Windows), pytest.

**Spec:** [`docs/superpowers/specs/2026-08-12-primeira-compra-real-design.md`](../specs/2026-08-12-primeira-compra-real-design.md) · **Issue:** [#9](https://github.com/lavarini/mistfall-reseller/issues/9)

## Global Constraints

- Resolução **fixa 2560×1440**. Outra dimensão é erro, não caso a tratar (ADR-0002).
- `src/mistfall/perifericos/windows.py` é o **único** arquivo que pode importar coisa de Windows. Nenhum outro arquivo, nem teste, pode importar `mss` ou `ctypes.wintypes`.
- Nomes de domínio em **português**: `Listagem`, `ItemAlvo`, `preco_unitario`, `Ouro`, `Categoria`, `Tela`, `Mao`. Não usar `Item`, `Offer`, `price`, `Listing`, `Screen`, `Hand`.
- **Na dúvida, não compra.** Toda divergência aperta **Esc**, nunca Espaço.
- Interpretador: `.venv/bin/python`. Testes: `.venv/bin/python -m pytest`.
- Commits em português, **sem** `Co-Authored-By` e sem menção a geração por IA.

## Constantes verificadas

Medidas contra os prints reais. **Não re-derivar.**

| Constante | Valor | Origem |
|---|---|---|
| `PRECO_UNITARIO_REL` | `(1500, 628, 1900, 674)` | lê `237` em `janela.png` |
| `QUANTIDADE_REL` | `(1500, 730, 1900, 776)` | lê `1` |
| `PRECO_TOTAL_REL` | `(1500, 826, 1900, 872)` | lê `237` |
| `ICONE_JANELA_REL` | `(1390, 448, 1518, 564)` | recorte 116×128, **mesma dimensão** da região de busca da lista |

Centro de cada slot, alvo do clique — `caixa_slot` já dá isso, mas os valores servem de conferência:

| linha | coluna 0 | coluna 1 |
|---|---|---|
| 0 | (964, 364) | (1975, 364) |
| 1 | (964, 542) | (1975, 542) |
| 2 | (964, 721) | (1975, 721) |
| 3 | (964, 899) | (1975, 899) |
| 4 | (964, 1078) | (1975, 1078) |
| 5 | (964, 1257) | (1975, 1257) |

### O caminho feliz, com números reais

`images/broche-dragao-orbe-codice-padrao.png`: Ouro **66160**, o piloto escolhe **Dragão a 246**, slot **(2,1)**, clique em **(1975, 721)**. Ouro esperado depois: **66160 − 246 = 65914**.

### Sobre as fixtures sintéticas

`janela.png` mostra um **Espelho Adornado**, que não é Item-alvo — serve para o caso negativo, mas não para o caminho feliz, que precisa de um modal com Dragão e preço 246. Esse frame não existe e será **sintetizado**.

Isso é aceitável porque os frames sintéticos testam a **orquestração**, não a visão. Que o pipeline de OCR lê a fonte do jogo já está provado contra `janela.png` real (237) e contra os 7 prints de lista. O que os sintéticos exercitam é "o piloto chama as coisas na ordem certa e aperta a tecla certa".

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/mistfall/janela.py` | Imagem do modal → item, Preço Unitário, Quantidade, Preço Total |
| `src/mistfall/perifericos/protocolos.py` | `Tela` e `Mao` |
| `src/mistfall/perifericos/falso.py` | `TelaFalsa`, `MaoFalsa` |
| `src/mistfall/perifericos/windows.py` | Único arquivo específico de Windows; sem lógica |
| `src/mistfall/piloto.py` | `Resultado`, `Desfecho`, `executar` |
| `ferramentas/piloto_cli.py` | Linha de comando |
| `ferramentas/sintetizar_fixtures.py` | Gera os PNGs sintéticos do caminho feliz |
| `fixtures/sinteticas/*.png` | Frames sintéticos, versionados |

---

### Task 1: Tornar o projeto instalável

Fecha a [#14](https://github.com/lavarini/mistfall-reseller/issues/14), que virou pré-requisito: sem ela, a montagem no Windows vira briga com `PYTHONPATH`.

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_instalacao.py`

**Interfaces:**
- Consumes: nada
- Produces: pacote `mistfall` importável de qualquer diretório após `pip install -e .`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_instalacao.py`:

```python
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

def test_mistfall_importa_de_fora_da_raiz(tmp_path):
    # Roda de um diretorio qualquer, sem PYTHONPATH: se o pacote estiver
    # instalado, importa; se depender do CWD, quebra.
    r = subprocess.run(
        [sys.executable, "-c", "import mistfall.geometria as g; print(g.RESOLUCAO)"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "(2560, 1440)" in r.stdout

def test_templates_sao_encontrados_de_fora_da_raiz(tmp_path):
    r = subprocess.run(
        [sys.executable, "-c",
         "from mistfall.itens import _templates; print(len(_templates()))"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "7"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_instalacao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall'`

- [ ] **Step 3: Declarar o build no pyproject**

Acrescentar ao `pyproject.toml`, mantendo o que já existe:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 4: Instalar em modo editável**

```bash
.venv/bin/python -m pip install -e .
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_instalacao.py -v`
Expected: PASS, 2 testes

Se `test_templates_sao_encontrados_de_fora_da_raiz` falhar, o problema é `itens.py` resolvendo `templates/` a partir de `parents[2]`, que muda quando instalado. Corrija para procurar a pasta relativa à raiz do repositório **e** relativa ao pacote, nessa ordem, e registre a decisão no relatório.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, 148 + 2 testes

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/test_instalacao.py
git commit -m "Torna o projeto instalavel com pip install -e .

O pacote so era encontrado porque o pytest injeta src no pythonpath, e as
ferramentas exigiam PYTHONPATH na mao. A montagem no Windows depende
disso: e la que menos se quer brigar com caminho.

Fecha #14."
```

---

### Task 2: Ler dentro da Janela de Confirmação

**Files:**
- Create: `src/mistfall/janela.py`
- Test: `tests/test_janela.py`

**Interfaces:**
- Consumes: `conferir_resolucao` de `geometria`; `identificar_item` de `itens`; `ItemAlvo` de `tipos`
- Produces: `ler_item_da_janela(img) -> ItemAlvo | None`; `ler_preco_da_janela(img) -> int | None`; `ler_quantidade_da_janela(img) -> int | None`; `ler_preco_total_da_janela(img) -> int | None`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_janela.py`:

```python
import cv2
import pytest
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_quantidade_da_janela, ler_preco_total_da_janela,
)

JANELA = "images/janela.png"

@pytest.fixture(scope="module")
def modal():
    return cv2.imread(JANELA)

def test_le_o_preco_unitario(modal):
    assert ler_preco_da_janela(modal) == 237

def test_le_a_quantidade(modal):
    assert ler_quantidade_da_janela(modal) == 1

def test_le_o_preco_total(modal):
    assert ler_preco_total_da_janela(modal) == 237

def test_rejeita_item_que_nao_e_alvo(modal):
    # O modal deste print mostra Espelho Adornado, que nao e Item-alvo.
    assert ler_item_da_janela(modal) is None

def test_rejeita_resolucao_errada():
    import numpy as np
    pequena = np.zeros((720, 1280, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        ler_preco_da_janela(pequena)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_janela.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.janela'`

- [ ] **Step 3: Implementar janela.py**

```python
"""Leitura dentro da Janela de Confirmacao.

E visao pura — imagem para dado. Nao tem nada de IO, e por isso nao vive
em perifericos.

As regioes foram medidas contra images/janela.png, que le 237 no Preco
Unitario, 1 na Quantidade e 237 no Preco Total.
"""

import cv2
import numpy as np
import pytesseract

from mistfall.geometria import conferir_resolucao
from mistfall.itens import identificar_item
from mistfall.tipos import ItemAlvo

PRECO_UNITARIO_REL = (1500, 628, 1900, 674)
QUANTIDADE_REL = (1500, 730, 1900, 776)
PRECO_TOTAL_REL = (1500, 826, 1900, 872)
# O recorte do icone tem 116x128 — exatamente a dimensao da regiao de busca
# da lista, entao os sete templates existentes servem sem adaptacao.
ICONE_JANELA_REL = (1390, 448, 1518, 564)

_CONFIG_OCR = "--psm 7 -c tessedit_char_whitelist=0123456789"


def _numero(img: np.ndarray, regiao: tuple[int, int, int, int]) -> int | None:
    conferir_resolucao(img)
    x0, y0, x1, y1 = regiao
    cinza = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    texto = pytesseract.image_to_string(binaria, config=_CONFIG_OCR).strip()
    return int(texto) if texto.isdigit() else None


def ler_preco_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_UNITARIO_REL)


def ler_quantidade_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, QUANTIDADE_REL)


def ler_preco_total_da_janela(img: np.ndarray) -> int | None:
    return _numero(img, PRECO_TOTAL_REL)


def ler_item_da_janela(img: np.ndarray) -> ItemAlvo | None:
    conferir_resolucao(img)
    x0, y0, x1, y1 = ICONE_JANELA_REL
    return identificar_item(img[y0:y1, x0:x1])
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_janela.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/janela.py tests/test_janela.py
git commit -m "Le item, Preco Unitario, Quantidade e Preco Total no modal

Regioes medidas contra images/janela.png. O recorte do icone tem as mesmas
dimensoes da regiao de busca da lista, entao os sete templates servem sem
adaptacao.

A unica amostra disponivel e negativa: o modal do print mostra Espelho
Adornado, que nao e Item-alvo. O casamento no sentido positivo so pode ser
provado com a execucao no Windows, que gera esse print."
```

---

### Task 3: Protocolos e dublês

**Files:**
- Create: `src/mistfall/perifericos/__init__.py`, `src/mistfall/perifericos/protocolos.py`, `src/mistfall/perifericos/falso.py`
- Test: `tests/test_perifericos_falso.py`

**Interfaces:**
- Consumes: nada
- Produces: `Tela` e `Mao` (Protocol); `TelaFalsa(caminhos: list[str])` com `capturar()` e atributo `capturas_feitas: int`; `MaoFalsa()` com `clicar/apertar_espaco/apertar_esc` e atributo `acoes: list[tuple]`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_perifericos_falso.py`:

```python
import numpy as np
import pytest
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa

LISTA = "images/broche-dragao-orbe-codice-padrao.png"
JANELA = "images/janela.png"

def test_tela_falsa_serve_os_frames_na_ordem():
    tela = TelaFalsa([LISTA, JANELA])
    primeira = tela.capturar()
    segunda = tela.capturar()
    assert primeira.shape == (1440, 2560, 3)
    assert not np.array_equal(primeira, segunda)

def test_tela_falsa_repete_o_ultimo_frame_quando_acaba():
    tela = TelaFalsa([LISTA, JANELA])
    tela.capturar()
    ultima = tela.capturar()
    assert np.array_equal(tela.capturar(), ultima)

def test_tela_falsa_conta_as_capturas():
    tela = TelaFalsa([LISTA])
    tela.capturar()
    tela.capturar()
    assert tela.capturas_feitas == 2

def test_tela_falsa_exige_pelo_menos_um_frame():
    with pytest.raises(ValueError, match="pelo menos um"):
        TelaFalsa([])

def test_mao_falsa_grava_na_ordem():
    mao = MaoFalsa()
    mao.clicar(10, 20)
    mao.apertar_espaco()
    mao.apertar_esc()
    assert mao.acoes == [("clicar", 10, 20), ("apertar_espaco",), ("apertar_esc",)]

def test_mao_falsa_comeca_vazia():
    assert MaoFalsa().acoes == []
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.perifericos'`

- [ ] **Step 3: Escrever os protocolos**

`src/mistfall/perifericos/__init__.py` fica vazio.

`src/mistfall/perifericos/protocolos.py`:

```python
"""A fronteira de IO do bot.

Tudo o que sabe que existe um mouse, um teclado e uma tela mora atras
destes dois protocolos. O orquestrador nao sabe se fala com o Windows ou
com um duble.
"""

from typing import Protocol

import numpy as np


class Tela(Protocol):
    def capturar(self) -> np.ndarray:
        """Devolve a tela atual como BGR 2560x1440."""
        ...


class Mao(Protocol):
    def clicar(self, x: int, y: int) -> None: ...

    def apertar_espaco(self) -> None: ...

    def apertar_esc(self) -> None:
        """Desfaz: fecha a Janela de Confirmacao sem comprar."""
        ...
```

- [ ] **Step 4: Escrever os dublês**

`src/mistfall/perifericos/falso.py`:

```python
"""Dubles da fronteira de IO, para exercitar o piloto sem jogo nem Windows."""

import cv2
import numpy as np


class TelaFalsa:
    """Serve uma sequencia roteirizada de PNGs.

    Depois do ultimo frame, repete o ultimo indefinidamente — o piloto
    pergunta quantas vezes quiser sem estourar o roteiro.
    """

    def __init__(self, caminhos: list[str]) -> None:
        if not caminhos:
            raise ValueError("TelaFalsa precisa de pelo menos um frame")
        self._frames = [cv2.imread(c) for c in caminhos]
        for caminho, frame in zip(caminhos, self._frames):
            if frame is None:
                raise ValueError(f"nao consegui ler o frame {caminho}")
        self._proximo = 0
        self.capturas_feitas = 0

    def capturar(self) -> np.ndarray:
        frame = self._frames[min(self._proximo, len(self._frames) - 1)]
        self._proximo += 1
        self.capturas_feitas += 1
        return frame.copy()


class MaoFalsa:
    """Grava o que lhe pediram, sem fazer nada."""

    def __init__(self) -> None:
        self.acoes: list[tuple] = []

    def clicar(self, x: int, y: int) -> None:
        self.acoes.append(("clicar", x, y))

    def apertar_espaco(self) -> None:
        self.acoes.append(("apertar_espaco",))

    def apertar_esc(self) -> None:
        self.acoes.append(("apertar_esc",))
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py -v`
Expected: PASS, 6 testes

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/perifericos tests/test_perifericos_falso.py
git commit -m "Cria a fronteira de IO e seus dubles

Dois protocolos, Tela e Mao, e um par de dubles. E o que permite exercitar
o piloto inteiro no macOS: a TelaFalsa serve um roteiro de PNGs e a
MaoFalsa grava o que lhe pediram, sem tocar em nada."
```

---

### Task 4: Fixtures sintéticas do caminho feliz

**Files:**
- Create: `ferramentas/sintetizar_fixtures.py`, `fixtures/sinteticas/janela-dragao-246.png`, `fixtures/sinteticas/lista-ouro-65914.png`
- Test: `tests/test_fixtures_sinteticas.py`

**Interfaces:**
- Consumes: `ItemAlvo`; templates de `templates/`
- Produces: os dois PNGs, versionados

Estes frames existem porque o caminho feliz precisa de um modal com **Dragão a 246** e de uma lista com o Ouro já debitado — nenhum dos dois existe entre os prints reais. **Eles testam a orquestração, não a visão:** que o OCR lê a fonte do jogo já está provado contra `janela.png` e os 7 prints de lista.

- [ ] **Step 1: Escrever o sintetizador**

`ferramentas/sintetizar_fixtures.py`:

```python
"""Gera os frames sinteticos do caminho feliz do piloto.

Eles NAO substituem print real: existem so para exercitar a orquestracao,
porque nao temos modal com Item-alvo dentro nem lista com o Ouro debitado.
Rode uma vez e versione a saida.
"""

import pathlib

import cv2

from mistfall.janela import (
    ICONE_JANELA_REL,
    PRECO_TOTAL_REL,
    PRECO_UNITARIO_REL,
)
from mistfall.ouro import CAIXA_OURO

DESTINO = pathlib.Path("fixtures/sinteticas")
FONTE_JANELA = "images/janela.png"
FONTE_LISTA = "images/broche-dragao-orbe-codice-padrao.png"

PRETO = (0, 0, 0)
CLARO = (220, 220, 220)


def _escrever_numero(img, regiao, texto: str) -> None:
    x0, y0, x1, y1 = regiao
    cv2.rectangle(img, (x0, y0), (x1, y1), PRETO, -1)
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
    orig_x = x0 + ((x1 - x0) - largura) // 2
    orig_y = y0 + ((y1 - y0) + altura) // 2
    cv2.putText(img, texto, (orig_x, orig_y), cv2.FONT_HERSHEY_SIMPLEX, 1.4, CLARO, 3)


def janela_com_dragao_a_246() -> None:
    img = cv2.imread(FONTE_JANELA)
    template = cv2.imread("templates/dragao.png")
    x0, y0, x1, y1 = ICONE_JANELA_REL
    alvo = img[y0:y1, x0:x1]
    dy = (alvo.shape[0] - template.shape[0]) // 2
    dx = (alvo.shape[1] - template.shape[1]) // 2
    alvo[dy:dy + template.shape[0], dx:dx + template.shape[1]] = template
    _escrever_numero(img, PRECO_UNITARIO_REL, "246")
    _escrever_numero(img, PRECO_TOTAL_REL, "246")
    cv2.imwrite(str(DESTINO / "janela-dragao-246.png"), img)


def lista_com_ouro_debitado() -> None:
    img = cv2.imread(FONTE_LISTA)
    _escrever_numero(img, CAIXA_OURO, "65914")
    cv2.imwrite(str(DESTINO / "lista-ouro-65914.png"), img)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    janela_com_dragao_a_246()
    lista_com_ouro_debitado()
    print("gerados em", DESTINO)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o sintetizador**

```bash
.venv/bin/python -m ferramentas.sintetizar_fixtures
```
Expected: `gerados em fixtures/sinteticas`

- [ ] **Step 3: Escrever o teste que valida as fixtures**

`tests/test_fixtures_sinteticas.py`:

```python
import cv2
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_preco_total_da_janela, ler_quantidade_da_janela,
)
from mistfall.ouro import ler_ouro
from mistfall.tipos import ItemAlvo

JANELA_DRAGAO = "fixtures/sinteticas/janela-dragao-246.png"
LISTA_DEBITADA = "fixtures/sinteticas/lista-ouro-65914.png"

def test_modal_sintetico_mostra_dragao():
    assert ler_item_da_janela(cv2.imread(JANELA_DRAGAO)) is ItemAlvo.DRAGAO

def test_modal_sintetico_le_246_no_preco_unitario():
    assert ler_preco_da_janela(cv2.imread(JANELA_DRAGAO)) == 246

def test_modal_sintetico_le_246_no_preco_total():
    assert ler_preco_total_da_janela(cv2.imread(JANELA_DRAGAO)) == 246

def test_modal_sintetico_preserva_a_quantidade_original():
    # A Quantidade nao foi mexida: continua vindo do print real.
    assert ler_quantidade_da_janela(cv2.imread(JANELA_DRAGAO)) == 1

def test_lista_sintetica_tem_o_ouro_debitado():
    assert ler_ouro(cv2.imread(LISTA_DEBITADA)) == 65914
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_fixtures_sinteticas.py -v`
Expected: PASS, 5 testes

Se algum OCR falhar, ajuste escala ou espessura em `_escrever_numero` até ler — o objetivo é um número legível pelo mesmo pipeline, não fidelidade à fonte do jogo.

- [ ] **Step 5: Commit**

```bash
git add ferramentas/sintetizar_fixtures.py fixtures/sinteticas tests/test_fixtures_sinteticas.py
git commit -m "Gera os frames sinteticos do caminho feliz

Nao existe print de modal com Item-alvo dentro nem de lista com o Ouro ja
debitado, e o caminho feliz precisa dos dois. Estes frames exercitam a
orquestracao, nao a visao: que o pipeline le a fonte do jogo ja esta
provado contra janela.png e os sete prints de lista."
```

---

### Task 5: O piloto — caminho feliz

**Files:**
- Create: `src/mistfall/piloto.py`
- Test: `tests/test_piloto.py`

**Interfaces:**
- Consumes: `Tela`, `Mao`; `varrer`; `escolher`; `Config`; `identificar_estado`, `EstadoTela`; `ler_ouro`; `caixa_slot`; as quatro funções de `janela`
- Produces: `Desfecho` (Enum: `COMPROU, NADA_COMPRAVEL, ABORTOU`); `Resultado` (dataclass); `executar(tela, mao, config, pasta, simular=False) -> Resultado`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_piloto.py`:

```python
from mistfall.config import Config
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import Desfecho, executar
from mistfall.tipos import ItemAlvo

LISTA = "images/broche-dragao-orbe-codice-padrao.png"
JANELA_DRAGAO = "fixtures/sinteticas/janela-dragao-246.png"
LISTA_DEBITADA = "fixtures/sinteticas/lista-ouro-65914.png"

def cfg():
    return Config(
        precos_alvo={
            ItemAlvo.BROCHE: 188, ItemAlvo.ADAGA: 199, ItemAlvo.LANTERNA: 234,
            ItemAlvo.DRAGAO: 246, ItemAlvo.ORBE: 253, ItemAlvo.REDE: 260,
            ItemAlvo.CODICE: 281,
        },
        fracao_sanidade=0.25,
    )

def roteiro_feliz():
    # pre-voo, apos o clique (modal), apos o Espaco (lista com Ouro debitado)
    return TelaFalsa([LISTA, JANELA_DRAGAO, LISTA_DEBITADA])

def test_caminho_feliz_compra(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path)
    assert r.desfecho is Desfecho.COMPROU

def test_caminho_feliz_clica_no_slot_certo(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path)
    assert mao.acoes[0] == ("clicar", 1975, 721)

def test_caminho_feliz_aperta_espaco_e_nunca_esc(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path)
    nomes = [a[0] for a in mao.acoes]
    assert nomes == ["clicar", "apertar_espaco"]

def test_caminho_feliz_registra_os_numeros(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path)
    assert r.ouro_antes == 66160
    assert r.ouro_depois == 65914
    assert r.preco_total_esperado == 246
    assert r.listagem.item is ItemAlvo.DRAGAO

def test_caminho_feliz_salva_os_prints(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path)
    assert len(list(tmp_path.glob("*.png"))) >= 3
    assert (tmp_path / "relatorio.json").exists()
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_piloto.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.piloto'`

- [ ] **Step 3: Implementar piloto.py**

```python
"""Orquestra uma unica Compra: varre, decide, clica, confere e aperta Espaco.

Uma Compra e para. Sem loop, sem Reset — esses sao a #6 e a #7.

Nao sabe se fala com o Windows ou com um duble: toda a fronteira de IO
passa pelos protocolos Tela e Mao.
"""

import json
import random
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.estado import identificar_estado
from mistfall.geometria import caixa_slot
from mistfall.janela import (
    ler_item_da_janela, ler_preco_da_janela,
    ler_preco_total_da_janela, ler_quantidade_da_janela,
)
from mistfall.leilao import varrer
from mistfall.ouro import ler_ouro
from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import EstadoTela, Listagem

PAUSA_ANTES_DO_CLIQUE = (0.2, 0.6)
INTERVALO_ENTRE_PERGUNTAS = 0.25
TETO_ESPERA_JANELA = 10.0
ESPERA_APOS_ESPACO = 2.0
TETO_ESPERA_OURO = 5.0


class Desfecho(Enum):
    COMPROU = "comprou"
    NADA_COMPRAVEL = "nada_compravel"
    ABORTOU = "abortou"


@dataclass
class Resultado:
    desfecho: Desfecho
    motivo: str = ""
    listagem: Listagem | None = None
    ouro_antes: int | None = None
    ouro_depois: int | None = None
    preco_total_esperado: int | None = None
    segundos_ate_a_janela: float | None = None
    capturas: list[str] = field(default_factory=list)


class _Diario:
    """Salva cada captura numerada e o que o bot leu nela."""

    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.nomes: list[str] = []

    def registrar(self, img: np.ndarray, rotulo: str) -> None:
        nome = f"{len(self.nomes):02d}-{rotulo}.png"
        cv2.imwrite(str(self.pasta / nome), img)
        self.nomes.append(nome)

    def fechar(self, resultado: Resultado) -> None:
        resultado.capturas = list(self.nomes)
        dados = asdict(resultado)
        dados["desfecho"] = resultado.desfecho.value
        if resultado.listagem is not None:
            dados["listagem"] = {
                "linha": resultado.listagem.linha,
                "coluna": resultado.listagem.coluna,
                "item": resultado.listagem.item.value if resultado.listagem.item else None,
                "preco_unitario": resultado.listagem.preco_unitario,
            }
        (self.pasta / "relatorio.json").write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _esperar_janela(tela: Tela, diario: _Diario) -> tuple[np.ndarray | None, float]:
    inicio = time.monotonic()
    while time.monotonic() - inicio < TETO_ESPERA_JANELA:
        img = tela.capturar()
        if identificar_estado(img) is EstadoTela.JANELA_CONFIRMACAO:
            diario.registrar(img, "janela")
            return img, time.monotonic() - inicio
        time.sleep(INTERVALO_ENTRE_PERGUNTAS)
    return None, time.monotonic() - inicio


def executar(tela: Tela, mao: Mao, config: Config,
             pasta: Path, simular: bool = False) -> Resultado:
    diario = _Diario(Path(pasta))

    def encerrar(r: Resultado) -> Resultado:
        diario.fechar(r)
        return r

    inicial = tela.capturar()
    diario.registrar(inicial, "pre-voo")

    estado = identificar_estado(inicial)
    if estado is not EstadoTela.LISTA:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  f"pre-voo viu {estado.value}, esperava lista"))

    ouro_antes = ler_ouro(inicial)
    if ouro_antes is None:
        return encerrar(Resultado(Desfecho.ABORTOU, "Ouro inicial ilegivel"))

    escolhida = escolher(varrer(inicial), config)
    if escolhida is None:
        return encerrar(Resultado(Desfecho.NADA_COMPRAVEL,
                                  "nenhuma Listagem abaixo do Preco-alvo",
                                  ouro_antes=ouro_antes))

    if simular:
        return encerrar(Resultado(Desfecho.NADA_COMPRAVEL,
                                  "modo simulado: nao clicou",
                                  listagem=escolhida, ouro_antes=ouro_antes))

    x0, y0, x1, y1 = caixa_slot(escolhida.linha, escolhida.coluna)
    time.sleep(random.uniform(*PAUSA_ANTES_DO_CLIQUE))
    mao.clicar((x0 + x1) // 2, (y0 + y1) // 2)

    modal, demorou = _esperar_janela(tela, diario)
    if modal is None:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  "a Janela de Confirmacao nao abriu",
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  segundos_ate_a_janela=demorou))

    item_no_modal = ler_item_da_janela(modal)
    preco_no_modal = ler_preco_da_janela(modal)
    quantidade = ler_quantidade_da_janela(modal)
    total = ler_preco_total_da_janela(modal)

    divergencia = None
    if item_no_modal is not escolhida.item:
        divergencia = (f"o modal mostra {item_no_modal}, "
                       f"decidimos comprar {escolhida.item}")
    elif preco_no_modal != escolhida.preco_unitario:
        divergencia = (f"o modal cobra {preco_no_modal}, "
                       f"a Listagem dizia {escolhida.preco_unitario}")
    elif quantidade != 1:
        divergencia = f"a Quantidade e {quantidade}, esperava 1"
    elif total is None:
        divergencia = "Preco Total ilegivel"

    if divergencia is not None:
        mao.apertar_esc()
        return encerrar(Resultado(Desfecho.ABORTOU, divergencia,
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  segundos_ate_a_janela=demorou))

    mao.apertar_espaco()
    time.sleep(ESPERA_APOS_ESPACO)

    ouro_depois = None
    inicio = time.monotonic()
    while time.monotonic() - inicio < TETO_ESPERA_OURO:
        depois = tela.capturar()
        ouro_depois = ler_ouro(depois)
        if ouro_depois is not None:
            diario.registrar(depois, "apos-espaco")
            break
        time.sleep(INTERVALO_ENTRE_PERGUNTAS)

    if ouro_depois is None:
        return encerrar(Resultado(Desfecho.ABORTOU,
                                  "Ouro final ilegivel: Compra indeterminada",
                                  listagem=escolhida, ouro_antes=ouro_antes,
                                  preco_total_esperado=total,
                                  segundos_ate_a_janela=demorou))

    caiu = ouro_antes - ouro_depois
    motivo = "" if caiu == total else f"Ouro caiu {caiu}, esperava {total}"
    return encerrar(Resultado(Desfecho.COMPROU, motivo, listagem=escolhida,
                              ouro_antes=ouro_antes, ouro_depois=ouro_depois,
                              preco_total_esperado=total,
                              segundos_ate_a_janela=demorou))
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_piloto.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/piloto.py tests/test_piloto.py
git commit -m "Orquestra uma unica Compra de ponta a ponta

Varre, decide, clica, espera a Janela ser detectada, confere item, preco e
quantidade, e so entao aperta Espaco. Uma Compra e para.

Como a Janela mostra o Preco Total, a confirmacao pelo Ouro e exata: o
saldo tem de cair exatamente esse valor, nao apenas diminuir."
```

---

### Task 6: O piloto — todos os caminhos de aborto

**Files:**
- Modify: `tests/test_piloto.py`

**Interfaces:**
- Consumes: tudo da Task 5
- Produces: nada novo — só cobertura

São os testes que guardam a pior falha do projeto. Se algum ficar vermelho, o bot está apertando Espaço quando não devia.

- [ ] **Step 1: Escrever os testes de aborto**

Acrescentar a `tests/test_piloto.py`:

```python
JANELA_ESPELHO = "images/janela.png"          # modal com item que nao e alvo
LISTA_SEM_NADA = "images/lanterna-dragao-orbe-rede.png"  # nada compravel
RESET = "images/reset-forja.png"              # outra Categoria

def test_item_divergente_aperta_esc_e_nunca_espaco(tmp_path):
    # O modal mostra Espelho Adornado; decidimos comprar Dragao.
    mao = MaoFalsa()
    tela = TelaFalsa([LISTA, JANELA_ESPELHO])
    r = executar(tela, mao, cfg(), tmp_path)
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert nomes[-1] == "apertar_esc"

def test_janela_que_nao_abre_aborta_sem_apertar_nada(tmp_path):
    # A tela nunca vira modal: fica na lista.
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA, LISTA]), mao, cfg(), tmp_path)
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert nomes == ["clicar"]
    assert r.segundos_ate_a_janela is not None

def test_nada_compravel_sai_limpo_sem_clicar(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA_SEM_NADA]), mao, cfg(), tmp_path)
    assert r.desfecho is Desfecho.NADA_COMPRAVEL
    assert mao.acoes == []

def test_pre_voo_em_outra_categoria_aborta(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([RESET]), mao, cfg(), tmp_path)
    assert r.desfecho is Desfecho.ABORTOU
    assert "outra_categoria" in r.motivo
    assert mao.acoes == []

def test_pre_voo_com_modal_aberto_aborta(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([JANELA_ESPELHO]), mao, cfg(), tmp_path)
    assert r.desfecho is Desfecho.ABORTOU
    assert mao.acoes == []

def test_modo_simulado_nao_toca_em_nada(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, simular=True)
    assert mao.acoes == []
    assert r.listagem.item is ItemAlvo.DRAGAO
    assert r.ouro_antes == 66160

def test_todo_aborto_salva_relatorio(tmp_path):
    executar(TelaFalsa([RESET]), MaoFalsa(), cfg(), tmp_path)
    assert (tmp_path / "relatorio.json").exists()

def test_ouro_que_cai_valor_inesperado_e_reportado(tmp_path):
    # Depois do Espaco a tela mostra um print real cujo Ouro e 64735, nao
    # os 65914 esperados. A Compra aconteceu, mas a queda nao bate.
    OUTRA_LISTA = "images/broche-tres-adaga-lanterna-rede-padrao.png"  # Ouro 64735
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, OUTRA_LISTA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path)
    assert r.desfecho is Desfecho.COMPROU
    assert r.ouro_depois == 64735
    assert "esperava 246" in r.motivo
```

- [ ] **Step 2: Rodar e confirmar que passam**

Run: `.venv/bin/python -m pytest tests/test_piloto.py -v`
Expected: PASS, 13 testes

Se `test_janela_que_nao_abre_aborta_sem_apertar_nada` demorar 10 segundos, é o teto de espera — está correto. Se incomodar, reduza `TETO_ESPERA_JANELA` via monkeypatch **no teste**, nunca no código.

- [ ] **Step 3: Provar por mutação que os testes mordem**

Troque, em `piloto.py`, o `mao.apertar_esc()` do bloco de divergência por `mao.apertar_espaco()`. Rode `tests/test_piloto.py`. **Tem de falhar.** Restaure e confirme que volta ao verde. Cole as duas saídas no relatório.

Um teste que não falha quando o bot compra na dúvida não está protegendo nada.

- [ ] **Step 4: Commit**

```bash
git add tests/test_piloto.py
git commit -m "Cobre os caminhos de aborto do piloto

Item divergente, Janela que nao abre, nada compravel, pre-voo em outra
Categoria, pre-voo com modal ja aberto e modo simulado.

Os testes de divergencia sao o coracao da suite: verificam que a Mao
recebeu Esc e nunca Espaco. Vermelho ali significa bot comprando na
duvida."
```

---

### Task 7: A camada de Windows

**Files:**
- Create: `src/mistfall/perifericos/windows.py`
- Test: `tests/test_perifericos_windows.py`

**Interfaces:**
- Consumes: `Tela`, `Mao`
- Produces: `TelaWindows()`, `MaoWindows()`

Este é o único arquivo do projeto que não roda no macOS, e por isso **não tem lógica nenhuma** — só traduz chamada em syscall. O teste que dá para escrever aqui verifica justamente isso.

- [ ] **Step 1: Escrever o teste que dá para rodar no Mac**

`tests/test_perifericos_windows.py`:

```python
import ast
import pathlib

FONTE = pathlib.Path("src/mistfall/perifericos/windows.py")

def test_nenhum_outro_arquivo_importa_windows():
    # Toda dependencia de Windows tem de estar confinada a este arquivo.
    proibidos = ("mss", "ctypes")
    for py in pathlib.Path("src").rglob("*.py"):
        if py == FONTE:
            continue
        texto = py.read_text(encoding="utf-8")
        for nome in proibidos:
            assert f"import {nome}" not in texto, f"{py} importa {nome}"

def test_windows_implementa_os_protocolos():
    arvore = ast.parse(FONTE.read_text(encoding="utf-8"))
    classes = {n.name: n for n in ast.walk(arvore) if isinstance(n, ast.ClassDef)}
    assert "TelaWindows" in classes
    assert "MaoWindows" in classes
    metodos = lambda c: {n.name for n in classes[c].body if isinstance(n, ast.FunctionDef)}
    assert "capturar" in metodos("TelaWindows")
    assert {"clicar", "apertar_espaco", "apertar_esc"} <= metodos("MaoWindows")

def test_usa_scancode_e_nao_virtual_key():
    # Jogos costumam ler scancode de hardware e ignorar tecla virtual.
    texto = FONTE.read_text(encoding="utf-8")
    assert "KEYEVENTF_SCANCODE" in texto
    assert "0x39" in texto  # Espaco
    assert "0x01" in texto  # Esc
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_perifericos_windows.py -v`
Expected: FAIL — o arquivo não existe

- [ ] **Step 3: Implementar windows.py**

```python
"""A unica parte do bot que so roda no Windows.

Sem logica: traduz chamada em syscall. Toda decisao vive em codigo
testavel no macOS.

O input vai por SendInput com KEYEVENTF_SCANCODE, nao com virtual-key.
Jogos costumam ler scancode de hardware direto e ignorar evento de tecla
virtual — e a razao classica de um script funcionar no Bloco de Notas e
nao no jogo.

Exige rodar como administrador: o UIPI do Windows impede um processo de
integridade menor de enviar input a uma janela de integridade maior, e o
jogo roda elevado. Sem elevacao, o input e ignorado em silencio, sem erro.
"""

import ctypes
from ctypes import wintypes

import numpy as np

LARGURA, ALTURA = 2560, 1440

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

SCANCODE_ESPACO = 0x39
SCANCODE_ESC = 0x01


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _UNIAO(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("uniao", _UNIAO)]


def _enviar(*entradas: _INPUT) -> None:
    quantidade = len(entradas)
    vetor = (_INPUT * quantidade)(*entradas)
    enviados = ctypes.windll.user32.SendInput(
        quantidade, vetor, ctypes.sizeof(_INPUT)
    )
    if enviados != quantidade:
        raise OSError(
            f"SendInput aceitou {enviados} de {quantidade} eventos. "
            "Rodando como administrador?"
        )


def _mouse(dwFlags: int, dx: int = 0, dy: int = 0) -> _INPUT:
    entrada = _INPUT(type=INPUT_MOUSE)
    entrada.uniao.mi = _MOUSEINPUT(dx, dy, 0, dwFlags, 0, None)
    return entrada


def _tecla(scancode: int, soltando: bool) -> _INPUT:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if soltando else 0)
    entrada = _INPUT(type=INPUT_KEYBOARD)
    entrada.uniao.ki = _KEYBDINPUT(0, scancode, flags, 0, None)
    return entrada


class TelaWindows:
    def __init__(self) -> None:
        import mss  # local: nao existe no macOS

        self._mss = mss.mss()
        self._monitor = self._mss.monitors[1]

    def capturar(self) -> np.ndarray:
        quadro = np.array(self._mss.grab(self._monitor))
        return quadro[:, :, :3]  # BGRA -> BGR


class MaoWindows:
    def clicar(self, x: int, y: int) -> None:
        # SendInput absoluto usa 0..65535 sobre a tela virtual.
        nx = x * 65535 // (LARGURA - 1)
        ny = y * 65535 // (ALTURA - 1)
        _enviar(_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny))
        _enviar(_mouse(MOUSEEVENTF_LEFTDOWN), _mouse(MOUSEEVENTF_LEFTUP))

    def apertar_espaco(self) -> None:
        _enviar(_tecla(SCANCODE_ESPACO, False), _tecla(SCANCODE_ESPACO, True))

    def apertar_esc(self) -> None:
        _enviar(_tecla(SCANCODE_ESC, False), _tecla(SCANCODE_ESC, True))
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_perifericos_windows.py -v`
Expected: PASS, 3 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/perifericos/windows.py tests/test_perifericos_windows.py
git commit -m "Implementa a fronteira de IO no Windows

Unico arquivo que nao roda no macOS, e sem logica nenhuma: so traduz
chamada em syscall.

Input por SendInput com KEYEVENTF_SCANCODE, nao virtual-key: jogos
costumam ler scancode de hardware e ignorar tecla virtual. SendInput
devolve quantos eventos aceitou, e recusa silenciosa vira OSError
mencionando administrador — que e a causa provavel, pelo UIPI."
```

---

### Task 8: Linha de comando e roteiro da execução

**Files:**
- Create: `ferramentas/piloto_cli.py`, `docs/execucao-windows.md`
- Modify: `pyproject.toml`
- Test: `tests/test_piloto_cli.py`

**Interfaces:**
- Consumes: `executar`, `Desfecho`, `carregar_config`, `TelaWindows`, `MaoWindows`
- Produces: comando `mistfall-piloto`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_piloto_cli.py`:

```python
from ferramentas.piloto_cli import codigo_de_saida, montar_parser
from mistfall.piloto import Desfecho, Resultado

def test_parser_tem_simular_e_pasta():
    args = montar_parser().parse_args(["--simular", "--pasta", "/tmp/x"])
    assert args.simular is True
    assert args.pasta == "/tmp/x"

def test_simular_e_falso_por_padrao():
    assert montar_parser().parse_args([]).simular is False

def test_comprou_sai_zero():
    assert codigo_de_saida(Resultado(Desfecho.COMPROU)) == 0

def test_nada_compravel_sai_zero():
    assert codigo_de_saida(Resultado(Desfecho.NADA_COMPRAVEL)) == 0

def test_abortou_sai_um():
    assert codigo_de_saida(Resultado(Desfecho.ABORTOU, "qualquer motivo")) == 1

def test_problema_de_ambiente_sai_dois(monkeypatch, capsys):
    # Resolucao errada, tesseract ausente e config invalida sobem excecao.
    # A CLI tem de traduzir isso em codigo 2, nao em traceback.
    import ferramentas.piloto_cli as cli

    def explodir(*_a, **_k):
        raise ValueError("esperava 2560x1440, recebi 1920x1080")

    monkeypatch.setattr(cli, "carregar_config", explodir)
    monkeypatch.setattr(sys, "argv", ["mistfall-piloto", "--simular"])
    assert cli.main() == 2
    assert "2560x1440" in capsys.readouterr().err
```

O teste acima precisa de `import sys` no topo do arquivo de teste.

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_piloto_cli.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar a CLI**

`ferramentas/piloto_cli.py`:

```python
"""Dispara uma unica Compra. Precisa rodar como administrador no Windows."""

import argparse
import sys
import time
from pathlib import Path

from mistfall.config import carregar_config
from mistfall.piloto import Desfecho, Resultado, executar

SEGUNDOS_DE_CONTAGEM = 5


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Faz uma Compra no Leilao e para.")
    p.add_argument("--simular", action="store_true",
                   help="varre e decide, mas nao clica nem aperta nada")
    p.add_argument("--pasta", default="execucao",
                   help="onde salvar prints e relatorio")
    p.add_argument("--config", default="config.toml")
    return p


def codigo_de_saida(resultado: Resultado) -> int:
    if resultado.desfecho is Desfecho.ABORTOU:
        return 1
    return 0


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        # Resolucao errada, tesseract ausente, mss faltando, config invalida,
        # SendInput recusado. Sao problemas de ambiente, nao de decisao: o
        # usuario precisa da mensagem, nao de um traceback.
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)

    from mistfall.perifericos.windows import MaoWindows, TelaWindows

    if not args.simular:
        for restam in range(SEGUNDOS_DE_CONTAGEM, 0, -1):
            print(f"comecando em {restam}... tire a mao do mouse", flush=True)
            time.sleep(1)

    resultado = executar(TelaWindows(), MaoWindows(), config,
                         Path(args.pasta), simular=args.simular)

    print(f"desfecho: {resultado.desfecho.value}")
    if resultado.motivo:
        print(f"motivo: {resultado.motivo}")
    if resultado.listagem is not None:
        print(f"listagem: {resultado.listagem}")
    if resultado.segundos_ate_a_janela is not None:
        print(f"a Janela levou {resultado.segundos_ate_a_janela:.2f}s para abrir")
    if resultado.ouro_antes is not None:
        print(f"Ouro: {resultado.ouro_antes} -> {resultado.ouro_depois}")
    print(f"prints e relatorio em {args.pasta}")
    return codigo_de_saida(resultado)


if __name__ == "__main__":
    sys.exit(main())
```

Acrescentar ao `pyproject.toml`:

```toml
[project.scripts]
mistfall-piloto = "ferramentas.piloto_cli:main"
```

- [ ] **Step 4: Escrever o roteiro da execução**

`docs/execucao-windows.md`:

```markdown
# Rodar a primeira Compra no Windows

## Montagem, uma vez

1. Instale o **Python 3.14** de python.org, marcando "Add python.exe to PATH".
2. Instale o **tesseract** (build do UB Mannheim) e marque a opcao de adicionar ao PATH.
3. Traga o repositorio para a maquina.
4. Numa janela de terminal, na raiz do repositorio:

   ```
   python -m pip install -e .
   python -m pip install mss
   ```

5. Confira que o tesseract responde: `tesseract --version`.

## Antes de cada execucao

- Jogo em **2560x1440**, em primeiro plano.
- Leilao aberto, aba **Comprar**, Categoria **Material de Construcao**.
- Pelo menos um **Item-alvo abaixo do Preco-alvo** visivel na tela.

## Primeira execucao: simulada

Terminal **normal**, sem administrador:

```
mistfall-piloto --simular --pasta execucao-simulada
```

Ela nao clica nem aperta nada. Confira no relatorio se o item e o preco
que ela diz que compraria batem com o que voce ve na tela. **Se isso nao
bater, pare aqui** — a visao nao esta lendo a tela ao vivo, e nao adianta
arriscar ouro.

## Segunda execucao: sem administrador, de proposito

Terminal **normal**, agora pra valer:

```
mistfall-piloto --pasta execucao-sem-admin
```

O esperado e o clique ser ignorado em silencio e o piloto abortar com
"a Janela de Confirmacao nao abriu". Isso **confirma o diagnostico de
UIPI** e responde uma pergunta em aberto do ADR-0001. Anote o que
aconteceu.

## Terceira execucao: valendo

Terminal **como administrador**:

```
mistfall-piloto --pasta execucao-real
```

Tire a mao do mouse durante a contagem de 5 segundos.

## O que trazer de volta

1. As tres pastas de execucao, inteiras.
2. O tempo que a Janela levou para abrir, que a saida imprime.
3. O que aconteceu na execucao sem administrador.
4. Se comprou: o Ouro antes e depois, e se a queda bateu com o Preco Total.
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_piloto_cli.py -v`
Expected: PASS, 6 testes

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS em tudo

- [ ] **Step 7: Commit**

```bash
git add ferramentas/piloto_cli.py docs/execucao-windows.md pyproject.toml tests/test_piloto_cli.py
git commit -m "Adiciona a linha de comando e o roteiro de execucao

Tres execucoes, nessa ordem: simulada para provar a visao ao vivo sem
risco, sem administrador para confirmar se a falha e mesmo silenciosa
(UIPI), e valendo.

A contagem de 5 segundos existe para dar tempo de tirar a mao do mouse."
```

---

## Depois deste plano

O produto real desta issue não é o código, é a evidência que a execução devolve: se funcionou, quanto a Janela demorou, se sem administrador falha em silêncio, e um print de modal com Item-alvo dentro — que hoje não existe e fecha a única lacuna que nenhum trabalho no Mac consegue fechar.

Com isso medido, a [#6](https://github.com/lavarini/mistfall-reseller/issues/6) ganha o número de que precisa, e o loop deixa de ser adivinhação.
