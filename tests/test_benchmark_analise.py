from types import SimpleNamespace

import pytest

from ferramentas import benchmark_analise


def test_medir_separa_aquecimento_compara_modos_e_exige_igualdade(monkeypatch, tmp_path):
    imagens = [tmp_path / "a.png", tmp_path / "b.png"]
    for imagem in imagens:
        imagem.write_bytes(b"imagem")
    monkeypatch.setattr(benchmark_analise.cv2, "imread", lambda _: object())

    chamadas = []

    def analisar(_, *, concorrente):
        chamadas.append(concorrente)
        return SimpleNamespace(
            ouro_observado=100,
            brutas=[1, 2],
            tempos={"analise_inicial_parede": 10.0 if concorrente else 20.0},
        )

    monkeypatch.setattr(benchmark_analise, "analisar_inicial", analisar)

    resumo = benchmark_analise.medir(imagens, repeticoes=2)

    assert resumo["resultados_iguais"] is True
    assert resumo["sequencial"]["n"] == 4
    assert resumo["concorrente"]["n"] == 4
    assert resumo["sequencial"]["mediana_ms"] == 20.0
    assert resumo["concorrente"]["mediana_ms"] == 10.0
    assert chamadas[0] is False


def test_medir_rejeita_imagem_ilegivel_com_caminho(monkeypatch, tmp_path):
    imagem = tmp_path / "corrompida.png"
    imagem.write_bytes(b"nao e png")
    monkeypatch.setattr(benchmark_analise.cv2, "imread", lambda _: None)

    with pytest.raises(ValueError, match="corrompida\\.png"):
        benchmark_analise.medir([imagem])


def test_medir_falha_quando_concorrencia_muda_o_resultado(monkeypatch, tmp_path):
    imagem = tmp_path / "a.png"
    imagem.write_bytes(b"imagem")
    monkeypatch.setattr(benchmark_analise.cv2, "imread", lambda _: object())

    def analisar(_, *, concorrente):
        return SimpleNamespace(
            ouro_observado=101 if concorrente else 100,
            brutas=[1, 2],
            tempos={"analise_inicial_parede": 10.0},
        )

    monkeypatch.setattr(benchmark_analise, "analisar_inicial", analisar)

    with pytest.raises(RuntimeError, match="pipeline concorrente mudou"):
        benchmark_analise.medir([imagem])
