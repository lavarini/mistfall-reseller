import cv2
import pytest
import mistfall.itens as itens_mod
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

def test_acha_os_templates_rodando_de_outro_diretorio(fonte, monkeypatch, tmp_path):
    # A pasta templates/ nao pode depender do diretorio corrente: ferramentas e
    # o loop importam esta camada de outros lugares.
    itens_mod._templates.cache_clear()
    monkeypatch.chdir(tmp_path)
    try:
        assert identificar_item(regiao_icone(fonte, 0, 0)) is ItemAlvo.BROCHE
    finally:
        itens_mod._templates.cache_clear()

def test_margem_sobre_o_segundo_colocado_e_folgada(outro):
    # 0.30 escrito a mao, nao importado de itens: medindo os 49 slots de
    # Item-alvo dos 7 prints de Leilao, a pior margem real e 0.383.
    for slot in ALVOS_OUTRO:
        ranking = sorted(pontuar(regiao_icone(outro, *slot)).values(), reverse=True)
        assert ranking[0] - ranking[1] > 0.30, slot

# images/janela.png nao e lista utilizavel: a Janela de Confirmacao cobre o
# Leilao e o que sobra por tras dos vidros do modal produz scores altos por
# acidente. Sao os piores casos conhecidos de identificacao.
JANELA = "images/janela.png"

@pytest.fixture(scope="module")
def modal():
    return cv2.imread(JANELA)

@pytest.mark.parametrize(
    "slot,melhor,segundo",
    [
        # slot, score do primeiro, score do segundo colocado (medidos)
        ((3, 0), 0.7411, 0.6459),  # dragao vs codice — margem 0.0952
        ((0, 0), 0.7378, 0.5379),  # broche vs lanterna — margem 0.1999
    ],
)
def test_recusa_quando_o_segundo_colocado_esta_colado(modal, slot, melhor, segundo):
    # Ambos passavam do limiar absoluto de 0.70 e viravam Item-alvo. Confundir
    # Broche (alvo 188) com Codice (alvo 281) faria o bot pagar 275 achando que
    # comprou barato — overpay de 46% com o preco lido corretamente.
    assert identificar_item(regiao_icone(modal, *slot)) is None

def test_a_margem_exigida_nao_derruba_nenhum_item_alvo_de_verdade(fonte, outro):
    # Contrapeso do teste acima: apertar a margem nao pode custar deteccao real.
    for img, alvos in ((fonte, ALVOS_FONTE), (outro, ALVOS_OUTRO)):
        for slot, item in alvos.items():
            assert identificar_item(regiao_icone(img, *slot)) is item, slot
