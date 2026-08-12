# Camada de Visão — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar um print 2560×1440 do Leilão numa lista de Listagens e numa decisão de Compra, inteiramente no macOS, sem jogo e sem Windows.

**Architecture:** Todo módulo aqui é função pura de imagem → dado. Não existe IO, não existe captura de tela, não existe clique — essa fronteira é de outro plano. A geometria dos slots é constante fixa (ADR-0002); a identificação de Item-alvo é template matching de ícone; o Preço-unitário sai de OCR de um recorte estreito. `decisao` não depende de imagem nenhuma.

**Tech Stack:** Python 3.14, opencv-python-headless 5.0, numpy 2.5, pytesseract 0.3 sobre tesseract 5.5, pytest. Tudo já instalado em `.venv/` exceto pytest.

**Escopo:** issues [#2](https://github.com/lavarini/mistfall-reseller/issues/2), [#3](https://github.com/lavarini/mistfall-reseller/issues/3) e [#4](https://github.com/lavarini/mistfall-reseller/issues/4). Fora: captura, injeção, loop, Reset, guardrails.

## Global Constraints

- Resolução **fixa 2560×1440**. Imagem de outra dimensão é erro, não caso a tratar (ADR-0002).
- **Nenhuma dependência de Windows** pode entrar neste plano. Se um `import` só funciona no Windows, ele está no plano errado.
- Nomes de domínio em **português**, conforme `CONTEXT.md`: `Listagem`, `ItemAlvo`, `preco_unitario`, `estoque`, `Ouro`, `Categoria`. Não usar `Item`, `Offer`, `price`, `Listing`.
- Os 7 Itens-alvo: `BROCHE, ADAGA, LANTERNA, ORBE, DRAGAO, REDE, CODICE`.
- Interpretador: `.venv/bin/python`. Testes: `.venv/bin/python -m pytest`.

## Constantes verificadas

Medidas contra `images/broche-tres-adaga-lanterna-rede-padrao.png` e conferidas com OCR 12/12 e inspeção visual dos 12 ícones. **Não re-derivar; usar como estão.**

| Constante | Valor | Significado |
|---|---|---|
| `SLOT_TOPO` | `287` | y do topo do card da linha 0 |
| `SLOT_PASSO` | `178.6` | distância vertical entre topos de linhas |
| `SLOT_COLUNAS` | `(459, 1470)` | x da borda esquerda de cada coluna |
| `LINHAS` | `6` | linhas visíveis |
| `BUSCA_ICONE_REL` | `(69, 29, 197, 145)` | região de **busca** do ícone (128×116), relativa ao card |
| `MARGEM_TEMPLATE` | `14` | quanto se corta de cada lado da busca para gerar o template (100×88) |
| `PRECO_REL` | `(931, 98, 1011, 143)` | recorte do Preço-unitário, relativo ao card |

Pipeline de OCR que deu 12/12: cinza → `resize` 4× `INTER_CUBIC` → threshold Otsu → `--psm 7 -c tessedit_char_whitelist=0123456789`.

### O template precisa ser MENOR que a região de busca

Isto não é detalhe de estilo — é a diferença entre funcionar e não funcionar, e já custou uma versão errada deste plano.

Se o template tiver **o mesmo tamanho** do recorte, `cv2.matchTemplate` devolve uma matriz 1×1: não desliza, não tolera nem um pixel de deslocamento. Como `SLOT_PASSO` é `178.6` e o arredondamento acumula linha a linha, o ícone sai de posição nas linhas de baixo. Medido: essa versão **perdeu 4 dos 7 Itens-alvo** em `broche-dragao-orbe-codice-padrao.png` (Dragão, Orbe, Lanterna e Códice ficaram invisíveis), enquanto parecia perfeita no print de onde os templates saíram.

Com o template recortado 14px para dentro da busca, o matching desliza numa janela de 29×29 e acha o alinhamento sozinho. Resultado medido: **7 de 7 Itens-alvo nos 7 prints de Leilão**, com margem de **0,38 a 0,48** entre o primeiro e o segundo colocado. Threshold `0.70` fica folgado dos dois lados.

### Convenção de nomes dos prints

`<item>-<numero>` indica quantos ouros aquele Item-alvo está **acima do corte**; citado sem número, está exatamente no corte. Item presente mas longe do corte não aparece no nome. Verificado: Broche a 188 sem número, 190 como `broche-dois`, 191 como `broche-tres` → corte 188 nos três. Adaga: corte 199.

Serve de conferência dos **Preços-alvo**, nunca do conteúdo dos slots — o rótulo de cada print tem de ser explícito.

## Conteúdo de referência do print principal

`images/broche-tres-adaga-lanterna-rede-padrao.png` contém os **sete** Itens-alvo, o que o torna a fonte única de todos os templates. Slots em `(linha, coluna)`:

| Slot | Item | Alvo? | Preço-unitário |
|---|---|---|---|
| 0,0 | Broche Ensanguentado | sim | 191 |
| 0,1 | Adaga Partida Ritualística | sim | 199 |
| 1,0 | Moeda do Rei de Norgard | não | 234 |
| 1,1 | Lanterna Desbravadora | sim | 234 |
| 2,0 | Espelho Adornado | não | 237 |
| 2,1 | Estandarte do Matador de Dragões | não | 239 |
| 3,0 | Estátua do Dragão Adormecido | sim | 250 |
| 3,1 | Orbe Ornamental | sim | 258 |
| 4,0 | Rede Arrastalmas | sim | 260 |
| 4,1 | Candeia de Mithril | não | 269 |
| 5,0 | Códice do Bosque Santo | sim | 295 |
| 5,1 | Minério de Obsidiana | não | 388 |

**Atenção:** o nome do arquivo descreve distância até o corte, **não** o conteúdo dos slots (ver seção acima). Este arquivo tem *um* Broche, apesar do `broche-tres` no nome — `tres` significa 3 ouros acima do corte. Nunca derivar expectativa de slot a partir do nome.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/mistfall/tipos.py` | `ItemAlvo`, `Listagem`, `EstadoTela` |
| `src/mistfall/geometria.py` | Constantes de slot e recortes; sem OpenCV além de fatiar array |
| `src/mistfall/precos.py` | Recorte → int por OCR |
| `src/mistfall/itens.py` | Recorte de ícone → `ItemAlvo | None` |
| `src/mistfall/leilao.py` | Imagem → `list[Listagem]` |
| `src/mistfall/config.py` | Preços-alvo e fração de sanidade |
| `src/mistfall/decisao.py` | `list[Listagem]` + config → `Listagem | None`; sem imagem |
| `src/mistfall/ouro.py` | Imagem → Ouro |
| `src/mistfall/estado.py` | Imagem → `EstadoTela` |
| `ferramentas/anotar.py` | CLI: print → print anotado |
| `templates/*.png` | 7 ícones recortados |
| `fixtures/esperado/*.json` | Expectativa rotulada por print |

---

### Task 1: Estrutura do projeto, tipos e geometria dos slots

**Files:**
- Create: `pyproject.toml`, `src/mistfall/__init__.py`, `src/mistfall/tipos.py`, `src/mistfall/geometria.py`
- Test: `tests/test_geometria.py`

**Interfaces:**
- Consumes: nada
- Produces: `ItemAlvo` (Enum: `BROCHE, ADAGA, LANTERNA, ORBE, DRAGAO, REDE, CODICE`); `Listagem` (dataclass: `linha: int`, `coluna: int`, `item: ItemAlvo | None`, `preco_unitario: int | None`); `EstadoTela` (Enum: `LISTA, JANELA_CONFIRMACAO, OUTRA_CATEGORIA, DESCONHECIDO`); `caixa_slot(linha, coluna) -> tuple[int,int,int,int]`; `regiao_icone(img, linha, coluna) -> np.ndarray` (região de busca, 116×128); `recorte_preco(img, linha, coluna) -> np.ndarray`; `TODOS_OS_SLOTS: list[tuple[int,int]]`; `MARGEM_TEMPLATE: int`

- [ ] **Step 1: Instalar pytest e criar o pyproject**

```bash
cd /Users/lavarini/lavarini/projects/mistfall-reseller
.venv/bin/python -m pip install pytest
```

`pyproject.toml`:

```toml
[project]
name = "mistfall-reseller"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "opencv-python-headless>=5.0",
    "numpy>=2.5",
    "pillow>=12.3",
    "pytesseract>=0.3.13",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_geometria.py`:

```python
import numpy as np
import pytest
from mistfall.geometria import (
    caixa_slot, regiao_icone, recorte_preco, TODOS_OS_SLOTS, RESOLUCAO,
)

def test_existem_doze_slots():
    assert len(TODOS_OS_SLOTS) == 12

def test_primeiro_slot_comeca_nas_constantes_medidas():
    x0, y0, x1, y1 = caixa_slot(0, 0)
    assert (x0, y0) == (459, 287)

def test_colunas_nao_se_sobrepoem():
    esquerda = caixa_slot(0, 0)
    direita = caixa_slot(0, 1)
    assert esquerda[2] <= direita[0]

def test_linhas_avancam_pelo_passo_medido():
    topos = [caixa_slot(i, 0)[1] for i in range(6)]
    passos = [b - a for a, b in zip(topos, topos[1:])]
    assert all(178 <= p <= 179 for p in passos), passos

def test_todos_os_slots_cabem_na_resolucao():
    largura, altura = RESOLUCAO
    for linha, coluna in TODOS_OS_SLOTS:
        x0, y0, x1, y1 = caixa_slot(linha, coluna)
        assert 0 <= x0 < x1 <= largura
        assert 0 <= y0 < y1 <= altura

def test_recortes_tem_o_tamanho_medido():
    img = np.zeros((1440, 2560, 3), dtype=np.uint8)
    assert regiao_icone(img, 0, 0).shape[:2] == (116, 128)
    assert recorte_preco(img, 0, 0).shape[:2] == (45, 80)

def test_recorte_rejeita_resolucao_errada():
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        regiao_icone(img, 0, 0)
```

- [ ] **Step 3: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_geometria.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall'`

- [ ] **Step 4: Escrever tipos.py**

```python
from dataclasses import dataclass
from enum import Enum

class ItemAlvo(Enum):
    BROCHE = "broche"
    ADAGA = "adaga"
    LANTERNA = "lanterna"
    ORBE = "orbe"
    DRAGAO = "dragao"
    REDE = "rede"
    CODICE = "codice"

class EstadoTela(Enum):
    LISTA = "lista"
    JANELA_CONFIRMACAO = "janela_confirmacao"
    OUTRA_CATEGORIA = "outra_categoria"
    DESCONHECIDO = "desconhecido"

@dataclass(frozen=True)
class Listagem:
    linha: int
    coluna: int
    item: ItemAlvo | None
    preco_unitario: int | None
```

- [ ] **Step 5: Escrever geometria.py**

```python
import numpy as np
from mistfall.tipos import Listagem, ItemAlvo, EstadoTela  # noqa: F401

RESOLUCAO = (2560, 1440)
SLOT_TOPO = 287
SLOT_PASSO = 178.6
SLOT_COLUNAS = (459, 1470)
SLOT_LARGURA = 1011
SLOT_ALTURA = 154
LINHAS = 6

# Regiao de BUSCA do icone. O template e menor que ela (ver MARGEM_TEMPLATE),
# para o matchTemplate poder deslizar e absorver o arredondamento de SLOT_PASSO.
BUSCA_ICONE_REL = (69, 29, 197, 145)
MARGEM_TEMPLATE = 14
PRECO_REL = (931, 98, 1011, 143)

TODOS_OS_SLOTS = [(linha, coluna) for linha in range(LINHAS) for coluna in range(2)]

def _conferir_resolucao(img: np.ndarray) -> None:
    altura, largura = img.shape[:2]
    if (largura, altura) != RESOLUCAO:
        raise ValueError(
            f"esperava 2560x1440, recebi {largura}x{altura}; "
            "a deteccao e acoplada a essa resolucao (ADR-0002)"
        )

def caixa_slot(linha: int, coluna: int) -> tuple[int, int, int, int]:
    x0 = SLOT_COLUNAS[coluna]
    y0 = int(SLOT_TOPO + SLOT_PASSO * linha)
    return x0, y0, x0 + SLOT_LARGURA, y0 + SLOT_ALTURA

def _recorte(img, linha, coluna, rel):
    _conferir_resolucao(img)
    x0, y0, _, _ = caixa_slot(linha, coluna)
    dx0, dy0, dx1, dy1 = rel
    return img[y0 + dy0 : y0 + dy1, x0 + dx0 : x0 + dx1]

def regiao_icone(img: np.ndarray, linha: int, coluna: int) -> np.ndarray:
    """Regiao de busca do icone — maior que o template, de proposito."""
    return _recorte(img, linha, coluna, BUSCA_ICONE_REL)

def recorte_preco(img: np.ndarray, linha: int, coluna: int) -> np.ndarray:
    return _recorte(img, linha, coluna, PRECO_REL)
```

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_geometria.py -v`
Expected: PASS, 7 testes

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/mistfall/__init__.py src/mistfall/tipos.py src/mistfall/geometria.py tests/test_geometria.py
git commit -m "Adiciona geometria fixa dos slots do Leilao

Coordenadas medidas contra os prints e conferidas com OCR 12/12 e
inspecao visual dos doze icones. Recusa resolucao diferente de 2560x1440
em vez de tentar se adaptar, conforme ADR-0002."
```

---

### Task 2: Leitura do Preço-unitário por OCR

**Files:**
- Create: `src/mistfall/precos.py`
- Test: `tests/test_precos.py`

**Interfaces:**
- Consumes: `recorte_preco` da Task 1
- Produces: `ler_preco(recorte: np.ndarray) -> int | None` — devolve `None` quando o OCR não produz dígitos

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_precos.py`:

```python
import cv2
import numpy as np
import pytest
from mistfall.geometria import recorte_preco
from mistfall.precos import ler_preco

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

ESPERADO = {
    (0, 0): 191, (0, 1): 199,
    (1, 0): 234, (1, 1): 234,
    (2, 0): 237, (2, 1): 239,
    (3, 0): 250, (3, 1): 258,
    (4, 0): 260, (4, 1): 269,
    (5, 0): 295, (5, 1): 388,
}

@pytest.fixture(scope="module")
def img():
    return cv2.imread(PRINT)

@pytest.mark.parametrize("slot,preco", sorted(ESPERADO.items()))
def test_le_o_preco_de_cada_slot(img, slot, preco):
    linha, coluna = slot
    assert ler_preco(recorte_preco(img, linha, coluna)) == preco

def test_recorte_vazio_devolve_none():
    assert ler_preco(np.zeros((45, 80, 3), dtype=np.uint8)) is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_precos.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.precos'`

- [ ] **Step 3: Implementar precos.py**

```python
import cv2
import numpy as np
import pytesseract

_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"

def ler_preco(recorte: np.ndarray) -> int | None:
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    texto = pytesseract.image_to_string(binaria, config=_CONFIG).strip()
    return int(texto) if texto.isdigit() else None
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_precos.py -v`
Expected: PASS, 13 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/precos.py tests/test_precos.py
git commit -m "Le o Preco-unitario por OCR

Cinza, upscale 4x cubico, threshold Otsu e tesseract em psm 7 com
whitelist de digitos. Acerta os doze slots do print de referencia."
```

---

### Task 3: Templates dos ícones e identificação de Item-alvo

**Files:**
- Create: `ferramentas/extrair_templates.py`, `src/mistfall/itens.py`, `templates/*.png`
- Test: `tests/test_itens.py`

**Interfaces:**
- Consumes: `regiao_icone`, `MARGEM_TEMPLATE`, `ItemAlvo` da Task 1
- Produces: `identificar_item(regiao: np.ndarray) -> ItemAlvo | None`; `pontuar(regiao) -> dict[ItemAlvo, float]`; `LIMIAR = 0.70`

- [ ] **Step 1: Escrever o extrator de templates**

`ferramentas/extrair_templates.py` — roda uma vez e versiona a saída.

```python
"""Extrai os 7 templates de icone do print que contem todos os Itens-alvo.

O template e o MIOLO da regiao de busca, cortado MARGEM_TEMPLATE de cada
lado. Se ele tivesse o tamanho da regiao, matchTemplate nao deslizaria e
perderia icones deslocados pelo arredondamento de SLOT_PASSO.
"""
import pathlib
import cv2
from mistfall.geometria import MARGEM_TEMPLATE, regiao_icone
from mistfall.tipos import ItemAlvo

ORIGEM = "images/broche-tres-adaga-lanterna-rede-padrao.png"
SLOTS = {
    ItemAlvo.BROCHE: (0, 0),
    ItemAlvo.ADAGA: (0, 1),
    ItemAlvo.LANTERNA: (1, 1),
    ItemAlvo.DRAGAO: (3, 0),
    ItemAlvo.ORBE: (3, 1),
    ItemAlvo.REDE: (4, 0),
    ItemAlvo.CODICE: (5, 0),
}

def main() -> None:
    destino = pathlib.Path("templates")
    destino.mkdir(exist_ok=True)
    img = cv2.imread(ORIGEM)
    m = MARGEM_TEMPLATE
    for item, (linha, coluna) in SLOTS.items():
        miolo = regiao_icone(img, linha, coluna)[m:-m, m:-m]
        cv2.imwrite(str(destino / f"{item.value}.png"), miolo)
        print("gravado", item.value, miolo.shape[:2])

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o extrator**

```bash
.venv/bin/python -m ferramentas.extrair_templates
```
Expected: sete linhas `gravado ... (88, 100)` e sete PNGs de 100×88 em `templates/` — **menores** que a região de busca de 128×116

- [ ] **Step 3: Escrever o teste que falha**

`tests/test_itens.py`:

```python
import cv2
import pytest
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone
from mistfall.itens import identificar_item, pontuar
from mistfall.tipos import ItemAlvo

FONTE = "images/broche-tres-adaga-lanterna-rede-padrao.png"
# Print diferente do que gerou os templates. Foi ele que expos o bug de
# template do mesmo tamanho da busca: quatro Itens-alvo sumiam aqui.
OUTRO = "images/broche-dragao-orbe-codice-padrao.png"

ALVOS_FONTE = {
    (0, 0): ItemAlvo.BROCHE,
    (0, 1): ItemAlvo.ADAGA,
    (1, 1): ItemAlvo.LANTERNA,
    (3, 0): ItemAlvo.DRAGAO,
    (3, 1): ItemAlvo.ORBE,
    (4, 0): ItemAlvo.REDE,
    (5, 0): ItemAlvo.CODICE,
}
NAO_ALVOS_FONTE = [(1, 0), (2, 0), (2, 1), (4, 1), (5, 1)]

ALVOS_OUTRO = {
    (0, 0): ItemAlvo.BROCHE,
    (0, 1): ItemAlvo.ADAGA,
    (2, 1): ItemAlvo.DRAGAO,
    (3, 0): ItemAlvo.ORBE,
    (4, 0): ItemAlvo.LANTERNA,
    (4, 1): ItemAlvo.CODICE,
    (5, 0): ItemAlvo.REDE,
}

@pytest.fixture(scope="module")
def fonte():
    return cv2.imread(FONTE)

@pytest.fixture(scope="module")
def outro():
    return cv2.imread(OUTRO)

@pytest.mark.parametrize("slot,item", sorted(ALVOS_FONTE.items()))
def test_identifica_cada_item_alvo(fonte, slot, item):
    assert identificar_item(regiao_icone(fonte, *slot)) is item

@pytest.mark.parametrize("slot", NAO_ALVOS_FONTE)
def test_rejeita_o_que_nao_e_item_alvo(fonte, slot):
    assert identificar_item(regiao_icone(fonte, *slot)) is None

@pytest.mark.parametrize("slot,item", sorted(ALVOS_OUTRO.items()))
def test_identifica_em_print_que_nao_gerou_os_templates(outro, slot, item):
    assert identificar_item(regiao_icone(outro, *slot)) is item

def test_acha_os_sete_itens_alvo_no_outro_print(outro):
    achados = {
        slot: identificar_item(regiao_icone(outro, *slot))
        for slot in TODOS_OS_SLOTS
    }
    assert {s: i for s, i in achados.items() if i} == ALVOS_OUTRO

def test_margem_sobre_o_segundo_colocado_e_folgada(outro):
    for slot in ALVOS_OUTRO:
        ranking = sorted(pontuar(regiao_icone(outro, *slot)).values(), reverse=True)
        assert ranking[0] - ranking[1] > 0.20, slot
```

- [ ] **Step 4: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_itens.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.itens'`

- [ ] **Step 5: Implementar itens.py**

```python
import functools
import pathlib
import cv2
import numpy as np
from mistfall.tipos import ItemAlvo

LIMIAR = 0.70
_PASTA = pathlib.Path("templates")

@functools.cache
def _templates() -> dict[ItemAlvo, np.ndarray]:
    carregados = {}
    for item in ItemAlvo:
        caminho = _PASTA / f"{item.value}.png"
        if not caminho.exists():
            raise FileNotFoundError(
                f"template ausente: {caminho}. "
                "Rode: .venv/bin/python -m ferramentas.extrair_templates"
            )
        carregados[item] = cv2.imread(str(caminho))
    return carregados

def pontuar(regiao: np.ndarray) -> dict[ItemAlvo, float]:
    """Score de cada Item-alvo para a regiao de busca.

    O template e menor que a regiao, entao matchTemplate desliza e devolve
    o melhor alinhamento — e assim absorve o deslocamento do arredondamento
    de SLOT_PASSO.
    """
    return {
        item: float(cv2.matchTemplate(regiao, template, cv2.TM_CCOEFF_NORMED).max())
        for item, template in _templates().items()
    }

def identificar_item(regiao: np.ndarray) -> ItemAlvo | None:
    scores = pontuar(regiao)
    melhor_item = max(scores, key=scores.get)
    return melhor_item if scores[melhor_item] >= LIMIAR else None
```

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_itens.py -v`
Expected: PASS, 21 testes

- [ ] **Step 7: Commit**

```bash
git add ferramentas/extrair_templates.py src/mistfall/itens.py templates tests/test_itens.py
git commit -m "Identifica os 7 Itens-alvo por template matching

Um unico print contem os sete itens, entao ele e a fonte de todos os
templates.

O template e menor que a regiao de busca de proposito. Com os dois do
mesmo tamanho, matchTemplate nao desliza e perde icones deslocados pelo
arredondamento de SLOT_PASSO — a versao anterior perdia quatro dos sete itens
num print diferente do que gerou os templates, parecendo perfeita no de
origem. Por isso os testes cobrem tambem esse segundo print."
```

---

### Task 4: Montagem das Listagens

**Files:**
- Create: `src/mistfall/leilao.py`
- Test: `tests/test_leilao.py`

**Interfaces:**
- Consumes: `TODOS_OS_SLOTS`, `regiao_icone`, `recorte_preco` (Task 1); `identificar_item` (Task 3); `ler_preco` (Task 2)
- Produces: `varrer(img: np.ndarray) -> list[Listagem]` — sempre 12 elementos, em ordem de leitura

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_leilao.py`:

```python
import cv2
import pytest
from mistfall.leilao import varrer
from mistfall.tipos import ItemAlvo

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

@pytest.fixture(scope="module")
def listagens():
    return varrer(cv2.imread(PRINT))

def test_devolve_os_doze_slots(listagens):
    assert len(listagens) == 12

def test_vem_em_ordem_de_leitura(listagens):
    # Lista literal de propósito: comparar com sorted(posicoes) seria
    # tautológico, porque TODOS_OS_SLOTS já nasce ordenado por construção.
    posicoes = [(l.linha, l.coluna) for l in listagens]
    assert posicoes == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1),
        (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1),
    ]

def test_encontra_os_sete_itens_alvo(listagens):
    achados = {l.item for l in listagens if l.item is not None}
    assert achados == set(ItemAlvo)

def test_casa_item_com_o_preco_do_mesmo_slot(listagens):
    por_item = {l.item: l.preco_unitario for l in listagens if l.item}
    assert por_item[ItemAlvo.BROCHE] == 191
    assert por_item[ItemAlvo.ADAGA] == 199
    assert por_item[ItemAlvo.CODICE] == 295

def test_le_preco_mesmo_de_slot_que_nao_e_alvo(listagens):
    nao_alvo = [l for l in listagens if l.item is None]
    assert all(l.preco_unitario is not None for l in nao_alvo)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_leilao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.leilao'`

- [ ] **Step 3: Implementar leilao.py**

```python
import numpy as np
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone, recorte_preco
from mistfall.itens import identificar_item
from mistfall.precos import ler_preco
from mistfall.tipos import Listagem

def varrer(img: np.ndarray) -> list[Listagem]:
    listagens = []
    for linha, coluna in TODOS_OS_SLOTS:
        listagens.append(
            Listagem(
                linha=linha,
                coluna=coluna,
                item=identificar_item(regiao_icone(img, linha, coluna)),
                preco_unitario=ler_preco(recorte_preco(img, linha, coluna)),
            )
        )
    return listagens
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_leilao.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/leilao.py tests/test_leilao.py
git commit -m "Monta as Listagens a partir de um print do Leilao

Le sempre os doze slots, inclusive os que nao sao Item-alvo, porque o
Preco-unitario deles ainda serve para depurar a deteccao."
```

---

### Task 5: Configuração e decisão de Compra

**Files:**
- Create: `src/mistfall/config.py`, `src/mistfall/decisao.py`, `config.toml`
- Test: `tests/test_decisao.py`

**Interfaces:**
- Consumes: `Listagem`, `ItemAlvo` (Task 1)
- Produces: `Config` (dataclass: `precos_alvo: dict[ItemAlvo, int]`, `fracao_sanidade: float`); `carregar_config(caminho) -> Config`; `escolher(listagens, config) -> Listagem | None`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_decisao.py`:

```python
import pytest
from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.tipos import ItemAlvo, Listagem

def cfg(**alvos):
    return Config(
        precos_alvo={ItemAlvo[k.upper()]: v for k, v in alvos.items()},
        fracao_sanidade=0.25,
    )

def lst(item, preco, linha=0, coluna=0):
    return Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)

def test_compra_abaixo_do_preco_alvo():
    escolhida = escolher([lst(ItemAlvo.BROCHE, 150)], cfg(broche=200))
    assert escolhida.preco_unitario == 150

def test_compra_exatamente_no_preco_alvo():
    assert escolher([lst(ItemAlvo.BROCHE, 200)], cfg(broche=200)) is not None

def test_ignora_acima_do_preco_alvo():
    assert escolher([lst(ItemAlvo.BROCHE, 201)], cfg(broche=200)) is None

def test_ignora_o_que_nao_e_item_alvo():
    assert escolher([lst(None, 10)], cfg(broche=200)) is None

def test_ignora_item_sem_preco_alvo_configurado():
    assert escolher([lst(ItemAlvo.ADAGA, 10)], cfg(broche=200)) is None

def test_ignora_preco_ilegivel():
    assert escolher([lst(ItemAlvo.BROCHE, None)], cfg(broche=200)) is None

def test_lista_vazia_nao_escolhe_nada():
    assert escolher([], cfg(broche=200)) is None

def test_escolhe_a_de_maior_margem():
    escolhida = escolher(
        [lst(ItemAlvo.BROCHE, 190, linha=0), lst(ItemAlvo.ADAGA, 120, linha=1)],
        cfg(broche=200, adaga=200),
    )
    assert escolhida.item is ItemAlvo.ADAGA

def test_empate_de_margem_escolhe_o_primeiro_em_ordem_de_leitura():
    escolhida = escolher(
        [lst(ItemAlvo.ADAGA, 150, linha=3), lst(ItemAlvo.BROCHE, 150, linha=1)],
        cfg(broche=200, adaga=200),
    )
    assert escolhida.linha == 1

def test_preco_absurdamente_baixo_e_leitura_falha_nao_pechincha():
    # 19 e menos de 25% de 200: OCR provavelmente comeu um digito
    assert escolher([lst(ItemAlvo.BROCHE, 19)], cfg(broche=200)) is None

def test_preco_na_fronteira_da_sanidade_e_aceito():
    assert escolher([lst(ItemAlvo.BROCHE, 50)], cfg(broche=200)) is not None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_decisao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.config'`

- [ ] **Step 3: Implementar config.py**

```python
import tomllib
from dataclasses import dataclass
from pathlib import Path
from mistfall.tipos import ItemAlvo

@dataclass(frozen=True)
class Config:
    precos_alvo: dict[ItemAlvo, int]
    fracao_sanidade: float

def carregar_config(caminho: str | Path = "config.toml") -> Config:
    dados = tomllib.loads(Path(caminho).read_text(encoding="utf-8"))
    return Config(
        precos_alvo={
            ItemAlvo(nome): int(valor)
            for nome, valor in dados["precos_alvo"].items()
        },
        fracao_sanidade=float(dados.get("fracao_sanidade", 0.25)),
    )
```

`config.toml` — estes **não** são chutes. Foram derivados da convenção de nomes dos prints (item nomeado sem número está exatamente no corte) e cada um bate em mais de um print. Confirme com o usuário antes de rodar valendo:

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

- [ ] **Step 4: Implementar decisao.py**

```python
from mistfall.config import Config
from mistfall.tipos import Listagem

def _comprável(listagem: Listagem, config: Config) -> bool:
    if listagem.item is None or listagem.preco_unitario is None:
        return False
    alvo = config.precos_alvo.get(listagem.item)
    if alvo is None:
        return False
    if listagem.preco_unitario < alvo * config.fracao_sanidade:
        return False  # leitura falha, nao pechincha
    return listagem.preco_unitario <= alvo

def escolher(listagens: list[Listagem], config: Config) -> Listagem | None:
    candidatas = [l for l in listagens if _comprável(l, config)]
    if not candidatas:
        return None
    return max(
        candidatas,
        key=lambda l: (
            config.precos_alvo[l.item] - l.preco_unitario,
            -l.linha,
            -l.coluna,
        ),
    )
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_decisao.py -v`
Expected: PASS, 11 testes

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/config.py src/mistfall/decisao.py config.toml tests/test_decisao.py
git commit -m "Decide a Compra a partir das Listagens e dos Precos-alvo

decisao nao depende de imagem nem de OCR: e regra de negocio pura,
testada com numeros escritos a mao. Preco muito abaixo do Preco-alvo e
tratado como leitura falha em vez de pechincha, porque a pior falha do
projeto e comprar caro por erro de leitura."
```

---

### Task 6: Ferramenta de anotação

**Files:**
- Create: `ferramentas/anotar.py`
- Test: `tests/test_anotar.py`

**Interfaces:**
- Consumes: `varrer` (Task 4), `caixa_slot` (Task 1)
- Produces: `anotar(img, listagens) -> np.ndarray`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_anotar.py`:

```python
import cv2
import numpy as np
from ferramentas.anotar import anotar
from mistfall.leilao import varrer

PRINT = "images/broche-tres-adaga-lanterna-rede-padrao.png"

def test_devolve_imagem_do_mesmo_tamanho():
    img = cv2.imread(PRINT)
    saida = anotar(img, varrer(img))
    assert saida.shape == img.shape

def test_nao_altera_a_imagem_original():
    img = cv2.imread(PRINT)
    copia = img.copy()
    anotar(img, varrer(img))
    assert np.array_equal(img, copia)

def test_desenha_alguma_coisa():
    img = cv2.imread(PRINT)
    saida = anotar(img, varrer(img))
    assert not np.array_equal(saida, img)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_anotar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'ferramentas.anotar'`

- [ ] **Step 3: Implementar anotar.py**

```python
"""Desenha sobre o print o que a deteccao enxergou.

Uso: .venv/bin/python -m ferramentas.anotar images/algum.png saida.png
"""
import sys
import cv2
import numpy as np
from mistfall.geometria import caixa_slot
from mistfall.leilao import varrer
from mistfall.tipos import Listagem

VERDE = (0, 220, 0)
VERMELHO = (0, 0, 220)

def anotar(img: np.ndarray, listagens: list[Listagem]) -> np.ndarray:
    saida = img.copy()
    for listagem in listagens:
        x0, y0, x1, y1 = caixa_slot(listagem.linha, listagem.coluna)
        alvo = listagem.item is not None
        cor = VERDE if alvo else VERMELHO
        cv2.rectangle(saida, (x0, y0), (x1, y1), cor, 2)
        nome = listagem.item.value if alvo else "-"
        preco = listagem.preco_unitario
        cv2.putText(
            saida,
            f"{nome} {preco if preco is not None else '??'}",
            (x0 + 200, y0 + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            cor,
            2,
        )
    return saida

def main() -> None:
    entrada, saida = sys.argv[1], sys.argv[2]
    img = cv2.imread(entrada)
    cv2.imwrite(saida, anotar(img, varrer(img)))
    print("gravado", saida)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_anotar.py -v`
Expected: PASS, 3 testes

- [ ] **Step 5: Olhar a saída de verdade**

```bash
.venv/bin/python -m ferramentas.anotar images/broche-dragao-orbe-codice-padrao.png /tmp/anotado.png
open /tmp/anotado.png
```

Confira a olho: as caixas estão em cima das Listagens, os nomes batem com os ícones e os preços batem com os números na tela. Este é o passo em que a detecção é julgada por um humano — se algo estiver torto, corrija antes de seguir.

- [ ] **Step 6: Commit**

```bash
git add ferramentas/anotar.py tests/test_anotar.py
git commit -m "Adiciona ferramenta de anotacao da deteccao

Desenha caixa, item e preco sobre o print. E assim que se ve se a
deteccao funciona, em vez de confiar num numero de acuracia agregado."
```

---

### Task 7: Corpus de expectativas e regressão (rotulagem humana)

**Files:**
- Create: `fixtures/esperado/*.json`, `ferramentas/propor_esperado.py`
- Test: `tests/test_regressao.py`

**Interfaces:**
- Consumes: `varrer` (Task 4), `anotar` (Task 6)
- Produces: um JSON por print de Leilão, com os 12 slots rotulados

- [ ] **Step 1: Gerar propostas de expectativa**

`ferramentas/propor_esperado.py`:

```python
"""Propoe o arquivo de expectativa de cada print, para revisao humana.

O que sai daqui NAO e verdade: e a leitura atual da deteccao. Precisa
ser conferido contra a imagem anotada antes de virar fixture.
"""
import glob
import json
import pathlib
import cv2
from mistfall.leilao import varrer

def main() -> None:
    destino = pathlib.Path("fixtures/esperado")
    destino.mkdir(parents=True, exist_ok=True)
    for caminho in sorted(glob.glob("images/*.png")):
        img = cv2.imread(caminho)
        if img.shape[:2] != (1440, 2560):
            print("pulando (resolucao diferente):", caminho)
            continue
        nome = pathlib.Path(caminho).stem
        slots = [
            {
                "linha": l.linha,
                "coluna": l.coluna,
                "item": l.item.value if l.item else None,
                "preco_unitario": l.preco_unitario,
            }
            for l in varrer(img)
        ]
        alvo = destino / f"{nome}.json"
        if alvo.exists():
            print("ja existe, preservando:", alvo)
            continue
        alvo.write_text(json.dumps({"slots": slots}, indent=2, ensure_ascii=False), encoding="utf-8")
        print("proposto", alvo)

if __name__ == "__main__":
    main()
```

```bash
.venv/bin/python -m ferramentas.propor_esperado
```

- [ ] **Step 2: Conferir cada print a olho e corrigir o JSON**

Para cada print de Leilão:

```bash
.venv/bin/python -m ferramentas.anotar images/<nome>.png /tmp/<nome>-anotado.png
open /tmp/<nome>-anotado.png
```

Compare a imagem anotada com o JSON e **corrija o JSON onde a detecção errou**. O JSON é a verdade; a detecção é o que está sendo julgado. Se os dois forem iguais só porque um foi gerado pelo outro, o teste não vale nada — é a revisão humana que dá valor ao corpus.

`janela.png`, `reset-forja.png` e `reset-chave.png` não são listas de Leilão utilizáveis; se o script os processar, apague os JSONs correspondentes. Eles servem à Task 9.

- [ ] **Step 3: Escrever o teste de regressão**

`tests/test_regressao.py`:

```python
import glob
import json
import pathlib
import cv2
import pytest
from mistfall.leilao import varrer

CASOS = sorted(glob.glob("fixtures/esperado/*.json"))

@pytest.mark.parametrize("caminho_json", CASOS, ids=lambda p: pathlib.Path(p).stem)
def test_deteccao_bate_com_o_corpus_rotulado(caminho_json):
    nome = pathlib.Path(caminho_json).stem
    esperado = json.loads(pathlib.Path(caminho_json).read_text(encoding="utf-8"))["slots"]
    img = cv2.imread(f"images/{nome}.png")
    obtido = [
        {
            "linha": l.linha,
            "coluna": l.coluna,
            "item": l.item.value if l.item else None,
            "preco_unitario": l.preco_unitario,
        }
        for l in varrer(img)
    ]
    assert obtido == esperado

def test_o_corpus_nao_esta_vazio():
    assert len(CASOS) >= 7
```

- [ ] **Step 4: Rodar a regressão**

Run: `.venv/bin/python -m pytest tests/test_regressao.py -v`
Expected: PASS. Qualquer falha aqui é um erro real de detecção descoberto pela rotulagem — corrija a detecção, não o corpus.

- [ ] **Step 5: Commit**

```bash
git add fixtures/esperado ferramentas/propor_esperado.py tests/test_regressao.py
git commit -m "Adiciona corpus rotulado e teste de regressao da deteccao

Cada print do Leilao ganha um JSON com os doze slots conferidos a olho
contra a imagem anotada. O nome do arquivo de print nao descreve o
conteudo de forma confiavel, entao o rotulo precisa ser explicito."
```

---

### Task 8: Leitura do Ouro

**Files:**
- Create: `src/mistfall/ouro.py`
- Test: `tests/test_ouro.py`

**Interfaces:**
- Consumes: nada além de OpenCV/pytesseract
- Produces: `ler_ouro(img: np.ndarray) -> int | None`; `CAIXA_OURO = (2350, 119, 2475, 160)`

O Ouro fica no topo direito do Leilão, exibido como `64,735` — a vírgula entra no whitelist e é removida depois.

`CAIXA_OURO` **já foi medida e validada** nos nove prints em que o Ouro é legível; não re-derivar. Com a Janela de Confirmação aberta o modal escurece a tela e a leitura devolve `None` — comportamento correto, porque o Ouro é lido com a lista visível.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_ouro.py`:

```python
import cv2
import pytest
from mistfall.ouro import ler_ouro

@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("broche-tres-adaga-lanterna-rede-padrao", 64735),
        ("adaga-tres-broche-dois-lanterna-rede-padrao", 64735),
        ("broche-dragao-orbe-codice-padrao", 66160),
        ("dragao-um-rede-padrao", 65234),
        ("lanterna-dragao-orbe-rede", 65972),
        ("reset-forja", 64735),
        ("reset-chave", 64735),
    ],
)
def test_le_o_ouro_do_topo_direito(nome, esperado):
    assert ler_ouro(cv2.imread(f"images/{nome}.png")) == esperado

def test_com_a_janela_de_confirmacao_aberta_o_ouro_fica_ilegivel():
    # O modal escurece a tela. Devolver None e correto: o Ouro e lido
    # com a lista visivel, nunca por cima da Janela de Confirmacao.
    assert ler_ouro(cv2.imread("images/janela.png")) is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_ouro.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.ouro'`

- [ ] **Step 3: Implementar ouro.py**

```python
import cv2
import numpy as np
import pytesseract

# Medida e validada nos nove prints em que o Ouro e legivel.
CAIXA_OURO = (2350, 119, 2475, 160)
_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789,"

def ler_ouro(img: np.ndarray) -> int | None:
    x0, y0, x1, y1 = CAIXA_OURO
    cinza = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    texto = pytesseract.image_to_string(binaria, config=_CONFIG).strip().replace(",", "")
    return int(texto) if texto.isdigit() else None
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_ouro.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/ouro.py tests/test_ouro.py
git commit -m "Le o Ouro do topo direito do Leilao

E a ancora de verdade para confirmar que uma Compra aconteceu, e o
insumo do piso de Ouro dos guardrails."
```

---

### Task 9: Detecção do estado da tela

**Files:**
- Create: `src/mistfall/estado.py`
- Test: `tests/test_estado.py`

**Interfaces:**
- Consumes: `EstadoTela` (Task 1), `ler_ouro` (Task 8)
- Produces: `identificar_estado(img: np.ndarray) -> EstadoTela`; `categoria_selecionada(img) -> str | None`

Prints de referência: `janela.png` é a Janela de Confirmação aberta; `reset-forja.png` e `reset-chave.png` estão em outra Categoria; os demais são a lista utilizável.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_estado.py`:

```python
import cv2
import pytest
from mistfall.estado import identificar_estado
from mistfall.tipos import EstadoTela

@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("broche-tres-adaga-lanterna-rede-padrao", EstadoTela.LISTA),
        ("broche-dragao-orbe-codice-padrao", EstadoTela.LISTA),
        ("janela", EstadoTela.JANELA_CONFIRMACAO),
        ("reset-forja", EstadoTela.OUTRA_CATEGORIA),
        ("reset-chave", EstadoTela.OUTRA_CATEGORIA),
    ],
)
def test_classifica_a_tela(nome, esperado):
    assert identificar_estado(cv2.imread(f"images/{nome}.png")) is esperado

def test_os_estados_sao_mutuamente_exclusivos():
    import glob, pathlib
    vistos = {}
    for caminho in sorted(glob.glob("images/*.png")):
        img = cv2.imread(caminho)
        if img.shape[:2] != (1440, 2560):
            continue
        vistos[pathlib.Path(caminho).stem] = identificar_estado(img)
    assert EstadoTela.DESCONHECIDO not in vistos.values(), vistos
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_estado.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.estado'`

- [ ] **Step 3: Implementar estado.py**

Os limiares abaixo **já foram medidos** contra os dez prints; não re-derivar. Brilho médio de duas regiões:

| Print | centro | menu |
|---|---|---|
| os 7 prints de lista | 12,1 – 13,3 | **37,1** |
| `reset-forja`, `reset-chave` | 11,5 – 13,0 | **32,9** |
| `janela` | **4,9** | 18,3 |

Duas coisas a notar. A Janela de Confirmação **escurece** o centro em vez de clarear — ela escurece o fundo atrás do modal, então o teste é `<`, não `>`. E o menu sozinho não distingue Janela de outra Categoria (18,3 também é baixo), por isso a Janela é testada **primeiro**.

```python
import cv2
import numpy as np
from mistfall.tipos import EstadoTela

REGIAO_JANELA = (900, 500, 1700, 950)
REGIAO_MENU = (80, 380, 360, 720)

# Janela de Confirmacao escurece o centro: 4.9 contra 11.5-13.3 do resto.
LIMIAR_JANELA = 8.0
# Material de Construcao selecionada da 37.1; outra Categoria da 32.9.
LIMIAR_MENU = 35.0

def _brilho(img: np.ndarray, regiao: tuple[int, int, int, int]) -> float:
    x0, y0, x1, y1 = regiao
    return float(cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).mean())

def identificar_estado(img: np.ndarray) -> EstadoTela:
    if _brilho(img, REGIAO_JANELA) < LIMIAR_JANELA:
        return EstadoTela.JANELA_CONFIRMACAO
    if _brilho(img, REGIAO_MENU) < LIMIAR_MENU:
        return EstadoTela.OUTRA_CATEGORIA
    return EstadoTela.LISTA
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_estado.py -v`
Expected: PASS, 6 testes

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -v`
Expected: PASS em tudo

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/estado.py tests/test_estado.py
git commit -m "Classifica a tela em lista, Janela de Confirmacao ou outra Categoria

O bot precisa saber o que esta na tela antes de agir: com a Janela
aberta a lista fica coberta e nao pode ser varrida."
```

---

## Depois deste plano

A camada de visão fica completa e verificada no Mac. O que falta para a v1, em outros planos:

- **#9** — Fatia 0 no Windows: captura, clique, Espaço, medição do tempo da Janela de Confirmação. HITL, não automatizável.
- **#6** — loop de Compra, que consome esta camada mais a fronteira de IO e a medição de tempo da #9.
- **#7** e **#8** — Reset e guardrails.
