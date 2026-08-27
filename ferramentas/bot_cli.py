"""Roda o laco de Compra ate o operador apertar F5.

Sem contagem regressiva: o F3 substitui o Alt+Tab cronometrado do
mistfall-piloto, porque e apertado de dentro do jogo.
"""

import argparse
import dataclasses
import sys
from pathlib import Path

from mistfall.ciclo import executar_ciclo
from mistfall.config import carregar_config
from mistfall.piloto import RITMO_PADRAO


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Repete a Compra no Leilao ate o F5.")
    p.add_argument("--pasta", default="sessao",
                   help="onde salvar as pastas de cada Volta")
    p.add_argument("--config", default="config.toml")
    p.add_argument("--espera-modal", type=int,
                   default=round(RITMO_PADRAO.espera_para_o_modal_abrir[0] * 1000),
                   help="ms entre o clique e o Espaco. E o PISO: a espera de "
                        "cada Compra e sorteada entre ele e 1,5x ele")
    return p


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)

    from mistfall.perifericos.windows import InterruptorWindows, MaoWindows, TelaWindows

    piso = args.espera_modal / 1000
    teto = args.espera_modal * 1.5 / 1000
    ritmo = dataclasses.replace(
        RITMO_PADRAO,
        espera_para_o_modal_abrir=(piso, teto),
    )

    print("aperte F3 no jogo para comecar, F4 para pausar, F5 para encerrar", flush=True)
    interruptor = InterruptorWindows()
    while True:
        executar_ciclo(
            TelaWindows(), MaoWindows(), config, Path(args.pasta),
            interruptor, ritmo=ritmo,
        )
        pediu_encerramento = getattr(interruptor, "pediu_encerramento", None)
        if pediu_encerramento is None or pediu_encerramento():
            break
        print("pausado; aguardando F3 para comecar novamente", flush=True)
    print(f"pastas das Voltas em {args.pasta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
