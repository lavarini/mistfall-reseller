import ast
import pathlib

import numpy as np
import pytest

from mistfall.perifericos import windows

FONTE = pathlib.Path("src/mistfall/perifericos/windows.py")

PROIBIDOS = {"mss", "ctypes"}

def _modulos_importados(caminho: pathlib.Path) -> set[str]:
    """Nome raiz de todo modulo importado, em qualquer forma de import.

    Usa AST em vez de busca de texto: procurar a string "import ctypes"
    deixa passar "from ctypes import wintypes", que e exatamente a forma
    usada aqui.
    """
    encontrados = set()
    for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            encontrados |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            encontrados.add(no.module.split(".")[0])
    return encontrados

def test_o_teste_de_import_pega_a_forma_from(tmp_path):
    # Guarda o proprio detector: a versao anterior deste teste procurava a
    # string "import ctypes" e nao pegava a forma abaixo.
    arquivo = tmp_path / "vazando.py"
    arquivo.write_text("from ctypes import wintypes\n", encoding="utf-8")
    assert "ctypes" in _modulos_importados(arquivo)

def test_nenhum_outro_arquivo_importa_windows():
    # Toda dependencia de Windows tem de estar confinada a este arquivo.
    for py in list(pathlib.Path("src").rglob("*.py")) + list(pathlib.Path("ferramentas").rglob("*.py")):
        if py == FONTE:
            continue
        vazando = _modulos_importados(py) & PROIBIDOS
        assert not vazando, f"{py} importa {vazando}"

def test_windows_implementa_os_protocolos():
    arvore = ast.parse(FONTE.read_text(encoding="utf-8"))
    classes = {n.name: n for n in ast.walk(arvore) if isinstance(n, ast.ClassDef)}
    assert "TelaWindows" in classes
    assert "MaoWindows" in classes
    metodos = lambda c: {n.name for n in classes[c].body if isinstance(n, ast.FunctionDef)}
    assert "capturar" in metodos("TelaWindows")
    assert {"clicar", "apertar_espaco", "apertar_esc"} <= metodos("MaoWindows")
    # Confere aridade, nao so o nome: um `botao=None` extra passaria pela
    # checagem de nomes acima sem ser percebido.
    clicar = next(
        n for n in classes["MaoWindows"].body
        if isinstance(n, ast.FunctionDef) and n.name == "clicar"
    )
    assert [a.arg for a in clicar.args.args] == ["self", "x", "y"]

def test_tecla_espaco_pressionada_usa_scancode_e_nao_virtual_key():
    # Jogos costumam ler scancode de hardware e ignorar tecla virtual: se o
    # scancode fosse escrito no campo errado (wVk em vez de wScan), uma
    # busca de texto por "0x39" no arquivo continuaria passando sem
    # detectar o bug. Aqui inspecionamos a struct que seria de fato
    # enviada ao SendInput.
    entrada = windows._tecla(windows.SCANCODE_ESPACO, soltando=False)
    ki = entrada.uniao.ki
    assert ki.wVk == 0
    assert ki.wScan == 0x39
    assert ki.dwFlags == 0x0008  # KEYEVENTF_SCANCODE, sem KEYEVENTF_KEYUP

def test_tecla_esc_solta_usa_scancode_e_marca_keyup():
    entrada = windows._tecla(windows.SCANCODE_ESC, soltando=True)
    ki = entrada.uniao.ki
    assert ki.wVk == 0
    assert ki.wScan == 0x01
    assert ki.dwFlags == 0x000A  # KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP

@pytest.mark.parametrize(
    "pixel, esperado",
    [((0, 0), (0, 0)), ((2559, 1439), (65535, 65535))],
)
def test_clicar_converte_pixel_para_coordenada_absoluta(monkeypatch, pixel, esperado):
    # SendInput absoluto usa 0..65535 sobre a tela virtual, nao pixels.
    # A conversao vive dentro de clicar, que chama _enviar (SendInput de
    # verdade) -- por isso trocamos _enviar por um gravador em vez de
    # mudar o codigo de producao para expor a conversao separadamente.
    chamadas = []
    monkeypatch.setattr(windows, "_enviar", lambda *entradas: chamadas.append(entradas))
    windows.MaoWindows().clicar(*pixel)
    (evento_move,) = chamadas[0]
    assert (evento_move.uniao.mi.dx, evento_move.uniao.mi.dy) == esperado

def test_clicar_move_antes_de_pressionar_e_soltar(monkeypatch):
    chamadas = []
    monkeypatch.setattr(windows, "_enviar", lambda *entradas: chamadas.append(entradas))
    windows.MaoWindows().clicar(100, 200)
    assert len(chamadas) == 2
    (evento_move,) = chamadas[0]
    evento_down, evento_up = chamadas[1]
    assert evento_move.uniao.mi.dwFlags == 0x8001  # MOVE | ABSOLUTE
    assert evento_down.uniao.mi.dwFlags == 0x0002  # LEFTDOWN
    assert evento_up.uniao.mi.dwFlags == 0x0004  # LEFTUP

def test_capturar_converte_bgra_para_bgr():
    # Sem passar pelo __init__ (que exige mss), injetamos um duble de
    # _mss cujo grab devolve um array BGRA sintetico e conferimos que a
    # fatia [:, :, :3] preserva os tres primeiros canais.
    tela = object.__new__(windows.TelaWindows)
    quadro_bgra = np.zeros((2, 2, 4), dtype=np.uint8)
    quadro_bgra[0, 0] = [10, 20, 30, 255]
    quadro_bgra[1, 1] = [40, 50, 60, 128]

    class _MssFalso:
        def grab(self, monitor):
            return quadro_bgra

    tela._mss = _MssFalso()
    tela._monitor = None

    resultado = tela.capturar()

    assert resultado.shape == (2, 2, 3)
    assert list(resultado[0, 0]) == [10, 20, 30]
    assert list(resultado[1, 1]) == [40, 50, 60]
