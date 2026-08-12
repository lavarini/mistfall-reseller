"""Extrai os 7 templates de icone do print que contem todos os Itens-alvo.

O template e o MIOLO da regiao de busca, cortado MARGEM_TEMPLATE de cada
lado. Se ele tivesse o tamanho da regiao, matchTemplate nao deslizaria e
perderia icones deslocados pelo arredondamento de SLOT_PASSO.
"""
import pathlib
import cv2
from mistfall.geometria import MARGEM_TEMPLATE, regiao_icone
from mistfall.tipos import ItemAlvo

ORIGEM = "images/broche-tres-adaga-lanterna-rede-padrao.png"
SLOTS = {
    ItemAlvo.BROCHE: (0, 0),
    ItemAlvo.ADAGA: (0, 1),
    ItemAlvo.LANTERNA: (1, 1),
    ItemAlvo.DRAGAO: (3, 0),
    ItemAlvo.ORBE: (3, 1),
    ItemAlvo.REDE: (4, 0),
    ItemAlvo.CODICE: (5, 0),
}

def main() -> None:
    destino = pathlib.Path("templates")
    destino.mkdir(exist_ok=True)
    img = cv2.imread(ORIGEM)
    m = MARGEM_TEMPLATE
    for item, (linha, coluna) in SLOTS.items():
        miolo = regiao_icone(img, linha, coluna)[m:-m, m:-m]
        cv2.imwrite(str(destino / f"{item.value}.png"), miolo)
        print("gravado", item.value, miolo.shape[:2])

if __name__ == "__main__":
    main()
