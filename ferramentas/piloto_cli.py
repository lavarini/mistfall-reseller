"""Dispara uma unica Compra. Precisa rodar como administrador no Windows."""

import argparse
import sys
import time
from pathlib import Path

from mistfall.config import carregar_config
from mistfall.piloto import Desfecho, Resultado, executar

SEGUNDOS_DE_CONTAGEM = 5


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Faz uma Compra no Leilao e para.")
    p.add_argument("--simular", action="store_true",
                   help="varre e decide, mas nao clica nem aperta nada")
    p.add_argument("--pasta", default="execucao",
                   help="onde salvar prints e relatorio")
    p.add_argument("--config", default="config.toml")
    return p


def codigo_de_saida(resultado: Resultado) -> int:
    if resultado.desfecho is Desfecho.ABORTOU:
        return 1
    return 0


def main() -> int:
    args = montar_parser().parse_args()
    try:
        return _rodar(args)
    except (ValueError, OSError, ImportError) as erro:
        # Resolucao errada, tesseract ausente, mss faltando, config invalida,
        # SendInput recusado. Sao problemas de ambiente, nao de decisao: o
        # usuario precisa da mensagem, nao de um traceback.
        print(f"problema de ambiente: {erro}", file=sys.stderr)
        return 2


def _rodar(args: argparse.Namespace) -> int:
    config = carregar_config(args.config)

    from mistfall.perifericos.windows import MaoWindows, TelaWindows

    if not args.simular:
        for restam in range(SEGUNDOS_DE_CONTAGEM, 0, -1):
            print(f"comecando em {restam}... tire a mao do mouse", flush=True)
            time.sleep(1)

    resultado = executar(TelaWindows(), MaoWindows(), config,
                         Path(args.pasta), simular=args.simular)

    print(f"desfecho: {resultado.desfecho.value}")
    if resultado.motivo:
        print(f"motivo: {resultado.motivo}")
    if resultado.listagem is not None:
        print(f"listagem: {resultado.listagem}")
    if resultado.segundos_ate_a_janela is not None:
        print(f"a Janela levou {resultado.segundos_ate_a_janela:.2f}s para abrir")
    if resultado.ouro_antes is not None:
        print(f"Ouro: {resultado.ouro_antes} -> {resultado.ouro_depois}")
    print(f"prints e relatorio em {args.pasta}")
    return codigo_de_saida(resultado)


if __name__ == "__main__":
    sys.exit(main())
