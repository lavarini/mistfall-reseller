import threading
import time

import numpy as np

from mistfall import analise


IMG = np.zeros((2, 2, 3), dtype=np.uint8)


def test_padrao_e_sequencial_e_reune_resultado_e_metricas(monkeypatch):
    monkeypatch.setattr(analise, "ler_ouro", lambda _: 1234)

    def varrer(_, tempos):
        tempos.update(itens=1.0, preparo_folha=2.0, tesseract_precos=3.0)
        return ["listagem"]

    monkeypatch.setattr(analise, "varrer_bruto", varrer)

    resultado = analise.analisar_inicial(IMG)

    assert resultado.ouro_observado == 1234
    assert resultado.brutas == ["listagem"]
    assert set(resultado.tempos) == {
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
