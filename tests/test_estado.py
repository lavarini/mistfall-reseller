import cv2
import pytest
from mistfall.estado import identificar_estado
from mistfall.tipos import EstadoTela

@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("broche-tres-adaga-lanterna-rede-padrao", EstadoTela.LISTA),
        ("broche-dragao-orbe-codice-padrao", EstadoTela.LISTA),
        ("janela", EstadoTela.JANELA_CONFIRMACAO),
        ("reset-forja", EstadoTela.OUTRA_CATEGORIA),
        ("reset-chave", EstadoTela.OUTRA_CATEGORIA),
    ],
)
def test_classifica_a_tela(nome, esperado):
    assert identificar_estado(cv2.imread(f"images/{nome}.png")) is esperado

def test_os_estados_sao_mutuamente_exclusivos():
    import glob, pathlib
    vistos = {}
    for caminho in sorted(glob.glob("images/*.png")):
        img = cv2.imread(caminho)
        if img.shape[:2] != (1440, 2560):
            continue
        vistos[pathlib.Path(caminho).stem] = identificar_estado(img)
    assert EstadoTela.DESCONHECIDO not in vistos.values(), vistos
