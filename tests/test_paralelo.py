import threading
import time

import pytest

from mistfall.paralelo import TRABALHADORES_PADRAO, mapear

def test_preserva_a_ordem_da_entrada():
    # Itens lentos primeiro: se a ordem viesse de quem termina antes, esta
    # lista sairia invertida.
    def devagar(n):
        time.sleep(0.02 if n < 3 else 0)
        return n * 10
    assert mapear(devagar, [0, 1, 2, 3, 4, 5], trabalhadores=4) == [0, 10, 20, 30, 40, 50]

def test_resultado_identico_ao_sequencial():
    itens = list(range(20))
    assert mapear(str, itens, trabalhadores=8) == mapear(str, itens, trabalhadores=1)

def test_um_trabalhador_roda_na_propria_thread():
    principal = threading.current_thread()
    threads = mapear(lambda _: threading.current_thread(), range(4), trabalhadores=1)
    assert all(t is principal for t in threads)

def test_varios_trabalhadores_usam_outras_threads():
    principal = threading.current_thread()
    threads = mapear(lambda _: threading.current_thread(), range(8), trabalhadores=4)
    assert any(t is not principal for t in threads)

def test_lista_vazia():
    assert mapear(str, [], trabalhadores=4) == []

def test_o_padrao_e_conservador():
    # Quatro ja da ganho de 3x e sobra CPU para o jogo, que roda na mesma
    # maquina e precisa desenhar a tela que o bot vai capturar.
    assert TRABALHADORES_PADRAO == 4

def test_zero_ou_negativo_e_erro():
    with pytest.raises(ValueError, match="trabalhadores"):
        mapear(str, [1, 2], trabalhadores=0)
