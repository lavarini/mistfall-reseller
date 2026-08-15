"""Executa uma Venda de um stack de tres unidades de um Item-alvo."""

import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import cv2

from mistfall.perifericos.protocolos import Mao, Tela
from mistfall.tipos import SlotArmazem
from mistfall.venda_visao import centro_slot_armazem, eh_janela_venda, eh_tela_venda


CENTRO_PRECO_VENDA = (1700, 806)
CENTRO_QUANTIDADE_VENDA = (1700, 907)
CENTRO_BOTAO_LISTAR = (1700, 1025)


@dataclass(frozen=True)
class RitmoVenda:
    pausa_antes_do_clique: float = 0.2
    intervalo_entre_perguntas: float = 0.1
    teto_espera_janela: float = 10.0
    teto_espera_fechamento: float = 10.0

    @classmethod
    def instantaneo(cls) -> "RitmoVenda":
        return cls(
            pausa_antes_do_clique=0.0,
            intervalo_entre_perguntas=0.0,
            teto_espera_janela=0.02,
            teto_espera_fechamento=0.02,
        )


RITMO_VENDA_PADRAO = RitmoVenda()


class DesfechoVenda(Enum):
    VENDEU = "vendeu"
    ABORTOU = "abortou"


@dataclass
class ResultadoVenda:
    desfecho: DesfechoVenda = DesfechoVenda.ABORTOU
    motivo: str = "explodiu durante a Venda"
    item: str | None = None
    linha: int | None = None
    coluna: int | None = None
    preco_venda: int | None = None
    quantidade: int = 3


def _esperar_frame(tela: Tela, predicado, teto: float, intervalo: float):
    inicio = time.monotonic()
    primeira = True
    ultimo = None
    while primeira or time.monotonic() - inicio < teto:
        primeira = False
        ultimo = tela.capturar()
        if predicado(ultimo):
            return ultimo, ultimo
        time.sleep(intervalo)
    return None, ultimo


def _gravar(pasta: Path, nome: str, frame) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(pasta / nome), frame)


def executar_venda(
    tela: Tela,
    mao: Mao,
    slot: SlotArmazem,
    preco_venda: int,
    pasta: Path,
    ritmo: RitmoVenda = RITMO_VENDA_PADRAO,
) -> ResultadoVenda:
    if (
        not isinstance(preco_venda, int)
        or isinstance(preco_venda, bool)
        or preco_venda <= 0
    ):
        raise ValueError("Preco de Venda precisa ser inteiro maior que zero")
    if slot.item is None or slot.quantidade != 3:
        raise ValueError("Venda exige Item-alvo com stack de quantidade 3")

    pasta = Path(pasta)
    resultado = ResultadoVenda(
        item=slot.item.value,
        linha=slot.linha,
        coluna=slot.coluna,
        preco_venda=preco_venda,
    )
    try:
        antes = tela.capturar()
        _gravar(pasta, "00-antes.png", antes)
        time.sleep(ritmo.pausa_antes_do_clique)
        mao.clicar(*centro_slot_armazem(slot))

        janela, _ = _esperar_frame(
            tela,
            eh_janela_venda,
            ritmo.teto_espera_janela,
            ritmo.intervalo_entre_perguntas,
        )
        if janela is None:
            resultado.motivo = "Janela de Confirmacao nao abriu"
            return resultado
        _gravar(pasta, "01-janela.png", janela)

        mao.clicar(*CENTRO_PRECO_VENDA)
        mao.selecionar_tudo()
        mao.digitar_numero(preco_venda)
        mao.clicar(*CENTRO_QUANTIDADE_VENDA)
        mao.selecionar_tudo()
        mao.digitar_numero(3)
        # O campo Quantidade continua com foco depois da digitacao. Nesse
        # estado, Espaco e inserido no campo em vez de acionar o atalho do
        # botao — observado na primeira execucao real de Venda. O clique
        # direto nao depende do foco e confirma a mesma acao.
        mao.clicar(*CENTRO_BOTAO_LISTAR)

        depois, ultimo = _esperar_frame(
            tela,
            eh_tela_venda,
            ritmo.teto_espera_fechamento,
            ritmo.intervalo_entre_perguntas,
        )
        if depois is None:
            if ultimo is not None:
                _gravar(pasta, "02-nao-fechou.png", ultimo)
            resultado.motivo = "Janela de Confirmacao nao fechou"
            return resultado
        _gravar(pasta, "02-depois.png", depois)
        resultado.desfecho = DesfechoVenda.VENDEU
        resultado.motivo = ""
        return resultado
    finally:
        pasta.mkdir(parents=True, exist_ok=True)
        dados = asdict(resultado)
        dados["desfecho"] = resultado.desfecho.value
        (pasta / "relatorio.json").write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
