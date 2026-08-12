import glob
import json
import pathlib
import cv2
import pytest
from mistfall.leilao import varrer

CASOS = sorted(glob.glob("fixtures/esperado/*.json"))

@pytest.mark.parametrize("caminho_json", CASOS, ids=lambda p: pathlib.Path(p).stem)
def test_deteccao_bate_com_o_corpus_rotulado(caminho_json):
    nome = pathlib.Path(caminho_json).stem
    esperado = json.loads(pathlib.Path(caminho_json).read_text(encoding="utf-8"))["slots"]
    img = cv2.imread(f"images/{nome}.png")
    obtido = [
        {
            "linha": l.linha,
            "coluna": l.coluna,
            "item": l.item.value if l.item else None,
            "preco_unitario": l.preco_unitario,
        }
        for l in varrer(img)
    ]
    assert obtido == esperado

def test_o_corpus_nao_esta_vazio():
    assert len(CASOS) >= 7
