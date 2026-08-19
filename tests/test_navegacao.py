import cv2
import numpy as np

from mistfall.navegacao import (
    CENTRO_ABA_COMPRAR,
    CENTRO_ABA_VENDER,
    ResultadoNavegacao,
    garantir_filtro_roxo,
    ir_para_compra,
    ir_para_venda,
)
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.tipos import Bau, EstadoTela
from mistfall.venda import RitmoVenda
from mistfall.venda_visao import CENTRO_ABA_ARMAZEM, PainelItens, centro_bau


RITMO = RitmoVenda.instantaneo()


def _tela(tmp_path, *codigos):
    caminhos = []
    for indice, codigo in enumerate(codigos):
        caminho = tmp_path / f"frame-{indice}.png"
        imagem = np.full((1440, 2560, 3), codigo, dtype=np.uint8)
        assert cv2.imwrite(str(caminho), imagem)
        caminhos.append(str(caminho))
    return TelaFalsa(caminhos)


def test_ir_para_venda_confirma_inventario_armazem_e_bau_dois_sem_clicar_no_primeiro(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        navegacao,
        "ler_painel_itens",
        lambda frame: {
            10: PainelItens.INVENTARIO,
            20: PainelItens.ARMAZEM,
            30: PainelItens.ARMAZEM,
        }[int(frame[0, 0, 0])],
    )
    monkeypatch.setattr(
        navegacao,
        "ler_bau_selecionado",
        lambda frame: Bau.SEGUNDO if int(frame[0, 0, 0]) == 30 else Bau.PRIMEIRO,
    )
    mao = MaoFalsa()

    resultado = ir_para_venda(_tela(tmp_path, 10, 20, 30), mao, RITMO)

    assert resultado.sucesso is True
    assert resultado.motivo == ""
    assert [acao[1:] for acao in mao.acoes] == [
        CENTRO_ABA_VENDER,
        CENTRO_ABA_ARMAZEM,
        centro_bau(Bau.SEGUNDO),
    ]
    assert centro_bau(Bau.PRIMEIRO) not in [acao[1:] for acao in mao.acoes]


def test_ir_para_compra_restaura_material_e_filtro_roxo(monkeypatch, tmp_path):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(
        navegacao,
        "identificar_estado",
        lambda frame: EstadoTela.LISTA if int(frame[0, 0, 0]) >= 20 else EstadoTela.DESCONHECIDO,
    )
    monkeypatch.setattr(
        navegacao,
        "filtro_roxo_ativo",
        lambda frame: int(frame[0, 0, 0]) == 40,
    )
    mao = MaoFalsa()

    resultado = ir_para_compra(_tela(tmp_path, 10, 20, 25, 30, 40), mao, RITMO)

    assert resultado.sucesso is True
    assert resultado.motivo == ""
    assert [acao[1:] for acao in mao.acoes] == [
        CENTRO_ABA_COMPRAR,
        navegacao.CENTRO_CATEGORIA_MATERIAL_CONSTRUCAO,
        navegacao.CENTRO_FILTRO_ROXO,
    ]


def test_garantir_filtro_roxo_rejeita_tela_de_compra_nao_confirmada(monkeypatch, tmp_path):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "identificar_estado", lambda _: EstadoTela.DESCONHECIDO)
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: False)

    resultado = garantir_filtro_roxo(_tela(tmp_path, 10), MaoFalsa(), RITMO)

    assert resultado.sucesso is False
    assert resultado.frame is not None
    assert isinstance(resultado.motivo, str)
    assert "Compra" in resultado.motivo
