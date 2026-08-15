import argparse
import json
import math
import statistics
from pathlib import Path

import cv2

from mistfall.analise import analisar_inicial


def _percentil_95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    indice = max(0, min(len(ordenados) - 1, math.ceil(len(ordenados) * 0.95) - 1))
    return ordenados[indice]


def _resumo(valores: list[float]) -> dict:
    return {
        "n": len(valores),
        "mediana_ms": statistics.median(valores),
        "p95_ms": _percentil_95(valores),
        "max_ms": max(valores),
    }


def _assinatura(resultado) -> tuple:
    return resultado.ouro_observado, tuple(resultado.brutas)


def medir(caminhos: list[Path], repeticoes: int = 1) -> dict:
    if not caminhos:
        raise ValueError("nenhum 00-pre-voo.png encontrado")
    if repeticoes < 1:
        raise ValueError("repeticoes precisa ser >= 1")

    imagens = []
    for caminho in caminhos:
        imagem = cv2.imread(str(caminho))
        if imagem is None:
            raise ValueError(f"imagem ilegivel: {caminho}")
        imagens.append(imagem)

    aquecimento = analisar_inicial(imagens[0], concorrente=False)
    tempos = {False: [], True: []}
    assinaturas = {False: [], True: []}
    for concorrente in (False, True):
        for _ in range(repeticoes):
            for imagem in imagens:
                resultado = analisar_inicial(imagem, concorrente=concorrente)
                tempos[concorrente].append(resultado.tempos["analise_inicial_parede"])
                assinaturas[concorrente].append(_assinatura(resultado))

    iguais = assinaturas[False] == assinaturas[True]
    if not iguais:
        raise RuntimeError("pipeline concorrente mudou o resultado da analise")
    return {
        "aquecimento_ms": aquecimento.tempos["analise_inicial_parede"],
        "sequencial": _resumo(tempos[False]),
        "concorrente": _resumo(tempos[True]),
        "resultados_iguais": iguais,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pasta", type=Path, default=Path("sessao"))
    parser.add_argument("--repeticoes", type=int, default=1)
    args = parser.parse_args()
    caminhos = sorted(args.pasta.glob("volta-*/00-pre-voo.png"))
    print(json.dumps(medir(caminhos, args.repeticoes), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
