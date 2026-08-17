"""Percorre os Baús à direita e vende cada stack alvo de quantidade tres."""

import json
import random
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from mistfall.config import Config
from mistfall.perifericos.protocolos import Interruptor, Mao, Tela
from mistfall.tipos import Bau, CapacidadeVenda
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
    capacidade_final: CapacidadeVenda | None = None
    baus_processados: list[int] = field(default_factory=list)


def _fechar(pasta: Path, sessao: SessaoVenda) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    dados = asdict(sessao)
    dados["desfecho"] = sessao.desfecho.value
    (pasta / "sessao.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _esperar_bau(tela: Tela, esperado: Bau, ritmo: RitmoVenda):
    inicio = time.monotonic()
    primeira = True
    while primeira or time.monotonic() - inicio < ritmo.teto_espera_fechamento:
        primeira = False
        frame = tela.capturar()
        if eh_tela_venda(frame) and ler_bau_selecionado(frame) is esperado:
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
    tela: Tela, mao: Mao, bau: Bau, ritmo: RitmoVenda,
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


def executar_ciclo_venda(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo: RitmoVenda = RITMO_VENDA_PADRAO,
    sorteio: random.Random | None = None,
) -> SessaoVenda:
    pasta = Path(pasta)
    sessao = SessaoVenda()
    if sorteio is None:
        sorteio = random.Random()
    interruptor.esperar_inicio()

    def encerrar(desfecho, motivo=""):
        sessao.desfecho = desfecho
        sessao.motivo = motivo
        return sessao

    try:
        frame = tela.capturar()
        bau_confirmado = None
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
            sessao.baus_processados.append(int(bau) + 1)

            candidatos = _candidatos(frame)
            # Uma lista inicialmente não vazia já representa trabalho válido;
            # só forçamos a troca de abas quando a leitura não encontrou alvo.
            resetou_armazem = bool(candidatos)
            while True:
                while candidatos:
                    if interruptor.pediram_parada():
                        return encerrar(DesfechoSessaoVenda.PAROU)

                    if capacidade.ocupadas >= capacidade.limite:
                        espera, motivo = _esperar_vaga(
                            tela, interruptor, capacidade, ritmo,
                        )
                        if motivo == "parou":
                            return encerrar(DesfechoSessaoVenda.PAROU)
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

                if resetou_armazem:
                    break
                frame_resetado = _forcar_reset_armazem(tela, mao, bau, ritmo)
                if frame_resetado is None:
                    return encerrar(
                        DesfechoSessaoVenda.ABORTOU,
                        "nao conseguiu resetar o Armazem",
                    )
                frame = frame_resetado
                capacidade = ler_capacidade(frame)
                if capacidade is None:
                    return encerrar(
                        DesfechoSessaoVenda.ABORTOU,
                        "Capacidade de Venda ilegivel depois do reset",
                    )
                sessao.capacidade_final = capacidade
                candidatos = _candidatos(frame)
                resetou_armazem = True

            if bau is Bau.QUARTO:
                return encerrar(DesfechoSessaoVenda.ARMAZEM_ESGOTADO)
            if interruptor.pediram_parada():
                return encerrar(DesfechoSessaoVenda.PAROU)
            proximo_bau = Bau(int(bau) + 1)
            mao.clicar(*centro_bau(proximo_bau))
            frame = _esperar_bau(tela, proximo_bau, ritmo)
            if frame is None:
                return encerrar(
                    DesfechoSessaoVenda.ABORTOU,
                    f"Bau {int(proximo_bau) + 1} nao abriu",
                )
            bau_confirmado = proximo_bau
    finally:
        _fechar(pasta, sessao)
