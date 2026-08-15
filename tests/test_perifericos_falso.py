import cv2
import numpy as np
import pytest
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa

LISTA = "images/broche-dragao-orbe-codice-padrao.png"
JANELA = "images/janela.png"

def test_tela_falsa_devolve_copia_nao_o_frame_original():
    tela = TelaFalsa([LISTA])
    primeira = tela.capturar()
    primeira[0, 0] = 255
    segunda = tela.capturar()
    original = cv2.imread(LISTA)
    assert np.array_equal(segunda, original)

def test_tela_falsa_serve_os_frames_na_ordem():
    # Confere QUAL frame veio em cada captura. "os dois diferem" passaria
    # tambem com a ordem invertida — e a ordem e todo o roteiro do piloto.
    tela = TelaFalsa([LISTA, JANELA])
    assert np.array_equal(tela.capturar(), cv2.imread(LISTA))
    assert np.array_equal(tela.capturar(), cv2.imread(JANELA))

def test_tela_falsa_repete_o_ultimo_frame_quando_acaba():
    tela = TelaFalsa([LISTA, JANELA])
    tela.capturar()
    ultima = tela.capturar()
    assert np.array_equal(tela.capturar(), ultima)

def test_tela_falsa_conta_as_capturas():
    tela = TelaFalsa([LISTA])
    tela.capturar()
    tela.capturar()
    assert tela.capturas_feitas == 2

def test_tela_falsa_exige_pelo_menos_um_frame():
    with pytest.raises(ValueError, match="pelo menos um"):
        TelaFalsa([])

def test_mao_falsa_grava_na_ordem():
    mao = MaoFalsa()
    mao.clicar(10, 20)
    mao.apertar_espaco()
    mao.apertar_esc()
    assert mao.acoes == [("clicar", 10, 20), ("apertar_espaco",), ("apertar_esc",)]

def test_mao_falsa_comeca_vazia():
    assert MaoFalsa().acoes == []


def test_mao_falsa_registra_selecao_e_numero():
    mao = MaoFalsa()
    mao.selecionar_tudo()
    mao.digitar_numero(338)
    assert mao.acoes == [("selecionar_tudo",), ("digitar_numero", 338)]


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
