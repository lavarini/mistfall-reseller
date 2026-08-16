# Espera de Estabilização após Compra — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Esperar entre 300 e 400 ms antes da próxima Volta somente quando a Volta anterior enviou uma Compra, mantendo 150 ms nos demais casos.

**Architecture:** `Ritmo` passa a declarar a faixa pós-Compra, enquanto uma função pura em `mistfall.ciclo` seleciona a espera a partir do desfecho e do `Random` da sessão. O loop dorme o valor selecionado e conserva a medição efetiva já existente, sem nova telemetria ou detecção visual.

**Tech Stack:** Python 3.14, `random.Random`, `dataclasses`, pytest e os dublês existentes do ciclo.

## Global Constraints

- `COMPRA_ENVIADA` usa distribuição uniforme entre `0.30` e `0.40` segundo.
- A média estatística da faixa pós-Compra é `0.35` segundo.
- Todos os outros desfechos que continuam o ciclo mantêm `espera_entre_voltas=0.15` segundo.
- `PAROU` encerra antes de qualquer espera.
- Usar a mesma instância de `random.Random` da sessão; não consultar o estado global de `random`.
- `Ritmo.instantaneo()` define a faixa pós-Compra como `(0.0, 0.0)` e a espera comum como `0.0`.
- Preservar decisão, Reset, Ouro, capturas, cliques, teclas, alternância e fluxo de Venda.
- Não adicionar detecção visual, configuração TOML, opção de CLI, dependência, campo ou arquivo de telemetria.
- A telemetria existente continua registrando a duração efetiva da espera quando a Volta seguinte começa.
- Preservar todas as pastas locais `sessao*/` fora dos commits.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade nesta mudança |
| --- | --- |
| `src/mistfall/piloto.py` | Declarar `espera_apos_compra=(0.30, 0.40)` e zerá-la no ritmo instantâneo. |
| `src/mistfall/ciclo.py` | Selecionar a espera por desfecho e usar o gerador da sessão. |
| `tests/test_piloto.py` | Provar os valores padrão e instantâneo do contrato de ritmo. |
| `tests/test_ciclo.py` | Provar faixa, diversidade, reprodução, isolamento global, desfechos e telemetria. |
| `tests/test_bot_cli.py` | Provar que a construção do ritmo pelo CLI preserva a faixa padrão. |
| `README.md` | Explicar 300–400 ms após Compra e 150 ms nas demais Voltas. |

### Task 1: Definir o contrato e selecionar a espera

**Files:**
- Modify: `src/mistfall/piloto.py`
- Modify: `src/mistfall/ciclo.py`
- Modify: `tests/test_piloto.py`
- Modify: `tests/test_ciclo.py`

**Interfaces:**
- Produces: `Ritmo.espera_apos_compra: tuple[float, float] = (0.30, 0.40)`.
- Produces: `_espera_para_proxima_volta(desfecho: Desfecho, ritmo: Ritmo, sorteio: random.Random) -> float`.

- [ ] **Step 1: Escrever o teste vermelho do contrato de ritmo**

Substituir `test_o_ritmo_tem_espera_entre_voltas` em `tests/test_piloto.py` por:

```python
def test_o_ritmo_separa_espera_comum_e_espera_apos_compra():
    assert Ritmo().espera_entre_voltas == 0.15
    assert Ritmo().espera_apos_compra == (0.30, 0.40)
    assert Ritmo.instantaneo().espera_entre_voltas == 0.0
    assert Ritmo.instantaneo().espera_apos_compra == (0.0, 0.0)
```

- [ ] **Step 2: Rodar o teste e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py::test_o_ritmo_separa_espera_comum_e_espera_apos_compra -q
```

Expected: FAIL com `AttributeError` porque `espera_apos_compra` ainda não existe.

- [ ] **Step 3: Adicionar a faixa ao Ritmo**

Em `src/mistfall/piloto.py`, logo depois de `espera_entre_voltas`, adicionar:

```python
# Tempo extra para a lista se reorganizar depois de uma Compra enviada.
# So o ciclo conhece o desfecho e decide quando usar esta faixa.
espera_apos_compra: tuple[float, float] = (0.30, 0.40)
```

Em `Ritmo.instantaneo()` adicionar:

```python
espera_apos_compra=(0.0, 0.0),
```

- [ ] **Step 4: Rodar o teste de ritmo e confirmar que passa**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py::test_o_ritmo_separa_espera_comum_e_espera_apos_compra -q
```

Expected: PASS.

- [ ] **Step 5: Escrever testes vermelhos da seleção pura**

Em `tests/test_ciclo.py`, importar `_espera_para_proxima_volta` e `dataclasses`:

```python
import dataclasses

from mistfall.ciclo import Sessao, _espera_para_proxima_volta, executar_ciclo
```

Adicionar:

```python
def test_compra_enviada_sorteia_espera_na_faixa_pos_compra():
    ritmo = Ritmo()
    vistos = {
        _espera_para_proxima_volta(
            Desfecho.COMPRA_ENVIADA, ritmo, random.Random(semente),
        )
        for semente in range(12)
    }
    assert len(vistos) > 1
    assert all(0.30 <= espera <= 0.40 for espera in vistos)


def test_mesma_semente_reproduz_espera_pos_compra():
    ritmo = Ritmo()
    primeira = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(91),
    )
    segunda = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(91),
    )
    assert primeira == segunda


def test_sorteio_injetado_da_espera_independe_do_random_global():
    ritmo = Ritmo()
    random.seed(1)
    primeira = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(73),
    )
    random.seed(999)
    segunda = _espera_para_proxima_volta(
        Desfecho.COMPRA_ENVIADA, ritmo, random.Random(73),
    )
    assert primeira == segunda


@pytest.mark.parametrize(
    "desfecho",
    [Desfecho.NADA_COMPRAVEL, Desfecho.ABORTOU, Desfecho.SIMULOU],
)
def test_desfecho_sem_compra_mantem_espera_comum(desfecho):
    ritmo = dataclasses.replace(Ritmo.instantaneo(), espera_entre_voltas=0.15)
    assert _espera_para_proxima_volta(
        desfecho, ritmo, random.Random(42),
    ) == 0.15
```

`PAROU` não entra nesse helper em produção porque o ciclo interrompe antes dele; esse contrato será testado na integração da Task 2.

- [ ] **Step 6: Rodar os testes da seleção e confirmar a falha**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo.py -q
```

Expected: FAIL na coleta porque `_espera_para_proxima_volta` ainda não existe.

- [ ] **Step 7: Implementar a seleção mínima**

Em `src/mistfall/ciclo.py`, depois de `linhas_do_fecho`, adicionar:

```python
def _espera_para_proxima_volta(
    desfecho: Desfecho,
    ritmo: Ritmo,
    sorteio: random.Random,
) -> float:
    if desfecho is Desfecho.COMPRA_ENVIADA:
        return sorteio.uniform(*ritmo.espera_apos_compra)
    return ritmo.espera_entre_voltas
```

Não chamar o helper no loop ainda; a integração fica na Task 2.

- [ ] **Step 8: Rodar testes focados do contrato e seleção**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py tests/test_ciclo.py -q
```

Expected: PASS.

- [ ] **Step 9: Commitar contrato e seleção**

```bash
git add src/mistfall/piloto.py src/mistfall/ciclo.py tests/test_piloto.py tests/test_ciclo.py
git commit -m "Define espera especifica apos Compra"
```

### Task 2: Aplicar a espera, preservar telemetria e documentar

**Files:**
- Modify: `src/mistfall/ciclo.py`
- Modify: `tests/test_ciclo.py`
- Modify: `tests/test_bot_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `Ritmo.espera_apos_compra` e `_espera_para_proxima_volta(...)` da Task 1.
- Preserva: `executar_ciclo(..., sorteio: random.Random | None = None) -> Sessao`.
- Preserva: formato atual de `tempos-do-laco.jsonl`.

- [ ] **Step 1: Criar um relógio de teste que mede a espera aplicada**

Em `tests/test_ciclo.py`, importar `SimpleNamespace` e adicionar:

```python
from types import SimpleNamespace


class _RelogioFalso:
    def __init__(self):
        self.agora = 100.0
        self.esperas = []

    def monotonic(self):
        return self.agora

    def sleep(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos

    def strftime(self, _formato):
        return "12:00:00"


def _instalar_relogio(monkeypatch):
    relogio = _RelogioFalso()
    monkeypatch.setattr(
        "mistfall.ciclo.time",
        SimpleNamespace(
            monotonic=relogio.monotonic,
            sleep=relogio.sleep,
            strftime=relogio.strftime,
        ),
    )
    return relogio
```

- [ ] **Step 2: Escrever testes vermelhos para Compra, outros desfechos e PAROU**

Adicionar a `tests/test_ciclo.py`:

```python
def test_ciclo_aplica_espera_pos_compra(monkeypatch, tmp_path):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(), espera_apos_compra=(0.30, 0.40),
    )
    piloto = _PilotoFalso([_compra_enviada(), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    assert len(relogio.esperas) == 1
    assert 0.30 <= relogio.esperas[0] <= 0.40


@pytest.mark.parametrize("desfecho", [Desfecho.NADA_COMPRAVEL, Desfecho.ABORTOU])
def test_ciclo_mantem_150_ms_quando_nao_compra(
    monkeypatch, tmp_path, desfecho,
):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(),
        espera_entre_voltas=0.15,
        espera_apos_compra=(0.30, 0.40),
    )
    piloto = _PilotoFalso([Resultado(desfecho), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    assert relogio.esperas == [0.15]


def test_parou_nao_dorme(monkeypatch, tmp_path):
    relogio = _instalar_relogio(monkeypatch)
    piloto = _PilotoFalso([Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=2),
        ritmo=Ritmo(),
        sorteio=random.Random(42),
    )

    assert relogio.esperas == []
```

O caso `NADA_COMPRAVEL` usa `_ResetFalso`, portanto também prova que uma Volta com Reset mantém os 150 ms.

- [ ] **Step 3: Fortalecer o teste da telemetria existente**

Substituir `test_o_laco_so_registra_intervalo_quando_a_proxima_volta_comeca` por um teste com o relógio falso e uma Compra seguida de `PAROU`:

```python
def test_telemetria_registra_espera_pos_compra_realmente_aplicada(
    monkeypatch, tmp_path,
):
    relogio = _instalar_relogio(monkeypatch)
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(), espera_apos_compra=(0.35, 0.35),
    )
    piloto = _PilotoFalso([_compra_enviada(), Resultado(Desfecho.PAROU)])
    monkeypatch.setattr("mistfall.ciclo.executar", piloto)
    monkeypatch.setattr("mistfall.ciclo.resetar_categoria", _ResetFalso())

    executar_ciclo(
        None, None, None, tmp_path,
        InterruptorFalso(parar_na_pergunta=3),
        ritmo=ritmo,
        sorteio=random.Random(42),
    )

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "tempos-do-laco.jsonl").read_text().splitlines()
    ]
    assert len(linhas) == 1
    assert linhas[0]["espera_efetiva_ms"] == 350.0
    assert linhas[0]["intervalo_entre_inicios_ms"] == 350.0
    assert relogio.esperas == [0.35]
```

- [ ] **Step 4: Rodar os testes do ciclo e confirmar as falhas**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo.py -q
```

Expected: os testes de Compra e telemetria FAIL porque o loop ainda usa sempre `espera_entre_voltas`; os testes de 150 ms e `PAROU` já podem passar.

- [ ] **Step 5: Ligar a seleção ao ponto único de espera do loop**

Em `src/mistfall/ciclo.py`, substituir:

```python
time.sleep(ritmo.espera_entre_voltas)
```

por:

```python
espera = _espera_para_proxima_volta(resultado.desfecho, ritmo, sorteio)
time.sleep(espera)
```

Manter `inicio_espera` imediatamente antes e `espera_anterior` imediatamente depois do `sleep`, para preservar a medição da duração real. Não mover o bloco acima do `if resultado.desfecho is Desfecho.PAROU: break`.

- [ ] **Step 6: Rodar os testes de ciclo e piloto**

Run:

```bash
.venv/bin/python -m pytest tests/test_ciclo.py tests/test_piloto.py -q
```

Expected: PASS.

- [ ] **Step 7: Atualizar a verificação do ritmo construído pelo CLI**

Em `tests/test_bot_cli.py::test_parar_antes_da_primeira_volta_sai_com_sucesso`, acrescentar:

```python
assert ritmo.espera_apos_compra == (0.30, 0.40)
```

Nenhuma alteração em `ferramentas/bot_cli.py` é necessária: `dataclasses.replace` preserva os demais campos do `Ritmo`.

- [ ] **Step 8: Documentar o comportamento operacional**

Em `README.md`, junto à descrição do loop de Compra, acrescentar:

```markdown
Depois de uma Compra enviada, o loop espera um valor sorteado entre 300 e 400 ms para a
lista se atualizar antes da próxima captura. Voltas sem Compra mantêm a espera fixa de
150 ms, evitando desacelerar a varredura comum.
```

- [ ] **Step 9: Rodar a suíte completa e verificar o diff**

Run:

```bash
.venv/bin/python -m pytest -q
git diff --check
git status --short
```

Expected: suíte completa PASS; `git diff --check` sem saída; somente os arquivos desta mudança aparecem modificados, além das pastas locais `sessao*/` não versionadas.

- [ ] **Step 10: Commitar integração e documentação**

```bash
git add src/mistfall/ciclo.py tests/test_ciclo.py tests/test_bot_cli.py README.md
git commit -m "Aplica espera maior apos Compra enviada"
```

- [ ] **Step 11: Verificar o estado final**

Run:

```bash
.venv/bin/python -m pytest -q
git log -2 --oneline
git status --short
```

Expected: suíte completa PASS; dois commits de implementação no topo; nenhuma alteração versionada pendente; todas as pastas `sessao*/` permanecem preservadas.
