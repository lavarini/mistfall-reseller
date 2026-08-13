import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

def test_mistfall_importa_de_fora_da_raiz(tmp_path):
    # Roda de um diretorio qualquer, sem PYTHONPATH: se o pacote estiver
    # instalado, importa; se depender do CWD, quebra.
    r = subprocess.run(
        [sys.executable, "-c", "import mistfall.geometria as g; print(g.RESOLUCAO)"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "(2560, 1440)" in r.stdout

def test_templates_sao_encontrados_de_fora_da_raiz(tmp_path):
    r = subprocess.run(
        [sys.executable, "-c",
         "from mistfall.itens import _templates; print(len(_templates()))"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "7"
