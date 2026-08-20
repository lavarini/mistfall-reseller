import cv2
import numpy as np

from mistfall.navegacao import (
    CENTRO_ABA_COMPRAR,
    CENTRO_ABA_VENDER,
    CENTRO_FILTRO_ROXO,
    TENTATIVAS_DE_CLIQUE,
    garantir_filtro_roxo,
    ir_para_compra,
    ir_para_venda,
)
from mistfall.ciclo_venda import DesfechoSessaoVenda, executar_ciclo_venda
from mistfall.config import Config
from mistfall.perifericos.falso import InterruptorFalso, MaoFalsa, TelaFalsa
from mistfall.tipos import Bau, CapacidadeVenda, EstadoTela, ItemAlvo, SlotArmazem
from mistfall.venda import DesfechoVenda, ResultadoVenda, RitmoVenda
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


def test_ir_para_venda_para_no_primeiro_estado_que_nao_estabiliza(monkeypatch, tmp_path):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "eh_tela_venda", lambda _: False)
    mao = MaoFalsa()

    resultado = ir_para_venda(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is False
    assert resultado.motivo == "Venda nao confirmou Inventario"
    assert [acao[1:] for acao in mao.acoes] == [CENTRO_ABA_VENDER] * TENTATIVAS_DE_CLIQUE


def test_ir_para_compra_para_no_primeiro_estado_que_nao_estabiliza(monkeypatch, tmp_path):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "identificar_estado", lambda _: EstadoTela.DESCONHECIDO)
    mao = MaoFalsa()

    resultado = ir_para_compra(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is False
    assert resultado.motivo == "Compra nao confirmou aba Comprar"
    assert [acao[1:] for acao in mao.acoes] == [CENTRO_ABA_COMPRAR] * TENTATIVAS_DE_CLIQUE


def test_ir_para_venda_repetem_frames_intermediarios_antes_do_proximo_clique(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        navegacao,
        "ler_painel_itens",
        lambda frame: {
            5: None,
            10: PainelItens.INVENTARIO,
            15: None,
            20: PainelItens.ARMAZEM,
            25: PainelItens.ARMAZEM,
            30: PainelItens.ARMAZEM,
        }[int(frame[0, 0, 0])],
    )
    monkeypatch.setattr(
        navegacao,
        "ler_bau_selecionado",
        lambda frame: Bau.SEGUNDO if int(frame[0, 0, 0]) == 30 else Bau.PRIMEIRO,
    )
    tela = _tela(tmp_path, 5, 10, 15, 20, 25, 30)

    class MaoQueObservaCapturas(MaoFalsa):
        def __init__(self):
            super().__init__()
            self.capturas_ao_clicar = []

        def clicar(self, x, y):
            self.capturas_ao_clicar.append(tela.capturas_feitas)
            super().clicar(x, y)

    mao = MaoQueObservaCapturas()

    resultado = ir_para_venda(tela, mao, RITMO)

    assert resultado.sucesso is True
    assert tela.capturas_feitas == 6
    assert mao.capturas_ao_clicar == [0, 2, 4]
    assert [acao[1:] for acao in mao.acoes] == [
        CENTRO_ABA_VENDER,
        CENTRO_ABA_ARMAZEM,
        centro_bau(Bau.SEGUNDO),
    ]


def test_navegacao_bem_sucedida_nao_altera_a_sessao_isolada_de_venda(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        navegacao,
        "ler_painel_itens",
        lambda frame: PainelItens.INVENTARIO
        if int(frame[0, 0, 0]) == 10
        else PainelItens.ARMAZEM,
    )
    monkeypatch.setattr(
        navegacao,
        "ler_bau_selecionado",
        lambda frame: Bau.SEGUNDO if int(frame[0, 0, 0]) == 30 else Bau.PRIMEIRO,
    )
    mao = MaoFalsa()
    resultado = ir_para_venda(_tela(tmp_path, 10, 20, 30), mao, RITMO)

    slot = SlotArmazem(0, 0, ItemAlvo.BROCHE, 3)
    monkeypatch.setattr(
        "mistfall.ciclo_venda.ler_capacidade", lambda _: CapacidadeVenda(0, 12),
    )
    monkeypatch.setattr("mistfall.ciclo_venda.ler_bau_selecionado", lambda _: Bau.QUARTO)
    monkeypatch.setattr("mistfall.ciclo_venda.varrer_armazem", lambda _: [slot])
    monkeypatch.setattr(
        "mistfall.ciclo_venda.executar_venda",
        lambda *args: ResultadoVenda(desfecho=DesfechoVenda.VENDEU, motivo=""),
    )

    sessao = executar_ciclo_venda(
        TelaFalsa(["images/venda-stash-2.png"]),
        mao,
        Config(
            precos_alvo={},
            precos_venda={item: 200 for item in ItemAlvo},
        ),
        tmp_path / "sessao-venda",
        InterruptorFalso(),
        RITMO,
    )

    assert resultado.sucesso is True
    assert sessao.desfecho is DesfechoSessaoVenda.ARMAZEM_ESGOTADO
    assert sessao.vendas == 1


def test_navegacao_tenta_o_clique_mais_de_uma_vez():
    # A spec manda "falhas transitorias geram nova tentativa"; um clique
    # perdido nao pode ser tratado como falha persistente.
    assert TENTATIVAS_DE_CLIQUE >= 2


def test_ir_para_venda_reclica_a_aba_quando_o_primeiro_clique_se_perde(
    monkeypatch, tmp_path,
):
    # Um clique perdido na aba Vender esgotava o teto de espera, devolvia
    # sucesso=False e encerrava a sessao inteira com ABORTOU.
    import mistfall.navegacao as navegacao

    mao = MaoFalsa()
    monkeypatch.setattr(navegacao, "eh_tela_venda", lambda _: True)
    monkeypatch.setattr(
        navegacao,
        "ler_painel_itens",
        lambda _: (
            PainelItens.ARMAZEM
            if len(mao.acoes) >= 3
            else PainelItens.INVENTARIO if len(mao.acoes) >= 2 else None
        ),
    )
    monkeypatch.setattr(
        navegacao,
        "ler_bau_selecionado",
        lambda _: Bau.SEGUNDO if len(mao.acoes) >= 4 else Bau.PRIMEIRO,
    )

    resultado = ir_para_venda(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is True
    assert resultado.motivo == ""
    assert [acao[1:] for acao in mao.acoes] == [
        CENTRO_ABA_VENDER,
        CENTRO_ABA_VENDER,
        CENTRO_ABA_ARMAZEM,
        centro_bau(Bau.SEGUNDO),
    ]


def test_ir_para_compra_reclica_a_aba_comprar_quando_o_primeiro_clique_se_perde(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    mao = MaoFalsa()
    monkeypatch.setattr(
        navegacao,
        "identificar_estado",
        lambda _: EstadoTela.LISTA if len(mao.acoes) >= 2 else EstadoTela.DESCONHECIDO,
    )
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: True)

    resultado = ir_para_compra(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is True
    assert [acao[1:] for acao in mao.acoes] == [
        CENTRO_ABA_COMPRAR,
        CENTRO_ABA_COMPRAR,
        navegacao.CENTRO_CATEGORIA_MATERIAL_CONSTRUCAO,
    ]


def test_garantir_filtro_roxo_reclica_o_filtro_quando_o_primeiro_clique_se_perde(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    mao = MaoFalsa()
    monkeypatch.setattr(navegacao, "identificar_estado", lambda _: EstadoTela.LISTA)
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: len(mao.acoes) >= 2)

    resultado = garantir_filtro_roxo(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is True
    assert [acao[1:] for acao in mao.acoes] == [CENTRO_FILTRO_ROXO] * 2


def test_filtro_roxo_esgotado_continua_devolvendo_falha_com_motivo(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    mao = MaoFalsa()
    monkeypatch.setattr(navegacao, "identificar_estado", lambda _: EstadoTela.LISTA)
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: False)

    resultado = garantir_filtro_roxo(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is False
    assert resultado.motivo == "Compra nao confirmou filtro roxo"
    assert [acao[1:] for acao in mao.acoes] == [CENTRO_FILTRO_ROXO] * TENTATIVAS_DE_CLIQUE


def test_motivo_da_tela_de_compra_nao_promete_categoria_verificada(
    monkeypatch, tmp_path,
):
    # `garantir_filtro_roxo` so confere que a tela e LISTA. Nao existe
    # detector de Categoria: dizer "nao confirmou Material de Construcao" era
    # diagnostico mentiroso.
    import mistfall.navegacao as navegacao

    monkeypatch.setattr(navegacao, "identificar_estado", lambda _: EstadoTela.DESCONHECIDO)
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: False)

    resultado = garantir_filtro_roxo(_tela(tmp_path, 10), MaoFalsa(), RITMO)

    assert resultado.sucesso is False
    assert resultado.motivo == "tela de Compra nao confirmou LISTA"


def test_motivo_do_passo_da_categoria_diz_o_que_foi_de_fato_verificado(
    monkeypatch, tmp_path,
):
    import mistfall.navegacao as navegacao

    mao = MaoFalsa()
    monkeypatch.setattr(
        navegacao,
        "identificar_estado",
        lambda _: EstadoTela.LISTA if len(mao.acoes) < 2 else EstadoTela.DESCONHECIDO,
    )
    monkeypatch.setattr(navegacao, "filtro_roxo_ativo", lambda _: True)

    resultado = ir_para_compra(_tela(tmp_path, 10), mao, RITMO)

    assert resultado.sucesso is False
    assert resultado.motivo == "tela de Compra nao confirmou LISTA depois da Categoria"
