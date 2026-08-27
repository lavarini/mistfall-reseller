"""Coordena Compra e Venda num unico laco adaptativo.

Compoe o que as Tasks 1-6 ja entregaram: `fluxo.py` decide o que fazer a
partir de eventos observados, `piloto.executar` roda uma Compra, `reset.py`
troca a Categoria quando nao ha o que comprar, `navegacao.py` confirma as
transicoes de aba/filtro, e `ciclo_venda.executar_venda_parcial` esvazia o
Bau 2 sem fechar a sessao de Venda. Este modulo nao inventa politica nova:
so decide QUANDO chamar cada um deles e junta os resultados num relatorio.

O toast da Compra anterior e o Ouro que confirma (ou nao) o seu envio sao
lidos do MESMO frame: `piloto.executar` chama `observador_frame_inicial`
com a captura de pre-voo antes de qualquer clique, e essa mesma captura
alimenta tanto `Resultado.ouro_observado` quanto `detectar_mensagem_compra`
aqui. Nao ha captura extra so para classificar o toast.

Confirmar uma Compra enviada depende de dois sinais, nesta ordem de
prioridade:

1. O toast "cheios" (`MensagemCompra.INVENTARIO_CHEIO`) sempre vale, mesmo
   sem Compra pendente: ele por si so manda vender.
2. Com Compra pendente, o toast "realizada"/"guardado" confirma; senao,
   compara-se o Ouro observado nesta Volta com o Ouro no momento do envio.
   Ouro legivel e sem queda vira `compra_inconclusiva(unidades=0)` — o
   contrato aceita a unidade provisoria, mas aqui o sinal diz "nao houve
   queda", entao nada e somado ao Estoque. Ouro ilegivel ou fora dessas
   duas leituras vira `compra_inconclusiva()` (a unidade default), porque
   nao ha evidencia contra a Compra ter acontecido.

Nenhum desses sinais isolados encerra o laco. So a falha persistente de
navegacao (depois das `TENTATIVAS_DE_CLIQUE` que `navegacao.py` faz
sozinho em cada passo), a
falha persistente de visao (`Desfecho.ABORTOU` do proprio `piloto.executar`
por `LIMITE_ABORTOS_CONSECUTIVOS` Voltas seguidas) e o F4 do operador — em
Compra ou em Venda — terminam a sessao.

Uma Volta `ABORTOU` conta para esse limite; qualquer Volta que nao seja
`ABORTOU` zera o contador, incluindo `Desfecho.SIMULOU` — SIMULOU e uma
simulacao bem-sucedida, nao falha, e contá-la junto derrubaria uma sessao
inteira rodada com `simular=True` na quinta Volta.
"""

import itertools
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np

from mistfall.ciclo_venda import DesfechoSessaoVenda, executar_venda_parcial
from mistfall.compra_visao import MensagemCompra, detectar_mensagem_compra
from mistfall.config import Config
from mistfall.fluxo import (
    AcaoFluxo,
    EstadoFluxo,
    EventoFluxo,
    aplicar_evento,
    estado_inicial,
)
from mistfall.navegacao import garantir_filtro_roxo, ir_para_compra, ir_para_venda
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.piloto import (
    RITMO_PADRAO, Desfecho, Ritmo, espera_para_proxima_volta,
    executar,
)
from mistfall.reset import CategoriaAlternativa, resetar_categoria
from mistfall.telemetria import TelemetriaSessao
from mistfall.venda import RITMO_VENDA_PADRAO, RitmoVenda


# Um Reset usa uma Categoria alternativa, e o proximo usa a outra — mesma
# alternancia de `ciclo.py`, para nao gastar sempre a mesma Categoria de
# apoio.
_ALTERNANCIA_RESET = (CategoriaAlternativa.FORJA, CategoriaAlternativa.CHAVE)

_ACOES_DE_VENDA = (
    AcaoFluxo.VENDER_POR_INVENTARIO_CHEIO,
    AcaoFluxo.VENDER_POR_FLUXO_LENTO,
    AcaoFluxo.VENDER_POR_OURO_BAIXO,
    # A Janela tambem pode mandar retomar uma Venda que saiu com lote cheio
    # no Armazem (`fluxo.py` devolve VENDER_POR_RETOMADA nesse caso). Sem
    # entrar aqui, o portao de saida do laco ("acao not in _ACOES_DE_VENDA")
    # descartaria a decisao e a retomada nunca chegaria a ir_para_venda.
    AcaoFluxo.VENDER_POR_RETOMADA,
)

# A Janela vale para as duas Vendas do regime lento. Se valesse so para a
# pressa, o livelock voltaria pela porta dos fundos: a Venda lista zero, uma
# Compra confirma, o saldo segue acima do lote, e a viagem se repete.
_ACOES_DO_REGIME_LENTO = (
    AcaoFluxo.VENDER_POR_FLUXO_LENTO,
    AcaoFluxo.VENDER_POR_RETOMADA,
)

# Mesma ideia de `resets_consecutivos >= 5` que `fluxo.py` ja usa como
# limiar de persistencia — um so vocabulario de limiar para o modo completo.
# Falha de visao (ABORTOU) e uma queda cega do piloto, entao o limite vive
# aqui, fora do contrato puro de `fluxo.py`, que continua selado.
LIMITE_ABORTOS_CONSECUTIVOS = 5


def _fechar(pasta: Path, sessao: "SessaoCompleta") -> None:
    """Grava o diagnostico da sessao, como `ciclo_venda` faz com o dele.

    Chamado num `finally`: o modo completo roda sem supervisao numa maquina
    onde ninguem pode depurar, entao a sessao que morre e justamente a que
    precisa deixar registro.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    estado = sessao.estado
    (pasta / "sessao.json").write_text(
        json.dumps(
            {
                "desfecho": sessao.desfecho.value,
                "motivo": sessao.motivo,
                "compras_enviadas": sessao.compras_enviadas,
                "unidades_listadas": sessao.unidades_listadas,
                "total_baus": sessao.total_baus,
                "estado": {
                    "estoque_estimado": estado.estoque_estimado,
                    "modo": estado.modo.value,
                    "intencoes_desde_reset": estado.intencoes_desde_reset,
                    "resets_desde_intencao": estado.resets_desde_intencao,
                    "resets_consecutivos": estado.resets_consecutivos,
                    "intervalos_lentos_consecutivos": (
                        estado.intervalos_lentos_consecutivos
                    ),
                    "pontos_de_pressa": estado.pontos_de_pressa,
                    "compra_pendente": estado.compra_pendente,
                    "capacidade_observada": (
                        list(estado.capacidade_observada)
                        if estado.capacidade_observada is not None
                        else None
                    ),
                },
                "eventos": [evento.tipo.value for evento in sessao.eventos],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class DesfechoSessaoCompleta(Enum):
    PAROU = "parou"
    ABORTOU = "abortou"


@dataclass
class SessaoCompleta:
    desfecho: DesfechoSessaoCompleta = DesfechoSessaoCompleta.ABORTOU
    motivo: str = ""
    estado: EstadoFluxo = field(default_factory=EstadoFluxo)
    compras_enviadas: int = 0
    unidades_listadas: int = 0
    # Trilha em memoria de cada EventoFluxo aplicado nesta sessao, para quem
    # inspeciona o proprio processo. A telemetria persistente (JSONL) vive em
    # `eventos-do-fluxo.jsonl`, escrita por `TelemetriaSessao.registrar_evento_fluxo`
    # a cada `aplicar()` — ver `executar_ciclo_completo`.
    eventos: list[EventoFluxo] = field(default_factory=list)
    # Contado pela primeira Venda da sessao e reusado pelas seguintes. Fica no
    # relatorio porque uma contagem errada erra a sessao inteira, em silencio.
    total_baus: int = 0


def executar_ciclo_completo(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo_compra: Ritmo = RITMO_PADRAO,
    ritmo_venda: RitmoVenda = RITMO_VENDA_PADRAO,
    sorteio: random.Random | None = None,
) -> SessaoCompleta:
    if sorteio is None:
        sorteio = random.Random()
    pasta = Path(pasta)

    sessao = SessaoCompleta(estado=estado_inicial())
    if interruptor.esperar_inicio() is False:
        return sessao
    estado = sessao.estado
    telemetria = TelemetriaSessao(pasta, time.monotonic())

    def aplicar(evento: EventoFluxo) -> AcaoFluxo:
        nonlocal estado
        sessao.eventos.append(evento)
        estado, acao = aplicar_evento(estado, evento)
        sessao.estado = estado
        telemetria.registrar_evento_fluxo(
            numero_da_volta, time.monotonic(), datetime.now(),
            estado, sessao.unidades_listadas, acao, evento,
        )
        return acao

    def encerrar(desfecho: DesfechoSessaoCompleta, motivo: str = "") -> SessaoCompleta:
        sessao.desfecho = desfecho
        sessao.motivo = motivo
        sessao.estado = estado
        return sessao

    try:
        # O modo completo comeca em Comprar, Item -> Material de Construcao: a
        # unica coisa que falta confirmar antes do laco e o filtro roxo.
        filtro = garantir_filtro_roxo(tela, mao, ritmo_venda)
        if not filtro.sucesso:
            return encerrar(DesfechoSessaoCompleta.ABORTOU, filtro.motivo)

        categorias = itertools.cycle(_ALTERNANCIA_RESET)
        proxima_categoria = next(categorias)
        ouro_no_envio: int | None = None
        numero_da_volta = 0
        numero_da_venda = 0
        abortos_consecutivos = 0
        # Zero deixa a Janela aberta na largada: nada foi vendido ainda, e nao
        # ha o que esperar.
        proxima_janela = 0.0
        # Falso deixa a primeira Volta anunciar a aresta se ja encontrar a
        # Janela aberta: um regime lento que comeca com o Armazem cheio (ou
        # retomado por F3 depois de crescer sozinho) nao pode esperar um
        # segundo ciclo fechar-e-abrir so para autorizar a primeira Venda.
        janela_estava_aberta = False

        while True:
            if interruptor.pediram_parada():
                return encerrar(DesfechoSessaoCompleta.PAROU)

            numero_da_volta += 1
            pasta_da_volta = pasta / f"volta-{numero_da_volta:04d}"

            frame_inicial: np.ndarray | None = None

            def observar(frame: np.ndarray) -> None:
                nonlocal frame_inicial
                frame_inicial = frame

            resultado = executar(
                tela, mao, config, pasta_da_volta,
                ritmo=ritmo_compra, sorteio=sorteio, interruptor=interruptor,
                observador_frame_inicial=observar,
            )

            # F4 pode ter sido apertado dentro da propria Compra (antes do
            # clique). Nao e falha estrategica: encerra a sessao na hora.
            if resultado.desfecho is Desfecho.PAROU:
                return encerrar(DesfechoSessaoCompleta.PAROU)

            # Falha persistente de visao: SIMULOU nao conta (e sucesso, nao
            # falha), e qualquer Volta que nao seja ABORTOU zera o contador.
            if resultado.desfecho is Desfecho.ABORTOU:
                abortos_consecutivos += 1
                if abortos_consecutivos >= LIMITE_ABORTOS_CONSECUTIVOS:
                    return encerrar(DesfechoSessaoCompleta.ABORTOU, resultado.motivo)
            else:
                abortos_consecutivos = 0

            mensagem = (
                detectar_mensagem_compra(frame_inicial)
                if frame_inicial is not None
                else MensagemCompra.NENHUMA
            )
            ouro_agora = resultado.ouro_observado

            # Confirmacao da Compra da Volta anterior, lida no mesmo frame que
            # abriu esta Volta.
            acao_confirmacao: AcaoFluxo | None = None
            if mensagem is MensagemCompra.INVENTARIO_CHEIO:
                acao_confirmacao = aplicar(EventoFluxo.MENSAGEM_INVENTARIO_CHEIO)
                ouro_no_envio = None
            elif estado.compra_pendente:
                confirmou = mensagem is MensagemCompra.SUCESSO or (
                    ouro_agora is not None
                    and ouro_no_envio is not None
                    and ouro_agora < ouro_no_envio
                )
                sem_queda_legivel = (
                    not confirmou
                    and ouro_agora is not None
                    and ouro_no_envio is not None
                    and ouro_agora >= ouro_no_envio
                )
                if confirmou:
                    acao_confirmacao = aplicar(EventoFluxo.compra_confirmada(unidades=1))
                elif sem_queda_legivel:
                    acao_confirmacao = aplicar(EventoFluxo.compra_inconclusiva(unidades=0))
                else:
                    acao_confirmacao = aplicar(EventoFluxo.compra_inconclusiva())
                ouro_no_envio = None

            # O que esta propria Volta encontrou: uma intencao (Listagem no
            # Preco-alvo, envie-se ou nao a Compra) ou nada compravel.
            if resultado.listagem is not None:
                acao_propria = aplicar(EventoFluxo.intencao_detectada())
                if resultado.desfecho is Desfecho.COMPRA_ENVIADA:
                    sessao.compras_enviadas += 1
                    aplicar(EventoFluxo.compra_enviada())
                    ouro_no_envio = ouro_agora
            elif resultado.desfecho is Desfecho.NADA_COMPRAVEL:
                # Se a confirmacao desta mesma Volta ja decidiu vender, a ida a
                # Venda e a volta por `ir_para_compra` restauram a Categoria e
                # recarregam a Listagem sozinhas: o Reset aqui seria clique
                # jogado fora. O evento continua valendo — nao havia nada
                # compravel, e e isso que o regime conta.
                if acao_confirmacao not in _ACOES_DE_VENDA:
                    resetar_categoria(
                        tela, mao, ritmo_compra,
                        categoria_alternativa=proxima_categoria, sorteio=sorteio,
                    )
                    proxima_categoria = next(categorias)
                acao_propria = aplicar(EventoFluxo.reset_executado())
            else:
                # ABORTOU/SIMULOU isolado: sinal ambiguo, nao e terminal e nao
                # justifica Reset por si so.
                acao_propria = AcaoFluxo.CONTINUAR_COMPRA

            acao = acao_confirmacao if acao_confirmacao in _ACOES_DE_VENDA else acao_propria

            # Aresta da Janela: a unica reavaliacao do regime lento que nao
            # depende de evento de Compra. Sem ela, o Fluxo Completo reseta
            # indefinidamente com o Armazem cheio e o Leilao seco.
            janela_aberta = time.monotonic() >= proxima_janela
            if (
                acao not in _ACOES_DE_VENDA
                and janela_aberta
                and not janela_estava_aberta
            ):
                acao = aplicar(EventoFluxo.JANELA_DE_VENDA_ABERTA)
            janela_estava_aberta = janela_aberta

            # Portao: nenhuma Venda do regime lento passa com a Janela
            # fechada. O toast de Inventario cheio e o Ouro abaixo do piso
            # atravessam — sao emergencia, nao ritmo.
            if acao in _ACOES_DO_REGIME_LENTO and not janela_aberta:
                acao = AcaoFluxo.CONTINUAR_COMPRA

            # Terceiro gatilho de Venda, e o unico alcancavel quando o Ouro
            # acaba: as Listagens no Preco-alvo continuam aparecendo, entao o
            # regime nunca vira lento, e nada e comprado, entao o Inventario
            # nunca enche. Entra como ultimo recurso, sem competir com os
            # outros dois quando eles ja decidiram vender.
            if (
                acao not in _ACOES_DE_VENDA
                and ouro_agora is not None
                and ouro_agora < config.piso_ouro
            ):
                acao = aplicar(EventoFluxo.ouro_abaixo_do_piso())

            if acao not in _ACOES_DE_VENDA:
                time.sleep(espera_para_proxima_volta(
                    resultado.desfecho, ritmo_compra, sorteio,
                ))
                continue

            nav_venda = ir_para_venda(tela, mao, ritmo_venda)
            if not nav_venda.sucesso:
                return encerrar(DesfechoSessaoCompleta.ABORTOU, nav_venda.motivo)

            numero_da_venda += 1
            pasta_da_venda = pasta / f"venda-{numero_da_venda:04d}"
            venda = executar_venda_parcial(
                tela, mao, config, pasta_da_venda, interruptor, ritmo_venda, sorteio,
                total_baus=sessao.total_baus,
            )
            if venda.total_baus:
                sessao.total_baus = venda.total_baus
            sessao.unidades_listadas += venda.unidades_listadas
            proxima_janela = time.monotonic() + config.intervalo_da_janela_s
            janela_estava_aberta = False
            aplicar(EventoFluxo.venda_encerrada(venda.resta_lote_cheio))
            if venda.unidades_listadas:
                aplicar(EventoFluxo.unidades_listadas(venda.unidades_listadas))
            elif venda.desfecho is DesfechoSessaoVenda.CAPACIDADE_CHEIA:
                # A Capacidade cheia ja foi reportada acima, via
                # `venda.resta_lote_cheio` dentro de `venda_encerrada`; nao ha
                # mais nada a fazer neste ramo.
                pass

            # `capacidade_final` fica None quando a Venda nem chegou a ler `X/Y`;
            # emitir o evento nesse caso registraria uma Capacidade inventada.
            if venda.capacidade_final is not None:
                aplicar(
                    EventoFluxo.capacidade_atualizada(
                        venda.capacidade_final.ocupadas,
                        venda.capacidade_final.limite,
                    )
                )

            # F4 tambem pode ter sido apertado dentro da Venda.
            if venda.desfecho is DesfechoSessaoVenda.PAROU:
                return encerrar(DesfechoSessaoCompleta.PAROU)

            nav_compra = ir_para_compra(tela, mao, ritmo_venda)
            if not nav_compra.sucesso:
                return encerrar(DesfechoSessaoCompleta.ABORTOU, nav_compra.motivo)
            aplicar(EventoFluxo.retorno_compra())

            if interruptor.pediram_parada():
                return encerrar(DesfechoSessaoCompleta.PAROU)
    finally:
        _fechar(pasta, sessao)
