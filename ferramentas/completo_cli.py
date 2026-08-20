"""Roda o fluxo completo de Compra e Venda ate o operador apertar F4.

Alterna sozinho entre Comprar e Vender, seguindo o coordenador de
`mistfall.ciclo_completo`. Como os demais lacos continuos do projeto, usa F3
para iniciar e F4 para parar.
"""

import argparse
import dataclasses
import sys
from pathlib import Path

from mistfall.ciclo_completo import DesfechoSessaoCompleta, executar_ciclo_completo
from mistfall.config import carregar_config, validar_precos_venda
from mistfall.piloto import RITMO_PADRAO
from mistfall.venda import RITMO_VENDA_PADRAO


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Alterna Compra e Venda no Leilao ate o F4.")
    p.add_argument("--pasta", default="sessao-completa",
                   help="onde salvar as pastas de cada Volta e cada Venda")
    p.add_argument("--config", default="config.toml")
    p.add_argument("--espera-modal", type=int,
                   default=round(RITMO_PADRAO.espera_para_o_modal_abrir[0] * 1000),
                   help="ms entre o clique e o Espaco na Compra. E o PISO: a "
                        "espera de cada Compra e sorteada entre ele e 1,5x ele")
    p.add_argument("--teto-janela", type=float,
                   default=RITMO_VENDA_PADRAO.teto_espera_janela,
                   help="segundos para a Janela de Confirmacao da Venda abrir")
    p.add_argument("--teto-fechamento", type=float,
                   default=RITMO_VENDA_PADRAO.teto_espera_fechamento,
                   help="segundos para a Janela de Confirmacao da Venda fechar")
    return p


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)
    validar_precos_venda(config)

    from mistfall.perifericos.windows import (
        InterruptorWindows, MaoWindows, TelaWindows, VK_F3, VK_F4,
    )

    piso = args.espera_modal / 1000
    teto = args.espera_modal * 1.5 / 1000
    ritmo_compra = dataclasses.replace(
        RITMO_PADRAO,
        espera_para_o_modal_abrir=(piso, teto),
    )
    ritmo_venda = dataclasses.replace(
        RITMO_VENDA_PADRAO,
        teto_espera_janela=args.teto_janela,
        teto_espera_fechamento=args.teto_fechamento,
    )

    print("aperte F3 no jogo para comecar, F4 para parar", flush=True)
    sessao = executar_ciclo_completo(
        TelaWindows(), MaoWindows(), config, Path(args.pasta),
        InterruptorWindows(vk_inicio=VK_F3, vk_parada=VK_F4),
        ritmo_compra, ritmo_venda,
    )
    print(f"pastas do fluxo completo em {args.pasta}")
    print(
        f"desfecho: {sessao.desfecho.value}"
        + (f" — {sessao.motivo}" if sessao.motivo else "")
    )
    print(
        f"Compras enviadas: {sessao.compras_enviadas}; "
        f"unidades listadas: {sessao.unidades_listadas}; "
        f"diagnostico completo em {Path(args.pasta) / 'sessao.json'}"
    )
    # Abortar e o codigo 1 da tabela "Codigos de saida": sem isto o operador
    # encontrava processo terminado em 0, sem nenhum sinal de que a sessao
    # tinha morrido.
    return 1 if sessao.desfecho is DesfechoSessaoCompleta.ABORTOU else 0


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
