import os
import subprocess
import sys

def _ambiente_limpo() -> dict[str, str]:
    """Sem PYTHONPATH: senao o teste passa por heranca do shell e nao por
    o pacote estar instalado."""
    return {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

def test_mistfall_importa_de_fora_da_raiz(tmp_path):
    # Roda de um diretorio qualquer, sem PYTHONPATH: se o pacote estiver
    # instalado, importa; se depender do CWD, quebra.
    r = subprocess.run(
        [sys.executable, "-c", "import mistfall.geometria as g; print(g.RESOLUCAO)"],
        cwd=tmp_path, capture_output=True, text=True, env=_ambiente_limpo(),
    )
    assert r.returncode == 0, r.stderr
    assert "(2560, 1440)" in r.stdout

def test_templates_sao_encontrados_de_fora_da_raiz(tmp_path):
    r = subprocess.run(
        [sys.executable, "-c",
         "from mistfall.itens import _templates; print(len(_templates()))"],
        cwd=tmp_path, capture_output=True, text=True, env=_ambiente_limpo(),
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "7"

def test_piloto_cli_importa_de_fora_da_raiz(tmp_path):
    # ferramentas/ tem de estar empacotado junto com mistfall/, senao o
    # comando mistfall-piloto quebra assim que instalado fora do repositorio
    # (que e exatamente onde ele vai rodar, numa maquina Windows qualquer).
    r = subprocess.run(
        [sys.executable, "-c", "import ferramentas.piloto_cli"],
        cwd=tmp_path, capture_output=True, text=True, env=_ambiente_limpo(),
    )
    assert r.returncode == 0, r.stderr


def test_o_entry_point_do_bot_existe():
    import tomllib, pathlib
    dados = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
    assert dados["project"]["scripts"]["mistfall-bot"] == "ferramentas.bot_cli:main"
