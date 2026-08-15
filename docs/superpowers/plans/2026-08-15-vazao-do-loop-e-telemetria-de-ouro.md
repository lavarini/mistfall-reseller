# Vazão do laço e telemetria de Ouro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retirar a confirmação de Ouro do caminho crítico, reduzir as esperas deliberadas e sobrepor a leitura de Ouro à varredura, preservando telemetria suficiente para medir a vazão real no Windows.

**Architecture:** O piloto captura e valida o estado uma vez, depois entrega o frame imutável a um novo coordenador de análise com dois ramos: Ouro e Listagens. O laço escreve telemetria de sessão em JSONL e trata Espaço enviado como `COMPRA_ENVIADA`, sem captura ou espera posterior. Instrumentação interna separa tempos sobrepostos e uma ferramenta de bancada compara análise sequencial e concorrente sem alterar o caminho de produção.

**Tech Stack:** Python 3.14, `concurrent.futures.ThreadPoolExecutor`, OpenCV, pytesseract/tesseract, JSON Lines, pytest.

## Global Constraints

- Ouro é somente telemetria: `None` não aborta, não impede Compra e não produz sinalizador de pânico.
- A varredura mantém exatamente uma chamada ao tesseract para a folha com os 12 Preços-unitários; nunca reintroduzir 12 OCRs individuais.
- O executor da análise inicial tem exatamente dois trabalhos de alto nível: Ouro e varredura.
- O frame inicial é capturado uma vez e compartilhado somente para leitura.
- A faixa entre clique e Espaço permanece em 80–120 ms.
- A pausa antes do clique passa para 50–150 ms e a espera entre Voltas para 150 ms.
- Não existe captura, OCR, enquete ou espera exclusiva depois de Espaço.
- O desfecho vivo é `COMPRA_ENVIADA`; não afirmar que a Compra foi confirmada.
- Métricas de ramos concorrentes incluem os tempos dos ramos e `analise_inicial_parede`; não somar tempos sobrepostos.
- A decisão de ativar concorrência no Windows depende de benchmark com o jogo aberto e igualdade exata do corpus.
- Fora de escopo: regras de pânico por Ouro, causa das 12 tentativas perdidas, espera adaptativa, OCR persistente, paralelismo por slot e otimização do Reset.

---

## Estrutura de arquivos

- Criar `src/mistfall/analise.py`: coordenar leitura de Ouro e varredura, sequencial ou concorrente, e devolver tempos dos dois ramos.
- Criar `src/mistfall/telemetria.py`: escrever `telemetria-ouro.jsonl` e `tempos-do-laco.jsonl`; não conter regra de negócio.
- Criar `ferramentas/benchmark_analise.py`: comparar os dois modos sobre `00-pre-voo.png` sem tocar no jogo.
- Criar `tests/test_analise.py`, `tests/test_telemetria.py` e `tests/test_benchmark_analise.py`: testar os novos limites isoladamente.
- Modificar `src/mistfall/precos.py` e `src/mistfall/leilao.py`: expor tempos internos sem alterar resultados ou multiplicar OCRs.
- Modificar `src/mistfall/piloto.py`: usar a análise coordenada, renomear o desfecho, remover confirmação pós-Espaço e publicar a observação por callback.
- Modificar `src/mistfall/ciclo.py`: escrever telemetria, medir intervalos do laço e contar Compras enviadas.
- Modificar `ferramentas/piloto_cli.py` e `ferramentas/bot_cli.py`: alinhar saída, códigos e ritmo.
- Modificar testes existentes e `README.md`: remover a semântica de confirmação de Ouro e documentar artefatos e benchmark.

---

### Task 1: Instrumentar a folha e a identificação de Itens-alvo

**Files:**
- Modify: `src/mistfall/precos.py`
- Modify: `src/mistfall/leilao.py`
- Test: `tests/test_precos.py`
- Test: `tests/test_leilao.py`

**Interfaces:**
- Consumes: `time.monotonic()`, `identificar_item(regiao)`, `ler_precos(recortes)`.
- Produces: `ler_precos(recortes: list[np.ndarray], tempos: dict[str, float] | None = None) -> list[int | None]` e `varrer_bruto(img: np.ndarray, tempos: dict[str, float] | None = None) -> list[Listagem]`.
- Os valores de `tempos` são milissegundos e usam as chaves `preparo_folha`, `tesseract_precos` e `itens`.

- [ ] **Step 1: Escrever testes vermelhos para os tempos internos**

Acrescente em `tests/test_precos.py`:

```python
def test_ler_precos_registra_preparo_e_tesseract_sem_mudar_resultado():
    tempos = {}
    assert ler_precos(_recortes(LISTA), tempos) == PRECOS_DA_LISTA
    assert set(tempos) == {"preparo_folha", "tesseract_precos"}
    assert all(ms >= 0 for ms in tempos.values())
```

Acrescente em `tests/test_leilao.py`:

```python
def test_varredura_bruta_registra_itens_e_tempos_da_folha():
    tempos = {}
    listagens = varrer_bruto(cv2.imread(LISTA), tempos)
    assert len(listagens) == 12
    assert set(tempos) == {"itens", "preparo_folha", "tesseract_precos"}
    assert all(ms >= 0 for ms in tempos.values())
```

- [ ] **Step 2: Rodar os testes e confirmar a falha de assinatura**

Run:

```bash
.venv/bin/python -m pytest tests/test_precos.py::test_ler_precos_registra_preparo_e_tesseract_sem_mudar_resultado tests/test_leilao.py::test_varredura_bruta_registra_itens_e_tempos_da_folha -v
```

Expected: FAIL com `TypeError` porque as funções ainda não aceitam `tempos`.

- [ ] **Step 3: Instrumentar sem mudar o contrato padrão**

Em `src/mistfall/precos.py`, importe `time` e mude a assinatura. Meça `_preparar` e a montagem da folha em `preparo_folha`; meça somente `pytesseract.image_to_data` em `tesseract_precos`:

```python
def ler_precos(recortes: list[np.ndarray],
               tempos: dict[str, float] | None = None) -> list[int | None]:
    if not recortes:
        if tempos is not None:
            tempos["preparo_folha"] = 0.0
            tempos["tesseract_precos"] = 0.0
        return []

    inicio = time.monotonic()
    pilha = [_preparar(recorte) for recorte in recortes]
    pecas: list[np.ndarray] = []
    faixas: list[tuple[int, int]] = []
    topo = 0
    for preparado in pilha:
        pecas.append(preparado)
        faixas.append((topo, topo + preparado.shape[0]))
        topo += preparado.shape[0]
        pecas.append(np.zeros((SEPARADOR, preparado.shape[1]), dtype=np.uint8))
        topo += SEPARADOR
    folha = np.vstack(pecas)
    if tempos is not None:
        tempos["preparo_folha"] = (time.monotonic() - inicio) * 1000

    inicio = time.monotonic()
    dados = pytesseract.image_to_data(
        folha, config=_CONFIG_FOLHA, output_type=pytesseract.Output.DICT,
    )
    if tempos is not None:
        tempos["tesseract_precos"] = (time.monotonic() - inicio) * 1000

    por_faixa: list[list[int]] = [[] for _ in recortes]
    for texto, y, altura in zip(dados["text"], dados["top"], dados["height"]):
        texto = texto.strip()
        if not texto.isdigit():
            continue
        centro = y + altura / 2
        for indice, (inicio_faixa, fim_faixa) in enumerate(faixas):
            if inicio_faixa <= centro < fim_faixa:
                por_faixa[indice].append(int(texto))
                break
    return [numeros[0] if len(numeros) == 1 else None for numeros in por_faixa]
```

Em `src/mistfall/leilao.py`, importe `time`, meça toda a compreensão de ícones e repasse o mesmo dicionário à folha:

```python
def varrer_bruto(img: np.ndarray,
                 tempos: dict[str, float] | None = None) -> list[Listagem]:
    icones = [regiao_icone(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    precos = [recorte_preco(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    inicio = time.monotonic()
    itens = [identificar_item(icone) for icone in icones]
    if tempos is not None:
        tempos["itens"] = (time.monotonic() - inicio) * 1000
    lidos = ler_precos(precos, tempos)
    return [
        Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)
        for (linha, coluna), item, preco in zip(TODOS_OS_SLOTS, itens, lidos)
    ]
```

`varrer(img)` continua sem parâmetro novo; somente o caminho de diagnóstico usa `varrer_bruto(..., tempos)`.

- [ ] **Step 4: Rodar testes focados e as regressões da visão**

Run:

```bash
.venv/bin/python -m pytest tests/test_precos.py tests/test_leilao.py tests/test_regressao.py -q
```

Expected: PASS; o teste existente de uma única chamada ao tesseract continua verde.

- [ ] **Step 5: Commitar a instrumentação isolada**

```bash
git add src/mistfall/precos.py src/mistfall/leilao.py tests/test_precos.py tests/test_leilao.py
git commit -m "Mede os custos internos da varredura"
```

---

### Task 2: Coordenar Ouro e Listagens em dois ramos

**Files:**
- Create: `src/mistfall/analise.py`
- Create: `tests/test_analise.py`

**Interfaces:**
- Consumes: `ler_ouro(img) -> int | None`, `varrer_bruto(img, tempos) -> list[Listagem]` da Task 1.
- Produces: `AnaliseInicial(ouro_observado: int | None, brutas: list[Listagem], tempos: dict[str, float])` e `analisar_inicial(img: np.ndarray, *, concorrente: bool = True) -> AnaliseInicial`.
- `tempos` sempre contém `ouro`, `varredura_total`, `itens`, `preparo_folha`, `tesseract_precos` e `analise_inicial_parede`.

- [ ] **Step 1: Escrever testes vermelhos para concorrência e equivalência**

Crie `tests/test_analise.py`:

```python
import threading
import time
from types import SimpleNamespace

import numpy as np

from mistfall import analise


IMG = np.zeros((2, 2, 3), dtype=np.uint8)


def test_sequencial_e_concorrente_devolvem_o_mesmo(monkeypatch):
    monkeypatch.setattr(analise, "ler_ouro", lambda _: 1234)

    def varrer(_, tempos):
        tempos.update(itens=1.0, preparo_folha=2.0, tesseract_precos=3.0)
        return ["listagem"]

    monkeypatch.setattr(analise, "varrer_bruto", varrer)
    sequencial = analise.analisar_inicial(IMG, concorrente=False)
    concorrente = analise.analisar_inicial(IMG, concorrente=True)
    assert sequencial.ouro_observado == concorrente.ouro_observado == 1234
    assert sequencial.brutas == concorrente.brutas == ["listagem"]
    assert set(concorrente.tempos) == {
        "ouro", "varredura_total", "itens", "preparo_folha",
        "tesseract_precos", "analise_inicial_parede",
    }


def test_modo_concorrente_roda_os_dois_ramos_em_threads_diferentes(monkeypatch):
    barreira = threading.Barrier(2, timeout=1)
    threads = []

    def ouro(_):
        threads.append(threading.current_thread())
        barreira.wait()
        return 10

    def varrer(_, tempos):
        threads.append(threading.current_thread())
        barreira.wait()
        tempos.update(itens=0.0, preparo_folha=0.0, tesseract_precos=0.0)
        return []

    monkeypatch.setattr(analise, "ler_ouro", ouro)
    monkeypatch.setattr(analise, "varrer_bruto", varrer)
    analise.analisar_inicial(IMG, concorrente=True)
    assert len({thread.ident for thread in threads}) == 2


def test_tempo_de_parede_nao_e_soma_dos_ramos(monkeypatch):
    def ouro(_):
        time.sleep(0.03)
        return 10

    def varrer(_, tempos):
        time.sleep(0.03)
        tempos.update(itens=0.0, preparo_folha=0.0, tesseract_precos=0.0)
        return []

    monkeypatch.setattr(analise, "ler_ouro", ouro)
    monkeypatch.setattr(analise, "varrer_bruto", varrer)
    resultado = analise.analisar_inicial(IMG, concorrente=True)
    assert resultado.tempos["analise_inicial_parede"] < (
        resultado.tempos["ouro"] + resultado.tempos["varredura_total"]
    )
```

- [ ] **Step 2: Rodar e confirmar que o módulo ainda não existe**

Run:

```bash
.venv/bin/python -m pytest tests/test_analise.py -v
```

Expected: FAIL na importação de `mistfall.analise`.

- [ ] **Step 3: Implementar o coordenador com exatamente dois trabalhos**

Crie `src/mistfall/analise.py`:

```python
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from mistfall.leilao import varrer_bruto
from mistfall.ouro import ler_ouro
from mistfall.tipos import Listagem


@dataclass(frozen=True)
class AnaliseInicial:
    ouro_observado: int | None
    brutas: list[Listagem]
    tempos: dict[str, float]


def _ouro(img: np.ndarray) -> tuple[int | None, float]:
    inicio = time.monotonic()
    valor = ler_ouro(img)
    return valor, (time.monotonic() - inicio) * 1000


def _listagens(img: np.ndarray) -> tuple[list[Listagem], dict[str, float]]:
    tempos: dict[str, float] = {}
    inicio = time.monotonic()
    brutas = varrer_bruto(img, tempos)
    tempos["varredura_total"] = (time.monotonic() - inicio) * 1000
    return brutas, tempos


def analisar_inicial(img: np.ndarray, *, concorrente: bool = True) -> AnaliseInicial:
    inicio = time.monotonic()
    if concorrente:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_ouro = executor.submit(_ouro, img)
            futuro_listagens = executor.submit(_listagens, img)
            ouro_observado, tempo_ouro = futuro_ouro.result()
            brutas, tempos = futuro_listagens.result()
    else:
        ouro_observado, tempo_ouro = _ouro(img)
        brutas, tempos = _listagens(img)
    tempos["ouro"] = tempo_ouro
    tempos["analise_inicial_parede"] = (time.monotonic() - inicio) * 1000
    return AnaliseInicial(ouro_observado, brutas, tempos)
```

- [ ] **Step 4: Rodar os testes do coordenador e da visão**

Run:

```bash
.venv/bin/python -m pytest tests/test_analise.py tests/test_ouro.py tests/test_leilao.py -q
```

Expected: PASS.

- [ ] **Step 5: Commitar o limite concorrente**

```bash
git add src/mistfall/analise.py tests/test_analise.py
git commit -m "Sobrepoe Ouro e varredura na analise inicial"
```

---

### Task 3: Tornar Espaço o fim da Compra enviada

**Files:**
- Modify: `src/mistfall/piloto.py`
- Modify: `ferramentas/piloto_cli.py`
- Modify: `tests/test_piloto.py`
- Modify: `tests/test_piloto_cli.py`

**Interfaces:**
- Consumes: `analisar_inicial(img, concorrente=True) -> AnaliseInicial` da Task 2.
- Produces: `Desfecho.COMPRA_ENVIADA`, `Resultado.ouro_observado: int | None` e `executar(..., observador_ouro: Callable[[int | None, float, datetime], None] | None = None) -> Resultado`.
- O callback recebe o Ouro, o instante monotônico da captura e o horário local da captura; ele é chamado uma vez depois que a análise termina, inclusive com Ouro `None`.

- [ ] **Step 1: Substituir os testes da confirmação por testes do novo contrato**

Em `tests/test_piloto.py`, remova a seção `Confirmacao pelo Ouro`, os testes que esperam captura depois de Espaço e os testes que exigem aborto para Ouro inicial ilegível. Acrescente:

```python
def test_espaco_encerra_a_compra_sem_captura_posterior(tmp_path):
    tela = TelaFalsa([LISTA])
    mao = MaoFalsa()
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert tela.capturas_feitas == 1
    assert [acao[0] for acao in mao.acoes] == ["clicar", "apertar_espaco"]


def test_ouro_ilegivel_e_telemetria_e_nao_aborto(tmp_path, monkeypatch):
    import mistfall.piloto as piloto
    real = piloto.analisar_inicial

    def sem_ouro(img, **kwargs):
        resultado = real(img, **kwargs)
        return dataclasses.replace(resultado, ouro_observado=None)

    monkeypatch.setattr(piloto, "analisar_inicial", sem_ouro)
    r = executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert r.ouro_observado is None


def test_publica_observacao_com_instante_da_captura(tmp_path):
    vistos = []
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             observador_ouro=lambda ouro, monotonic, horario:
                 vistos.append((ouro, monotonic, horario)))
    assert len(vistos) == 1
    ouro, monotonic, horario = vistos[0]
    assert ouro == 66160
    assert monotonic > 0
    assert horario.tzinfo is not None


def test_relatorio_remove_campos_da_confirmacao_do_ouro(tmp_path):
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["ouro_observado"] == 66160
    for campo in ("ouro_antes", "ouro_depois", "preco_total_esperado",
                  "confirmacao_do_ouro"):
        assert campo not in dados and campo not in dados["tempos"]
```

Substitua `test_o_relatorio_registra_o_tempo_de_cada_etapa` por:

```python
def test_o_relatorio_separa_processamento_e_esperas(tmp_path):
    r = executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99))
    assert set(r.tempos) == {
        "captura_pre_voo", "gravacao_pre_voo", "estado", "ouro",
        "varredura_total", "itens", "preparo_folha", "tesseract_precos",
        "analise_inicial_parede", "conferencia_e_decisao",
        "pausa_antes_do_clique", "clique", "espera_modal", "espaco",
    }
    assert all(ms >= 0 for ms in r.tempos.values())
```

Substitua `test_o_tempo_por_etapa_vai_para_o_json` por uma leitura do relatório que afirma o
mesmo conjunto literal em `dados["tempos"]`.

- [ ] **Step 2: Rodar os testes novos e observar os contratos antigos falharem**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py tests/test_piloto_cli.py -q
```

Expected: FAIL porque `COMPRA_ENVIADA`, `ouro_observado`, `observador_ouro` e as métricas novas ainda não existem.

- [ ] **Step 3: Reescrever o caminho vivo do piloto**

Em `src/mistfall/piloto.py`:

- importe `datetime`, `Callable` e `analisar_inicial`;
- substitua `COMPROU` por `COMPRA_ENVIADA = "compra_enviada"` e remova `OURO_NAO_CAIU`;
- remova de `Resultado` `ouro_antes`, `ouro_depois` e `preco_total_esperado`; acrescente `ouro_observado`;
- remova `espera_apos_espaco` e `teto_espera_ouro` de `Ritmo` e `instantaneo()`;
- apague `_esperar_o_ouro_cair` e todo código morto exclusivo da confirmação;
- mude o padrão de `pausa_antes_do_clique` para `(0.05, 0.15)`;
- meça captura, gravação e estado separadamente;
- capture o timestamp imediatamente depois de `tela.capturar()`;
- depois de validar `EstadoTela.LISTA`, chame `analisar_inicial(inicial)` e publique a observação;
- meça `conferencia_e_decisao` ao redor de `conferir_ordenacao` e `escolher`;
- meça a pausa sorteada, `mao.clicar`, a espera da Janela e `mao.apertar_espaco`;
- encerre imediatamente com `Desfecho.COMPRA_ENVIADA`.

A assinatura deve ficar:

```python
def executar(tela: Tela, mao: Mao, config: Config, pasta: Path,
             simular: bool = False, ritmo: Ritmo = RITMO_PADRAO,
             sorteio: random.Random | None = None,
             interruptor: Interruptor | None = None,
             observador_ouro: Callable[[int | None, float, datetime], None] | None = None,
             concorrente: bool = True) -> Resultado:
```

O núcleo da análise deve seguir esta ordem:

```python
instante_captura = time.monotonic()
horario_captura = datetime.now().astimezone()
# salvar e validar estado
analise = analisar_inicial(inicial, concorrente=concorrente)
r.ouro_observado = analise.ouro_observado
r.tempos.update(analise.tempos)
if observador_ouro is not None:
    observador_ouro(r.ouro_observado, instante_captura, horario_captura)
# conferir ordenação, decidir, clicar, esperar modal, apertar Espaço
return encerrar(Desfecho.COMPRA_ENVIADA)
```

Em `ferramentas/piloto_cli.py`, imprima `Ouro observado: N` quando presente, remova a seta antes/depois e faça `codigo_de_saida` tratar `COMPRA_ENVIADA` como zero. Elimine o código 3 e todo texto que o descreve.

- [ ] **Step 4: Rodar os testes do piloto e do CLI**

Run:

```bash
.venv/bin/python -m pytest tests/test_piloto.py tests/test_piloto_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Procurar símbolos mortos antes do commit**

Run:

```bash
rg -n "OURO_NAO_CAIU|ouro_antes|ouro_depois|preco_total_esperado|confirmacao_do_ouro|espera_apos_espaco|teto_espera_ouro" src ferramentas tests
```

Expected: nenhuma referência viva; referências em fixtures históricas não entram neste comando.

- [ ] **Step 6: Commitar a semântica não bloqueante**

```bash
git add src/mistfall/piloto.py ferramentas/piloto_cli.py tests/test_piloto.py tests/test_piloto_cli.py
git commit -m "Tira a leitura de Ouro do caminho da Compra"
```

---

### Task 4: Persistir telemetria e tempos do laço

**Files:**
- Create: `src/mistfall/telemetria.py`
- Create: `tests/test_telemetria.py`
- Modify: `src/mistfall/ciclo.py`
- Modify: `tests/test_ciclo.py`

**Interfaces:**
- Consumes: callback `observador_ouro` e `Desfecho.COMPRA_ENVIADA` da Task 3.
- Produces: `TelemetriaSessao(pasta: Path, inicio_monotonico: float)`, `registrar_ouro(volta: int, ouro: int | None, instante: float, horario: datetime) -> None` e `registrar_intervalo(volta: int, proximo_inicio: float, espera_ms: float, intervalo_ms: float) -> None`.
- Produces: `Sessao(voltas: int = 0, compras_enviadas: int = 0)`; não calcula Ouro gasto.

- [ ] **Step 1: Escrever testes vermelhos do escritor JSONL**

Crie `tests/test_telemetria.py`:

```python
import json
from datetime import datetime, timezone

from mistfall.telemetria import TelemetriaSessao


def test_registra_ouro_inclusive_nulo_sem_corromper_linhas(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    horario = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    telemetria.registrar_ouro(1, 500, 10.25, horario)
    telemetria.registrar_ouro(2, None, 11.00, horario)
    linhas = [json.loads(linha) for linha in
              (tmp_path / "telemetria-ouro.jsonl").read_text().splitlines()]
    assert linhas == [
        {"volta": 1, "instante_monotonico_ms": 250.0,
         "horario": horario.isoformat(), "ouro": 500, "origem": "pre_voo"},
        {"volta": 2, "instante_monotonico_ms": 1000.0,
         "horario": horario.isoformat(), "ouro": None, "origem": "pre_voo"},
    ]


def test_registra_intervalo_real_entre_voltas(tmp_path):
    telemetria = TelemetriaSessao(tmp_path, inicio_monotonico=10.0)
    telemetria.registrar_intervalo(3, proximo_inicio=12.5,
                                   espera_ms=150.2, intervalo_ms=980.4)
    linha = json.loads((tmp_path / "tempos-do-laco.jsonl").read_text())
    assert linha == {"volta": 3, "proximo_inicio_monotonico_ms": 2500.0,
                     "espera_efetiva_ms": 150.2, "intervalo_entre_inicios_ms": 980.4}
```

- [ ] **Step 2: Rodar e confirmar a ausência do módulo**

Run:

```bash
.venv/bin/python -m pytest tests/test_telemetria.py -v
```

Expected: FAIL na importação de `mistfall.telemetria`.

- [ ] **Step 3: Implementar escrita append-only focada**

Crie `src/mistfall/telemetria.py`:

```python
import json
from datetime import datetime
from pathlib import Path


class TelemetriaSessao:
    def __init__(self, pasta: Path, inicio_monotonico: float) -> None:
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.inicio_monotonico = inicio_monotonico

    @staticmethod
    def _acrescentar(caminho: Path, dados: dict) -> None:
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(dados, ensure_ascii=False) + "\n")

    def registrar_ouro(self, volta: int, ouro: int | None,
                       instante: float, horario: datetime) -> None:
        self._acrescentar(self.pasta / "telemetria-ouro.jsonl", {
            "volta": volta,
            "instante_monotonico_ms": round(
                (instante - self.inicio_monotonico) * 1000, 1),
            "horario": horario.isoformat(),
            "ouro": ouro,
            "origem": "pre_voo",
        })

    def registrar_intervalo(self, volta: int, proximo_inicio: float,
                            espera_ms: float, intervalo_ms: float) -> None:
        self._acrescentar(self.pasta / "tempos-do-laco.jsonl", {
            "volta": volta,
            "proximo_inicio_monotonico_ms": round(
                (proximo_inicio - self.inicio_monotonico) * 1000, 1),
            "espera_efetiva_ms": round(espera_ms, 1),
            "intervalo_entre_inicios_ms": round(intervalo_ms, 1),
        })
```

- [ ] **Step 4: Integrar ao laço com relógio monotônico real**

Em `src/mistfall/ciclo.py`:

- troque `compras` por `compras_enviadas` e remova `ouro_gasto` de `Sessao`;
- mapeie `COMPRA_ENVIADA` para `"compra enviada"`;
- crie `TelemetriaSessao` no começo de `executar_ciclo`;
- no começo de cada Volta, guarde `inicio_da_volta`;
- passe a `executar` uma closure que chama `registrar_ouro(sessao.voltas, ...)`;
- depois da linha de console, meça a espera real de 150 ms;
- no começo seguinte, registre o intervalo referente à Volta anterior;
- conte somente `COMPRA_ENVIADA` em `_contabilizar`.

Use estado pendente explícito para não inventar uma próxima Volta quando F3 encerrar:

```python
inicio_da_sessao = time.monotonic()
telemetria = TelemetriaSessao(pasta, inicio_da_sessao)
inicio_anterior = None
espera_anterior = None
volta_anterior = None

while not interruptor.pediram_parada():
    inicio_da_volta = time.monotonic()
    if inicio_anterior is not None:
        telemetria.registrar_intervalo(
            volta_anterior, inicio_da_volta,
            espera_anterior * 1000,
            (inicio_da_volta - inicio_anterior) * 1000,
        )
    # executar a Volta, passando observador_ouro
    inicio_anterior = inicio_da_volta
    volta_anterior = sessao.voltas
    inicio_espera = time.monotonic()
    time.sleep(ritmo.espera_entre_voltas)
    espera_anterior = time.monotonic() - inicio_espera
```

Atualize `Ritmo.espera_entre_voltas` para `0.15` na Task 3 ou neste passo caso ainda esteja em
`1.0`.

- [ ] **Step 5: Atualizar testes do laço para telemetria e nova contabilidade**

Em `tests/test_ciclo.py`, faça `_comprou` devolver `Resultado(Desfecho.COMPRA_ENVIADA,
ouro_observado=1000)` e faça `_PilotoFalso` chamar o callback recebido:

```python
observador = kwargs.get("observador_ouro")
resultado = self.roteiro.pop(0) if self.roteiro else Resultado(Desfecho.NADA_COMPRAVEL)
if observador is not None:
    observador(resultado.ouro_observado, time.monotonic(), datetime.now().astimezone())
return resultado
```

Substitua o teste de Ouro gasto por:

```python
def test_a_sessao_conta_compras_enviadas(monkeypatch, tmp_path):
    sessao, _, _ = _rodar(
        monkeypatch, tmp_path,
        [_comprou(), Resultado(Desfecho.NADA_COMPRAVEL), _comprou()],
        parar_na_pergunta=4)
    assert sessao.voltas == 3
    assert sessao.compras_enviadas == 2
```

Acrescente em `tests/test_ciclo.py`:

```python
def test_o_laco_escreve_ouro_de_cada_volta_em_jsonl(monkeypatch, tmp_path):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    linhas = [json.loads(linha) for linha in
              (tmp_path / "telemetria-ouro.jsonl").read_text().splitlines()]
    assert [linha["volta"] for linha in linhas] == [1, 2]
    assert [linha["ouro"] for linha in linhas] == [1000, 1000]


def test_o_laco_so_registra_intervalo_quando_a_proxima_volta_comeca(
        monkeypatch, tmp_path):
    _rodar(monkeypatch, tmp_path, [_comprou(), _comprou()], parar_na_pergunta=3)
    linhas = [json.loads(linha) for linha in
              (tmp_path / "tempos-do-laco.jsonl").read_text().splitlines()]
    assert [linha["volta"] for linha in linhas] == [1]
    assert linhas[0]["espera_efetiva_ms"] >= 0
    assert linhas[0]["intervalo_entre_inicios_ms"] >= linhas[0]["espera_efetiva_ms"]
```

Altere `test_cada_volta_tem_a_propria_pasta` para filtrar diretórios:

```python
assert sorted(p.name for p in tmp_path.iterdir() if p.is_dir()) == [
    "volta-0001", "volta-0002",
]
```

- [ ] **Step 6: Rodar os testes de telemetria e ciclo**

Run:

```bash
.venv/bin/python -m pytest tests/test_telemetria.py tests/test_ciclo.py -q
```

Expected: PASS.

- [ ] **Step 7: Commitar os artefatos da sessão**

```bash
git add src/mistfall/telemetria.py src/mistfall/ciclo.py tests/test_telemetria.py tests/test_ciclo.py
git commit -m "Registra Ouro e vazao sem bloquear o laco"
```

---

### Task 5: Criar benchmark sequencial versus concorrente

**Files:**
- Create: `ferramentas/benchmark_analise.py`
- Create: `tests/test_benchmark_analise.py`

**Interfaces:**
- Consumes: `analisar_inicial(img, concorrente: bool) -> AnaliseInicial` da Task 2.
- Produces: `medir(caminhos: list[Path], repeticoes: int = 1) -> dict` e CLI `python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 3`.
- O dicionário contém `aquecimento_ms`, `sequencial`, `concorrente` e `resultados_iguais`; cada modo contém `n`, `mediana_ms`, `p95_ms` e `max_ms`.

- [ ] **Step 1: Escrever teste vermelho do resumo e da igualdade**

Crie `tests/test_benchmark_analise.py`:

```python
from types import SimpleNamespace

from ferramentas import benchmark_analise


def test_medir_separa_aquecimento_compara_modos_e_exige_igualdade(monkeypatch, tmp_path):
    imagens = [tmp_path / "a.png", tmp_path / "b.png"]
    for imagem in imagens:
        imagem.write_bytes(b"imagem")
    monkeypatch.setattr(benchmark_analise.cv2, "imread", lambda _: object())

    chamadas = []
    def analisar(_, *, concorrente):
        chamadas.append(concorrente)
        return SimpleNamespace(ouro_observado=100, brutas=[1, 2],
                               tempos={"analise_inicial_parede": 10.0 if concorrente else 20.0})
    monkeypatch.setattr(benchmark_analise, "analisar_inicial", analisar)

    resumo = benchmark_analise.medir(imagens, repeticoes=2)
    assert resumo["resultados_iguais"] is True
    assert resumo["sequencial"]["n"] == 4
    assert resumo["concorrente"]["n"] == 4
    assert resumo["sequencial"]["mediana_ms"] == 20.0
    assert resumo["concorrente"]["mediana_ms"] == 10.0
    assert chamadas[0] is False  # aquecimento separado
```

- [ ] **Step 2: Rodar e confirmar a ausência da ferramenta**

Run:

```bash
.venv/bin/python -m pytest tests/test_benchmark_analise.py -v
```

Expected: FAIL na importação de `ferramentas.benchmark_analise`.

- [ ] **Step 3: Implementar benchmark determinístico e saída JSON**

Crie `ferramentas/benchmark_analise.py` com:

```python
import argparse
import json
import math
import statistics
from pathlib import Path

import cv2

from mistfall.analise import analisar_inicial


def _percentil_95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    indice = max(0, min(len(ordenados) - 1, math.ceil(len(ordenados) * 0.95) - 1))
    return ordenados[indice]


def _resumo(valores: list[float]) -> dict:
    return {"n": len(valores), "mediana_ms": statistics.median(valores),
            "p95_ms": _percentil_95(valores), "max_ms": max(valores)}


def _assinatura(resultado) -> tuple:
    return resultado.ouro_observado, tuple(resultado.brutas)


def medir(caminhos: list[Path], repeticoes: int = 1) -> dict:
    if not caminhos:
        raise ValueError("nenhum 00-pre-voo.png encontrado")
    if repeticoes < 1:
        raise ValueError("repeticoes precisa ser >= 1")
    imagens = [cv2.imread(str(caminho)) for caminho in caminhos]
    aquecimento = analisar_inicial(imagens[0], concorrente=False)
    tempos = {False: [], True: []}
    assinaturas = {False: [], True: []}
    for concorrente in (False, True):
        for _ in range(repeticoes):
            for imagem in imagens:
                resultado = analisar_inicial(imagem, concorrente=concorrente)
                tempos[concorrente].append(resultado.tempos["analise_inicial_parede"])
                assinaturas[concorrente].append(_assinatura(resultado))
    iguais = assinaturas[False] == assinaturas[True]
    if not iguais:
        raise RuntimeError("pipeline concorrente mudou o resultado da analise")
    return {
        "aquecimento_ms": aquecimento.tempos["analise_inicial_parede"],
        "sequencial": _resumo(tempos[False]),
        "concorrente": _resumo(tempos[True]),
        "resultados_iguais": iguais,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pasta", type=Path, default=Path("sessao"))
    parser.add_argument("--repeticoes", type=int, default=1)
    args = parser.parse_args()
    caminhos = sorted(args.pasta.glob("volta-*/00-pre-voo.png"))
    print(json.dumps(medir(caminhos, args.repeticoes), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Antes de `analisar_inicial`, rejeite explicitamente `cv2.imread(...) is None` com `ValueError`
citando o caminho. Acrescente um teste focado para essa mensagem.

- [ ] **Step 4: Rodar teste e benchmark real local**

Run:

```bash
.venv/bin/python -m pytest tests/test_benchmark_analise.py -q
.venv/bin/python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 1
```

Expected: teste PASS; benchmark imprime JSON com `resultados_iguais: true`. Registre os números
locais no handoff, mas não use o Mac para decidir o padrão do Windows.

- [ ] **Step 5: Commitar a bancada reproduzível**

```bash
git add ferramentas/benchmark_analise.py tests/test_benchmark_analise.py
git commit -m "Compara a analise sequencial e concorrente"
```

---

### Task 6: Alinhar CLI, documentação e regressão completa

**Files:**
- Modify: `ferramentas/bot_cli.py`
- Modify: `tests/test_bot_cli.py`
- Modify: `README.md`
- Modify: `docs/execucao-windows.md`
- Modify: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: `Ritmo` com pausa 50–150 ms e espera entre Voltas de 150 ms; `Sessao.compras_enviadas`; os dois JSONL; CLI do benchmark.
- Produces: documentação operacional coerente com `COMPRA_ENVIADA`, Ouro observacional e código de saída sem o antigo código 3.

- [ ] **Step 1: Escrever guardas documentais e de CLI**

Em `tests/test_bot_cli.py`, no teste que espiona `executar_ciclo`, capture `ritmo` e afirme:

```python
assert ritmo.pausa_antes_do_clique == (0.05, 0.15)
assert ritmo.espera_entre_voltas == 0.15
assert ritmo.espera_para_o_modal_abrir == (0.1, 0.15)
```

Em `tests/test_documentacao.py`, acrescente:

```python
EXECUCAO_WINDOWS = pathlib.Path("docs/execucao-windows.md").read_text(encoding="utf-8")


def test_readme_diz_que_ouro_nao_bloqueia_e_documenta_telemetria():
    minusculo = README.lower()
    assert "telemetria-ouro.jsonl" in README
    assert "tempos-do-laco.jsonl" in README
    assert "não confirma" in minusculo or "nao confirma" in minusculo
    assert "benchmark_analise" in README


def test_documentacao_viva_nao_promete_codigo_3_ou_confirmacao_do_ouro():
    textos = README + EXECUCAO_WINDOWS
    assert "OURO NAO CAIU" not in textos
    assert "confirmacao_do_ouro" not in textos
    assert "| `3` |" not in textos
```

- [ ] **Step 2: Rodar e confirmar que a documentação viva está antiga**

Run:

```bash
.venv/bin/python -m pytest tests/test_bot_cli.py tests/test_documentacao.py -q
```

Expected: FAIL nos novos guardas documentais.

- [ ] **Step 3: Atualizar a documentação operacional**

Em `README.md` e `docs/execucao-windows.md`:

- diga que `compra_enviada` significa clique e Espaço enviados, não Compra confirmada;
- explique que Ouro é observado no frame inicial e nunca bloqueia;
- remova código de saída 3, `OURO NAO CAIU`, Ouro antes/depois e confirmação posterior;
- documente `telemetria-ouro.jsonl`, `tempos-do-laco.jsonl` e as novas chaves de `tempos`;
- documente as esperas 50–150 ms, 80–120 ms e 150 ms;
- documente o benchmark:

```powershell
python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 3
```

- diga explicitamente que o resultado do Windows com o jogo aberto decide se a concorrência
  fica ativa; o resultado local não decide;
- mantenha `trabalhadores` documentado como dormente e esclareça que as duas threads novas não
  usam essa configuração nem dividem a folha em 12 OCRs.

- [ ] **Step 4: Rodar suite completa e checagens estáticas do repositório**

Run:

```bash
.venv/bin/python -m pytest -q
git diff --check
rg -n "OURO_NAO_CAIU|ouro_antes|ouro_depois|preco_total_esperado|confirmacao_do_ouro|espera_apos_espaco|teto_espera_ouro" src ferramentas tests README.md docs/execucao-windows.md
```

Expected: pytest PASS, `git diff --check` sem saída e `rg` sem referências vivas. Não altere
specs e planos históricos para satisfazer a busca: eles não entram no comando.

- [ ] **Step 5: Fazer uma execução local do benchmark e guardar o resumo no commit/PR**

Run:

```bash
.venv/bin/python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 1
```

Expected: JSON válido, resultados iguais e estatísticas de ambos os modos. Copie mediana e p95
para a mensagem de handoff; não versione saída gerada.

- [ ] **Step 6: Commitar integração e documentação**

```bash
git add ferramentas/bot_cli.py tests/test_bot_cli.py README.md docs/execucao-windows.md tests/test_documentacao.py
git commit -m "Documenta o laco sem confirmacao de Ouro"
```

---

## Validação final no Windows

Esta validação não bloqueia o merge do código testável no Mac, mas decide o padrão operacional
da concorrência antes da próxima sessão valendo.

- [ ] Rodar com o jogo aberto:

```powershell
python -m ferramentas.benchmark_analise --pasta sessao --repeticoes 3
```

- [ ] Confirmar `resultados_iguais: true`.
- [ ] Comparar mediana, p95 e máximo de `sequencial` e `concorrente`.
- [ ] Se concorrente não reduzir o tempo de parede, mudar o padrão de `executar(...,
  concorrente=False)` e registrar o resultado na mensagem do commit; manter todo o restante.
- [ ] Rodar `mistfall-bot --pasta sessao-otimizada`, parar com F3 e trazer de volta a pasta.
- [ ] Calcular tentativas por minuto, mediana/p95 de `analise_inicial_parede`, tempos dos ramos e
  intervalo entre inícios usando os JSONL e relatórios.
- [ ] Comparar com a linha de base desta spec: aproximadamente 4,8 s por Volta saudável,
  `pre_voo` mediano de 380,1 ms e `varredura` mediana de 381,9 ms.
