"""Percorre os Baús à direita e vende cada stack alvo de quantidade tres."""

import json
import random
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from mistfall.config import Config
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.tipos import BAU_INICIAL, CapacidadeVenda
from mistfall.venda import (
    DesfechoVenda,
    RITMO_VENDA_PADRAO,
    RitmoVenda,
    executar_venda,
)
from mistfall.venda_visao import (
    CENTRO_ABA_ARMAZEM,
    CENTRO_ABA_INVENTARIO,
    PainelItens,
    centro_bau,
    eh_tela_venda,
    contar_baus,
    ler_bau_selecionado,
    ler_capacidade,
    ler_painel_itens,
    varrer_armazem,
)


class DesfechoSessaoVenda(Enum):
    CAPACIDADE_CHEIA = "capacidade_cheia"
    ARMAZEM_ESGOTADO = "armazem_esgotado"
    PAROU = "parou"
    ABORTOU = "abortou"


@dataclass
class SessaoVenda:
    desfecho: DesfechoSessaoVenda = DesfechoSessaoVenda.ABORTOU
    motivo: str = ""
    vendas: int = 0
    unidades_listadas: int = 0
    capacidade_final: CapacidadeVenda | None = None
    baus_processados: list[int] = field(default_factory=list)
    # Quantos Baus o Armazem tinha nesta sessao. Contado uma vez, da
    # propria tela: o numero muda entre seasons.
    total_baus: int = 0


def _fechar(pasta: Path, sessao: SessaoVenda) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    dados = asdict(sessao)
    dados["desfecho"] = sessao.desfecho.value
    (pasta / "sessao.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _esperar_bau(tela: Tela, esperado: int, ritmo: RitmoVenda):
    inicio = time.monotonic()
    primeira = True
    while primeira or time.monotonic() - inicio < ritmo.teto_espera_fechamento:
        primeira = False
        frame = tela.capturar()
        if eh_tela_venda(frame) and ler_bau_selecionado(frame) == esperado:
            return frame
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None


def _esperar_painel(tela: Tela, esperado: PainelItens, ritmo: RitmoVenda):
    inicio = time.monotonic()
    primeira = True
    while primeira or time.monotonic() - inicio < ritmo.teto_espera_fechamento:
        primeira = False
        frame = tela.capturar()
        if ler_painel_itens(frame) is esperado:
            return frame
        time.sleep(ritmo.intervalo_entre_perguntas)
    return None


def _forcar_reset_armazem(
    tela: Tela, mao: Mao, bau: int, ritmo: RitmoVenda,
):
    mao.clicar(*CENTRO_ABA_INVENTARIO)
    if _esperar_painel(tela, PainelItens.INVENTARIO, ritmo) is None:
        return None
    mao.clicar(*CENTRO_ABA_ARMAZEM)
    return _esperar_bau(tela, bau, ritmo)


def _candidatos(frame):
    return [
        slot for slot in varrer_armazem(frame)
        if slot.item is not None and slot.quantidade == 3
    ]


def _capacidade_do_armazem_do_bau(
    frame, bau: int,
) -> CapacidadeVenda | None:
    if (
        ler_painel_itens(frame) is not PainelItens.ARMAZEM
        or ler_bau_selecionado(frame) != bau
    ):
        return None
    return ler_capacidade(frame)


def _esperar_vaga(
    tela: Tela,
    interruptor: Interruptor,
    capacidade: CapacidadeVenda,
    ritmo: RitmoVenda,
):
    tentativa = 0
    while capacidade.ocupadas >= capacidade.limite:
        espera = ritmo.esperas_capacidade_cheia[
            min(tentativa, len(ritmo.esperas_capacidade_cheia) - 1)
        ]
        inicio = time.monotonic()
        while time.monotonic() - inicio < espera:
            if interruptor.pediram_parada():
                return None, "parou"
            intervalo = ritmo.intervalo_entre_perguntas
            restante = espera - (time.monotonic() - inicio)
            time.sleep(min(intervalo, restante) if intervalo > 0 else restante)
        frame = tela.capturar()
        capacidade = ler_capacidade(frame)
        if capacidade is None:
            return None, "capacidade ilegivel"
        tentativa += 1
    return (frame, capacidade), ""


def _esperar_vaga_parcial(
    tela: Tela,
    interruptor: Interruptor,
    capacidade: CapacidadeVenda,
    ritmo: RitmoVenda,
):
    inicio = time.monotonic()
    while capacidade.ocupadas >= capacidade.limite:
        if interruptor.pediram_parada():
            return None, "parou"
        frame = tela.capturar()
        capacidade = ler_capacidade(frame)
        if capacidade is None:
            return None, "capacidade ilegivel"
        if capacidade.ocupadas < capacidade.limite:
            return (frame, capacidade), ""
        if time.monotonic() - inicio >= 3.0:
            return (frame, capacidade), "capacidade cheia"
        time.sleep(ritmo.intervalo_entre_perguntas)
    return (frame, capacidade), ""


def executar_ciclo_venda(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo: RitmoVenda = RITMO_VENDA_PADRAO,
    sorteio: random.Random | None = None,
) -> SessaoVenda:
    return _executar_sessao_venda(
        tela, mao, config, pasta, interruptor, ritmo, sorteio, parcial=False,
    )


def executar_venda_parcial(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo: RitmoVenda = RITMO_VENDA_PADRAO,
    sorteio: random.Random | None = None,
    total_baus: int = 0,
) -> SessaoVenda:
    """Venda parcial, opcionalmente com a contagem de Baus ja conhecida.

    O Fluxo Completo conta os Baus na primeira Venda e repassa o numero nas
    seguintes; sem ele, a sessao conta sozinha.
    """
    return _executar_sessao_venda(
        tela, mao, config, pasta, interruptor, ritmo, sorteio, parcial=True,
        total_baus=total_baus,
    )


def _executar_sessao_venda(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo: RitmoVenda,
    sorteio: random.Random | None,
    *,
    parcial: bool,
    total_baus: int = 0,
) -> SessaoVenda:
    pasta = Path(pasta)
    sessao = SessaoVenda(total_baus=total_baus)
    if sorteio is None:
        sorteio = random.Random()
    if not parcial and interruptor.esperar_inicio() is False:
        return sessao

    def encerrar(desfecho, motivo=""):
        sessao.desfecho = desfecho
        sessao.motivo = motivo
        return sessao

    try:
        frame = tela.capturar()
        bau_confirmado = None
        if parcial:
            mao.clicar(*centro_bau(BAU_INICIAL))
            frame = _esperar_bau(tela, BAU_INICIAL, ritmo)
            if frame is None:
                return encerrar(
                    DesfechoSessaoVenda.ABORTOU,
                    f"Bau {BAU_INICIAL + 1} nao abriu",
                )
            bau_confirmado = BAU_INICIAL
        while True:
            if not eh_tela_venda(frame):
                return encerrar(DesfechoSessaoVenda.ABORTOU, "tela de Venda ilegivel")
            if ler_painel_itens(frame) is not PainelItens.ARMAZEM:
                return encerrar(
                    DesfechoSessaoVenda.ABORTOU,
                    "Armazem nao esta selecionado",
                )

            capacidade = ler_capacidade(frame)
            if capacidade is None:
                return encerrar(DesfechoSessaoVenda.ABORTOU, "Capacidade de Venda ilegivel")
            sessao.capacidade_final = capacidade

            bau = bau_confirmado or ler_bau_selecionado(frame)
            bau_confirmado = None
            if bau is None:
                return encerrar(DesfechoSessaoVenda.ABORTOU, "Bau selecionado ilegivel")
            if not sessao.total_baus:
                sessao.total_baus = contar_baus(frame)
                if sessao.total_baus < 2:
                    # O jogo sempre da ao menos dois Baus, entao menos que isso
                    # e leitura errada, nao Armazem pequeno.
                    return encerrar(
                        DesfechoSessaoVenda.ABORTOU,
                        f"contagem de Baus implausivel: {sessao.total_baus}",
                    )
            sessao.baus_processados.append(bau + 1)

            candidatos = _candidatos(frame)
            # Uma leitura vazia pode ser legítima, mas também pode ter ocorrido
            # enquanto a tela ainda trocava de Bau. Releia no proprio Armazem
            # antes de considerar o Bau vazio.
            if not candidatos:
                time.sleep(ritmo.intervalo_entre_perguntas)
                releitura = tela.capturar()
                capacidade_releitura = _capacidade_do_armazem_do_bau(releitura, bau)
                if capacidade_releitura is not None:
                    frame = releitura
                    capacidade = capacidade_releitura
                    sessao.capacidade_final = capacidade
                    candidatos = _candidatos(frame)
                else:
                    frame_resetado = _forcar_reset_armazem(tela, mao, bau, ritmo)
                    capacidade_resetada = (
                        None
                        if frame_resetado is None
                        else _capacidade_do_armazem_do_bau(frame_resetado, bau)
                    )
                    if capacidade_resetada is None:
                        return encerrar(
                            DesfechoSessaoVenda.ABORTOU,
                            "nao conseguiu validar o Armazem depois de leitura inconclusiva",
                        )
                    frame = frame_resetado
                    capacidade = capacidade_resetada
                    sessao.capacidade_final = capacidade
                    candidatos = _candidatos(frame)
            while True:
                while candidatos:
                    if interruptor.pediram_parada():
                        return encerrar(DesfechoSessaoVenda.PAROU)

                    if capacidade.ocupadas >= capacidade.limite:
                        esperar_vaga = (
                            _esperar_vaga_parcial if parcial else _esperar_vaga
                        )
                        espera, motivo = esperar_vaga(tela, interruptor, capacidade, ritmo)
                        if motivo == "parou":
                            return encerrar(DesfechoSessaoVenda.PAROU)
                        if motivo == "capacidade cheia":
                            _, capacidade = espera
                            sessao.capacidade_final = capacidade
                            return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)
                        if espera is None:
                            return encerrar(
                                DesfechoSessaoVenda.ABORTOU,
                                motivo,
                            )
                        frame, capacidade = espera
                        sessao.capacidade_final = capacidade

                    slot = candidatos.pop(0)
                    resultado = executar_venda(
                        tela,
                        mao,
                        slot,
                        config.precos_venda[slot.item],
                        pasta / f"venda-{sessao.vendas + 1:04d}",
                        ritmo,
                        sorteio,
                    )
                    if resultado.desfecho is not DesfechoVenda.VENDEU:
                        return encerrar(DesfechoSessaoVenda.ABORTOU, resultado.motivo)
                    sessao.vendas += 1
                    sessao.unidades_listadas = sessao.vendas * 3

                    frame = tela.capturar()
                    if not eh_tela_venda(frame):
                        return encerrar(
                            DesfechoSessaoVenda.ABORTOU,
                            "tela de Venda ilegivel depois da Venda",
                        )
                    capacidade = ler_capacidade(frame)
                    if capacidade is None:
                        return encerrar(
                            DesfechoSessaoVenda.ABORTOU,
                            "Capacidade de Venda ilegivel depois da Venda",
                        )
                    sessao.capacidade_final = capacidade
                    if parcial and capacidade.ocupadas >= capacidade.limite:
                        espera, motivo = _esperar_vaga_parcial(
                            tela, interruptor, capacidade, ritmo,
                        )
                        if motivo == "parou":
                            return encerrar(DesfechoSessaoVenda.PAROU)
                        if motivo == "capacidade cheia":
                            _, capacidade = espera
                            sessao.capacidade_final = capacidade
                            return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)
                        if espera is None:
                            return encerrar(DesfechoSessaoVenda.ABORTOU, motivo)
                        frame, capacidade = espera
                        sessao.capacidade_final = capacidade

                break

            if bau >= sessao.total_baus - 1:
                return encerrar(DesfechoSessaoVenda.ARMAZEM_ESGOTADO)
            if interruptor.pediram_parada():
                return encerrar(DesfechoSessaoVenda.PAROU)
            proximo_bau = bau + 1
            mao.clicar(*centro_bau(proximo_bau))
            frame = _esperar_bau(tela, proximo_bau, ritmo)
            if frame is None:
                return encerrar(
                    DesfechoSessaoVenda.ABORTOU,
                    f"Bau {proximo_bau + 1} nao abriu",
                )
            bau_confirmado = proximo_bau
    finally:
        _fechar(pasta, sessao)
