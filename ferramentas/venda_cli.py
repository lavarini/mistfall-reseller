"""Roda o ciclo de Venda na aba Vender com o Armazem aberto."""

import argparse
import dataclasses
import sys
from pathlib import Path

from mistfall.ciclo_venda import executar_ciclo_venda
from mistfall.config import carregar_config, validar_precos_venda
from mistfall.venda import RITMO_VENDA_PADRAO


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Vende stacks de tres dos Itens-alvo no Armazem."
    )
    parser.add_argument("--pasta", default="sessao-venda")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument(
        "--teto-janela", type=float,
        default=RITMO_VENDA_PADRAO.teto_espera_janela,
        help="segundos para a Janela de Confirmacao abrir",
    )
    parser.add_argument(
        "--teto-fechamento", type=float,
        default=RITMO_VENDA_PADRAO.teto_espera_fechamento,
        help="segundos para a Janela de Confirmacao fechar",
    )
    return parser


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)
    validar_precos_venda(config)

    from mistfall.perifericos.windows import (
        InterruptorWindows,
        MaoWindows,
        TelaWindows,
    )

    ritmo = dataclasses.replace(
        RITMO_VENDA_PADRAO,
        teto_espera_janela=args.teto_janela,
        teto_espera_fechamento=args.teto_fechamento,
    )
    print("aperte F2 no jogo para comecar, F3 para parar", flush=True)
    executar_ciclo_venda(
        TelaWindows(),
        MaoWindows(),
        config,
        Path(args.pasta),
        InterruptorWindows(),
        ritmo,
    )
    print(f"relatorios da Venda em {args.pasta}")
    return 0


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
