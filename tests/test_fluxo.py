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


def test_ouro_abaixo_do_piso_manda_vender():
    # Terceiro motivo de Venda, separado dos outros dois para a telemetria
    # distinguir. Vale mesmo no regime rapido e com o Inventario vazio: sao
    # justamente esses os estados em que os outros dois gatilhos nao alcancam.
    estado, acao = aplicar_evento(estado_inicial(), EventoFluxo.ouro_abaixo_do_piso())
    assert acao is AcaoFluxo.VENDER_POR_OURO_BAIXO
    assert estado == estado_inicial()


def test_ouro_abaixo_do_piso_nao_mexe_no_regime_nem_no_estoque():
    # E um sinal, nao uma Compra nem um Reset: nao pode contaminar a cadencia
    # que decide rapido/lento.
    partida = replace(estado_inicial(), estoque_estimado=7, resets_consecutivos=2)
    depois, _ = aplicar_evento(partida, EventoFluxo.ouro_abaixo_do_piso())
    assert depois == partida


def _em_regime_lento():
    """Leva o estado ao regime lento pelo caminho real dos cinco Resets."""
    estado = estado_inicial()
    for _ in range(5):
        estado, _ = aplicar_evento(estado, EventoFluxo.RESET)
    assert estado.modo is ModoFluxo.LENTO
    return estado


def test_duas_intencoes_coladas_devolvem_o_regime_ao_rapido():
    estado = _em_regime_lento()
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    assert estado.modo is ModoFluxo.RAPIDO


def test_dois_intervalos_de_um_reset_devolvem_o_regime_ao_rapido():
    estado = _em_regime_lento()
    for evento in (
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
    ):
        estado, _ = aplicar_evento(estado, evento)
    assert estado.modo is ModoFluxo.RAPIDO


def test_um_unico_intervalo_de_um_reset_nao_tira_do_regime_lento():
    estado = _em_regime_lento()
    for evento in (
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
    ):
        estado, _ = aplicar_evento(estado, evento)
    assert estado.pontos_de_pressa == 1
    assert estado.modo is ModoFluxo.LENTO


def test_intervalo_de_dois_resets_nao_soma_nem_zera_os_pontos_de_pressa():
    estado = _em_regime_lento()
    for evento in (
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
    ):
        estado, _ = aplicar_evento(estado, evento)
    assert estado.pontos_de_pressa == 1
    assert estado.modo is ModoFluxo.LENTO


def test_intervalo_de_tres_resets_zera_os_pontos_de_pressa():
    estado = _em_regime_lento()
    for evento in (
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
        EventoFluxo.RESET,
        EventoFluxo.RESET,
        EventoFluxo.RESET,
        EventoFluxo.INTENCAO,
    ):
        estado, _ = aplicar_evento(estado, evento)
    assert estado.pontos_de_pressa == 0
    assert estado.modo is ModoFluxo.LENTO


def test_pontos_de_pressa_anteriores_nao_sobrevivem_a_entrada_no_lento():
    """Os cinco Resets que trazem o lento tambem apagam a pressa acumulada.

    Sem isso, um ponto ganho no regime rapido deixaria a primeira Intencao
    depois da entrada devolver o regime ao rapido de imediato.
    """
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
    assert estado.pontos_de_pressa == 1
    for _ in range(5):
        estado, _ = aplicar_evento(estado, EventoFluxo.RESET)
    assert estado.modo is ModoFluxo.LENTO
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    assert estado.pontos_de_pressa == 0
    assert estado.modo is ModoFluxo.LENTO


def test_saida_do_lento_manda_comprar_e_nao_vender():
    estado = _em_regime_lento()
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    estado, acao = aplicar_evento(estado, EventoFluxo.INTENCAO)
    assert estado.modo is ModoFluxo.RAPIDO
    assert acao is AcaoFluxo.EXECUTAR_COMPRA


def test_estoque_acima_do_limiar_nao_vende_depois_de_sair_do_lento():
    estado = replace(_em_regime_lento(), estoque_estimado=46)
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    assert estado.modo is ModoFluxo.RAPIDO
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, acao = aplicar_evento(estado, EventoFluxo.COMPRA_CONFIRMADA)
    assert estado.estoque_estimado == 47
    assert acao is AcaoFluxo.CONTINUAR_COMPRA


def test_ouro_abaixo_do_piso_nao_mexe_nos_pontos_de_pressa():
    estado = _em_regime_lento()
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    estado, _ = aplicar_evento(estado, EventoFluxo.RESET)
    estado, _ = aplicar_evento(estado, EventoFluxo.INTENCAO)
    antes = estado.pontos_de_pressa
    estado, acao = aplicar_evento(estado, EventoFluxo.OURO_ABAIXO_DO_PISO)
    assert estado.pontos_de_pressa == antes
    assert acao is AcaoFluxo.VENDER_POR_OURO_BAIXO


def test_primeira_intencao_da_sessao_ja_nasce_com_a_pressa_cheia():
    """Sem Intencao anterior nao existe intervalo, e o intervalo lido e zero.

    Isso deixa a pressa cheia desde a primeira Volta, o que e coerente com a
    sessao comecar no regime rapido e nao adianta saida nenhuma: o lento so e
    alcancado depois de um intervalo de tres Resets ou mais, que zera a pressa
    no mesmo evento em que e lido, antes da conferencia de saida.
    """
    estado, _ = aplicar_evento(estado_inicial(), EventoFluxo.INTENCAO)
    assert estado.pontos_de_pressa == 2
    assert estado.modo is ModoFluxo.RAPIDO


def test_limiar_de_venda_por_saldo_sai_da_constante_do_lote():
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    estado = estado_inicial(
        modo=ModoFluxo.LENTO,
        estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES - 1,
    )
    estado, _ = aplicar_evento(estado, EventoFluxo.COMPRA_ENVIADA)
    estado, acao = aplicar_evento(estado, EventoFluxo.COMPRA_CONFIRMADA)
    assert estado.estoque_estimado == LOTE_DE_VENDA_EM_UNIDADES
    assert acao is AcaoFluxo.VENDER_POR_FLUXO_LENTO
