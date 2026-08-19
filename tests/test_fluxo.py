from mistfall.fluxo import (
    AcaoFluxo,
    EventoFluxo,
    ModoFluxo,
    aplicar_evento,
    estado_inicial,
)


def _rodar(nomes: list[str]) -> ModoFluxo:
    estado = estado_inicial()
    for nome in nomes:
        evento = getattr(EventoFluxo, nome.upper())
        estado, _ = aplicar_evento(estado, evento)
    return estado.modo


def test_tres_resets_entre_intencoes_isolados_mantem_ritmo_rapido():
    assert _rodar(["intencao", "reset", "intencao"]) is ModoFluxo.RAPIDO


def test_tres_intervalos_lentos_consecutivos_entram_em_ritmo_lento():
    sequencia = ["intencao", "reset", "reset", "reset", "intencao"] * 3
    assert _rodar(sequencia) is ModoFluxo.LENTO


def test_cinco_resets_consecutivos_entram_imediatamente_em_ritmo_lento():
    assert _rodar(["reset"] * 5) is ModoFluxo.LENTO


def test_compra_confirmada_soma_uma_unidade_ao_estoque():
    estado = estado_inicial()
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, acao = aplicar_evento(estado, EventoFluxo.COMPRA_CONFIRMADA)
    assert estado.estoque_estimado == 1
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_compra_inconclusiva_soma_unidade_provisoria():
    estado = estado_inicial()
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_INCONCLUSIVA)
    assert estado.estoque_estimado == 1
    assert estado.compra_pendente is False


def test_inventario_cheio_nao_soma_unidade_e_decide_venda_distinta():
    estado = estado_inicial()
    estado, acao = aplicar_evento(
        estado, EventoFluxo.MENSAGEM_INVENTARIO_CHEIO
    )
    assert estado.estoque_estimado == 0
    assert acao is AcaoFluxo.VENDER_POR_INVENTARIO_CHEIO


def test_saldo_de_venda_e_parcial():
    estado = estado_inicial(estoque_estimado=100)
    estado, _ = aplicar_evento(estado, EventoFluxo.unidades_listadas(45))
    assert estado.estoque_estimado == 55


def test_estoque_lento_atingindo_45_decide_venda_por_fluxo_lento():
    estado = estado_inicial(modo=ModoFluxo.LENTO, estoque_estimado=44)
    estado, acao = aplicar_evento(
        estado, EventoFluxo.compra_confirmada()
    )
    assert estado.estoque_estimado == 45
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO

