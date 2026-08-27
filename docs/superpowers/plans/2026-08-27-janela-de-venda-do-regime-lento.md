# Janela de Venda do regime lento — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o trinco que trava a Venda do regime lento por uma Janela de tempo, e dar à retomada da drenagem uma contagem real de stacks em vez do Estoque estimado.

**Architecture:** Depois de qualquer Venda o regime lento espera um intervalo antes de voltar a vender (nível). Na Volta em que esse intervalo vence, o coordenador emite um evento (aresta) que dá ao regime lento uma reavaliação que não depende de Compra nenhuma. Com a Janela aberta, duas regras decidem: o limiar de saldo já existente, e a retomada, armada pela varredura de Baús que a Venda faz ao sair por Capacidade cheia.

**Tech Stack:** Python 3.14, pytest. Interpretador e testes saem de `.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-08-27-janela-de-venda-do-regime-lento-design.md`

## Global Constraints

- Português em código, commits e documentação, com o glossário de `CONTEXT.md` como única fonte dos termos. Proibidos: `Item` isolado, `Offer`, `Listing`, `price`. Formas compostas do glossário (`Item-alvo`, `Preço-alvo`, `preco_unitario`) são corretas.
- Sem atribuição de IA em commit, issue, PR ou comentário.
- Testes: `.venv/bin/python -m pytest`. Nunca `pytest` solto.
- `fluxo.py` é política pura: sem relógio, sem tela, sem clique, sem dormir. Tempo entra por evento vindo do coordenador, como `OURO_ABAIXO_DO_PISO` já faz.
- `mistfall-bot` e `mistfall-venda` mantêm comportamento e defaults idênticos. Nenhuma tarefa toca o regime rápido.
- Nenhuma dependência exclusiva de Windows na camada de visão (ADR-0001).
- Ao commitar, adicione só os arquivos da própria tarefa, um a um. Nunca `git add .`, `-A` ou `-f`.

---

### Task 1: Uma constante só para o lote

Hoje o limiar do gatilho por saldo é `45` literal em `fluxo.py`, e a varredura desta feature precisa do mesmo número em stacks (15). Dois literais divergem com o tempo; um, não.

**Files:**
- Modify: `src/mistfall/tipos.py`
- Modify: `src/mistfall/fluxo.py` (função `_acao_por_saldo`)
- Test: `tests/test_fluxo.py`

**Interfaces:**
- Consumes: nada.
- Produces: em `mistfall.tipos` — `UNIDADES_POR_STACK: int = 3`, `LOTE_DE_VENDA_EM_STACKS: int = 15`, `LOTE_DE_VENDA_EM_UNIDADES: int = 45`.

- [ ] **Step 1: Escreva o teste que falha**

Em `tests/test_fluxo.py`, no fim do arquivo:

```python
def test_limiar_de_venda_por_saldo_sai_da_constante_do_lote():
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    estado = estado_inicial(
        modo=ModoFluxo.LENTO,
        estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES - 1,
    )
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, acao = aplicar_evento(estado, EventoFluxo.COMPRA_CONFIRMADA)
    assert estado.estoque_estimado == LOTE_DE_VENDA_EM_UNIDADES
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO
```

- [ ] **Step 2: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_fluxo.py::test_limiar_de_venda_por_saldo_sai_da_constante_do_lote -v`
Expected: FAIL com `ImportError: cannot import name 'LOTE_DE_VENDA_EM_UNIDADES'`

- [ ] **Step 3: Crie as constantes**

No topo de `src/mistfall/tipos.py`, junto de `BAU_INICIAL`:

```python
# Um stack de Item-alvo vai ate 3 unidades, e uma Venda lista um stack
# inteiro. O lote e o tanto que justifica uma ida a aba Vender: quinze
# stacks, quarenta e cinco unidades. Os dois numeros sao a mesma coisa em
# unidades diferentes, e por isso moram juntos — separados, divergem.
UNIDADES_POR_STACK = 3
LOTE_DE_VENDA_EM_STACKS = 15
LOTE_DE_VENDA_EM_UNIDADES = LOTE_DE_VENDA_EM_STACKS * UNIDADES_POR_STACK
```

- [ ] **Step 4: Use a constante em `fluxo.py`**

No topo de `src/mistfall/fluxo.py`, acrescente ao bloco de imports:

```python
from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES
```

E troque o literal em `_acao_por_saldo`:

```python
def _acao_por_saldo(estado: EstadoFluxo) -> AcaoFluxo:
    if (
        estado.modo is ModoFluxo.LENTO
        and estado.estoque_estimado >= LOTE_DE_VENDA_EM_UNIDADES
    ):
        return AcaoFluxo.VENDER_POR_FLUXO_LENTO
    return AcaoFluxo.CONTINUAR_COMPRA
```

- [ ] **Step 5: Rode a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. Nenhum teste existente muda de comportamento — o valor continua 45.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/tipos.py src/mistfall/fluxo.py tests/test_fluxo.py
git commit -m "Extrai o lote de Venda para uma constante unica"
```

---

### Task 2: A Venda responde se resta um lote cheio

Ao sair por `CAPACIDADE_CHEIA`, a Venda precisa responder uma pergunta binária: resta um lote cheio no Armazém? Ela varre os Baús contando stacks de 3 e para assim que atinge 15.

Duas restrições vindas dos commits recentes, e nenhuma é opcional:

- Começa do `BAU_INICIAL`, não do Baú atual. O commit `305768f` faz a Venda voltar ao primeiro Baú ao detectar capacidade estagnada, e o motivo da estagnação é não saber se as Listagens registraram. Se não registraram, o stack continua num Baú anterior.
- Leitura vazia não é prova de Baú vazio. O commit `7bca077` estabeleceu a releitura antes de acreditar. Contar um Baú transitoriamente vazio como zero subconta, desliga a retomada e faz o bot sentar em cima do estoque — a direção de erro do bug original. **A varredura erra para cima ou não erra:** qualquer Baú que não abriu conta como incerteza, e incerteza devolve `True`.

**Files:**
- Modify: `src/mistfall/ciclo_venda.py`
- Test: `tests/test_ciclo_venda.py`

**Interfaces:**
- Consumes: `LOTE_DE_VENDA_EM_STACKS` de `mistfall.tipos` (Task 1).
- Produces: `SessaoVenda.resta_lote_cheio: bool = False`; `_resta_lote_cheio(tela, mao, interruptor, ritmo, total_baus) -> bool`.

- [ ] **Step 1: Escreva os testes que falham**

Em `tests/test_ciclo_venda.py`, no fim do arquivo:

```python
def test_varredura_para_assim_que_confirma_o_lote_cheio(monkeypatch):
    from mistfall.ciclo_venda import _resta_lote_cheio

    # Quinze stacks cabem no primeiro Bau: a varredura nao deve abrir o segundo.
    slots = [SlotArmazem(0, coluna, ItemAlvo.BROCHE, 3) for coluna in range(15)]
    baus_abertos = []
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_bau",
        lambda tela, esperado, ritmo: baus_abertos.append(esperado) or object(),
    )

    resta = _resta_lote_cheio(
        TelaFalsa([STASH]), MaoFalsa(), InterruptorFalso(),
        RitmoVenda.instantaneo(), total_baus=4,
    )

    assert resta is True
    assert baus_abertos == [0]


def test_varredura_soma_stacks_de_baus_diferentes(monkeypatch):
    from mistfall.ciclo_venda import _resta_lote_cheio

    # Oito stacks por Bau: o lote so fecha no segundo.
    slots = [SlotArmazem(0, coluna, ItemAlvo.BROCHE, 3) for coluna in range(8)]
    baus_abertos = []
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_bau",
        lambda tela, esperado, ritmo: baus_abertos.append(esperado) or object(),
    )

    resta = _resta_lote_cheio(
        TelaFalsa([STASH]), MaoFalsa(), InterruptorFalso(),
        RitmoVenda.instantaneo(), total_baus=4,
    )

    assert resta is True
    assert baus_abertos == [0, 1]


def test_varredura_devolve_falso_quando_o_armazem_nao_tem_lote(monkeypatch):
    from mistfall.ciclo_venda import _resta_lote_cheio

    slots = [SlotArmazem(0, 0, ItemAlvo.BROCHE, 3), SlotArmazem(0, 1, ItemAlvo.ORBE, 2)]
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_bau",
        lambda tela, esperado, ritmo: object(),
    )

    resta = _resta_lote_cheio(
        TelaFalsa([STASH]), MaoFalsa(), InterruptorFalso(),
        RitmoVenda.instantaneo(), total_baus=2,
    )

    assert resta is False


def test_bau_que_nao_abre_conta_como_incerteza_e_devolve_verdadeiro(monkeypatch):
    from mistfall.ciclo_venda import _resta_lote_cheio

    # Armazem quase vazio, mas um Bau nao abriu: nao da para afirmar que
    # acabou, e afirmar que acabou e o erro que trava a drenagem.
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    monkeypatch.setattr(
        "mistfall.ciclo_venda._esperar_bau",
        lambda tela, esperado, ritmo: None if esperado == 1 else object(),
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda._capacidade_do_armazem_do_bau",
        lambda frame, bau: CapacidadeVenda(0, 12),
    )

    resta = _resta_lote_cheio(
        TelaFalsa([STASH]), MaoFalsa(), InterruptorFalso(),
        RitmoVenda.instantaneo(), total_baus=2,
    )

    assert resta is True
```

- [ ] **Step 2: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py -q -k "varredura or bau_que_nao_abre"`
Expected: FAIL com `ImportError: cannot import name '_resta_lote_cheio'`

- [ ] **Step 3: Implemente a varredura**

Em `src/mistfall/ciclo_venda.py`, depois de `_capacidade_do_armazem_do_bau`:

```python
def _resta_lote_cheio(
    tela: Tela,
    mao: Mao,
    interruptor: Interruptor,
    ritmo: RitmoVenda,
    total_baus: int,
) -> bool:
    """Ha ao menos um lote cheio de stacks sobrando no Armazem?

    Para assim que confirma o lote: com o Armazem cheio ela sai no primeiro
    Bau, e so fica cara quando resta pouco — que e quando a resposta importa.

    Comeca do primeiro Bau, e nao do Bau onde a Venda parou: a deteccao de
    capacidade estagnada faz a Venda voltar ao inicio, e o motivo da
    estagnacao e nao saber se as Listagens registraram. Se nao registraram, o
    stack continua num Bau anterior.

    Qualquer Bau que nao abriu vira incerteza, e incerteza devolve verdadeiro.
    Errar para cima custa uma ida a aba Vender; errar para baixo desliga a
    retomada e deixa o bot sentado em cima do Armazem cheio.
    """
    stacks = 0
    houve_leitura_incerta = False
    for bau in range(total_baus):
        if interruptor.pediram_parada():
            return True
        mao.clicar(*centro_bau(bau))
        frame = _esperar_bau(tela, bau, ritmo)
        if frame is None:
            houve_leitura_incerta = True
            continue
        candidatos = _candidatos(frame)
        if not candidatos:
            # Leitura vazia pode ter acontecido com a tela ainda trocando de
            # Bau. Releia antes de acreditar que o Bau esta vazio.
            time.sleep(ritmo.intervalo_entre_perguntas)
            releitura = tela.capturar()
            if _capacidade_do_armazem_do_bau(releitura, bau) is None:
                houve_leitura_incerta = True
                continue
            candidatos = _candidatos(releitura)
        stacks += len(candidatos)
        if stacks >= LOTE_DE_VENDA_EM_STACKS:
            return True
    return houve_leitura_incerta
```

E no bloco de imports do arquivo, acrescente `LOTE_DE_VENDA_EM_STACKS`:

```python
from mistfall.tipos import BAU_INICIAL, CapacidadeVenda, LOTE_DE_VENDA_EM_STACKS
```

- [ ] **Step 4: Rode e veja passar**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py -q`
Expected: PASS, e nenhum teste existente quebrado.

- [ ] **Step 5: Escreva o teste da fiação no desfecho**

Em `tests/test_ciclo_venda.py`:

```python
def test_saida_por_capacidade_cheia_registra_se_resta_lote(monkeypatch, tmp_path):
    slots = [SlotArmazem(0, coluna, ItemAlvo.BROCHE, 3) for coluna in range(20)]
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: slots)
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 0)
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", lambda _: 4)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(12, 12),
    )
    monkeypatch.setattr(
        "mistfall.ciclo_venda._resta_lote_cheio",
        lambda *args, **kwargs: True,
    )

    sessao = executar_venda_parcial(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA
    assert sessao.resta_lote_cheio is True


def test_armazem_esgotado_nunca_arma_a_retomada(monkeypatch, tmp_path):
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [])
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: 0)
    monkeypatch.setattr("mistfall.ciclo_venda.contar_baus", lambda _: 2)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12),
    )

    sessao = executar_venda_parcial(
        TelaFalsa([STASH]), MaoFalsa(), config(), tmp_path,
        InterruptorFalso(), RitmoVenda.instantaneo(),
    )

    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO
    assert sessao.resta_lote_cheio is False
```

- [ ] **Step 6: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo_venda.py -q -k "resta_lote or nunca_arma"`
Expected: FAIL com `AttributeError: 'SessaoVenda' object has no attribute 'resta_lote_cheio'`

- [ ] **Step 7: Acrescente o campo e a fiação**

Em `SessaoVenda`, depois de `total_baus`:

```python
    # Ha lote cheio sobrando no Armazem depois desta Venda? So a saida por
    # Capacidade cheia responde de verdade; Armazem esgotado nao tem o que
    # sobrar, e ABORTOU/PAROU nao sabem — e religar a retomada em cima de uma
    # falha de visao viraria laco silencioso. Nesses tres, falso.
    resta_lote_cheio: bool = False
```

Na saída por Capacidade cheia (a linha que hoje é `return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)`), passe a preencher o campo antes de encerrar:

```python
                        if motivo == "capacidade cheia":
                            _, capacidade = espera
                            sessao.capacidade_final = capacidade
                            sessao.resta_lote_cheio = _resta_lote_cheio(
                                tela, mao, interruptor, ritmo, sessao.total_baus,
                            )
                            return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)
```

- [ ] **Step 8: Rode a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. Confirme especificamente que `tests/test_venda_cli.py` e os testes de `executar_ciclo_venda` continuam passando — o `mistfall-venda` usa `_esperar_vaga`, que espera vaga indefinidamente e nunca sai por Capacidade cheia, então ele não deve tocar neste caminho.

- [ ] **Step 9: Commit**

```bash
git add src/mistfall/ciclo_venda.py tests/test_ciclo_venda.py
git commit -m "Conta se resta lote cheio ao sair por Capacidade cheia"
```

---

### Task 3: A política ganha a Janela e a retomada

`fluxo.py` continua puro. Ele não sabe que horas são: recebe `janela_de_venda_aberta` de quem tem relógio, exatamente como já recebe `ouro_abaixo_do_piso` de quem tem acesso ao Ouro.

**Files:**
- Modify: `src/mistfall/fluxo.py`
- Test: `tests/test_fluxo.py`

**Interfaces:**
- Consumes: `LOTE_DE_VENDA_EM_UNIDADES` de `mistfall.tipos` (Task 1).
- Produces: `EventoFluxo.venda_encerrada(resta_lote_cheio: bool)`; `EventoFluxo.janela_de_venda_aberta()`; `AcaoFluxo.VENDER_POR_RETOMADA`; `EstadoFluxo.retomada_pendente: bool = False`.

- [ ] **Step 1: Escreva os testes que falham**

Em `tests/test_fluxo.py`, no fim do arquivo:

```python
def test_venda_encerrada_com_lote_restante_arma_a_retomada():
    estado = _em_regime_lento()
    estado, acao = aplicar_evento(
        estado, EventoFluxo.venda_encerrada(resta_lote_cheio=True)
    )
    assert estado.retomada_pendente is True
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_venda_encerrada_sem_lote_restante_desarma_a_retomada():
    estado = _em_regime_lento()
    estado, _ = aplicar_evento(
        estado, EventoFluxo.venda_encerrada(resta_lote_cheio=True)
    )
    estado, _ = aplicar_evento(
        estado, EventoFluxo.venda_encerrada(resta_lote_cheio=False)
    )
    assert estado.retomada_pendente is False


def test_janela_aberta_com_retomada_armada_manda_vender():
    estado = _em_regime_lento()
    estado, _ = aplicar_evento(
        estado, EventoFluxo.venda_encerrada(resta_lote_cheio=True)
    )
    estado, acao = aplicar_evento(estado, EventoFluxo.janela_de_venda_aberta())
    assert acao is AcaoFluxo.VENDER_POR_RETOMADA


def test_janela_aberta_com_saldo_acima_do_lote_manda_vender_pela_pressa():
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    estado = replace(
        _em_regime_lento(), estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES
    )
    estado, acao = aplicar_evento(estado, EventoFluxo.janela_de_venda_aberta())
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO


def test_janela_aberta_sem_saldo_e_sem_retomada_continua_comprando():
    estado = _em_regime_lento()
    estado, acao = aplicar_evento(estado, EventoFluxo.janela_de_venda_aberta())
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_janela_aberta_no_regime_rapido_nunca_manda_vender():
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    # O regime rapido vende so por Inventario cheio e por Ouro abaixo do
    # piso. Nem saldo nem retomada valem nele.
    estado = estado_inicial(estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES * 2)
    estado, _ = aplicar_evento(
        estado, EventoFluxo.venda_encerrada(resta_lote_cheio=True)
    )
    estado, acao = aplicar_evento(estado, EventoFluxo.janela_de_venda_aberta())
    assert estado.modo is ModoFluxo.RAPIDO
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_janela_aberta_nao_mexe_no_regime_nem_no_estoque():
    estado = replace(_em_regime_lento(), estoque_estimado=7)
    depois, _ = aplicar_evento(estado, EventoFluxo.janela_de_venda_aberta())
    assert depois.modo is estado.modo
    assert depois.estoque_estimado == estado.estoque_estimado
    assert depois.resets_consecutivos == estado.resets_consecutivos
```

- [ ] **Step 2: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_fluxo.py -q -k "janela or retomada"`
Expected: FAIL com `AttributeError: type object 'EventoFluxo' has no attribute 'venda_encerrada'`

- [ ] **Step 3: Acrescente o tipo de evento e a ação**

Em `_TipoEvento`, no fim da enum:

```python
    VENDA_ENCERRADA = "venda_encerrada"
    JANELA_DE_VENDA_ABERTA = "janela_de_venda_aberta"
```

Em `AcaoFluxo`, depois de `VENDER_POR_FLUXO_LENTO`:

```python
    VENDER_POR_RETOMADA = "vender_por_retomada"
```

- [ ] **Step 4: Acrescente o campo do evento e as fábricas**

Em `EventoFluxo`, acrescente o campo depois de `capacidade`:

```python
    resta_lote_cheio: bool = False
```

E as duas fábricas, depois de `ouro_abaixo_do_piso`:

```python
    @classmethod
    def venda_encerrada(cls, resta_lote_cheio: bool) -> "EventoFluxo":
        """Uma Venda acabou, e disse se sobrou lote cheio no Armazem.

        Quem responde e a propria Venda, que le o Armazem: a resposta e
        independente do Estoque estimado, que subconta.
        """
        return cls(
            _TipoEvento.VENDA_ENCERRADA, resta_lote_cheio=resta_lote_cheio
        )

    @classmethod
    def janela_de_venda_aberta(cls) -> "EventoFluxo":
        """A Janela venceu e o regime lento pode voltar a vender.

        O intervalo vive na configuracao e o relogio e do coordenador: a
        politica continua pura, como no piso de Ouro.
        """
        return cls(_TipoEvento.JANELA_DE_VENDA_ABERTA)
```

E a constante de conveniência, junto das outras no fim do bloco:

```python
EventoFluxo.JANELA_DE_VENDA_ABERTA = EventoFluxo.janela_de_venda_aberta()
```

- [ ] **Step 5: Acrescente o campo de estado**

Em `EstadoFluxo`, depois de `capacidade_observada`:

```python
    # A ultima Venda saiu por Capacidade cheia deixando lote cheio para tras.
    # E o que distingue drenagem interrompida de fim de lote.
    retomada_pendente: bool = False
```

- [ ] **Step 6: Implemente os dois ramos**

Em `aplicar_evento`, antes do `raise ValueError` final:

```python
    if tipo is _TipoEvento.VENDA_ENCERRADA:
        novo = replace(estado, retomada_pendente=evento.resta_lote_cheio)
        return novo, AcaoFluxo.CONTINUAR_COMPRA

    if tipo is _TipoEvento.JANELA_DE_VENDA_ABERTA:
        # Reavaliacao que nao depende de Compra nenhuma. Sem ela, o gatilho
        # por saldo so e consultado nos ramos de Compra, e o Fluxo Completo
        # reseta indefinidamente com o Armazem cheio e o Leilao seco.
        if estado.modo is not ModoFluxo.LENTO:
            return estado, AcaoFluxo.CONTINUAR_COMPRA
        if estado.estoque_estimado >= LOTE_DE_VENDA_EM_UNIDADES:
            return estado, AcaoFluxo.VENDER_POR_FLUXO_LENTO
        if estado.retomada_pendente:
            return estado, AcaoFluxo.VENDER_POR_RETOMADA
        return estado, AcaoFluxo.CONTINUAR_COMPRA
```

- [ ] **Step 7: Rode e veja passar**

Run: `.venv/bin/python -m pytest tests/test_fluxo.py -q`
Expected: PASS, incluindo todos os testes que já existiam.

- [ ] **Step 8: Commit**

```bash
git add src/mistfall/fluxo.py tests/test_fluxo.py
git commit -m "Da a politica a Janela de Venda e a retomada da drenagem"
```

---

### Task 4: O coordenador troca o trinco pela Janela

Aqui morrem os dois defeitos. `gatilho_por_saldo_suspenso` é um trinco: arma uma vez e só destrava com uma Venda que liste unidades — que nunca acontece, porque ela mesma impede a Venda. A Janela é prazo.

A Janela é nível e aresta ao mesmo tempo, e a distinção importa:

- **Nível:** `agora >= proxima_janela` é conferido a cada Volta e autoriza a Venda vinda do gatilho de pressa. `proxima_janela` só é reagendada quando uma Venda acontece — uma Janela que abre e não vende continua aberta. Reagendar na emissão barraria por mais um intervalo inteiro uma Compra que cruzasse o limiar logo depois, sem nada ter sido vendido.
- **Aresta:** na Volta em que a Janela passa de fechada a aberta, emite `janela_de_venda_aberta` uma vez.

**Files:**
- Modify: `src/mistfall/config.py`
- Modify: `src/mistfall/ciclo_completo.py`
- Test: `tests/test_config.py`
- Test: `tests/test_ciclo_completo.py`

**Interfaces:**
- Consumes: `EventoFluxo.venda_encerrada`, `EventoFluxo.JANELA_DE_VENDA_ABERTA`, `AcaoFluxo.VENDER_POR_RETOMADA` (Task 3); `SessaoVenda.resta_lote_cheio` (Task 2).
- Produces: `Config.intervalo_da_janela_s: int = 180`.

- [ ] **Step 1: Escreva o teste da configuração**

Em `tests/test_config.py`, no fim do arquivo:

```python
def test_intervalo_da_janela_tem_padrao_e_e_configuravel(tmp_path):
    from mistfall.config import carregar_config

    arquivo = tmp_path / "config.toml"
    arquivo.write_text(
        "[precos_alvo]\nbroche = 188\n", encoding="utf-8",
    )
    assert carregar_config(arquivo).intervalo_da_janela_s == 180

    arquivo.write_text(
        "intervalo_da_janela_s = 90\n[precos_alvo]\nbroche = 188\n",
        encoding="utf-8",
    )
    assert carregar_config(arquivo).intervalo_da_janela_s == 90
```


- [ ] **Step 2: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_config.py -q -k intervalo_da_janela`
Expected: FAIL com `AttributeError: 'Config' object has no attribute 'intervalo_da_janela_s'`

- [ ] **Step 3: Acrescente a chave**

No topo de `src/mistfall/config.py`, junto das outras constantes de padrão:

```python
INTERVALO_DA_JANELA_PADRAO = 180
```

Em `Config`, depois de `ouro_alvo_recuperacao`:

```python
    # Segundos que o regime lento espera, depois de uma Venda, antes de poder
    # voltar a vender. E o que impede o ida-e-volta de aba a cada Compra
    # quando a Capacidade do NPC esta cheia — e, ao contrario do trinco que
    # substituiu, vence sozinho.
    intervalo_da_janela_s: int = INTERVALO_DA_JANELA_PADRAO
```

Na função de carga, junto dos outros `_inteiro_positivo`:

```python
    intervalo_da_janela_s = _inteiro_positivo(
        dados, "intervalo_da_janela_s", INTERVALO_DA_JANELA_PADRAO, arquivo
    )
```

E acrescente `intervalo_da_janela_s=intervalo_da_janela_s,` à construção do `Config` no `return`.

- [ ] **Step 4: Rode e veja passar**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Escreva os testes do coordenador**

Em `tests/test_ciclo_completo.py`, no fim do arquivo:

```python
def test_reset_com_armazem_cheio_vende_quando_a_janela_abre(monkeypatch, tmp_path):
    # O defeito que originou tudo: em regime lento, com o Armazem cheio e o
    # Leilao seco, o gatilho por saldo so era consultado em evento de Compra,
    # e o bot resetava indefinidamente sem nunca ir vender.
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 4,
        venda=SessaoVenda(DesfechoSessaoVenda.ARMAZEM_ESGOTADO, unidades_listadas=45),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 5 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=0))

    assert chamadas.count("venda") >= 1


def test_janela_fechada_segura_a_venda_do_regime_lento(monkeypatch, tmp_path):
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 6,
        venda=SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=0),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 8 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=3600))

    # A primeira Venda passa (Janela aberta na largada); a Janela fecha por
    # uma hora e nenhuma outra pode acontecer, mesmo com o saldo acima do lote.
    assert chamadas.count("venda") == 1


def test_capacidade_cheia_nao_trava_a_venda_para_sempre(monkeypatch, tmp_path):
    # O trinco antigo: uma Venda que voltava sem listar nada suspendia o
    # gatilho por saldo ate uma Venda listar alguma coisa — que nunca
    # acontecia, porque a suspensao impedia a Venda.
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 6,
        venda=SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=0),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 12 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=0))

    assert chamadas.count("venda") >= 2
```

- [ ] **Step 6: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_ciclo_completo.py -q -k "janela or trava_a_venda or armazem_cheio"`
Expected: FAIL. O primeiro e o terceiro falham porque o gatilho não é reavaliado; o segundo falha porque não existe Janela nenhuma para segurar.

- [ ] **Step 7: Implemente a Janela no coordenador**

Em `src/mistfall/ciclo_completo.py`.

Acrescente ao import de `mistfall.fluxo` a ação nova, e ao lado de `_ACOES_DE_VENDA`:

```python
# A Janela vale para as duas Vendas do regime lento. Se valesse so para a
# pressa, o livelock voltaria pela porta dos fundos: a Venda lista zero, uma
# Compra confirma, o saldo segue acima do lote, e a viagem se repete.
_ACOES_DO_REGIME_LENTO = (
    AcaoFluxo.VENDER_POR_FLUXO_LENTO,
    AcaoFluxo.VENDER_POR_RETOMADA,
)
```

Substitua a inicialização `gatilho_por_saldo_suspenso = False` por:

```python
        # Zero deixa a Janela aberta na largada: nada foi vendido ainda, e nao
        # ha o que esperar.
        proxima_janela = 0.0
        # Verdadeiro suprime a aresta na primeira Volta: a Janela nasce aberta,
        # entao nao ha transicao de fechada para aberta a anunciar.
        janela_estava_aberta = True
```

Substitua o bloco do trinco (as quatro linhas que começam em `# Livelock:` e terminam em `acao = AcaoFluxo.CONTINUAR_COMPRA`) por, logo **depois** da seleção de `acao` e **antes** da conferência do Ouro:

```python
            # Aresta da Janela: a unica reavaliacao do regime lento que nao
            # depende de evento de Compra. Sem ela, o Fluxo Completo reseta
            # indefinidamente com o Armazem cheio e o Leilao seco.
            janela_aberta = time.monotonic() >= proxima_janela
            if (
                acao not in _ACOES_DE_VENDA
                and janela_aberta
                and not janela_estava_aberta
            ):
                acao = aplicar(EventoFluxo.JANELA_DE_VENDA_ABERTA)
            janela_estava_aberta = janela_aberta
```

E depois da conferência do Ouro, no lugar onde estava o trinco:

```python
            # Portao: nenhuma Venda do regime lento passa com a Janela
            # fechada. O toast de Inventario cheio e o Ouro abaixo do piso
            # atravessam — sao emergencia, nao ritmo.
            if acao in _ACOES_DO_REGIME_LENTO and not janela_aberta:
                acao = AcaoFluxo.CONTINUAR_COMPRA
```

Por fim, no bloco que roda depois de `executar_venda_parcial`, remova as quatro linhas que mexiam em `gatilho_por_saldo_suspenso` e acrescente, logo depois de `sessao.unidades_listadas += venda.unidades_listadas`:

```python
            proxima_janela = time.monotonic() + config.intervalo_da_janela_s
            janela_estava_aberta = False
            aplicar(EventoFluxo.venda_encerrada(venda.resta_lote_cheio))
```

Mantenha a linha `aplicar(EventoFluxo.unidades_listadas(venda.unidades_listadas))` dentro do `if venda.unidades_listadas:` que já existe, removendo dele apenas a atribuição do trinco.

- [ ] **Step 8: Rode a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde. Os dois testes de supressão que existiam (`test_capacidade_cheia_sem_listar_suspende_o_gatilho_por_saldo` e `test_uma_venda_com_unidades_reabre_o_gatilho_por_saldo`) descrevem o trinco que deixou de existir — apague os dois, porque os três testes novos do Step 5 cobrem o comportamento que os substitui. Não os adapte: eles afirmam que a supressão é permanente, que é exatamente o defeito.

- [ ] **Step 9: Commit**

```bash
git add src/mistfall/config.py src/mistfall/ciclo_completo.py tests/test_config.py tests/test_ciclo_completo.py
git commit -m "Troca o trinco da Venda do regime lento por uma Janela de tempo"
```

---

### Task 5: Registrar o que faltava para diagnosticar

Este bug não pôde ser diagnosticado a partir dos registros: `eventos-do-fluxo.jsonl` grava `modo` e `resets_desde_intencao`, mas não grava os contadores que **decidem** o regime. Eles só aparecem no `sessao.json`, no fim.

**Files:**
- Modify: `src/mistfall/telemetria.py`
- Modify: `src/mistfall/ciclo_completo.py` (o dump de `sessao.json`)
- Test: `tests/test_telemetria.py`
- Test: `tests/test_ciclo_completo.py`

**Interfaces:**
- Consumes: `EstadoFluxo.retomada_pendente` (Task 3).
- Produces: nada que outra tarefa consuma.

- [ ] **Step 1: Escreva o teste que falha**

Em `tests/test_telemetria.py`, no fim do arquivo:

```python
def test_evento_do_fluxo_registra_os_contadores_que_decidem_o_regime(tmp_path):
    from dataclasses import replace as _replace

    telemetria = TelemetriaSessao(tmp_path, 0.0)
    estado = _replace(
        EstadoFluxo(),
        resets_consecutivos=4,
        intervalos_lentos_consecutivos=2,
        pontos_de_pressa=1,
        retomada_pendente=True,
    )
    telemetria.registrar_evento_fluxo(
        volta=7, instante=1.0, horario=datetime(2026, 8, 27, 12, 0),
        estado=estado, unidades_listadas=0,
        acao=AcaoFluxo.CONTINUAR_COMPRA, evento=EventoFluxo.RESET,
    )

    linha = json.loads(
        (tmp_path / "eventos-do-fluxo.jsonl").read_text(encoding="utf-8")
    )
    assert linha["resets_consecutivos"] == 4
    assert linha["intervalos_lentos_consecutivos"] == 2
    assert linha["pontos_de_pressa"] == 1
    assert linha["retomada_pendente"] is True
```


- [ ] **Step 2: Rode e veja falhar**

Run: `.venv/bin/python -m pytest tests/test_telemetria.py -q -k contadores_que_decidem`
Expected: FAIL com `KeyError: 'resets_consecutivos'`

- [ ] **Step 3: Acrescente as quatro chaves**

Em `registrar_evento_fluxo`, no dicionário, depois de `"resets_desde_intencao"`:

```python
                "resets_consecutivos": estado.resets_consecutivos,
                "intervalos_lentos_consecutivos": (
                    estado.intervalos_lentos_consecutivos
                ),
                "pontos_de_pressa": estado.pontos_de_pressa,
                "retomada_pendente": estado.retomada_pendente,
```

E atualize a docstring do método: onde ela diz que `estado` fornece "o regime, as Intenções e os Resets desde a última, e o saldo estimado", acrescente que fornece também os contadores que decidem o regime — e por que: sem eles por Volta não dá para reconstruir por que a Venda não disparou.

- [ ] **Step 4: Rode e veja passar**

Run: `.venv/bin/python -m pytest tests/test_telemetria.py -q`
Expected: PASS.

- [ ] **Step 5: Acrescente `retomada_pendente` ao `sessao.json`**

Em `tests/test_ciclo_completo.py`, no teste `test_grava_sessao_json_com_desfecho_e_motivo_mesmo_ao_abortar`, junto das asserções que já existem:

```python
    assert dados["estado"]["retomada_pendente"] is False
```

Rode e veja falhar com `KeyError`, depois acrescente a chave em `_fechar`, no dicionário do estado, depois de `"pontos_de_pressa"`:

```python
                    "retomada_pendente": estado.retomada_pendente,
```

- [ ] **Step 6: Rode a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde.

- [ ] **Step 7: Commit**

```bash
git add src/mistfall/telemetria.py src/mistfall/ciclo_completo.py tests/test_telemetria.py tests/test_ciclo_completo.py
git commit -m "Registra por Volta os contadores que decidem o regime"
```

---

### Task 6: O glossário

`CONTEXT.md` é a única fonte dos termos. A Janela e a retomada são conceitos novos do domínio, e o verbete do Regime do Fluxo passa a ter uma vizinha.

**Files:**
- Modify: `CONTEXT.md`
- Test: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: nada.
- Produces: nada.

- [ ] **Step 1: Rode a suíte da documentação para ter a linha de base**

Run: `.venv/bin/python -m pytest tests/test_documentacao.py -q`
Expected: PASS. Esses testes não checam formato de verbete — cada um afirma um fato específico sobre o texto. Nenhum fala de Janela nem de Retomada, então acrescentar os dois verbetes não deve quebrar nada; se quebrar, o texto novo contradisse alguma afirmação existente e é o texto que muda, não o teste.

- [ ] **Step 2: Acrescente o verbete**

Em `CONTEXT.md`, logo depois do verbete **Regime do Fluxo**:

```markdown
**Janela de Venda**:
O intervalo que o regime lento espera, depois de uma Venda, antes de poder
voltar a vender. Vale para as duas Vendas do regime lento — a por saldo e a de
retomada — e não vale para o toast de Inventário cheio nem para o Ouro abaixo
do piso, que são emergência e não ritmo.

Ela abre sozinha, e é isso que a distingue do trinco que substituiu: a
supressão anterior armava quando uma Venda voltava sem listar nada e só
destravava com uma Venda que listasse alguma coisa — que nunca acontecia,
porque a própria supressão impedia a Venda.

Na Volta em que a Janela vence, o Fluxo Completo reavalia o regime lento sem
depender de nenhuma Compra. Sem essa reavaliação, o gatilho por saldo só era
consultado nos ramos de Compra, e o bot resetava indefinidamente com o Armazém
cheio e o Leilão seco.
_Avoid_: Cooldown, Timer, Debounce.

**Retomada**:
A Venda que o regime lento faz quando a Venda anterior saiu por Capacidade
cheia deixando um lote cheio para trás — drenagem interrompida, não terminada.
Distingue-se da Venda por saldo por não olhar o Estoque estimado: quem responde
se resta lote é a própria Venda, varrendo os Baús e parando assim que confirma
quinze stacks. É o que impede a subcontagem do Estoque estimado de contaminar a
decisão.
_Avoid_: Retry, Reprocessamento, Segunda passada.
```

- [ ] **Step 3: Atualize o verbete do Regime do Fluxo**

Nesse verbete, troque a frase

> Só o regime lento dispara Venda por saldo — o regime rápido só vende quando o Inventário e o Armazém acusam estar cheios.

por

> Só o regime lento dispara Venda por saldo, e ele tem duas: a por saldo, quando o Estoque estimado alcança o lote, e a Retomada, quando a Venda anterior saiu por Capacidade cheia deixando lote para trás. As duas passam pela Janela de Venda. O regime rápido não tem nenhuma das duas — vende quando o Inventário e o Armazém acusam estar cheios, ou quando o Ouro cai abaixo do piso.

- [ ] **Step 4: Rode a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: tudo verde.

- [ ] **Step 5: Commit**

```bash
git add CONTEXT.md
git commit -m "Documenta a Janela de Venda e a Retomada"
```

---

## Fora de escopo, de propósito

**O defeito do Estoque estimado.** Compra real cujo Ouro está legível e não caiu soma zero, e não há reconciliação — `ESTOQUE_RECONCILIADO` existe, é testado e não tem chamador. A varredura da Task 2 resolve a decisão de retomada de forma independente dessa contagem, mas o gatilho por saldo continua pendurado nela. Reconciliar de verdade exige trabalho de visão que não está feito.

**O toast de Inventário cheio sem Janela.** Inventário cheio mais Capacidade cheia produz toast a cada Volta e viagem a cada Volta. Existe hoje, não é regressão desta mudança, e pôr Janela nele mudaria o regime rápido — que esta feature não toca.
