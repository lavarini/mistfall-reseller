import glob
import json
import pathlib
import cv2
import pytest
from mistfall.leilao import varrer, varrer_bruto

CASOS = sorted(glob.glob("fixtures/esperado/*.json"))

def _compara_slots(nome_print, esperado_slots, obtido_slots):
    """Compara slots respeitando gaps conhecidos de OCR (ocr_lido_atual).

    Retorna lista de erros encontrados, ou lista vazia se tudo bater.
    Cada erro é uma tupla (print, slot_id, mensagem).
    """
    erros = []

    if len(obtido_slots) != len(esperado_slots):
        erros.append((
            nome_print,
            "[contagem desalinhada]",
            f"corpus e varredura divergem em contagem: esperado {len(esperado_slots)} slots, obtido {len(obtido_slots)}"
        ))
        return erros

    for obtido, esperado in zip(obtido_slots, esperado_slots):
        linha_esp = esperado.get("linha")
        coluna_esp = esperado.get("coluna")
        slot_id = f"({linha_esp},{coluna_esp})"

        # Comparar posição (linha/coluna) antes de qualquer outro campo.
        # Se divergir, o corpus está desalinhado com a varredura — erro crítico.
        linha_obt = obtido.get("linha")
        coluna_obt = obtido.get("coluna")
        if linha_obt != linha_esp or coluna_obt != coluna_esp:
            erros.append((
                nome_print,
                slot_id,
                f"corpus desalinhado: esperado slot ({linha_esp},{coluna_esp}), "
                f"mas varredura forneceu ({linha_obt},{coluna_obt}) nesta posição"
            ))
            # Continua verificando, pois há outras falhas neste mesmo slot
            continue

        # Item é sempre comparado exato — nenhuma exceção
        if obtido.get("item") != esperado.get("item"):
            erros.append((
                nome_print,
                slot_id,
                f"item diverge: esperado {esperado.get('item')!r}, obtido {obtido.get('item')!r}"
            ))

        # Preço tem duas regras
        tem_ocr_gap = "ocr_lido_atual" in esperado
        if tem_ocr_gap:
            # Gap conhecido: compare obtido contra ocr_lido_atual (a falha atual)
            gap_value = esperado["ocr_lido_atual"]
            if obtido.get("preco_unitario") != gap_value:
                erros.append((
                    nome_print,
                    slot_id,
                    f"preço divergiu do gap conhecido: esperado leitura {gap_value!r}, obtido {obtido.get('preco_unitario')!r} "
                    f"(verdade humana é {esperado.get('preco_unitario')}; gap pode ter sido corrigido ou piorou)"
                ))
        else:
            # Sem gap: compare contra preco_unitario (a verdade)
            if obtido.get("preco_unitario") != esperado.get("preco_unitario"):
                erros.append((
                    nome_print,
                    slot_id,
                    f"preço diverge: esperado {esperado.get('preco_unitario')}, obtido {obtido.get('preco_unitario')}"
                ))

    return erros

@pytest.mark.parametrize("caminho_json", CASOS, ids=lambda p: pathlib.Path(p).stem)
def test_deteccao_bate_com_o_corpus_rotulado(caminho_json):
    # Compara contra varrer_bruto de proposito: o corpus documenta o que o OCR
    # entrega, sem a conferencia de ordenacao por cima. A conferencia tem testes
    # proprios (tests/test_ordenacao.py e o teste de corpus logo abaixo); se ela
    # entrasse aqui, os slots que ela invalida virariam gap de OCR no JSON e o
    # corpus perderia o registro do que o pipeline de leitura realmente faz.
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
        for l in varrer_bruto(img)
    ]

    erros = _compara_slots(nome, esperado, obtido)
    if erros:
        msg_erros = "\n".join(f"  {print_nome} slot {slot_id}: {msg}" for print_nome, slot_id, msg in erros)
        raise AssertionError(f"Detecção divergiu do corpus:\n{msg_erros}")

def test_o_corpus_nao_esta_vazio():
    assert len(CASOS) >= 7

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

@pytest.mark.parametrize("caminho_json", CASOS, ids=lambda p: pathlib.Path(p).stem)
def test_conferencia_de_ordenacao_derruba_exatamente_os_slots_previstos(caminho_json):
    nome = pathlib.Path(caminho_json).stem
    img = cv2.imread(f"images/{nome}.png")
    brutas = {(l.linha, l.coluna): l.preco_unitario for l in varrer_bruto(img)}
    conferidas = {(l.linha, l.coluna): l.preco_unitario for l in varrer(img)}

    derrubados = sorted(
        slot
        for slot, preco in brutas.items()
        if preco is not None and conferidas[slot] is None
    )
    assert derrubados == DERRUBADOS_PELA_ORDENACAO.get(nome, [])

def test_a_verdade_humana_do_corpus_e_nao_decrescente():
    """A premissa em que a conferencia de ordenacao se apoia.

    Se algum dia um print rotulado a olho sair fora de ordem, a premissa caiu e
    `conferir_ordenacao` passa a invalidar leitura boa — este teste avisa antes.
    """
    for caminho in CASOS:
        nome = pathlib.Path(caminho).stem
        slots = json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))["slots"]
        verdades = [slot["preco_unitario"] for slot in slots]
        assert all(v is not None for v in verdades), nome
        assert verdades == sorted(verdades), (nome, verdades)

def test_slot_com_gap_de_ocr_tem_verdade_humana_propria():
    """Sem isto, editar a verdade de um slot com gap nao quebra teste nenhum.

    Em slot com `ocr_lido_atual` o teste de regressao compara o obtido contra a
    leitura falha, e o `preco_unitario` (a verdade humana) fica sem afirmacao.
    """
    conferidos = 0
    for caminho in CASOS:
        nome = pathlib.Path(caminho).stem
        slots = json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))["slots"]
        for slot in slots:
            if "ocr_lido_atual" not in slot:
                continue
            conferidos += 1
            onde = f"{nome} ({slot['linha']},{slot['coluna']})"
            verdade = slot["preco_unitario"]
            assert isinstance(verdade, int), onde
            assert verdade > 0, onde
            # Se fossem iguais nao haveria gap nenhum a registrar.
            assert verdade != slot["ocr_lido_atual"], onde
    assert conferidos == 0

def test_corpus_tem_gaps_conhecidos_de_ocr():
    """Afirma quantos slots carregam falha de OCR conhecida.

    Se alguém adicionar um gap novo sem perceber, ou fechar um gap,
    esse número muda e o teste avisa que o corpus precisa reavaliação.
    """
    total_gaps = 0
    for caminho in CASOS:
        slots = json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))["slots"]
        total_gaps += sum(1 for slot in slots if "ocr_lido_atual" in slot)

    assert total_gaps == 0, (
        f"Corpus tem {total_gaps} slots com ocr_lido_atual, esperado 0. "
        "A leitura em folha unica fechou os cinco gaps que existiam. "
        "Se um gap novo apareceu, o OCR regrediu — investigue antes de "
        "adicionar ocr_lido_atual de volta."
    )

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
