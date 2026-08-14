# Preço exato, sorteio e paralelismo — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comprar só no preço exato do corte, sortear entre os candidatos empatados, e cortar o ciclo de 2304 ms para ~958 ms paralelizando o OCR.

**Architecture:** Três mudanças independentes sobre código já em `main`. A regra de decisão troca `≤` por `==` e ganha um sorteador injetado. O OCR — 96% do custo da varredura — passa por um helper de paralelismo compartilhado, com número de trabalhadores configurável. Nada da fronteira de IO muda.

**Tech Stack:** Python 3.14, `concurrent.futures.ThreadPoolExecutor`, `random.Random`, pytest.

**Spec:** [`docs/superpowers/specs/2026-08-13-preco-exato-e-paralelismo-design.md`](../specs/2026-08-13-preco-exato-e-paralelismo-design.md)

## Global Constraints

- Resolução **fixa 2560×1440**. `src/mistfall/perifericos/windows.py` é o único arquivo que pode importar `mss` ou `ctypes`.
- Nomes de domínio em **português**: `Listagem`, `ItemAlvo`, `preco_unitario`, `Ouro`, `Categoria`. Não usar `Item`, `Offer`, `price`, `Listing`.
- **Na dúvida, não compra.** Toda divergência no modal aperta **Esc**, nunca Espaço.
- Interpretador: `.venv/bin/python`. Testes: `.venv/bin/python -m pytest`.
- Commits em português, **sem** `Co-Authored-By` e sem menção a geração por IA.

## Por que cada mudança existe

**Preço exato.** Os Itens-alvo nunca ficam abaixo do corte — verificado em 49 observações do corpus, zero abaixo. Trocar `≤` por `==` **encolhe a janela de erro perigoso** de "todo o intervalo abaixo do alvo" para "um único valor": o OCR agora precisa acertar exatamente o número do corte para causar Compra indevida.

**Sorteio.** Com igualdade exata toda margem vira zero e os candidatos empatam. O desempate atual é ordem de leitura, e a lista é ordenada por preço crescente — o que premiaria sempre os cortes mais baratos. Medido no corpus: Orbe e Códice nunca seriam comprados, e a Rede uma vez em quatro oportunidades.

**Paralelismo.** `pytesseract` roda o binário do tesseract como **subprocesso**, então o GIL não é o gargalo e threads escalam. Medido: 12 OCRs caem de 1725 ms para 578 ms com 4 trabalhadores, com resultado idêntico ao sequencial.

## Números medidos, para usar nos testes

**Candidatos com preço exato, a partir de `varrer()`** — já com a conferência de ordenação aplicada. Repare que diferem da contagem do corpus bruto: em `lanterna-dragao-orbe-rede` a ordenação anula todos os candidatos.

| Print | Candidatos | Quais |
|---|---|---|
| `adaga-tres-broche-dois-lanterna-rede-padrao` | 2 | lanterna (1,1), rede (4,0) |
| `broche-dragao-orbe-codice-padrao` | 3 | dragao (2,1), orbe (3,0), codice (4,1) |
| `broche-tres-adaga-lanterna-rede-padrao` | 3 | adaga (0,1), lanterna (1,1), rede (4,0) |
| `broche-tres-dragao-padrao` | 1 | dragao (2,1) |
| `dragao-um-rede-padrao` | 1 | rede (4,0) |
| `lanterna-dragao-orbe-rede` | **0** | — |
| `rede-dois-dragao-padrao` | 1 | dragao (2,1) |

**Escala do paralelismo**, 12 OCRs: 1 thread 1725 ms · 2 threads 1080 ms · **4 threads 578 ms** · 8 threads 461 ms · 12 threads 413 ms.

---

## Estrutura de arquivos

| Arquivo | Mudança |
|---|---|
| `src/mistfall/paralelo.py` | **novo** — `mapear`, `TRABALHADORES_PADRAO` |
| `src/mistfall/decisao.py` | regra `==`, sorteio injetado, sai a fração de sanidade |
| `src/mistfall/config.py` | sai `fracao_sanidade`, entra `trabalhadores` |
| `src/mistfall/leilao.py` | `varrer` e `varrer_bruto` ganham `trabalhadores` |
| `src/mistfall/piloto.py` | modal em paralelo, sorteador, tempo por etapa |
| `ferramentas/piloto_cli.py` | imprime o tempo por etapa |
| `config.toml` | sai `fracao_sanidade`, entra `trabalhadores` |

---

### Task 1: Preço exato e sorteio

**Files:**
- Modify: `src/mistfall/decisao.py`, `src/mistfall/config.py`, `config.toml`
- Test: `tests/test_decisao.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `Config`, `Listagem`, `ItemAlvo`
- Produces: `escolher(listagens: list[Listagem], config: Config, sorteio: random.Random) -> Listagem | None`; `Config(precos_alvo: dict[ItemAlvo, int])` — **sem** `fracao_sanidade`

O `sorteio` é **obrigatório**, sem valor padrão. Um padrão global compartilhado tornaria os testes dependentes de estado entre si, e um padrão criado na assinatura seria avaliado uma vez na importação — os dois modos errados de fazer isso.

- [ ] **Step 1: Escrever os testes que falham**

Substituir `tests/test_decisao.py` inteiro:

```python
import random

import pytest

from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.tipos import ItemAlvo, Listagem

def cfg(**alvos):
    return Config(precos_alvo={ItemAlvo[k.upper()]: v for k, v in alvos.items()})

def lst(item, preco, linha=0, coluna=0):
    return Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)

def sorteio():
    return random.Random(20260813)

def test_compra_no_preco_exato():
    escolhida = escolher([lst(ItemAlvo.BROCHE, 188)], cfg(broche=188), sorteio())
    assert escolhida is not None

def test_ignora_um_acima_do_corte():
    assert escolher([lst(ItemAlvo.BROCHE, 189)], cfg(broche=188), sorteio()) is None

def test_ignora_um_abaixo_do_corte():
    # Os Itens-alvo nunca ficam abaixo do corte: isso e leitura suspeita,
    # nao pechincha.
    assert escolher([lst(ItemAlvo.BROCHE, 187)], cfg(broche=188), sorteio()) is None

def test_ignora_muito_abaixo_do_corte():
    assert escolher([lst(ItemAlvo.BROCHE, 19)], cfg(broche=188), sorteio()) is None

def test_ignora_o_que_nao_e_item_alvo():
    assert escolher([lst(None, 188)], cfg(broche=188), sorteio()) is None

def test_ignora_item_sem_corte_configurado():
    assert escolher([lst(ItemAlvo.ADAGA, 199)], cfg(broche=188), sorteio()) is None

def test_ignora_preco_ilegivel():
    assert escolher([lst(ItemAlvo.BROCHE, None)], cfg(broche=188), sorteio()) is None

def test_lista_vazia_nao_escolhe_nada():
    assert escolher([], cfg(broche=188), sorteio()) is None

def test_um_unico_candidato_e_sempre_o_escolhido():
    so_um = [lst(ItemAlvo.BROCHE, 188, linha=0), lst(ItemAlvo.ADAGA, 300, linha=1)]
    for _ in range(20):
        assert escolher(so_um, cfg(broche=188, adaga=199), sorteio()).item is ItemAlvo.BROCHE

def test_com_semente_fixa_a_escolha_e_deterministica():
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.ADAGA, 199, linha=1),
                  lst(ItemAlvo.REDE, 260, linha=2)]
    config = cfg(broche=188, adaga=199, rede=260)
    primeira = escolher(candidatos, config, random.Random(7)).item
    for _ in range(5):
        assert escolher(candidatos, config, random.Random(7)).item is primeira

def test_o_sorteio_alcanca_todos_os_candidatos():
    # Pega a implementacao que diz sortear e devolve sempre o mesmo — foi
    # exatamente o vies que motivou esta mudanca.
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.ADAGA, 199, linha=1),
                  lst(ItemAlvo.REDE, 260, linha=2)]
    config = cfg(broche=188, adaga=199, rede=260)
    rng = random.Random(20260813)
    vistos = {escolher(candidatos, config, rng).item for _ in range(200)}
    assert vistos == {ItemAlvo.BROCHE, ItemAlvo.ADAGA, ItemAlvo.REDE}

def test_o_sorteio_nao_privilegia_a_ordem_de_leitura():
    # Com 2 candidatos e 400 sorteios, uma implementacao que devolvesse o
    # primeiro daria 400 para ele. Exigimos que nenhum passe de 70%.
    candidatos = [lst(ItemAlvo.BROCHE, 188, linha=0),
                  lst(ItemAlvo.REDE, 260, linha=5)]
    config = cfg(broche=188, rede=260)
    rng = random.Random(20260813)
    contagem = {ItemAlvo.BROCHE: 0, ItemAlvo.REDE: 0}
    for _ in range(400):
        contagem[escolher(candidatos, config, rng).item] += 1
    assert max(contagem.values()) < 280, contagem

def test_config_nao_tem_mais_fracao_de_sanidade():
    # A regra de igualdade exata ja rejeita tudo abaixo do corte, entao a
    # fracao virou config inalcancavel — e config que parece protecao e nao
    # protege e pior que config nenhuma.
    assert not hasattr(cfg(broche=188), "fracao_sanidade")
```

Em `tests/test_config.py`, remover os cinco testes que citam `fracao_sanidade` e acrescentar:

```python
def test_config_real_nao_declara_fracao_de_sanidade():
    assert not hasattr(carregar_config("config.toml"), "fracao_sanidade")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_decisao.py -v`
Expected: FAIL — `escolher()` ainda não aceita `sorteio`, e `Config` ainda exige `fracao_sanidade`

- [ ] **Step 3: Reescrever decisao.py**

```python
import random

from mistfall.config import Config
from mistfall.tipos import Listagem


def _comprável(listagem: Listagem, config: Config) -> bool:
    """Compravel e o que esta EXATAMENTE no corte.

    Os Itens-alvo nunca ficam abaixo do corte — verificado em 49 observacoes
    do corpus, zero abaixo. Entao preco menor que o corte e leitura suspeita,
    nao pechincha, e a regra de igualdade encolhe a janela de erro perigoso de
    "todo o intervalo abaixo" para "um unico valor".
    """
    if listagem.item is None or listagem.preco_unitario is None:
        return False
    alvo = config.precos_alvo.get(listagem.item)
    if alvo is None:
        return False
    return listagem.preco_unitario == alvo


def escolher(listagens: list[Listagem], config: Config,
             sorteio: random.Random) -> Listagem | None:
    """Sorteia uma entre as Listagens que estao no corte.

    Com igualdade exata todos os candidatos empatam, entao nao existe criterio
    natural de desempate. Ordem de leitura seria o pior possivel: a lista e
    ordenada por preco crescente, entao ela premiaria sempre os cortes mais
    baratos — medido no corpus, Orbe e Codice nunca seriam comprados.

    O sorteador vem de fora para os testes poderem fixar a semente.
    """
    candidatas = [l for l in listagens if _comprável(l, config)]
    if not candidatas:
        return None
    return sorteio.choice(candidatas)
```

- [ ] **Step 4: Tirar a fração de sanidade da config**

Em `src/mistfall/config.py`: remover o campo `fracao_sanidade` do dataclass `Config`, a constante `FRACAO_SANIDADE_PADRAO`, e a leitura da chave em `carregar_config`. Manter intactas todas as mensagens de erro sobre `[precos_alvo]`.

Em `config.toml`, remover a linha `fracao_sanidade = 0.25`.

- [ ] **Step 5: Corrigir os outros chamadores**

`tests/test_leilao.py` e `tests/test_piloto.py` constroem `Config(...)` com `fracao_sanidade` e chamam `escolher`. Ajuste as duas construções e passe um `random.Random` com semente fixa onde `escolher` for chamado. `src/mistfall/piloto.py` também chama `escolher` — passe `random.Random()` por enquanto; a Task 5 torna isso injetável.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS. A suíte está em **226** antes desta task.

- [ ] **Step 7: Provar por mutação**

Troque `==` por `<=` em `_comprável`. Rode `tests/test_decisao.py`: **tem de falhar** (`test_ignora_um_abaixo_do_corte`). Restaure.

Troque `sorteio.choice(candidatas)` por `candidatas[0]`. Rode: **tem de falhar** (`test_o_sorteio_alcanca_todos_os_candidatos`). Restaure.

Cole as duas saídas no relatório.

- [ ] **Step 8: Commit**

```bash
git add src/mistfall/decisao.py src/mistfall/config.py config.toml tests/
git commit -m "Compra so no preco exato do corte, sorteando entre os empatados

Os Itens-alvo nunca ficam abaixo do corte: 49 observacoes no corpus, zero
abaixo. A regra de igualdade encolhe a janela de erro perigoso de 'todo o
intervalo abaixo do alvo' para 'um unico valor'.

Isso zera todas as margens e empata os candidatos. O desempate por ordem
de leitura premiaria sempre os cortes mais baratos, porque a lista e
ordenada por preco crescente — medido no corpus, Orbe e Codice nunca
seriam comprados e a Rede uma vez em quatro. Passa a sortear.

A fracao de sanidade sai junto: com a regra nova ela virou inalcancavel."
```

---

### Task 2: Helper de paralelismo

**Files:**
- Create: `src/mistfall/paralelo.py`
- Test: `tests/test_paralelo.py`

**Interfaces:**
- Consumes: nada
- Produces: `TRABALHADORES_PADRAO = 4`; `mapear(funcao, itens, trabalhadores=TRABALHADORES_PADRAO) -> list`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_paralelo.py`:

```python
import threading
import time

import pytest

from mistfall.paralelo import TRABALHADORES_PADRAO, mapear

def test_preserva_a_ordem_da_entrada():
    # Itens lentos primeiro: se a ordem viesse de quem termina antes, esta
    # lista sairia invertida.
    def devagar(n):
        time.sleep(0.02 if n < 3 else 0)
        return n * 10
    assert mapear(devagar, [0, 1, 2, 3, 4, 5], trabalhadores=4) == [0, 10, 20, 30, 40, 50]

def test_resultado_identico_ao_sequencial():
    itens = list(range(20))
    assert mapear(str, itens, trabalhadores=8) == mapear(str, itens, trabalhadores=1)

def test_um_trabalhador_roda_na_propria_thread():
    principal = threading.current_thread()
    threads = mapear(lambda _: threading.current_thread(), range(4), trabalhadores=1)
    assert all(t is principal for t in threads)

def test_varios_trabalhadores_usam_outras_threads():
    principal = threading.current_thread()
    threads = mapear(lambda _: threading.current_thread(), range(8), trabalhadores=4)
    assert any(t is not principal for t in threads)

def test_lista_vazia():
    assert mapear(str, [], trabalhadores=4) == []

def test_o_padrao_e_conservador():
    # Quatro ja da ganho de 3x e sobra CPU para o jogo, que roda na mesma
    # maquina e precisa desenhar a tela que o bot vai capturar.
    assert TRABALHADORES_PADRAO == 4

def test_zero_ou_negativo_e_erro():
    with pytest.raises(ValueError, match="trabalhadores"):
        mapear(str, [1, 2], trabalhadores=0)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_paralelo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.paralelo'`

- [ ] **Step 3: Implementar paralelo.py**

```python
"""Aplica uma funcao a varios itens em paralelo, preservando a ordem.

Existe porque 96% do custo da varredura e OCR de preco, e o pytesseract nao
faz OCR em Python: ele grava a imagem em arquivo temporario e roda o binario
do tesseract como subprocesso. O GIL nao e o gargalo, entao threads escalam —
12 OCRs caem de 1725 ms para 578 ms com quatro trabalhadores.

Mora num lugar so de proposito: ThreadPoolExecutor solto em cada chamador
viraria a quarta copia de logica repetida neste projeto.
"""

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

# Quatro da ganho de 3x e sobra CPU para o jogo, que roda na mesma maquina e
# precisa desenhar a tela que o bot vai capturar. Doze renderia mais 165 ms e
# disputaria tudo.
TRABALHADORES_PADRAO = 4

E = TypeVar("E")
S = TypeVar("S")


def mapear(funcao: Callable[[E], S], itens: Iterable[E],
           trabalhadores: int = TRABALHADORES_PADRAO) -> list[S]:
    """Devolve os resultados na ordem da entrada, sempre.

    Com `trabalhadores=1` roda de verdade na thread do chamador — e a saida
    para depurar e para isolar a paralelizacao de qualquer suspeita.
    """
    if trabalhadores < 1:
        raise ValueError(f"trabalhadores precisa ser >= 1, recebi {trabalhadores}")
    itens = list(itens)
    if trabalhadores == 1 or not itens:
        return [funcao(item) for item in itens]
    with ThreadPoolExecutor(max_workers=trabalhadores) as executor:
        return list(executor.map(funcao, itens))
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest tests/test_paralelo.py -v`
Expected: PASS, 7 testes

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/paralelo.py tests/test_paralelo.py
git commit -m "Adiciona helper de paralelismo com ordem preservada

O pytesseract roda o binario do tesseract como subprocesso, entao o GIL
nao e o gargalo e threads escalam de verdade: 12 OCRs caem de 1725 ms para
578 ms com quatro trabalhadores.

Num lugar so, e nao ThreadPoolExecutor solto em cada chamador: este
projeto ja tem a #13 aberta sobre logica de OCR duplicada em tres
arquivos."
```

---

### Task 3: Varredura paralela

**Files:**
- Modify: `src/mistfall/leilao.py`, `src/mistfall/config.py`, `config.toml`
- Test: `tests/test_leilao.py`

**Interfaces:**
- Consumes: `mapear`, `TRABALHADORES_PADRAO` da Task 2
- Produces: `varrer_bruto(img, trabalhadores=TRABALHADORES_PADRAO)`; `varrer(img, trabalhadores=TRABALHADORES_PADRAO)`; `Config.trabalhadores: int`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_leilao.py`:

```python
from mistfall.paralelo import TRABALHADORES_PADRAO

LISTA = "images/broche-dragao-orbe-codice-padrao.png"

def test_paralelo_devolve_o_mesmo_que_sequencial():
    img = cv2.imread(LISTA)
    assert varrer(img, trabalhadores=4) == varrer(img, trabalhadores=1)

def test_paralelo_preserva_a_posicao_de_cada_slot():
    img = cv2.imread(LISTA)
    posicoes = [(l.linha, l.coluna) for l in varrer(img, trabalhadores=8)]
    assert posicoes == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1),
        (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1),
    ]

def test_varrer_bruto_tambem_bate_entre_paralelo_e_sequencial():
    img = cv2.imread(LISTA)
    assert varrer_bruto(img, trabalhadores=4) == varrer_bruto(img, trabalhadores=1)

def test_o_padrao_e_o_do_helper():
    import inspect
    assert inspect.signature(varrer).parameters["trabalhadores"].default == TRABALHADORES_PADRAO
```

Em `tests/test_config.py`:

```python
def test_config_real_declara_trabalhadores():
    assert carregar_config("config.toml").trabalhadores == 4

def test_trabalhadores_ausente_usa_o_padrao(tmp_path):
    arquivo = tmp_path / "c.toml"
    arquivo.write_text("[precos_alvo]\nbroche = 188\n", encoding="utf-8")
    assert carregar_config(arquivo).trabalhadores == 4

def test_trabalhadores_invalido_diz_o_arquivo_e_a_chave(tmp_path):
    arquivo = tmp_path / "c.toml"
    arquivo.write_text("trabalhadores = 0\n[precos_alvo]\nbroche = 188\n", encoding="utf-8")
    with pytest.raises(ValueError, match="trabalhadores"):
        carregar_config(arquivo)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_leilao.py tests/test_config.py -v`
Expected: FAIL — `varrer()` ainda não aceita `trabalhadores`

- [ ] **Step 3: Paralelizar a varredura**

Substituir `varrer_bruto` e `varrer` em `src/mistfall/leilao.py`:

```python
def varrer_bruto(img: np.ndarray,
                 trabalhadores: int = TRABALHADORES_PADRAO) -> list[Listagem]:
    """Le os doze slots como estao, sem conferir nada entre eles.

    Existe separada de `varrer` para o corpus de regressao poder documentar o
    que o OCR entrega de fato. Quem decide Compra usa `varrer`.

    So o OCR de preco e paralelizado: os doze casamentos de icone custam 49 ms
    somados, e nao ha o que ganhar ali.
    """
    icones = [regiao_icone(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    precos = [recorte_preco(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    itens = [identificar_item(icone) for icone in icones]
    lidos = mapear(ler_preco, precos, trabalhadores)
    return [
        Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)
        for (linha, coluna), item, preco in zip(TODOS_OS_SLOTS, itens, lidos)
    ]


def varrer(img: np.ndarray,
           trabalhadores: int = TRABALHADORES_PADRAO) -> list[Listagem]:
    """Imagem do Leilao -> doze Listagens ja conferidas contra a ordenacao."""
    return conferir_ordenacao(varrer_bruto(img, trabalhadores))
```

Acrescentar ao topo: `from mistfall.paralelo import TRABALHADORES_PADRAO, mapear`.

- [ ] **Step 4: Pôr `trabalhadores` na config**

Em `src/mistfall/config.py`, acrescentar o campo `trabalhadores: int = TRABALHADORES_PADRAO` ao dataclass — **com valor padrão**, senão toda construção de `Config` nos testes da Task 1 quebra — e lê-lo em `carregar_config`, usando o mesmo padrão quando a chave estiver ausente. Valor menor que 1 levanta `ValueError` citando o arquivo e a chave, no mesmo padrão das mensagens que já existem ali.

Em `config.toml`, acrescentar `trabalhadores = 4` antes da seção `[precos_alvo]`.

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Medir o ganho**

```bash
.venv/bin/python - <<'PY'
import cv2, sys, time
sys.path.insert(0, "src")
from mistfall.leilao import varrer
img = cv2.imread("images/broche-dragao-orbe-codice-padrao.png")
for t in (1, 4):
    varrer(img, trabalhadores=t)
    inicio = time.monotonic()
    varrer(img, trabalhadores=t)
    print("trabalhadores=%d -> %.0f ms" % (t, (time.monotonic() - inicio) * 1000))
PY
```

Cole a saída no relatório. O esperado é algo perto de 1425 ms contra 630 ms; se a diferença for muito menor, a paralelização não está pegando e vale investigar antes de seguir.

- [ ] **Step 7: Commit**

```bash
git add src/mistfall/leilao.py src/mistfall/config.py config.toml tests/
git commit -m "Paraleliza o OCR de preco da varredura

96% do custo da varredura era OCR de preco. So ele foi paralelizado: os
doze casamentos de icone somam 49 ms e nao tem o que ganhar.

O numero de trabalhadores vem da config, com padrao 4 — ja da ganho de 3x
e sobra CPU para o jogo, que roda na mesma maquina e precisa desenhar a
tela que o bot captura."
```

---

### Task 4: Modal em paralelo

**Files:**
- Modify: `src/mistfall/piloto.py`
- Test: `tests/test_piloto.py`

**Interfaces:**
- Consumes: `mapear` da Task 2; `Config.trabalhadores` da Task 3
- Produces: `_conferir_a_janela(modal, escolhida, r, trabalhadores)`

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/test_piloto.py`:

```python
def test_as_leituras_do_modal_passam_pelo_helper_de_paralelismo(monkeypatch, tmp_path):
    # Sem isto o teste de equivalencia abaixo passaria trivialmente: as tres
    # leituras sequenciais dao o mesmo resultado que as paralelas, entao so
    # comparar resultado nao prova que o helper entrou no caminho.
    import mistfall.piloto as piloto
    from mistfall.paralelo import mapear as mapear_real

    chamadas = []

    def espiao(funcao, itens, trabalhadores):
        itens = list(itens)
        chamadas.append(len(itens))
        return mapear_real(funcao, itens, trabalhadores)

    monkeypatch.setattr(piloto, "mapear", espiao)
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert 3 in chamadas, "as tres leituras do modal nao passaram pelo mapear"

def test_conferencia_do_modal_bate_entre_paralelo_e_sequencial(tmp_path):
    def rodar(trabalhadores):
        config = dataclasses.replace(cfg(), trabalhadores=trabalhadores)
        return executar(roteiro_feliz(), MaoFalsa(), config, tmp_path, ritmo=JA)
    um = rodar(1)
    quatro = rodar(4)
    assert (um.item_no_modal, um.preco_no_modal, um.quantidade_no_modal,
            um.preco_total_esperado) == (
           quatro.item_no_modal, quatro.preco_no_modal, quatro.quantidade_no_modal,
           quatro.preco_total_esperado)
    assert um.desfecho is quatro.desfecho
```

O arquivo precisa de `import dataclasses` no topo. O `mapear` tem de ser importado em
`piloto.py` como nome de módulo (`from mistfall.paralelo import mapear`) para o
`monkeypatch` alcançá-lo.

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_piloto.py -k "modal" -v`
Expected: FAIL em `test_as_leituras_do_modal_passam_pelo_helper_de_paralelismo` com
`AssertionError: as tres leituras do modal nao passaram pelo mapear` — hoje elas são três
chamadas sequenciais e o helper não entra no caminho.

- [ ] **Step 3: Paralelizar as três leituras do modal**

Em `_conferir_a_janela`, substituir as três chamadas sequenciais:

```python
    r.preco_no_modal, r.quantidade_no_modal, r.preco_total_esperado = mapear(
        lambda ler: ler(modal),
        (ler_preco_da_janela, ler_quantidade_da_janela, ler_preco_total_da_janela),
        trabalhadores,
    )
```

A assinatura passa a ser `_conferir_a_janela(modal, escolhida, r, trabalhadores)`, e quem chama passa `config.trabalhadores`. O casamento de ícone continua sequencial — 38 ms, não há o que ganhar.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/piloto.py tests/test_piloto.py
git commit -m "Paraleliza as tres leituras de numero do modal

341 ms para 160 ms. O casamento de icone fica sequencial: 38 ms, nao ha o
que ganhar."
```

---

### Task 5: Sorteador injetado e tempo por etapa

**Files:**
- Modify: `src/mistfall/piloto.py`, `ferramentas/piloto_cli.py`
- Test: `tests/test_piloto.py`, `tests/test_piloto_cli.py`

**Interfaces:**
- Consumes: `escolher(..., sorteio)` da Task 1
- Produces: `executar(tela, mao, config, pasta, simular=False, ritmo=RITMO_PADRAO, sorteio=None)`; `Resultado.tempos: dict[str, float]`

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_piloto.py`:

```python
def test_sorteio_injetado_torna_a_escolha_deterministica(tmp_path):
    escolhas = {
        executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99)).listagem.item
        for _ in range(5)
    }
    assert len(escolhas) == 1

def test_o_relatorio_registra_o_tempo_de_cada_etapa(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99))
    assert set(r.tempos) >= {"pre_voo", "varredura", "modal"}
    assert all(v >= 0 for v in r.tempos.values())

def test_o_tempo_por_etapa_vai_para_o_json(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             sorteio=random.Random(99))
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert "tempos" in dados and "varredura" in dados["tempos"]
```

O arquivo precisa de `import json` e `import random` no topo.

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_piloto.py -k "sorteio or tempo" -v`
Expected: FAIL — `executar()` ainda não aceita `sorteio`, e `Resultado` não tem `tempos`

- [ ] **Step 3: Implementar**

Em `piloto.py`:

- `Resultado` ganha `tempos: dict[str, float] = field(default_factory=dict)`
- `executar` ganha `sorteio: random.Random | None = None`; quando `None`, cria um `random.Random()` próprio da execução — nunca um global compartilhado
- Cada etapa é cronometrada com `time.monotonic()` e gravada em `r.tempos` em milissegundos, com as chaves `"pre_voo"`, `"varredura"`, `"modal"` e `"confirmacao_do_ouro"`
- `escolher(...)` passa a receber o sorteador

Em `ferramentas/piloto_cli.py`, imprimir os tempos ao fim, uma linha por etapa.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/piloto.py ferramentas/piloto_cli.py tests/
git commit -m "Injeta o sorteador e registra o tempo de cada etapa

O tempo por etapa existe porque os numeros medidos ate agora sao de um Mac
de doze nucleos ocioso. Na maquina Windows o jogo disputa CPU, e ninguem
sabe o efeito. Instrumentar agora significa que a execucao volta dizendo
qual valor de trabalhadores usar, em vez de a gente chutar duas vezes."
```

---

### Task 6: Documentação

**Files:**
- Modify: `CONTEXT.md`, `README.md`, `docs/superpowers/specs/2026-08-11-mvp-bot-leilao-design.md`
- Test: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: nada
- Produces: nada — só documentação e um teste que a guarda

Sem isto, os documentos que definem o projeto passam a mentir. O glossário é o que mais importa: ele é a fonte da linguagem do domínio.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_documentacao.py`:

```python
import pathlib

CONTEXT = pathlib.Path("CONTEXT.md").read_text(encoding="utf-8")
README = pathlib.Path("README.md").read_text(encoding="utf-8")

def test_o_glossario_nao_promete_menor_ou_igual():
    # Preco-alvo virou o preco EXATO. O texto antigo dizia "maximo que
    # aceitamos pagar" e "menor ou igual".
    assert "menor ou igual" not in CONTEXT
    assert "preço unitário máximo" not in CONTEXT

def test_o_glossario_fala_em_preco_exato():
    assert "exat" in CONTEXT.lower()

def test_a_fracao_de_sanidade_sumiu_da_documentacao():
    assert "fracao_sanidade" not in CONTEXT
    assert "fracao_sanidade" not in README

def test_o_readme_descreve_o_sorteio():
    assert "sorteia" in README.lower() or "sorteio" in README.lower()
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `.venv/bin/python -m pytest tests/test_documentacao.py -v`
Expected: FAIL nos quatro

- [ ] **Step 3: Atualizar CONTEXT.md**

Reescrever a entrada **Preço-alvo**:

```markdown
**Preço-alvo**:
O preço unitário exato pelo qual compramos um Item-alvo. O bot compra uma Listagem
quando o Preço-unitário dela é **igual** ao Preço-alvo — nem acima, nem abaixo.
Os Itens-alvo não ficam abaixo desse valor: ele é chão de mercado, e um preço menor
é leitura errada, não pechincha.
_Avoid_: Preço-limite, Valor, Preço-máximo (todos aliases; usar Preço-alvo).
```

- [ ] **Step 4: Atualizar README.md**

O passo 5 de "Como funciona" passa a: *"Sorteia uma Listagem entre as que estão exatamente no Preço-alvo"*.

Na seção "Configuração", remover o bloco sobre `fracao_sanidade`, tirar a linha do exemplo TOML, acrescentar `trabalhadores = 4` ao exemplo, e explicar que ele controla quantos OCRs rodam em paralelo — padrão conservador porque o jogo divide a CPU.

- [ ] **Step 5: Marcar a spec antiga como superada**

Em `docs/superpowers/specs/2026-08-11-mvp-bot-leilao-design.md`, acrescentar uma nota na seção que descreve a regra de decisão, dizendo que `≤` e a fração de sanidade foram substituídas por igualdade exata mais sorteio, e apontando para a spec de 2026-08-13.

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add CONTEXT.md README.md docs/ tests/test_documentacao.py
git commit -m "Poe glossario, README e spec antiga de acordo com a regra nova

Preco-alvo deixou de ser 'o maximo que aceitamos pagar' e virou o preco
exato. O glossario e a fonte da linguagem do dominio, entao ele e o que
mais importa acertar.

O teste que guarda isso existe porque documentacao desatualizada nao
quebra nada — ela so mente ate alguem acreditar."
```

---

## Depois deste plano

O ciclo cai de 2304 ms para ~958 ms com o padrão de 4 trabalhadores, medido no Mac. A execução da [#9](https://github.com/lavarini/mistfall-reseller/issues/9) passa a devolver o tempo real de cada etapa na máquina Windows, com o jogo disputando CPU — e é esse número que decide se `trabalhadores` sobe ou desce.

Fica pendente de medição, registrado na spec: **inverter a autoridade do preço**, decidindo pelo valor lido no modal em vez do da lista. Existe uma única amostra real de modal e ela é negativa; a #9 traz a primeira positiva.
