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


# 0 correu como esperado, 1 abortou por seguranca, 2 problema de ambiente
# (em main), 3 apertou Espaco e o Ouro nao se moveu — que nao pode sair como
# 0, sob pena de ficar indistinguivel de uma Compra confirmada.
CODIGO_POR_DESFECHO = {
    Desfecho.COMPROU: 0,
    Desfecho.NADA_COMPRAVEL: 0,
    Desfecho.SIMULOU: 0,
    Desfecho.ABORTOU: 1,
    Desfecho.OURO_NAO_CAIU: 3,
}


def codigo_de_saida(resultado: Resultado) -> int:
    # Sem default: desfecho novo sem codigo tem de estourar aqui, nao sair 0.
    return CODIGO_POR_DESFECHO[resultado.desfecho]


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
        # A contagem nao existe para tirar a mao do mouse: existe para o jogo
        # virar a janela ativa, que e para onde o SendInput vai. Alt+Tab, e
        # nao clique — clicar no jogo pode abrir um modal sozinho.
        for restam in range(SEGUNDOS_DE_CONTAGEM, 0, -1):
            print(f"comecando em {restam}... Alt+Tab para o jogo AGORA "
                  "(nao clique nele) e tire a mao do mouse", flush=True)
            time.sleep(1)

    resultado = executar(TelaWindows(), MaoWindows(), config,
                         Path(args.pasta), simular=args.simular)

    print(f"desfecho: {resultado.desfecho.value}")
    if resultado.motivo:
        print(f"motivo: {resultado.motivo}")
    if resultado.listagem is not None:
        print(f"listagem: {resultado.listagem}")
    if resultado.segundos_ate_a_janela is not None:
        print("a Janela levou no maximo "
              f"{resultado.segundos_ate_a_janela:.2f}s para abrir "
              "(teto: inclui uma captura e uma deteccao de estado)")
    if resultado.escala_do_icone is not None:
        print(f"a Janela mostrava: item={resultado.item_no_modal} "
              f"preco={resultado.preco_no_modal} "
              f"quantidade={resultado.quantidade_no_modal} "
              f"total={resultado.preco_total_esperado}")
        print(f"scores do icone (escala {resultado.escala_do_icone}): "
              f"{resultado.scores_do_icone}")
    if resultado.ouro_antes is not None:
        print(f"Ouro: {resultado.ouro_antes} -> {resultado.ouro_depois}")
    if resultado.tempos:
        print("Tempo por etapa (ms):")
        for etapa, ms in resultado.tempos.items():
            print(f"  {etapa}: {ms:.1f}")
    print(f"prints e relatorio em {args.pasta}")
    return codigo_de_saida(resultado)


if __name__ == "__main__":
    sys.exit(main())
