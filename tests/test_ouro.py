import cv2
import pytest
from mistfall.ouro import ler_ouro

@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("broche-tres-adaga-lanterna-rede-padrao", 64735),
        ("adaga-tres-broche-dois-lanterna-rede-padrao", 64735),
        ("broche-dragao-orbe-codice-padrao", 66160),
        ("dragao-um-rede-padrao", 65234),
        ("lanterna-dragao-orbe-rede", 65972),
        ("reset-forja", 64735),
        ("reset-chave", 64735),
    ],
)
def test_le_o_ouro_do_topo_direito(nome, esperado):
    assert ler_ouro(cv2.imread(f"images/{nome}.png")) == esperado

def test_com_a_janela_de_confirmacao_aberta_o_ouro_fica_ilegivel():
    # O modal escurece a tela. Devolver None e correto: o Ouro e lido
    # com a lista visivel, nunca por cima da Janela de Confirmacao.
    assert ler_ouro(cv2.imread("images/janela.png")) is None
