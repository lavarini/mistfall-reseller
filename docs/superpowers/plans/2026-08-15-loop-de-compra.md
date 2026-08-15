# Loop de Compra com F2 e F3 — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um laço que repete a Compra sozinho, ligado por F2 e desligado por F3, com uma
linha de feedback por Volta no PowerShell.

**Architecture:** Um terceiro protocolo, `Interruptor`, entra ao lado de `Tela` e `Mao`, com
implementação Windows por `GetAsyncKeyState` e um dublê roteirizado. Um módulo novo,
`ciclo.py`, compõe `piloto.executar` e `reset.resetar_categoria` num laço; o `piloto.py`
continua sendo de uma Compra só e apenas passa a consultar o Interruptor em dois pontos.

**Tech Stack:** Python 3.14, pytest, `ctypes` da biblioteca padrão (sem dependência nova).

**Spec:** [`docs/superpowers/specs/2026-08-15-loop-de-compra-design.md`](../specs/2026-08-15-loop-de-compra-design.md)

## Global Constraints

- **Português** em código, testes, commits e documentação, com o glossário do `CONTEXT.md`.
  Não usar `Item`, `Offer`, `Listing`, `price`.
- **Sem atribuição de IA** em commit, comentário, issue ou PR.
- **Interpretador e testes**: `.venv/bin/python -m pytest`.
- **Nenhuma dependência exclusiva de Windows fora de `src/mistfall/perifericos/windows.py`.**
  `tests/test_perifericos_windows.py` varre `src/`, `ferramentas/` e `tests/` por AST e falha
  se qualquer outro arquivo importar `ctypes` ou `mss` (ADR-0001).
- **Saída de console sem acento e sem cor.** Padrão já estabelecido em `piloto_cli.py`.
- **Detecção acoplada a 2560×1440** de propósito (ADR-0002).
- **A Janela de Confirmação não é consultada** (ADR-0003). Nada neste plano a religa.
- Baseline: **286 testes verdes**. Nenhuma tarefa pode reduzir esse número.

## Decisão tomada neste plano, que não estava na spec

O desfecho de uma Compra interrompida pelo F3 é um valor novo, **`Desfecho.PAROU`**, e não
um `ABORTOU` com motivo diferente. Razão: `CODIGO_POR_DESFECHO` mapeia `ABORTOU` para o
código de saída 1, que significa "abortou por seguranca", e uma parada pedida pelo operador
não é falha. O mapa foi escrito sem `default` justamente para que um desfecho novo estoure
em vez de sair 0 por engano — a Task 2 fecha esse buraco de propósito.

---

### Task 1: O protocolo `Interruptor` e o dublê

**Files:**
- Modify: `src/mistfall/perifericos/protocolos.py`
- Modify: `src/mistfall/perifericos/falso.py`
- Test: `tests/test_perifericos_falso.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Interruptor` (Protocol) com `esperar_inicio() -> None` e
  `pediram_parada() -> bool`; `InterruptorFalso(parar_na_pergunta: int | None = None)` com os
  atributos públicos `perguntas: int` e `inicios: int`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_perifericos_falso.py`, no fim do arquivo:

```python
from mistfall.perifericos.falso import InterruptorFalso


def test_o_interruptor_falso_nunca_para_por_padrao():
    interruptor = InterruptorFalso()
    assert [interruptor.pediram_parada() for _ in range(5)] == [False] * 5


def test_o_interruptor_falso_para_na_pergunta_pedida():
    interruptor = InterruptorFalso(parar_na_pergunta=3)
    # A terceira pergunta e as seguintes devolvem True: uma vez pedida, a
    # parada nao volta atras.
    assert [interruptor.pediram_parada() for _ in range(4)] == [
        False, False, True, True]


def test_o_interruptor_falso_conta_as_perguntas():
    interruptor = InterruptorFalso()
    interruptor.pediram_parada()
    interruptor.pediram_parada()
    assert interruptor.perguntas == 2


def test_o_interruptor_falso_registra_o_inicio():
    # esperar_inicio nao bloqueia no duble: so anota que foi chamado, para o
    # teste do ciclo poder afirmar que o laco espera pelo F2 antes de agir.
    interruptor = InterruptorFalso()
    interruptor.esperar_inicio()
    assert interruptor.inicios == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py -v`
Expected: FAIL com `ImportError: cannot import name 'InterruptorFalso'`

- [ ] **Step 3: Implementar o protocolo**

Em `src/mistfall/perifericos/protocolos.py`, depois de `Mao`:

```python
class Interruptor(Protocol):
    """O par F2/F3 visto pelo bot.

    Terceira fronteira de IO, pela mesma razao das outras duas: a decisao de
    parar e testavel no macOS, e so a leitura da tecla mora no Windows.
    """

    def esperar_inicio(self) -> None:
        """Bloqueia ate o operador pedir para comecar."""
        ...

    def pediram_parada(self) -> bool:
        """Foi pedida parada desde a ultima pergunta?

        E pergunta com trinco, nao leitura instantanea: uma tecla apertada e
        solta enquanto o bot dormia continua registrada na pergunta seguinte.
        Sem isso o F3 so pegaria se fosse segurado no instante da checagem.
        """
        ...
```

- [ ] **Step 4: Implementar o dublê**

Em `src/mistfall/perifericos/falso.py`, no fim:

```python
class InterruptorFalso:
    """Interruptor roteirizado: para na enesima pergunta, ou nunca.

    Conta perguntas e inicios para os testes do ciclo poderem afirmar quantas
    vezes o laco consultou a parada, e nao so o efeito dela.
    """

    def __init__(self, parar_na_pergunta: int | None = None) -> None:
        self.perguntas = 0
        self.inicios = 0
        self._parar_na = parar_na_pergunta

    def esperar_inicio(self) -> None:
        self.inicios += 1

    def pediram_parada(self) -> bool:
        self.perguntas += 1
        return self._parar_na is not None and self.perguntas >= self._parar_na
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_perifericos_falso.py -v`
Expected: PASS

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. O total sobe em 4 e nenhum teste antigo muda.

- [ ] **Step 7: Commit**

```bash
git add src/mistfall/perifericos/protocolos.py src/mistfall/perifericos/falso.py tests/test_perifericos_falso.py
git commit -m "Adiciona o Interruptor como terceira fronteira de IO"
```

---

### Task 2: `piloto.executar` obedece ao Interruptor

**Files:**
- Modify: `src/mistfall/piloto.py`
- Modify: `ferramentas/piloto_cli.py:41-47`
- Test: `tests/test_piloto.py`
- Test: `tests/test_piloto_cli.py`

**Interfaces:**
- Consumes: `Interruptor`, `InterruptorFalso` da Task 1.
- Produces: `Desfecho.PAROU` (valor `"parou"`); assinatura
  `executar(tela, mao, config, pasta, simular=False, ritmo=RITMO_PADRAO, sorteio=None, interruptor=None)`;
  campo novo `Ritmo.espera_entre_voltas: float = 1.0`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_piloto.py`, no fim. Os helpers abaixo já existem no arquivo e são os reais:
`cfg()` monta a Config, `roteiro_feliz()` devolve a `TelaFalsa` do caminho de Compra, `JA` é
o `Ritmo.instantaneo()`, `MaoFalsa` grava em `.acoes` uma tupla por ação
(`("clicar", x, y)`, `("apertar_espaco",)`), e `TelaFalsa` conta em `.capturas_feitas`.

```python
from mistfall.perifericos.falso import InterruptorFalso


def test_sem_interruptor_o_piloto_se_comporta_como_antes(tmp_path):
    # Guarda os 286: o parametro novo tem default None, e com ele nada muda.
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPROU
    assert mao.acoes[0][0] == "clicar"


def test_parada_antes_do_clique_nao_clica(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1),
                 interruptor=InterruptorFalso(parar_na_pergunta=1))
    assert r.desfecho is Desfecho.PAROU
    # O ponto da abordagem cooperativa: F3 durante a varredura nao pode
    # deixar o bot completar mais uma Compra.
    assert mao.acoes == []


def test_a_parada_encurta_a_enquete_do_ouro(tmp_path):
    # Pergunta 1 e a de antes do clique, e passa. A 2 e a primeira volta da
    # enquete do Ouro, e para — antes de a enquete capturar qualquer coisa.
    tela = TelaFalsa([LISTA, LISTA_DEBITADA])
    mao = MaoFalsa()
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1),
                 interruptor=InterruptorFalso(parar_na_pergunta=2))
    # A Compra ja aconteceu: o Espaco foi apertado antes da enquete. O que a
    # parada faz e nao cumprir o teto de espera.
    assert ("apertar_espaco",) in mao.acoes
    # So a captura do pre-voo: a enquete parou antes de olhar de novo.
    assert tela.capturas_feitas == 1
    # E ABORTOU, e nao PAROU, de proposito: sem ler o Ouro depois do Espaco,
    # o piloto nao sabe se a Compra aconteceu. "Compra indeterminada" e a
    # verdade, e o operador que apertou F3 no meio da confirmacao precisa
    # ver isso, nao um "parou" limpo.
    assert r.desfecho is Desfecho.ABORTOU
    assert r.ouro_depois is None


def test_o_ritmo_tem_espera_entre_voltas():
    assert Ritmo().espera_entre_voltas == 1.0
    assert Ritmo.instantaneo().espera_entre_voltas == 0.0
```

Em `tests/test_piloto_cli.py`, no fim:

```python
def test_todo_desfecho_tem_codigo_de_saida():
    # O mapa foi escrito sem default de proposito: desfecho novo sem codigo
    # tem de estourar, nao sair 0 e virar indistinguivel de sucesso.
    for desfecho in Desfecho:
        assert desfecho in CODIGO_POR_DESFECHO


def test_parada_pedida_sai_com_zero():
    # F3 e decisao do operador, nao falha do bot.
    assert CODIGO_POR_DESFECHO[Desfecho.PAROU] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_piloto.py tests/test_piloto_cli.py -v`
Expected: FAIL com `AttributeError: PAROU` e `AttributeError: espera_entre_voltas`

- [ ] **Step 3: Implementar em `piloto.py`**

Adicione ao enum `Desfecho`, depois de `ABORTOU`:

```python
    # O operador pediu parada. Nao e falha: sai 0, ao contrario de ABORTOU.
    PAROU = "parou"
```

Adicione ao `Ritmo`, depois de `espera_categoria_carregar`:

```python
    # Respiro entre uma Volta e a proxima. Nao e cosmetico: como so o F3 para
    # o laco, uma tela que nao seja LISTA faz o pre-voo abortar na hora, e sem
    # esta espera o ciclo gira em rotacao maxima capturando a tela dezenas de
    # vezes por segundo. Mesmo valor de espera_categoria_carregar, e pelo
    # mesmo motivo: e palpite calibravel, nao medida.
    espera_entre_voltas: float = 1.0
```

E em `Ritmo.instantaneo()`, dentro do `return cls(...)`:

```python
            espera_entre_voltas=0.0,
```

Troque a assinatura de `executar`:

```python
def executar(tela: Tela, mao: Mao, config: Config, pasta: Path,
             simular: bool = False, ritmo: Ritmo = RITMO_PADRAO,
             sorteio: random.Random | None = None,
             interruptor: Interruptor | None = None) -> Resultado:
```

Importe `Interruptor` na linha de import dos protocolos:

```python
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
```

Logo antes do bloco do clique — depois do `if simular:` e antes de `x0, y0, x1, y1 =
caixa_slot(...)`:

```python
        # Ultimo ponto em que ainda ha o que abortar. Depois do Espaco a
        # Compra ja aconteceu, e entre o clique e o Espaco sobram 80-120 ms.
        if interruptor is not None and interruptor.pediram_parada():
            return encerrar(Desfecho.PAROU, "parada pedida antes do clique")
```

Troque a assinatura de `_esperar_o_ouro_cair` e o corpo do laço:

```python
def _esperar_o_ouro_cair(tela: Tela, diario: _Diario, r: Resultado,
                         ritmo: Ritmo,
                         interruptor: Interruptor | None = None) -> None:
```

Dentro do `while`, logo depois de `primeira_volta = False`:

```python
        if interruptor is not None and interruptor.pediram_parada():
            break
```

E na chamada, dentro de `executar`:

```python
        _esperar_o_ouro_cair(tela, diario, r, ritmo, interruptor)
```

- [ ] **Step 4: Implementar em `piloto_cli.py`**

Em `CODIGO_POR_DESFECHO`, adicione a entrada e atualize o comentário acima do mapa:

```python
    Desfecho.PAROU: 0,
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_piloto.py tests/test_piloto_cli.py -v`
Expected: PASS

- [ ] **Step 6: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. Nenhum teste antigo pode ter mudado — se algum falhar, o default
`None` do parâmetro novo não está preservando o comportamento.

- [ ] **Step 7: Commit**

```bash
git add src/mistfall/piloto.py ferramentas/piloto_cli.py tests/test_piloto.py tests/test_piloto_cli.py
git commit -m "O piloto obedece ao Interruptor antes do clique e na enquete do Ouro"
```

---

### Task 3: O ciclo, o laço e o Reset alternante

**Files:**
- Create: `src/mistfall/ciclo.py`
- Test: `tests/test_ciclo.py`

**Interfaces:**
- Consumes: `Desfecho`, `Resultado`, `Ritmo`, `RITMO_PADRAO`, `executar` de `piloto.py`;
  `CategoriaAlternativa`, `resetar_categoria` de `reset.py`; `Interruptor` dos protocolos.
- Produces: `Sessao(voltas: int, compras: int, ouro_gasto: int)` e
  `executar_ciclo(tela, mao, config, pasta, interruptor, ritmo=RITMO_PADRAO, sorteio=None) -> Sessao`.

- [ ] **Step 1: Escrever os testes que falham**

Crie `tests/test_ciclo.py`:

```python
"""O laco: quantas Voltas, quando reseta e com qual Categoria."""

import pathlib

import pytest

from mistfall.ciclo import Sessao, executar_ciclo
from mistfall.perifericos.falso import InterruptorFalso
from mistfall.piloto import Desfecho, Resultado, Ritmo
from mistfall.reset import CategoriaAlternativa


class _PilotoFalso:
    """Devolve desfechos de um roteiro, sem tocar em tela nem em mao.

    O ciclo e testado contra este duble, e nao contra o piloto de verdade:
    o que esta em jogo aqui e a decisao de resetar e a de parar, nao a
    Compra — essa ja tem os testes dela em test_piloto.py.
    """

    def __init__(self, roteiro: list[Resultado]) -> None:
        self.roteiro = list(roteiro)
        self.chamadas = 0

    def __call__(self, tela, mao, config, pasta, **kwargs) -> Resultado:
        self.chamadas += 1
        pathlib.Path(pasta).mkdir(parents=True, exist_ok=True)
        if self.roteiro:
            return self.roteiro.pop(0)
        return Resultado(Desfecho.NADA_COMPRAVEL)


class _ResetFalso:
    def __init__(self) -> None:
        self.categorias: list[CategoriaAlternativa] = []

    def __call__(self, tela, mao, ritmo=None, categoria_alternativa=None) -> bool:
        self.categorias.append(categoria_alternativa)
        return True


def _comprou(preco: int = 200) -> Resultado:
    return Resultado(Desfecho.COMPROU, ouro_antes=1000, ouro_depois=1000 - preco,
                     preco_total_esperado=preco)


def _rodar(monkeypatch, tmp_path, roteiro, parar_na_pergunta):
    piloto, reset = _PilotoFalso(roteiro), _ResetFalso()
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", reset)
    sessao = executar_ciclo(
        tela=None, mao=None, config=None, pasta=tmp_path,
        interruptor=InterruptorFalso(parar_na_pergunta=parar_na_pergunta),
        ritmo=Ritmo.instantaneo(),
    )
    return sessao, piloto, reset


def test_o_laco_espera_o_inicio_antes_de_qualquer_coisa(monkeypatch, tmp_path):
    interruptor = InterruptorFalso(parar_na_pergunta=1)
    monkeypatch.setattr("mistfall.ciclo.executar", _PilotoFalso([]))
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())
    executar_ciclo(tela=None, mao=None, config=None, pasta=tmp_path,
                   interruptor=interruptor, ritmo=Ritmo.instantaneo())
    assert interruptor.inicios == 1


def test_a_parada_encerra_o_laco_sem_rodar_volta(monkeypatch, tmp_path):
    _, piloto, _ = _rodar(monkeypatch, tmp_path, [_comprou()], parar_na_pergunta=1)
    assert piloto.chamadas == 0


def test_o_laco_roda_ate_a_parada(monkeypatch, tmp_path):
    sessao, piloto, _ = _rodar(
        monkeypatch, tmp_path, [_comprou(), _comprou(), _comprou()],
        parar_na_pergunta=4)
    assert piloto.chamadas == 3
    assert sessao.voltas == 3


def test_nada_compravel_dispara_reset(monkeypatch, tmp_path):
    _, _, reset = _rodar(monkeypatch, tmp_path,
                         [Resultado(Desfecho.NADA_COMPRAVEL)], parar_na_pergunta=2)
    assert reset.categorias == [CategoriaAlternativa.FORJA]


@pytest.mark.parametrize("desfecho", [
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU])
def test_os_outros_desfechos_nao_resetam(monkeypatch, tmp_path, desfecho):
    # A lista recarrega sozinha depois de uma Compra ou tentativa; abortar
    # nem chegou a mexer na tela.
    _, _, reset = _rodar(monkeypatch, tmp_path, [Resultado(desfecho)],
                         parar_na_pergunta=2)
    assert reset.categorias == []


def test_a_categoria_do_reset_alterna(monkeypatch, tmp_path):
    # Um Reset usa UMA Categoria alternativa. A alternancia e entre Resets
    # sucessivos, nunca dentro do mesmo.
    _, _, reset = _rodar(
        monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)] * 3,
        parar_na_pergunta=4)
    assert reset.categorias == [CategoriaAlternativa.FORJA,
                                CategoriaAlternativa.CHAVE,
                                CategoriaAlternativa.FORJA]


def test_a_sessao_conta_compras_e_ouro_gasto(monkeypatch, tmp_path):
    sessao, _, _ = _rodar(
        monkeypatch, tmp_path,
        [_comprou(200), Resultado(Desfecho.NADA_COMPRAVEL), _comprou(150)],
        parar_na_pergunta=4)
    assert sessao.voltas == 3
    assert sessao.compras == 2
    assert sessao.ouro_gasto == 350


def test_cada_volta_tem_a_propria_pasta(monkeypatch, tmp_path):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["volta-0001", "volta-0002"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'mistfall.ciclo'`

- [ ] **Step 3: Implementar**

Crie `src/mistfall/ciclo.py`:

```python
"""O laco: repete a Compra ate o operador pedir parada.

Nao duplica nada do piloto nem do reset — compoe os dois. O piloto continua
sendo "uma Compra e para"; quem sabe que existe uma proxima Volta e este
modulo.

So o F3 encerra o laco. Nenhuma falha o encerra, por mais que se repita:
decisao do dono do projeto, registrada na spec junto com o que ela deixa em
aberto. A `espera_entre_voltas` e o que impede uma tela errada de virar um
laco em rotacao maxima.
"""

import itertools
import random
import time
from dataclasses import dataclass
from pathlib import Path

from mistfall.config import Config
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.piloto import RITMO_PADRAO, Desfecho, Resultado, Ritmo, executar
from mistfall.reset import CategoriaAlternativa, resetar_categoria

# A ordem e a alternancia: um Reset usa uma Categoria alternativa, e o
# proximo usa a outra. Nunca as duas no mesmo Reset.
ALTERNANCIA = (CategoriaAlternativa.FORJA, CategoriaAlternativa.CHAVE)


@dataclass
class Sessao:
    """O acumulado da sessao, e nao a lista de Voltas.

    Guardar cada Resultado faria a memoria crescer sem teto numa sessao
    longa, que e exatamente o caso de uso.
    """

    voltas: int = 0
    compras: int = 0
    ouro_gasto: int = 0


def executar_ciclo(tela: Tela, mao: Mao, config: Config, pasta: Path,
                   interruptor: Interruptor, ritmo: Ritmo = RITMO_PADRAO,
                   sorteio: random.Random | None = None) -> Sessao:
    interruptor.esperar_inicio()

    sessao = Sessao()
    categorias = itertools.cycle(ALTERNANCIA)
    pasta = Path(pasta)

    while not interruptor.pediram_parada():
        sessao.voltas += 1
        pasta_da_volta = pasta / f"volta-{sessao.voltas:04d}"
        resultado = executar(tela, mao, config, pasta_da_volta, ritmo=ritmo,
                             sorteio=sorteio, interruptor=interruptor)
        _contabilizar(sessao, resultado)

        if resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            resetar_categoria(tela, mao, ritmo,
                              categoria_alternativa=next(categorias))

        time.sleep(ritmo.espera_entre_voltas)

    return sessao


def _contabilizar(sessao: Sessao, resultado: Resultado) -> None:
    if resultado.desfecho is not Desfecho.COMPROU:
        return
    sessao.compras += 1
    if resultado.ouro_antes is not None and resultado.ouro_depois is not None:
        sessao.ouro_gasto += resultado.ouro_antes - resultado.ouro_depois
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -v`
Expected: PASS

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde, com os testes novos de `test_ciclo.py` somados ao total.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/ciclo.py tests/test_ciclo.py
git commit -m "Adiciona o ciclo: laco de Voltas com Reset alternante"
```

---

### Task 4: A Volta de rotina não deixa PNG no disco

**Files:**
- Modify: `src/mistfall/ciclo.py`
- Test: `tests/test_ciclo.py`

**Interfaces:**
- Consumes: `executar_ciclo` da Task 3.
- Produces: nada novo na API pública. Efeito observável: `volta-NNNN/*.png` some quando o
  desfecho é `NADA_COMPRAVEL`; `relatorio.json` permanece sempre.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_ciclo.py`. Ajuste o `_PilotoFalso` para escrever os arquivos que o `_Diario`
de verdade escreveria — substitua o corpo do `__call__` por:

```python
    def __call__(self, tela, mao, config, pasta, **kwargs) -> Resultado:
        self.chamadas += 1
        pasta = pathlib.Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        # O que o _Diario de verdade deixa: um PNG por captura e o relatorio.
        (pasta / "00-pre-voo.png").write_bytes(b"png de mentira")
        (pasta / "relatorio.json").write_text("{}", encoding="utf-8")
        if self.roteiro:
            return self.roteiro.pop(0)
        return Resultado(Desfecho.NADA_COMPRAVEL)
```

E acrescente ao fim do arquivo:

```python
def test_volta_de_rotina_descarta_os_prints(monkeypatch, tmp_path):
    # NADA_COMPRAVEL e o caso comum e o que nao carrega informacao: uma tela
    # sem Item-alvo no Preco-alvo e o esperado na maioria das Voltas.
    _rodar(monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)],
           parar_na_pergunta=2)
    volta = tmp_path / "volta-0001"
    assert list(volta.glob("*.png")) == []


def test_volta_de_rotina_mantem_o_relatorio(monkeypatch, tmp_path):
    # O JSON e pequeno e e o que permite reconstruir a sessao depois.
    _rodar(monkeypatch, tmp_path, [Resultado(Desfecho.NADA_COMPRAVEL)],
           parar_na_pergunta=2)
    assert (tmp_path / "volta-0001" / "relatorio.json").exists()


@pytest.mark.parametrize("desfecho", [
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU])
def test_volta_interessante_guarda_os_prints(monkeypatch, tmp_path, desfecho):
    _rodar(monkeypatch, tmp_path, [Resultado(desfecho)], parar_na_pergunta=2)
    assert (tmp_path / "volta-0001" / "00-pre-voo.png").exists()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -k descarta -v`
Expected: FAIL — o PNG continua lá

- [ ] **Step 3: Implementar**

Em `src/mistfall/ciclo.py`, acrescente a constante depois de `ALTERNANCIA`:

```python
# Desfechos cuja Volta vale guardar inteira. O complemento — NADA_COMPRAVEL —
# e o caso comum e o unico que nao carrega diagnostico nenhum.
DESFECHOS_QUE_VALEM_PRINT = frozenset({
    Desfecho.COMPROU, Desfecho.OURO_NAO_CAIU, Desfecho.ABORTOU, Desfecho.PAROU,
})
```

E a função, no fim do módulo:

```python
def _descartar_os_prints(pasta: Path) -> None:
    """Apaga so os PNGs, nunca o relatorio.

    O descarte e do ciclo, e nao do piloto: quem sabe que a Volta foi rotina
    e quem viu o desfecho. O piloto continua gravando tudo e segue ignorante
    do laco.
    """
    for png in pasta.glob("*.png"):
        png.unlink()
```

Dentro de `executar_ciclo`, logo depois de `_contabilizar(sessao, resultado)`:

```python
        if resultado.desfecho not in DESFECHOS_QUE_VALEM_PRINT:
            _descartar_os_prints(pasta_da_volta)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -v`
Expected: PASS

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/ciclo.py tests/test_ciclo.py
git commit -m "A Volta de rotina descarta os prints e mantem o relatorio"
```

---

### Task 5: O feedback no PowerShell

**Files:**
- Modify: `src/mistfall/ciclo.py`
- Test: `tests/test_ciclo.py`

**Interfaces:**
- Consumes: `Sessao`, `executar_ciclo` das Tasks 3 e 4.
- Produces: `linha_da_volta(numero: int, resultado: Resultado, resetou: CategoriaAlternativa | None, relogio: str) -> str`
  e `linhas_do_fecho(sessao: Sessao) -> list[str]`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_ciclo.py`, no fim:

```python
import unicodedata

from mistfall.ciclo import linha_da_volta, linhas_do_fecho
from mistfall.tipos import ItemAlvo, Listagem


def _sem_acento(texto: str) -> bool:
    return texto == unicodedata.normalize("NFKD", texto).encode(
        "ascii", "ignore").decode("ascii")


def test_a_linha_da_compra_mostra_item_preco_e_ouro():
    listagem = Listagem(linha=0, coluna=0, item=ItemAlvo.BROCHE,
                        preco_unitario=200)
    linha = linha_da_volta(
        1, Resultado(Desfecho.COMPROU, listagem=listagem, ouro_antes=59227,
                     ouro_depois=59027), None, "23:47:12")
    assert "[0001]" in linha
    assert "23:47:12" in linha
    assert "comprou" in linha
    assert "200" in linha
    assert "59227" in linha and "59027" in linha


def test_a_linha_do_nada_compravel_diz_para_onde_resetou():
    linha = linha_da_volta(2, Resultado(Desfecho.NADA_COMPRAVEL),
                           CategoriaAlternativa.FORJA, "23:47:19")
    assert "Reset" in linha and "forja" in linha


def test_a_linha_do_ouro_nao_caiu_grita():
    # E o desfecho mais provavel da primeira execucao real (#9): tem de
    # saltar aos olhos numa tela que rola sozinha.
    linha = linha_da_volta(4, Resultado(Desfecho.OURO_NAO_CAIU,
                                        motivo="o Ouro nao se moveu"),
                           None, "23:47:33")
    assert "OURO NAO CAIU" in linha


def test_a_linha_do_aborto_carrega_o_motivo():
    linha = linha_da_volta(
        5, Resultado(Desfecho.ABORTOU, motivo="pre-voo viu janela, esperava lista"),
        None, "23:47:40")
    assert "esperava lista" in linha


@pytest.mark.parametrize("desfecho", list(Desfecho))
def test_nenhuma_linha_tem_acento(desfecho):
    # A pagina de codigo do console do Windows: o projeto inteiro escreve
    # saida sem acento, e esta e a unica superficie que o operador ve
    # enquanto o bot roda.
    linha = linha_da_volta(1, Resultado(desfecho, motivo="qualquer"),
                           CategoriaAlternativa.CHAVE, "00:00:00")
    assert _sem_acento(linha), linha


def test_o_fecho_resume_a_sessao():
    linhas = linhas_do_fecho(Sessao(voltas=12, compras=3, ouro_gasto=550))
    texto = "\n".join(linhas)
    assert "12" in texto and "3" in texto and "550" in texto
    assert _sem_acento(texto)


def test_o_laco_imprime_uma_linha_por_volta(monkeypatch, tmp_path, capsys):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    saida = capsys.readouterr().out
    assert "[0001]" in saida and "[0002]" in saida
    assert saida.count("comprou") == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -k linha -v`
Expected: FAIL com `ImportError: cannot import name 'linha_da_volta'`

- [ ] **Step 3: Implementar**

Em `src/mistfall/ciclo.py`, adicione ao topo do módulo (depois dos imports existentes):

```python
# Sem acento e sem cor. O projeto inteiro escreve saida de console assim, por
# causa da pagina de codigo do console do Windows: um mojibake na unica
# superficie que o operador ve enquanto o bot roda custa caro e nao avisa.
ROTULO_POR_DESFECHO = {
    Desfecho.COMPROU: "comprou",
    Desfecho.NADA_COMPRAVEL: "nada",
    Desfecho.OURO_NAO_CAIU: "OURO NAO CAIU",
    Desfecho.ABORTOU: "abortou",
    Desfecho.SIMULOU: "simulou",
    Desfecho.PAROU: "parou",
}
```

E as duas funções, antes de `executar_ciclo`:

```python
def linha_da_volta(numero: int, resultado: Resultado,
                   resetou: CategoriaAlternativa | None,
                   relogio: str) -> str:
    # Sem default no lookup: desfecho novo tem de estourar aqui, e nao virar
    # uma linha muda no meio de uma sessao longa.
    # Quatro digitos, como a pasta da Volta: a ~7 s por Volta, mil Voltas sao
    # duas horas de sessao, e tres digitos estourariam antes do fim do dia.
    partes = [f"[{numero:04d}]", relogio, ROTULO_POR_DESFECHO[resultado.desfecho]]

    if resultado.desfecho is Desfecho.COMPROU and resultado.listagem is not None:
        item = resultado.listagem.item
        partes.append(item.value if item is not None else "?")
        partes.append(f"{resultado.listagem.preco_unitario}g")
    if resultado.ouro_antes is not None and resultado.ouro_depois is not None:
        partes.append(f"Ouro {resultado.ouro_antes} -> {resultado.ouro_depois}")
    if resetou is not None:
        partes.append(f"-> Reset ({resetou.value})")
    if resultado.motivo:
        partes.append(resultado.motivo)

    return "  ".join(partes)


def linhas_do_fecho(sessao: Sessao) -> list[str]:
    return [
        "",
        f"parado. {sessao.voltas} Voltas, {sessao.compras} Compras, "
        f"{sessao.ouro_gasto} de Ouro gasto",
    ]
```

Dentro de `executar_ciclo`, guarde a Categoria usada e imprima. Substitua o bloco do Reset e
o do descarte por:

```python
        resetou = None
        if resultado.desfecho is Desfecho.NADA_COMPRAVEL:
            resetou = next(categorias)
            resetar_categoria(tela, mao, ritmo, categoria_alternativa=resetou)

        if resultado.desfecho not in DESFECHOS_QUE_VALEM_PRINT:
            _descartar_os_prints(pasta_da_volta)

        print(linha_da_volta(sessao.voltas, resultado, resetou,
                             time.strftime("%H:%M:%S")), flush=True)
```

E no fim da função, antes do `return sessao`:

```python
    for linha in linhas_do_fecho(sessao):
        print(linha, flush=True)
```

Cuidado com a ordem: o `next(categorias)` agora acontece **uma vez só** por Reset. Se ele
ficar tanto no `resetou =` quanto na chamada, a alternância pula uma Categoria a cada Reset e
o teste `test_a_categoria_do_reset_alterna` pega.

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_ciclo.py -v`
Expected: PASS

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/ciclo.py tests/test_ciclo.py
git commit -m "Uma linha por Volta no console, sem acento e sem cor"
```

---

### Task 6: `InterruptorWindows` e o CLI `mistfall-bot`

**Files:**
- Modify: `src/mistfall/perifericos/windows.py`
- Create: `ferramentas/bot_cli.py`
- Modify: `pyproject.toml:16-17`
- Test: `tests/test_perifericos_windows.py`
- Test: `tests/test_bot_cli.py`
- Test: `tests/test_instalacao.py`

**Interfaces:**
- Consumes: `executar_ciclo`, `Sessao` da Task 5; `Interruptor` da Task 1.
- Produces: `windows.VK_F2` (`0x71`), `windows.VK_F3` (`0x72`),
  `windows._tecla_foi_pressionada(vk: int) -> bool`, `windows.InterruptorWindows`;
  `ferramentas.bot_cli.main() -> int`; entry point `mistfall-bot`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_perifericos_windows.py`, no fim. Repare que este arquivo **pode** importar
`windows`, e é o único que pode — os testes monkeypatcham o helper de mais baixo nível em vez
de tocar em `windll`, exatamente como os testes de clique já fazem com `_enviar`.

```python
def test_esperar_inicio_bloqueia_ate_o_f2(monkeypatch):
    # A primeira chamada limpa o trinco: sem isso, um F2 apertado antes de o
    # bot subir faria o laco comecar sozinho.
    respostas = [False, False, False, True]
    vistos = []

    def falso(vk):
        vistos.append(vk)
        return respostas.pop(0)

    monkeypatch.setattr(windows, "_tecla_foi_pressionada", falso)
    monkeypatch.setattr(windows.time, "sleep", lambda _: None)
    windows.InterruptorWindows().esperar_inicio()
    assert vistos == [windows.VK_F2] * 4
    assert respostas == []


def test_pediram_parada_le_o_f3(monkeypatch):
    monkeypatch.setattr(windows, "_tecla_foi_pressionada",
                        lambda vk: vk == windows.VK_F3)
    assert windows.InterruptorWindows().pediram_parada() is True


def test_pediram_parada_e_falso_sem_f3(monkeypatch):
    monkeypatch.setattr(windows, "_tecla_foi_pressionada", lambda vk: False)
    assert windows.InterruptorWindows().pediram_parada() is False
```

Crie `tests/test_bot_cli.py`:

```python
"""O CLI do laco. Nao importa windows: a suite roda no macOS."""

from ferramentas.bot_cli import montar_parser


def test_o_parser_aceita_pasta_config_e_espera_modal():
    args = montar_parser().parse_args(
        ["--pasta", "sessao", "--config", "outro.toml", "--espera-modal", "150"])
    assert args.pasta == "sessao"
    assert args.config == "outro.toml"
    assert args.espera_modal == 150


def test_a_pasta_padrao_nao_e_a_do_piloto():
    # Duas ferramentas, dois destinos: o bot nao pode sobrescrever a pasta de
    # depuracao do mistfall-piloto.
    assert montar_parser().parse_args([]).pasta != "execucao"
```

Em `tests/test_instalacao.py`, acrescente:

```python
def test_o_entry_point_do_bot_existe():
    import tomllib, pathlib
    dados = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
    assert dados["project"]["scripts"]["mistfall-bot"] == "ferramentas.bot_cli:main"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_instalacao.py -v`
Expected: FAIL com `AttributeError: VK_F2` e `ModuleNotFoundError: ferramentas.bot_cli`

- [ ] **Step 3: Implementar em `windows.py`**

Depois das constantes de scancode existentes:

```python
# Virtual-key das teclas de controle do operador. Aqui e virtual-key mesmo, e
# nao scancode: GetAsyncKeyState le o teclado do lado de ca, e nao injeta
# evento no jogo — e o oposto do que o SendInput faz.
VK_F2 = 0x71
VK_F3 = 0x72
```

Depois de `_enviar`:

```python
def _tecla_foi_pressionada(vk: int) -> bool:
    """Trinco: a tecla foi pressionada desde a chamada anterior?

    O bit 0x0001 do GetAsyncKeyState guarda a transicao, e nao o estado
    atual. E o que faz o F3 ser notado mesmo quando apertado e solto durante
    um time.sleep do piloto — sem ele, so pegaria a tecla segurada no
    instante exato da pergunta.

    Se esse comportamento se mostrar instavel na maquina do jogo, o plano B
    e uma thread de fundo enquetando esta mesma funcao e guardando o flag:
    mesma interface, mesmos testes, mudanca contida neste arquivo.
    """
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x0001)


class InterruptorWindows:
    """F2 comeca, F3 para."""

    def __init__(self, intervalo: float = 0.05) -> None:
        self._intervalo = intervalo

    def esperar_inicio(self) -> None:
        # A primeira leitura descarta o trinco acumulado: sem ela, um F2
        # apertado antes de o bot subir faria o laco comecar sozinho.
        _tecla_foi_pressionada(VK_F2)
        while not _tecla_foi_pressionada(VK_F2):
            time.sleep(self._intervalo)

    def pediram_parada(self) -> bool:
        return _tecla_foi_pressionada(VK_F3)
```

- [ ] **Step 4: Implementar o CLI**

Crie `ferramentas/bot_cli.py`:

```python
"""Roda o laco de Compra ate o operador apertar F3.

Sem contagem regressiva: o F2 substitui o Alt+Tab cronometrado do
mistfall-piloto, porque e apertado de dentro do jogo.
"""

import argparse
import dataclasses
import sys
from pathlib import Path

from mistfall.ciclo import executar_ciclo
from mistfall.config import carregar_config
from mistfall.piloto import RITMO_PADRAO


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Repete a Compra no Leilao ate o F3.")
    p.add_argument("--pasta", default="sessao",
                   help="onde salvar as pastas de cada Volta")
    p.add_argument("--config", default="config.toml")
    p.add_argument("--espera-modal", type=int,
                   default=round(RITMO_PADRAO.espera_para_o_modal_abrir[0] * 1000),
                   help="ms entre o clique e o Espaco. E o PISO: a espera de "
                        "cada Compra e sorteada entre ele e 1,5x ele")
    return p


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)

    from mistfall.perifericos.windows import (
        InterruptorWindows, MaoWindows, TelaWindows,
    )

    piso = args.espera_modal / 1000
    ritmo = dataclasses.replace(
        RITMO_PADRAO, espera_para_o_modal_abrir=(piso, piso * 1.5))

    print("aperte F2 no jogo para comecar, F3 para parar", flush=True)
    sessao = executar_ciclo(
        TelaWindows(), MaoWindows(), config, Path(args.pasta),
        InterruptorWindows(), ritmo=ritmo,
    )
    print(f"pastas das Voltas em {args.pasta}")
    return 0 if sessao.voltas else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Registrar o entry point**

Em `pyproject.toml`, na seção `[project.scripts]`:

```toml
mistfall-bot = "ferramentas.bot_cli:main"
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_instalacao.py -v`
Expected: PASS

- [ ] **Step 7: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. O guarda de imports de `test_perifericos_windows.py` tem de continuar
verde: `bot_cli.py` importa `windows` **dentro** de `_rodar`, nunca no topo.

- [ ] **Step 8: Commit**

```bash
git add src/mistfall/perifericos/windows.py ferramentas/bot_cli.py pyproject.toml tests/test_perifericos_windows.py tests/test_bot_cli.py tests/test_instalacao.py
git commit -m "Liga o laco no Windows: F2 comeca, F3 para, mistfall-bot roda"
```

---

### Task 7: A documentação alcança o código

**Files:**
- Modify: `CONTEXT.md`
- Modify: `README.md`
- Modify: `docs/adr/0001-dev-mac-run-windows.md:64-71`
- Test: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: tudo das Tasks 1-6.
- Produces: nada de código.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_documentacao.py`, no fim:

```python
def test_o_glossario_define_volta():
    assert "**Volta**" in CONTEXT


def test_o_glossario_define_interruptor():
    assert "**Interruptor**" in CONTEXT


def test_o_readme_documenta_as_teclas():
    assert "F2" in README and "F3" in README


def test_o_adr_nao_diz_mais_que_o_clique_nao_foi_confirmado():
    # A execucao real confirmou: execucao-real/01-janela.png existe, ou seja
    # o bot clicou e a Janela abriu.
    adr = pathlib.Path("docs/adr/0001-dev-mac-run-windows.md").read_text(
        encoding="utf-8")
    assert "Que o clique com duração resolve" not in adr
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_documentacao.py -v`
Expected: FAIL nos quatro

- [ ] **Step 3: Acrescentar os termos ao `CONTEXT.md`**

No fim do arquivo, seguindo o formato das entradas existentes:

```markdown
**Volta**:
Uma iteração do laço de Compra: uma varredura e, conforme o desfecho, uma Compra ou um
Reset. A sessão do bot é uma sequência de Voltas, e cada uma guarda a própria pasta de
prints e relatório.
_Avoid_: Iteração, Ciclo, Rodada.

**Interruptor**:
O par de teclas com que o operador liga e desliga o bot: F2 começa, F3 para. É a terceira
fronteira de IO, ao lado da Tela e da Mão, e o F3 é consultado antes de cada clique e
durante a espera pelo Ouro — nunca entre o clique e o Espaço, onde já não há o que abortar.
_Avoid_: Hotkey, Atalho, Tecla de pânico.
```

- [ ] **Step 4: Documentar o bot no `README.md`**

Acrescente uma seção junto de onde o `mistfall-piloto` já é descrito:

```markdown
### Rodar o laço

```
mistfall-bot --pasta sessao
```

Aperte **F2** dentro do jogo para começar e **F3** para parar. Cada Volta imprime uma linha
no console e guarda a própria pasta; as Voltas sem nada comprável descartam os prints e
mantêm só o relatório.

Não há piso de Ouro: o bot compra enquanto houver Listagem no Preço-alvo e Ouro na conta, e
o único freio é o F3.
```

- [ ] **Step 5: Corrigir o ADR-0001**

Substitua a seção "## O que ainda não foi observado" por:

```markdown
## O que a execução seguinte confirmou

**O clique com duração resolve.** A execução guardada em `execucao-real/` clicou numa
Listagem e a Janela de Confirmação abriu — o `01-janela.png` é a evidência. A correção
derivada por eliminação acima está certa.

O que continua sem observação é o **Espaço**: aquela execução abortou lendo o modal, e
nenhuma Compra jamais completou. É o que a [#9](https://github.com/lavarini/mistfall-reseller/issues/9)
existe para responder, e a razão de o desfecho `OURO_NAO_CAIU` ser um código de saída
próprio.

Se administrador é necessário para alguma coisa também segue em aberto.
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_documentacao.py -v`
Expected: PASS

- [ ] **Step 7: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. Este é o portão final do plano: 286 testes originais mais os novos,
sem nenhum removido.

- [ ] **Step 8: Commit**

```bash
git add CONTEXT.md README.md docs/adr/0001-dev-mac-run-windows.md tests/test_documentacao.py
git commit -m "Documenta a Volta, o Interruptor e o clique ja confirmado"
```

---

## Depois do plano, e fora dele

Três coisas ficam pendentes de propósito, e cada uma é decisão do dono do projeto:

- **A issue #6** tem critérios de aceite que o ADR-0003 tornou obsoletos (conferência dupla
  do preço, esperar a Janela ser detectada antes do Espaço). Fechá-la sem ajustar seria
  fechar mentindo.
- **A #8 fica com dois terços em aberto**: sem piso de Ouro e sem log estruturado de Compras.
- **O trinco do `GetAsyncKeyState`** só se confirma na máquina do jogo. É a única premissa
  deste plano que nenhum teste alcança.
