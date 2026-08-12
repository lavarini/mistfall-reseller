"""Propoe o arquivo de expectativa de cada print, para revisao humana.

O que sai daqui NAO e verdade: e a leitura atual da deteccao. Precisa
ser conferido contra a imagem anotada antes de virar fixture.
"""
import glob
import json
import pathlib
import cv2
from mistfall.geometria import conferir_resolucao
from mistfall.leilao import varrer

def main() -> None:
    destino = pathlib.Path("fixtures/esperado")
    destino.mkdir(parents=True, exist_ok=True)
    for caminho in sorted(glob.glob("images/*.png")):
        img = cv2.imread(caminho)
        # O contrato de resolucao mora em geometria; nada de repetir o literal
        # aqui, ainda por cima na convencao invertida (altura, largura).
        try:
            conferir_resolucao(img)
        except ValueError as erro:
            print("pulando:", caminho, "-", erro)
            continue
        nome = pathlib.Path(caminho).stem
        slots = [
            {
                "linha": l.linha,
                "coluna": l.coluna,
                "item": l.item.value if l.item else None,
                "preco_unitario": l.preco_unitario,
            }
            for l in varrer(img)
        ]
        alvo = destino / f"{nome}.json"
        if alvo.exists():
            print("ja existe, preservando:", alvo)
            continue
        alvo.write_text(json.dumps({"slots": slots}, indent=2, ensure_ascii=False), encoding="utf-8")
        print("proposto", alvo)

if __name__ == "__main__":
    main()
