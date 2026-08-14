# Leitura de preços em folha única — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ler os doze Preços-unitários da varredura numa única chamada ao tesseract, empilhando os recortes numa folha com separadores, para cair de 503 ms para 221 ms e de 79/84 para 84/84 de acerto.

**Architecture:** Uma função nova `ler_precos(recortes) -> list[int | None]` em `src/mistfall/precos.py` prepara cada recorte (cinza, ampliação 4×, Otsu), empilha com faixas pretas de 40 px entre eles e faz uma chamada `image_to_data` com `--psm 6`. A correspondência slot↔preço volta pela posição vertical de cada número detectado, nunca pela ordem em que saem. `ler_preco`, que lê um recorte só, permanece para as três leituras do modal.

**Tech Stack:** Python 3, OpenCV (`cv2`), NumPy, `pytesseract`, `pytest`.

## Global Constraints

- Código, testes, commits e documentação em **português**, usando o glossário de `CONTEXT.md`: Leilão, Listagem, Item-alvo, Preço-alvo, Preço-unitário, Estoque, Compra, Janela de Confirmação, Ouro, Categoria, Reset.
- **Não** usar `Item`, `Offer`, `Listing`, `price` em nomes de função, variável ou teste.
- **Sem atribuição de IA** em lugar nenhum: sem `Co-Authored-By`, sem "gerado por IA", sem "🤖 Generated with Claude Code" em commits, issues ou PRs.
- Interpretador e testes saem do venv do projeto: `.venv/bin/python -m pytest`.
- A camada de visão roda no macOS contra os prints em `images/`. **Nenhuma dependência exclusiva de Windows pode entrar nela** (ADR-0001).
- A detecção é acoplada de propósito à resolução 2560×1440 (ADR-0002) — decisão registrada, não descuido.
- Todos os comandos rodam a partir de `/Users/lavarini/lavarini/projects/mistfall-folha-unica`, na branch `folha-unica`.
- Valores medidos que **não** podem ser alterados sem nova medição: `SEPARADOR = 40`, ampliação `fx=4, fy=4`, config `--psm 6 -c tessedit_char_whitelist=0123456789`.

---

### Task 1: `ler_precos` — a folha única

**Files:**
- Modify: `src/mistfall/precos.py`
- Test: `tests/test_precos.py`

**Interfaces:**
- Consumes: `mistfall.geometria.recorte_preco(img, linha, coluna) -> np.ndarray` e `mistfall.geometria.TODOS_OS_SLOTS` (lista de 12 tuplas `(linha, coluna)`, na ordem `(0,0), (0,1), (1,0) … (5,1)`), ambos já existentes.
- Produces: `mistfall.precos.ler_precos(recortes: list[np.ndarray]) -> list[int | None]` — recebe recortes na ordem dos slots, devolve valores na mesma ordem, com `None` no índice de cada recorte ilegível. `mistfall.precos.SEPARADOR = 40`. `mistfall.precos.ler_preco(recorte) -> int | None` permanece inalterada na assinatura.

O arquivo `src/mistfall/precos.py` hoje é este, por inteiro:

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

- [ ] **Step 1: Escrever os testes que falham**

Acrescente ao final de `tests/test_precos.py`. O arquivo já começa com:

```python
import cv2
import numpy as np
import pytest
from mistfall.geometria import recorte_preco
from mistfall.precos import ler_preco
```

Ajuste o import para `from mistfall.precos import SEPARADOR, ler_preco, ler_precos` e acrescente:

```python
from mistfall.geometria import TODOS_OS_SLOTS

LISTA = "images/broche-dragao-orbe-codice-padrao.png"

# Verdade humana dos doze slots deste print, rotulada a olho. E a mesma que
# fixtures/esperado/broche-dragao-orbe-codice-padrao.json carrega; esta copia
# existe para o teste de ler_precos nao depender do corpus.
PRECOS_DA_LISTA = [188, 215, 218, 237, 241, 246, 253, 268, 281, 281, 313, 357]


def _recortes(caminho):
    img = cv2.imread(caminho)
    return [recorte_preco(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]


def test_ler_precos_le_os_doze_slots_de_uma_vez():
    assert ler_precos(_recortes(LISTA)) == PRECOS_DA_LISTA


def test_recorte_ilegivel_vira_none_no_indice_certo():
    # O jeito ingenuo de ler a folha e pegar os numeros na ordem em que saem.
    # Isso quebra em silencio: um preco ilegivel produz onze numeros em vez de
    # doze, e a correspondencia slot-preco se desloca inteira. Este teste apaga
    # um recorte e exige que so o indice dele mude.
    recortes = _recortes(LISTA)
    recortes[5] = np.zeros_like(recortes[5])

    lidos = ler_precos(recortes)

    assert lidos[5] is None
    esperado = list(PRECOS_DA_LISTA)
    esperado[5] = None
    assert lidos == esperado


def test_ler_precos_sem_recortes_devolve_lista_vazia():
    assert ler_precos([]) == []


def test_o_separador_esta_no_meio_do_plato_medido():
    # SEPARADOR nao e numero escolhido a olho. Varrido contra o corpus inteiro,
    # 30 a 60 px dao 84/84; 5 px cola digito de slots vizinhos e 120 px faz o
    # --psm 6 tratar os pedacos como regioes separadas, caindo para 69/84.
    # Sem este teste alguem "limpa" o 40 para 8 ou 100 e a suite nao reclama.
    assert 30 <= SEPARADOR <= 60
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_precos.py -v`
Expected: FAIL — `ImportError: cannot import name 'SEPARADOR' from 'mistfall.precos'`

- [ ] **Step 3: Implementar**

Substitua `src/mistfall/precos.py` inteiro por:

```python
import cv2
import numpy as np
import pytesseract

_CONFIG_UM = "--psm 7 -c tessedit_char_whitelist=0123456789"
_CONFIG_FOLHA = "--psm 6 -c tessedit_char_whitelist=0123456789"

# Altura da faixa preta entre dois recortes na folha. Medido contra o corpus:
# 30 a 60 px acertam 84 de 84. Fora disso piora nos dois sentidos — 5 px cola
# digito de slots vizinhos (82/84), 120 px faz o --psm 6 parar de ver um bloco
# unico e tratar os pedacos como regioes separadas (69/84), que e justamente o
# contexto entre linhas que faz a folha ler melhor que os recortes isolados.
# 40 e o centro do plato: erra por 10 px para qualquer lado sem mudar nada.
SEPARADOR = 40


def _preparar(recorte: np.ndarray) -> np.ndarray:
    """Cinza, ampliacao 4x e Otsu — o preparo que as duas leituras dividem."""
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    ampliado = cv2.resize(cinza, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binaria = cv2.threshold(
        ampliado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binaria


def ler_preco(recorte: np.ndarray) -> int | None:
    """Le um recorte sozinho. Serve as tres leituras da Janela de Confirmacao,
    que nao sao doze e nao formam bloco contiguo na tela."""
    texto = pytesseract.image_to_string(_preparar(recorte), config=_CONFIG_UM).strip()
    return int(texto) if texto.isdigit() else None


def ler_precos(recortes: list[np.ndarray]) -> list[int | None]:
    """Le varios recortes numa chamada so, empilhados numa folha.

    O pytesseract nao faz OCR em Python: grava a imagem num arquivo temporario
    e executa o binario do tesseract. Doze recortes eram doze execucoes, e na
    maquina do jogo isso custava 5729 ms contra 477 ms no Mac — criar processo
    no Windows e caro. Uma chamada paga esse custo uma vez.

    E le melhor, nao so mais rapido: com --psm 7 cada recorte e julgado como
    linha solta, sem contexto. Empilhados, o --psm 6 compara altura de digito,
    alinhamento e espessura entre as linhas. E a mesma informacao que faz um
    humano ler 241 onde um digito isolado pareceria 24. No corpus sobe de 79
    para 84 acertos em 84 slots.

    A correspondencia volta por POSICAO, nunca pela ordem em que os numeros
    saem: um recorte ilegivel produziria onze numeros em vez de doze e
    deslocaria a correspondencia inteira — o slot 6 receberia o preco do 7, e
    um erro num slot viraria erro em todos. Como sabemos em que faixa vertical
    cada recorte foi empilhado, cada numero volta ao seu indice pela caixa que
    o image_to_data devolve, e recorte ilegivel vira None no lugar certo.
    """
    if not recortes:
        return []

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

    dados = pytesseract.image_to_data(
        np.vstack(pecas), config=_CONFIG_FOLHA,
        output_type=pytesseract.Output.DICT,
    )

    achados: list[int | None] = [None] * len(recortes)
    for texto, y, altura in zip(dados["text"], dados["top"], dados["height"]):
        texto = texto.strip()
        if not texto.isdigit():
            continue
        centro = y + altura / 2
        for indice, (inicio, fim) in enumerate(faixas):
            if inicio <= centro < fim:
                if achados[indice] is None:
                    achados[indice] = int(texto)
                break
    return achados
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/test_precos.py -v`
Expected: PASS, todos.

- [ ] **Step 5: Commit**

```bash
git add src/mistfall/precos.py tests/test_precos.py
git commit -m "Le os precos de varios recortes numa chamada so

O pytesseract executa o binario do tesseract a cada chamada, e doze
recortes eram doze criacoes de processo. Na maquina do jogo isso custava
5729 ms contra 477 ms no Mac.

Empilhados com faixa preta de 40 px entre eles e lidos com --psm 6, os
doze saem numa chamada. E leem melhor: o psm 6 compara altura de digito
e alinhamento entre as linhas, onde o psm 7 julgava cada recorte sozinho.

A correspondencia volta por posicao, nao pela ordem dos numeros: recorte
ilegivel vira None no indice certo em vez de deslocar os outros onze."
```

---

### Task 2: A varredura passa a usar a folha única

**Files:**
- Modify: `src/mistfall/leilao.py`
- Modify: `src/mistfall/piloto.py:187`, `src/mistfall/piloto.py:301`, `src/mistfall/piloto.py:338`
- Test: `tests/test_leilao.py`, `tests/test_piloto.py`

**Interfaces:**
- Consumes: `mistfall.precos.ler_precos(recortes: list[np.ndarray]) -> list[int | None]` (Task 1).
- Produces: `mistfall.leilao.varrer_bruto(img: np.ndarray) -> list[Listagem]` e `mistfall.leilao.varrer(img: np.ndarray) -> list[Listagem]`, **ambas sem o parâmetro `trabalhadores`**. `mistfall.piloto._conferir_a_janela(modal, escolhida, r, trabalhadores)` mantém o parâmetro — o modal continua paralelo.

**Contexto que o implementador precisa saber:** `src/mistfall/paralelo.py` **não** é apagado, e `trabalhadores` **continua** em `config.toml` e em `mistfall.config.Config`. O que muda é só quem o consome: antes a varredura e o modal, agora só o modal. Isso é decisão registrada na spec, não descuido.

- [ ] **Step 1: Escrever o teste que falha**

Em `tests/test_leilao.py`, **apague** o bloco inteiro que começa com o comentário `# --- paralelismo da varredura ---` e vai até o fim do arquivo — são cinco testes (`test_paralelo_devolve_o_mesmo_que_sequencial`, `test_paralelo_preserva_a_posicao_de_cada_slot`, `test_varrer_bruto_tambem_bate_entre_paralelo_e_sequencial`, `test_o_padrao_e_o_do_helper`, `test_varrer_repassa_os_trabalhadores_ao_helper`) mais a constante `LISTA` e o import `from mistfall.paralelo import TRABALHADORES_PADRAO`.

No lugar, acrescente:

```python
# --- a varredura le os doze precos numa chamada so --------------------------

LISTA = "images/broche-dragao-orbe-codice-padrao.png"


def test_a_varredura_faz_uma_unica_chamada_ao_tesseract(monkeypatch):
    # Comparar resultado nao distingue uma chamada de doze: as duas leem os
    # mesmos slots. Este projeto ja teve doze defeitos da familia "teste que
    # nao testa", cinco deles numa branch so, e nenhum apareceu como suite
    # vermelha. Espiar a chamada e o que separa as duas implementacoes.
    import pytesseract
    from mistfall import precos as modulo_precos

    em_folha = []
    um_a_um = []
    data_real = pytesseract.image_to_data
    string_real = pytesseract.image_to_string

    def espiao_data(*args, **kwargs):
        em_folha.append(1)
        return data_real(*args, **kwargs)

    def espiao_string(*args, **kwargs):
        um_a_um.append(1)
        return string_real(*args, **kwargs)

    monkeypatch.setattr(modulo_precos.pytesseract, "image_to_data", espiao_data)
    monkeypatch.setattr(modulo_precos.pytesseract, "image_to_string", espiao_string)

    varrer_bruto(cv2.imread(LISTA))

    assert len(em_folha) == 1, f"esperava uma chamada em folha, houve {len(em_folha)}"
    assert um_a_um == [], f"a varredura voltou a ler recorte a recorte: {len(um_a_um)} chamadas"


def test_a_varredura_preserva_a_posicao_de_cada_slot():
    posicoes = [(l.linha, l.coluna) for l in varrer(cv2.imread(LISTA))]
    assert posicoes == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1),
        (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1),
    ]


def test_a_varredura_nao_aceita_mais_trabalhadores():
    # Com uma chamada so nao ha o que paralelizar. Parametro que nao faz nada e
    # a mesma falha que esta base ja cometeu — config que promete e nao entrega.
    import inspect
    assert "trabalhadores" not in inspect.signature(varrer).parameters
    assert "trabalhadores" not in inspect.signature(varrer_bruto).parameters
```

Em `tests/test_piloto.py`, **apague** o teste `test_a_varredura_repassa_os_trabalhadores_configurados_ao_helper` inteiro, com o comentário acima dele. Ele guardava o repasse de `config.trabalhadores` até `varrer_bruto`, e esse caminho deixa de existir. O caminho que sobrou — `config.trabalhadores` até o modal — continua guardado por `test_as_leituras_do_modal_passam_pelo_helper_de_paralelismo`, que fica.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_leilao.py -v`
Expected: FAIL — `test_a_varredura_faz_uma_unica_chamada_ao_tesseract` falha com `esperava uma chamada em folha, houve 0` e `test_a_varredura_nao_aceita_mais_trabalhadores` falha porque o parâmetro ainda existe.

- [ ] **Step 3: Implementar em `leilao.py`**

Troque as linhas 1 a 30 de `src/mistfall/leilao.py` por:

```python
import dataclasses
import numpy as np
from mistfall.geometria import TODOS_OS_SLOTS, regiao_icone, recorte_preco
from mistfall.itens import identificar_item
from mistfall.precos import ler_precos
from mistfall.tipos import Listagem

def varrer_bruto(img: np.ndarray) -> list[Listagem]:
    """Le os doze slots como estao, sem conferir nada entre eles.

    Existe separada de `varrer` para o corpus de regressao poder documentar o
    que o OCR entrega de fato. Quem decide Compra usa `varrer`.

    Os doze precos saem de UMA chamada ao tesseract, com os recortes empilhados
    numa folha — nao ha `trabalhadores` aqui porque nao ha o que paralelizar.
    O helper de paralelismo continua no projeto e continua servindo as tres
    leituras da Janela de Confirmacao; `config.trabalhadores` alimenta aquele
    caminho, nao este.
    """
    icones = [regiao_icone(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    precos = [recorte_preco(img, linha, coluna) for linha, coluna in TODOS_OS_SLOTS]
    itens = [identificar_item(icone) for icone in icones]
    lidos = ler_precos(precos)
    return [
        Listagem(linha=linha, coluna=coluna, item=item, preco_unitario=preco)
        for (linha, coluna), item, preco in zip(TODOS_OS_SLOTS, itens, lidos)
    ]
```

E as duas últimas linhas do arquivo por:

```python
def varrer(img: np.ndarray) -> list[Listagem]:
    """Imagem do Leilao -> doze Listagens ja conferidas contra a ordenacao."""
    return conferir_ordenacao(varrer_bruto(img))
```

`conferir_ordenacao`, no meio do arquivo, **não muda em nada** — nem código, nem docstring.

- [ ] **Step 4: Implementar em `piloto.py`**

Em `src/mistfall/piloto.py`, linha 301, troque:

```python
        brutas = varrer_bruto(inicial, config.trabalhadores)
```

por:

```python
        brutas = varrer_bruto(inicial)
```

As linhas 187 e 338 (`_conferir_a_janela(... trabalhadores)` e `config.trabalhadores` na chamada dela) **ficam como estão** — o modal continua paralelo.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: `tests/test_precos.py`, `tests/test_leilao.py` e `tests/test_piloto.py` passam. `tests/test_regressao.py` **falha** — o corpus ainda descreve os gaps de OCR antigos. É esperado, e a Task 3 fecha.

- [ ] **Step 6: Commit**

```bash
git add src/mistfall/leilao.py src/mistfall/piloto.py tests/test_leilao.py tests/test_piloto.py
git commit -m "A varredura le os doze precos numa chamada, sem trabalhadores

varrer e varrer_bruto perdem o parametro: com uma chamada so nao ha o que
paralelizar, e parametro que nao faz nada e a falha que esta base ja
cometeu quando trabalhadores nao chegava na varredura e o README dizia
que chegava.

O helper de paralelismo fica, e config.trabalhadores continua valendo —
para as tres leituras da Janela de Confirmacao, que e o unico caminho que
ainda paraleliza.

Saem seis testes que guardavam o caminho antigo, entre eles o espiao de
repasse ate varrer_bruto. Ele nasceu de um achado de review real e sai
porque o caminho acabou, nao porque incomoda: o repasse ate o modal
continua guardado por test_as_leituras_do_modal_passam_pelo_helper."
```

---

### Task 3: O corpus fecha os cinco gaps de OCR

**Files:**
- Modify: `fixtures/esperado/broche-dragao-orbe-codice-padrao.json`, `fixtures/esperado/broche-tres-dragao-padrao.json`, `fixtures/esperado/lanterna-dragao-orbe-rede.json`, `fixtures/esperado/rede-dois-dragao-padrao.json`
- Modify: `tests/test_regressao.py`

**Interfaces:**
- Consumes: `mistfall.leilao.varrer_bruto(img)` e `mistfall.leilao.varrer(img)` sem `trabalhadores` (Task 2).
- Produces: corpus sem nenhum campo `ocr_lido_atual`; `DERRUBADOS_PELA_ORDENACAO` vazio.

**Os cinco gaps a remover** — cada um é um campo `"ocr_lido_atual": <n>` dentro do slot indicado. Remova **apenas** esse campo; `preco_unitario`, `linha`, `coluna` e `item` do slot ficam intactos.

| arquivo | slot | `ocr_lido_atual` a remover | `preco_unitario` que fica |
|---|---|---|---|
| `broche-dragao-orbe-codice-padrao.json` | (1,1) | `null` | 237 |
| `broche-dragao-orbe-codice-padrao.json` | (2,0) | `24` | 241 |
| `broche-tres-dragao-padrao.json` | (4,0) | `2892` | 282 |
| `lanterna-dragao-orbe-rede.json` | (0,1) | `293` | 223 |
| `rede-dois-dragao-padrao.json` | (3,0) | `null` | 249 |

- [ ] **Step 1: Ver a suíte de regressão falhar**

Run: `.venv/bin/python -m pytest tests/test_regressao.py -q`
Expected: FAIL. Os slots com gap agora leem a verdade humana, e o teste os compara contra `ocr_lido_atual`; e `test_conferencia_de_ordenacao_derruba_exatamente_os_slots_previstos` falha porque a ordenação não derruba mais nada.

- [ ] **Step 2: Remover os cinco campos `ocr_lido_atual`**

Edite os quatro JSONs conforme a tabela acima. Confira depois com:

Run: `grep -c ocr_lido_atual fixtures/esperado/*.json`
Expected: `0` em todos os sete arquivos.

- [ ] **Step 3: Zerar os dois guardas em `tests/test_regressao.py`**

Em `test_slot_com_gap_de_ocr_tem_verdade_humana_propria`, a última linha passa de `assert conferidos == 5` para:

```python
    assert conferidos == 0
```

Em `test_corpus_tem_gaps_conhecidos_de_ocr`, o `assert` passa a:

```python
    assert total_gaps == 0, (
        f"Corpus tem {total_gaps} slots com ocr_lido_atual, esperado 0. "
        "A leitura em folha unica fechou os cinco gaps que existiam. "
        "Se um gap novo apareceu, o OCR regrediu — investigue antes de "
        "adicionar ocr_lido_atual de volta."
    )
```

- [ ] **Step 4: Esvaziar `DERRUBADOS_PELA_ORDENACAO`**

Troque o bloco de comentário e o dicionário inteiro por:

```python
# Slots cujo Preco-unitario a conferencia de ordenacao derruba em cada print.
# Vazio desde a leitura em folha unica: os tres prints que apareciam aqui
# apareciam por erro de OCR — um 24 onde a verdade era 241, um 2892 onde era
# 282, um 293 onde era 223 — e a folha unica le os tres certo. Nenhuma leitura
# do corpus viola mais a ordenacao.
#
# Dicionario vazio nao e teste sem dentes: se o OCR regredir e voltar a produzir
# preco fora de ordem, a ordenacao derruba slots e este teste quebra na hora. O
# comportamento da propria regra e provado em tests/test_ordenacao.py, com
# listagens montadas a mao — nao depende do corpus acertar ou errar.
DERRUBADOS_PELA_ORDENACAO = {}
```

- [ ] **Step 5: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, tudo verde.

- [ ] **Step 6: Commit**

```bash
git add fixtures/esperado tests/test_regressao.py
git commit -m "Fecha os cinco gaps de OCR do corpus

A leitura em folha unica acerta os cinco slots que o corpus registrava
como falha conhecida: o 24 onde a verdade era 241, o 2892 onde era 282,
o 293 onde era 223 e os dois nulls. Os campos ocr_lido_atual saem e os
guardas passam a afirmar zero.

DERRUBADOS_PELA_ORDENACAO fica vazio pelo mesmo motivo: os tres prints
que apareciam la apareciam por erro de leitura, e agora nenhuma leitura
do corpus viola a ordenacao. A regra continua valendo e continua provada
em test_ordenacao.py; se o OCR regredir, o dicionario vazio quebra."
```

---

### Task 4: O print da máquina do jogo vira caso de teste

**Files:**
- Modify: `tests/test_regressao.py`

**Interfaces:**
- Consumes: `mistfall.leilao.varrer_bruto(img)` sem `trabalhadores` (Task 2).
- Produces: nada que outra tarefa use.

**Contexto:** `images/sete-itens-ocr-227-como-297.png` veio da máquina do jogo e **não** tem fixture no corpus — os doze slots dele nunca foram rotulados a olho. O que se sabe com certeza humana é o slot `(0,1)`, que o nome do arquivo registra: a verdade é **227** e a leitura recorte-a-recorte dava **297**. É a #17. Não invente verdade para os outros onze slots; um corpus rotulado pelo que o código produz não prova nada.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente ao final de `tests/test_regressao.py`:

```python
def test_o_print_da_maquina_do_jogo_le_o_227():
    """A #17: a leitura recorte-a-recorte lia 297 onde a verdade e 227.

    Um 2 virando 9 e a falha mais perigosa que existe aqui — nao quebra nada,
    nao gera erro, so faz o bot pagar 70 ouros a mais. Foi a conferencia de
    ordenacao que pegou, derrubando a tela inteira.

    Este print nao tem fixture no corpus: os doze slots dele nunca foram
    rotulados a olho, e so o (0,1) tem verdade humana — o nome do arquivo a
    registra. Por isso o teste afirma um slot, e nao doze.
    """
    img = cv2.imread("images/sete-itens-ocr-227-como-297.png")
    slots = {(l.linha, l.coluna): l.preco_unitario for l in varrer_bruto(img)}
    assert slots[(0, 1)] == 227
```

- [ ] **Step 2: Rodar**

Run: `.venv/bin/python -m pytest tests/test_regressao.py::test_o_print_da_maquina_do_jogo_le_o_227 -v`
Expected: PASS — a folha única já lê 227. Se falhar com `297`, pare: a Task 1 não ficou como o plano descreve, e o resto do plano não se sustenta.

- [ ] **Step 3: Commit**

```bash
git add tests/test_regressao.py
git commit -m "Guarda o 227 do print da maquina do jogo

A leitura recorte-a-recorte lia 297 onde a verdade e 227, e um 2 virando
9 e a falha mais cara que existe aqui: nao quebra nada, so faz o bot
pagar 70 ouros a mais. Quem pegou foi a conferencia de ordenacao,
derrubando a tela inteira.

O print nao tem fixture porque os doze slots dele nunca foram rotulados a
olho — so o (0,1) tem verdade humana, que o nome do arquivo registra."
```

---

### Task 5: Documentação

**Files:**
- Modify: `README.md:17`, `README.md:169-174`, `README.md:182`
- Modify: `docs/superpowers/specs/2026-08-13-preco-exato-e-paralelismo-design.md`
- Test: `tests/test_documentacao.py`

**Interfaces:**
- Consumes: o comportamento entregue pelas Tasks 1 a 4.
- Produces: nada que outra tarefa use.

**Contexto:** `tests/test_documentacao.py` já tem `test_o_readme_documenta_os_trabalhadores`, que exige a palavra `trabalhadores` no README. Ela continua lá — o que muda é o que o texto diz que ela faz.

- [ ] **Step 1: Escrever o teste que falha**

Acrescente ao final de `tests/test_documentacao.py`:

```python
def test_o_readme_nao_promete_paralelismo_na_varredura():
    # A varredura passou a fazer uma chamada so. O texto antigo dizia que
    # `trabalhadores` controlava OCRs em paralelo "na varredura dos 12 slots
    # e nos numeros da Janela de Confirmacao" — metade disso deixou de ser
    # verdade. Config que promete uma coisa e faz outra ja custou um review
    # inteiro neste projeto.
    assert "na varredura dos 12 slots" not in README


def test_o_readme_explica_a_leitura_em_folha_unica():
    assert "folha" in README.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/test_documentacao.py -v`
Expected: FAIL nos dois testes novos.

- [ ] **Step 3: Atualizar o passo 4 do "Como funciona"**

Em `README.md`, a linha 17 é hoje:

```markdown
4. Lê o **Preço-unitário** de cada slot por OCR
```

Troque por:

```markdown
4. Lê o **Preço-unitário** dos 12 slots por OCR, numa **chamada só**: os recortes vão
   empilhados numa folha, separados por faixas pretas, e cada número volta ao seu slot pela
   posição vertical
```

- [ ] **Step 4: Reescrever o parágrafo de `trabalhadores`**

Em `README.md`, o parágrafo das linhas 169 a 174 é hoje:

```markdown
`trabalhadores` controla quantos OCRs rodam em paralelo — na varredura dos 12 slots e nos
números da Janela de Confirmação. O padrão é **4**: já dá um ganho de ~3× sobre rodar
sequencial, e deixa CPU sobrando para o próprio jogo, que roda na mesma máquina e precisa
desenhar a tela que o bot captura. Subir para o total de núcleos rende pouco mais e disputa
tudo com o jogo — `trabalhadores=1` continua disponível, e roda sequencial de verdade, útil
para depurar.
```

Troque por:

```markdown
`trabalhadores` controla quantos OCRs rodam em paralelo **na Janela de Confirmação** — são as
três leituras dela, e só. A varredura dos 12 slots **não** usa este número: ela faz uma chamada
só ao tesseract, com os doze recortes empilhados numa folha, e não há o que paralelizar.

Vale a pena saber por quê, porque foi o contrário do esperado: paralelizar doze execuções do
tesseract continua sendo doze execuções, e o custo real era criar processo — 5729 ms na máquina
do jogo contra 477 ms no Mac, com o mesmo paralelismo ligado. Trocar doze chamadas por uma
levou a varredura de 503 ms para 221 ms no Mac, e de quebra subiu o acerto do corpus de 79 para
84 slots em 84: empilhados, o tesseract compara altura de dígito e alinhamento entre as linhas,
onde antes julgava cada recorte sozinho.

O padrão é **4**, e deixa CPU sobrando para o próprio jogo, que roda na mesma máquina e precisa
desenhar a tela que o bot captura. `trabalhadores=1` continua disponível, e roda sequencial de
verdade, útil para depurar.
```

- [ ] **Step 5: Corrigir a contagem de testes**

Em `README.md`, linha 182, está `São 257 testes, e todos rodam no Mac sem o jogo aberto.` Rode `.venv/bin/python -m pytest -q | tail -1` e troque `257` pelo número que sair.

- [ ] **Step 6: Anotar a spec de 2026-08-13**

Em `docs/superpowers/specs/2026-08-13-preco-exato-e-paralelismo-design.md`, acrescente logo no topo do arquivo, depois da linha do título:

```markdown
> **Nota de 2026-08-14.** A seção de paralelismo desta spec descreve a varredura dos 12 slots
> rodando OCR em paralelo. Isso mudou: a varredura passou a ler os doze preços numa chamada só
> — ver `2026-08-14-leitura-de-precos-em-folha-unica-design.md`. Os números de paralelismo
> registrados aqui continuam válidos, mas valem agora só para as três leituras da Janela de
> Confirmação, que é o único caminho que ainda usa `trabalhadores`.
```

- [ ] **Step 7: Rodar a suíte inteira**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, tudo verde.

- [ ] **Step 8: Commit**

```bash
git add README.md docs/superpowers/specs/2026-08-13-preco-exato-e-paralelismo-design.md tests/test_documentacao.py
git commit -m "Documenta que a varredura nao paraleliza mais

O README dizia que trabalhadores controlava OCRs em paralelo na varredura
dos 12 slots e no modal. Metade deixou de ser verdade, e config que
promete uma coisa e faz outra ja custou um review inteiro aqui.

Explica tambem o resultado contraintuitivo, que vale mais que o numero:
paralelizar doze execucoes do tesseract continua sendo doze execucoes, e
o custo era criar processo. Uma chamada so levou a varredura de 503 ms
para 221 ms e o acerto do corpus de 79 para 84 em 84.

A spec de 2026-08-13 ganha nota no topo apontando para a nova."
```

---

### Task 6: A issue de análise e remoção futura do helper

**Files:** nenhum — a entrega é uma issue no GitHub.

**Interfaces:**
- Consumes: o estado final das Tasks 1 a 5.
- Produces: nada que outra tarefa use.

**Contexto:** o helper `src/mistfall/paralelo.py` fica no código por decisão explícita do usuário: ainda estamos experimentando, e mantê-lo permite voltar atrás sem reconstruir nada. A issue existe para que "fica no código" seja decisão registrada, e não esquecimento. **Não** implemente a remoção.

- [ ] **Step 1: Publicar a issue**

```bash
gh issue create --repo lavarini/mistfall-reseller \
  --title "Avaliar a remoção do helper de paralelismo" \
  --body-file - <<'CORPO'
## Parent

#1

## O que aconteceu

A varredura dos 12 slots parou de usar `src/mistfall/paralelo.py`. Ela passou a ler os doze
Preços-unitários numa chamada só ao tesseract, com os recortes empilhados numa folha, e não há
mais o que paralelizar ali.

O helper **ficou no código** por decisão explícita: ainda estamos experimentando a leitura em
folha única, e mantê-lo permite voltar atrás sem reconstruir nada.

## O que ele ainda serve

Um caminho só: as três leituras da Janela de Confirmação, em
`piloto._conferir_a_janela`. É por isso que `trabalhadores` continua em `config.toml` e continua
tendo efeito.

## A pergunta a responder

Três leituras justificam um `ThreadPoolExecutor`, um módulo próprio, oito testes e uma chave de
configuração?

O que decide é medição na máquina do jogo, não no Mac: lá o custo de criar processo é o que
pesa, e é justamente esse custo que o paralelismo do modal ainda divide. Se o ganho real for de
poucas dezenas de milissegundos, o helper sai e as três leituras viram três chamadas em
sequência.

Se sair, sai junto: `config.trabalhadores`, a chave em `config.toml`, `tests/test_paralelo.py` e
as menções no README.

## Acceptance criteria

- [ ] O tempo das três leituras do modal está medido na máquina do jogo, com `trabalhadores=1`
      e com `trabalhadores=4`
- [ ] A decisão — manter ou remover — está registrada com o número que a sustenta
- [ ] Se for remover, `paralelo.py`, `config.trabalhadores`, a chave do `config.toml`,
      `tests/test_paralelo.py` e as menções no README saem juntos, sem deixar config órfã
- [ ] Se for manter, o README diz por que três leituras justificam o helper

## Blocked by

Nada impede a decisão. Mas ela depende de uma execução na máquina do jogo com os dois valores de
`trabalhadores`, e sem esse número a escolha é palpite.
CORPO
```

- [ ] **Step 2: Reportar o número da issue**

Anote o número que o `gh` devolver — ele entra no relatório final da branch.

---

## Auto-revisão

**Cobertura da spec:**

| requisito da spec | tarefa |
|---|---|
| `ler_precos(recortes) -> list[int | None]` em `precos.py` | 1 |
| `ler_preco` permanece para o modal | 1 |
| separador obrigatório, `SEPARADOR = 40` no platô medido | 1 |
| correspondência por posição, não por ordem | 1 (teste do slot ilegível) |
| `varrer_bruto` chama `ler_precos` uma vez | 2 |
| `trabalhadores` sai da varredura, seis testes saem junto | 2 |
| helper de paralelismo fica no código | 2 (não é tocado) e 6 |
| `conferir_ordenacao` não muda | 2 (dito explicitamente) |
| corpus 84/84, cinco `ocr_lido_atual` viram zero | 3 |
| `DERRUBADOS_PELA_ORDENACAO` vazio, com a razão registrada | 3 |
| print da máquina do jogo lê 227 (#17) | 4 |
| "uma chamada, não doze" com espião | 2 |
| README e spec de 2026-08-13 atualizados | 5 |
| issue de remoção futura do helper | 6 |

**Fora de escopo, como a spec manda:** aplicar folha única ao modal; trocar `pytesseract` por `tesserocr`; a animação do modal (#18, do usuário); o portão do ícone (#19).

**Consistência de tipos:** `ler_precos(list[np.ndarray]) -> list[int | None]` é definida na Task 1 e consumida na Task 2 com o mesmo nome e a mesma assinatura. `varrer`/`varrer_bruto` perdem `trabalhadores` na Task 2 e são chamadas sem ele nas Tasks 3 e 4. `SEPARADOR` é definido e testado na Task 1, e não é referenciado depois.

**Ordem obrigatória:** 1 → 2 → 3. A suíte fica vermelha entre a Task 2 e a Task 3, de propósito e por um motivo declarado (o corpus ainda descreve os gaps antigos). As Tasks 4, 5 e 6 podem vir em qualquer ordem depois da 3.
