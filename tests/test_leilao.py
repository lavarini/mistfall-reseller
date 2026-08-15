import cv2
import pytest
from mistfall.config import Config
from mistfall.decisao import escolher
from mistfall.leilao import varrer, varrer_bruto
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
    # Precos literais deste print. "Todo nao-alvo tem preco" seria falso em
    # geral — o corpus registra tres slots em que o OCR nao devolve digito —
    # e so passava por acaso, porque esta fixture nao tem gap nenhum.
    por_slot = {(l.linha, l.coluna): l.preco_unitario for l in listagens if l.item is None}
    assert por_slot == {
        (1, 0): 234,
        (2, 0): 237,
        (2, 1): 239,
        (4, 1): 269,
        (5, 1): 388,
    }

# --- varrer sobre a Janela de Confirmacao -------------------------------------
#
# Nada acopla `identificar_estado` a `varrer`: essa fronteira e do plano do loop.
# Entao `varrer` pode ser chamada com o modal aberto, e o que ela devolve nesse
# caso e comportamento observado, nao desenho. Estes testes fixam a observacao
# para que qualquer mudanca nela apareca em vez de passar batida.

@pytest.fixture(scope="module")
def listagens_do_modal():
    return varrer(cv2.imread("images/janela.png"))

def test_atraves_do_modal_ainda_sobra_um_item_alvo(listagens_do_modal):
    # A Janela de Confirmacao cobre a lista, mas partes do Leilao aparecem por
    # tras dela e o template matching ainda acerta o icone do slot (0,1), com
    # margem 0.348. Eram quatro slots antes da margem minima sobre o segundo
    # colocado; sobrou o unico com margem de Item-alvo de verdade.
    achados = {(l.linha, l.coluna): l.item for l in listagens_do_modal if l.item}
    assert achados == {(0, 1): ItemAlvo.ADAGA}

def test_atraves_do_modal_so_um_preco_e_legivel(listagens_do_modal):
    # 4 nao e Preco-unitario de Listagem nenhuma: e sujeira do modal caindo
    # dentro do recorte do slot (4,0). Antes da leitura em folha unica o que
    # vazava era 1174, numero da Tendencia de Mercado, no slot (1,0) — o
    # numero mudou, o fato de nao ser preco de verdade nao.
    precos = {(l.linha, l.coluna): l.preco_unitario for l in listagens_do_modal}
    assert {slot: p for slot, p in precos.items() if p is not None} == {(4, 0): 4}

def test_nenhum_slot_do_modal_tem_item_e_preco_ao_mesmo_tempo(listagens_do_modal):
    # E so por isto que `escolher` nao compra nada aqui. E acidente, nao
    # desenho: quem garante que o modal nao e varrido e o loop, com
    # identificar_estado. Se este teste cair, a protecao de verdade sumiu.
    assert [
        (l.linha, l.coluna)
        for l in listagens_do_modal
        if l.item is not None and l.preco_unitario is not None
    ] == []

def test_escolher_nao_compra_nada_atraves_do_modal(listagens_do_modal):
    import random
    config = Config(
        precos_alvo={item: 2000 for item in ItemAlvo},  # alvo generoso de proposito
    )
    assert escolher(listagens_do_modal, config, random.Random(42)) is None


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


def test_varredura_bruta_registra_itens_e_tempos_da_folha():
    tempos = {}
    listagens = varrer_bruto(cv2.imread(LISTA), tempos)
    assert len(listagens) == 12
    assert set(tempos) == {"itens", "preparo_folha", "tesseract_precos"}
    assert all(ms >= 0 for ms in tempos.values())


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
