from unittest import mock

import cv2
import numpy as np
import pytest
from mistfall import precos
from mistfall.geometria import recorte_preco, TODOS_OS_SLOTS
from mistfall.precos import SEPARADOR, ler_preco, ler_precos, _preparar

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


def test_faixa_com_dois_numeros_vira_none():
    # Achado do review final. O tesseract pode partir um preco em dois tokens
    # na mesma faixa — 241 saindo como "24" e "1". Ficar com o primeiro
    # devolveria 24, um preco MENOR que o verdadeiro, e preco menor aqui e
    # leitura errada e nao pechincha: e assim que o bot compra pelo motivo
    # errado. O --psm 7 antigo devolvia None nesse caso porque conferia
    # isdigit() na linha toda; a folha unica nao pode perder essa rede.
    #
    # O corpus nao produz esse caso hoje (as 84 faixas dao um token cada), e e
    # justamente por isso que o teste dubla a saida do tesseract: sem dublar,
    # o guarda nao teria como falhar.
    recortes = [np.zeros((45, 80, 3), dtype=np.uint8) for _ in range(2)]
    altura = _preparar(recortes[0]).shape[0]

    def dados_partidos(*args, **kwargs):
        return {
            # Faixa 0: o preco partiu em dois tokens.
            "text": ["24", "1", "253"],
            "top": [10, 10, altura + SEPARADOR + 10],
            "height": [20, 20, 20],
        }

    with mock.patch.object(precos.pytesseract, "image_to_data", dados_partidos):
        lidos = ler_precos(recortes)

    assert lidos == [None, 253]


def test_o_separador_esta_no_meio_do_plato_medido():
    # SEPARADOR nao e numero escolhido a olho: varrido contra o corpus inteiro,
    # 30 a 60 px dao 84/84; 5 px cola digito de slots vizinhos e 120 px faz o
    # --psm 6 tratar os pedacos como regioes separadas, caindo para 69/84.
    #
    # Este teste NAO revarre o corpus — ele so trava o 40 dentro do plato
    # medido, para alguem nao "limpar" o numero para 8 ou 100 sem reclamacao.
    # Quem guarda o acerto de verdade, no valor vivo, e o
    # test_deteccao_bate_com_o_corpus_rotulado.
    assert 30 <= SEPARADOR <= 60
