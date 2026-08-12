"""Propoe o arquivo de expectativa de cada print, para revisao humana.

O que sai daqui NAO e verdade: e a leitura atual da deteccao. Precisa
ser conferido contra a imagem anotada antes de virar fixture.
"""
import glob
import json
import pathlib
import cv2
from mistfall.leilao import varrer

def main() -> None:
    destino = pathlib.Path("fixtures/esperado")
    destino.mkdir(parents=True, exist_ok=True)
    for caminho in sorted(glob.glob("images/*.png")):
        img = cv2.imread(caminho)
        if img.shape[:2] != (1440, 2560):
            print("pulando (resolucao diferente):", caminho)
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
