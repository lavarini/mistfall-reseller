"""Percorre os Baús à direita e vende cada stack alvo de quantidade tres."""

import json
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
    centro_bau,
    eh_tela_venda,
    ler_bau_selecionado,
    ler_capacidade,
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


def executar_ciclo_venda(
    tela: Tela,
    mao: Mao,
    config: Config,
    pasta: Path,
    interruptor: Interruptor,
    ritmo: RitmoVenda = RITMO_VENDA_PADRAO,
) -> SessaoVenda:
    pasta = Path(pasta)
    sessao = SessaoVenda()
    interruptor.esperar_inicio()

    def encerrar(desfecho, motivo=""):
        sessao.desfecho = desfecho
        sessao.motivo = motivo
        return sessao

    try:
        frame = tela.capturar()
        while True:
            if not eh_tela_venda(frame):
                return encerrar(DesfechoSessaoVenda.ABORTOU, "tela de Venda ilegivel")

            capacidade = ler_capacidade(frame)
            if capacidade is None:
                return encerrar(DesfechoSessaoVenda.ABORTOU, "Capacidade de Venda ilegivel")
            sessao.capacidade_final = capacidade
            if capacidade.ocupadas >= capacidade.limite:
                return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)

            bau = ler_bau_selecionado(frame)
            if bau is None:
                return encerrar(DesfechoSessaoVenda.ABORTOU, "Bau selecionado ilegivel")
            sessao.baus_processados.append(int(bau) + 1)

            candidatos = [
                slot for slot in varrer_armazem(frame)
                if slot.item is not None and slot.quantidade == 3
            ]
            for indice, slot in enumerate(candidatos, start=1):
                if interruptor.pediram_parada():
                    return encerrar(DesfechoSessaoVenda.PAROU)

                resultado = executar_venda(
                    tela,
                    mao,
                    slot,
                    config.precos_venda[slot.item],
                    pasta / f"venda-{sessao.vendas + 1:04d}",
                    ritmo,
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
                if capacidade.ocupadas >= capacidade.limite:
                    return encerrar(DesfechoSessaoVenda.CAPACIDADE_CHEIA)

            if bau is Bau.QUARTO:
                return encerrar(DesfechoSessaoVenda.ARMAZEM_ESGOTADO)
            if interruptor.pediram_parada():
                return encerrar(DesfechoSessaoVenda.PAROU)
            mao.clicar(*centro_bau(Bau(int(bau) + 1)))
            time.sleep(ritmo.intervalo_entre_perguntas)
            frame = tela.capturar()
    finally:
        _fechar(pasta, sessao)
