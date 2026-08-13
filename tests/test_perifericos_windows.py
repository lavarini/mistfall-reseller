import ast
import pathlib

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

def test_usa_scancode_e_nao_virtual_key():
    # Jogos costumam ler scancode de hardware e ignorar tecla virtual.
    texto = FONTE.read_text(encoding="utf-8")
    assert "KEYEVENTF_SCANCODE" in texto
    assert "0x39" in texto  # Espaco
    assert "0x01" in texto  # Esc
