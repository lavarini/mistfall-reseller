from dataclasses import replace

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
    sequencia = (
        ["intencao"]
        + ["reset"] * 3
        + ["intencao"]
        + ["reset"] * 3
        + ["intencao"]
        + ["reset"] * 3
        + ["intencao"]
    )
    assert _rodar(sequencia) is ModoFluxo.LENTO


def test_terceiro_intervalo_lento_dispara_venda_imediata():
    estado = estado_inicial()
    eventos = (
        [EventoFluxo.INTENCAO]
        + [EventoFluxo.RESET] * 3
        + [EventoFluxo.INTENCAO]
        + [EventoFluxo.RESET] * 3
        + [EventoFluxo.INTENCAO]
        + [EventoFluxo.RESET] * 3
    )
    for evento in eventos:
        estado, _ = aplicar_evento(estado, evento)
    estado, acao = aplicar_evento(estado, EventoFluxo.INTENCAO)
    assert estado.modo is ModoFluxo.LENTO
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO


def test_intervalos_lentos_sao_reiniciados_por_intervalo_rapido():
    estado = estado_inicial()
    for evento in (
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.RESET,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
    ):
        estado, _ = aplicar_evento(estado, evento)
    assert estado.intervalos_lentos_consecutivos == 0


def test_cinco_resets_consecutivos_entram_imediatamente_em_ritmo_lento():
    assert _rodar(["reset"] * 5) is ModoFluxo.LENTO


def test_quinto_reset_dispara_venda_imediata():
    estado = estado_inicial()
    for _ in range(4):
        estado, acao = aplicar_evento(estado, EventoFluxo.RESET)
        assert acao is AcaoFluxo.CONTINUAR_COMPRA
    estado, acao = aplicar_evento(estado, EventoFluxo.RESET)
    assert estado.modo is ModoFluxo.LENTO
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO


def test_sinal_nao_transicional_e_modo_ja_lento_continuam_compra():
    estado, acao = aplicar_evento(estado_inicial(), EventoFluxo.RESET)
    assert acao is AcaoFluxo.CONTINUAR_COMPRA
    estado = estado_inicial(modo=ModoFluxo.LENTO)
    estado, acao = aplicar_evento(estado, EventoFluxo.RESET)
    assert estado.modo is ModoFluxo.LENTO
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_reset_zera_intencoes_desde_reset_e_intencao_incrementa():
    estado, _ = aplicar_evento(estado_inicial(), EventoFluxo.INTENCAO)
    assert estado.intencoes_desde_reset == 1
    estado, _ = aplicar_evento(estado, EventoFluxo.RESET)
    assert estado.intencoes_desde_reset == 0


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


def test_confirmacao_sem_compra_pendente_e_ignorada():
    estado = estado_inicial()
    confirmado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_CONFIRMADA)
    inconclusivo, _ = aplicar_evento(estado, EventoFluxo.COMPRA_INCONCLUSIVA)
    assert confirmado == estado
    assert inconclusivo == estado


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


def test_reconciliacao_define_saldo_real_do_armazem():
    estado, _ = aplicar_evento(
        estado_inicial(estoque_estimado=100),
        EventoFluxo.estoque_reconciliado(12),
    )
    assert estado.estoque_estimado == 12


def test_retorno_a_compra_e_evento_explicito():
    estado, acao = aplicar_evento(
        estado_inicial(), EventoFluxo.retorno_compra()
    )
    assert estado == estado_inicial()
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_evento_desconhecido_nao_e_silenciosamente_aceito():
    evento = EventoFluxo(object())
    try:
        aplicar_evento(estado_inicial(), evento)
    except ValueError as exc:
        assert "desconhecido" in str(exc)
    else:
        raise AssertionError("evento desconhecido deveria ser rejeitado")


def test_reset_nao_e_acao_publica_da_politica():
    assert not hasattr(AcaoFluxo, "EXECUTAR_RESET")


def test_listagem_acima_do_saldo_satura_o_estoque_em_zero():
    # O Estoque estimado é contagem interna otimista, não invariante: quando a
    # Venda lista mais unidades do que ele contava, a divergência é informação,
    # não erro de programação. Levantar aqui derrubava a sessão inteira no
    # caminho canônico do regime rápido, onde o Estoque começa em 0 e a única
    # Venda é a disparada pelo toast de inventário cheio.
    estado = estado_inicial(estoque_estimado=2)

    estado, acao = aplicar_evento(estado, EventoFluxo.unidades_listadas(3))

    assert estado.estoque_estimado == 0
    assert acao is AcaoFluxo.CONTINUAR_VENDA


def test_listagem_de_unidades_negativas_continua_sendo_erro():
    # Saturar não vale para o negativo: nenhuma Venda lista -1 unidade, então
    # isso só chega aqui por erro de programação.
    try:
        aplicar_evento(estado_inicial(estoque_estimado=2), EventoFluxo.unidades_listadas(-1))
    except ValueError as exc:
        assert "negativas" in str(exc)
    else:
        raise AssertionError("unidades negativas deveriam ser rejeitadas")


def test_estoque_lento_atingindo_45_decide_venda_por_fluxo_lento():
    estado = estado_inicial(modo=ModoFluxo.LENTO, estoque_estimado=44)
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, acao = aplicar_evento(
        estado, EventoFluxo.compra_confirmada()
    )
    assert estado.estoque_estimado == 45
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO


def test_compra_inconclusiva_com_zero_unidades_nao_soma_estoque():
    # `unidades=0` e o sinal "o Ouro estava legivel e nao caiu", ou seja, a
    # Compra provavelmente nao aconteceu. Somar uma unidade otimista aqui
    # inflaria o Estoque estimado a cada Volta com o Ouro zerado.
    estado = replace(estado_inicial(), compra_pendente=True)
    depois, _ = aplicar_evento(estado, EventoFluxo.compra_inconclusiva(unidades=0))
    assert depois.estoque_estimado == 0
    assert depois.compra_pendente is False


def test_compra_inconclusiva_sem_argumento_soma_a_unidade_provisoria():
    # O default continua sendo a unidade otimista: sem evidencia contra, a
    # Compra pode ter acontecido.
    estado = replace(estado_inicial(), compra_pendente=True)
    depois, _ = aplicar_evento(estado, EventoFluxo.compra_inconclusiva())
    assert depois.estoque_estimado == 1
