import glob
import json
import pathlib
import cv2
import pytest
from mistfall.leilao import varrer

CASOS = sorted(glob.glob("fixtures/esperado/*.json"))

def _compara_slots(nome_print, esperado_slots, obtido_slots):
    """Compara slots respeitando gaps conhecidos de OCR (ocr_lido_atual).

    Retorna lista de erros encontrados, ou lista vazia se tudo bater.
    Cada erro é uma tupla (print, slot_id, mensagem).
    """
    erros = []

    if len(obtido_slots) != len(esperado_slots):
        erros.append((
            nome_print,
            "[contagem desalinhada]",
            f"corpus e varredura divergem em contagem: esperado {len(esperado_slots)} slots, obtido {len(obtido_slots)}"
        ))
        return erros

    for obtido, esperado in zip(obtido_slots, esperado_slots):
        linha_esp = esperado.get("linha")
        coluna_esp = esperado.get("coluna")
        slot_id = f"({linha_esp},{coluna_esp})"

        # Comparar posição (linha/coluna) antes de qualquer outro campo.
        # Se divergir, o corpus está desalinhado com a varredura — erro crítico.
        linha_obt = obtido.get("linha")
        coluna_obt = obtido.get("coluna")
        if linha_obt != linha_esp or coluna_obt != coluna_esp:
            erros.append((
                nome_print,
                slot_id,
                f"corpus desalinhado: esperado slot ({linha_esp},{coluna_esp}), "
                f"mas varredura forneceu ({linha_obt},{coluna_obt}) nesta posição"
            ))
            # Continua verificando, pois há outras falhas neste mesmo slot
            continue

        # Item é sempre comparado exato — nenhuma exceção
        if obtido.get("item") != esperado.get("item"):
            erros.append((
                nome_print,
                slot_id,
                f"item diverge: esperado {esperado.get('item')!r}, obtido {obtido.get('item')!r}"
            ))

        # Preço tem duas regras
        tem_ocr_gap = "ocr_lido_atual" in esperado
        if tem_ocr_gap:
            # Gap conhecido: compare obtido contra ocr_lido_atual (a falha atual)
            gap_value = esperado["ocr_lido_atual"]
            if obtido.get("preco_unitario") != gap_value:
                erros.append((
                    nome_print,
                    slot_id,
                    f"preço divergiu do gap conhecido: esperado leitura {gap_value!r}, obtido {obtido.get('preco_unitario')!r} "
                    f"(verdade humana é {esperado.get('preco_unitario')}; gap pode ter sido corrigido ou piorou)"
                ))
        else:
            # Sem gap: compare contra preco_unitario (a verdade)
            if obtido.get("preco_unitario") != esperado.get("preco_unitario"):
                erros.append((
                    nome_print,
                    slot_id,
                    f"preço diverge: esperado {esperado.get('preco_unitario')}, obtido {obtido.get('preco_unitario')}"
                ))

    return erros

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

    erros = _compara_slots(nome, esperado, obtido)
    if erros:
        msg_erros = "\n".join(f"  {print_nome} slot {slot_id}: {msg}" for print_nome, slot_id, msg in erros)
        raise AssertionError(f"Detecção divergiu do corpus:\n{msg_erros}")

def test_o_corpus_nao_esta_vazio():
    assert len(CASOS) >= 7

def test_corpus_tem_gaps_conhecidos_de_ocr():
    """Afirma quantos slots carregam falha de OCR conhecida.

    Se alguém adicionar um gap novo sem perceber, ou fechar um gap,
    esse número muda e o teste avisa que o corpus precisa reavaliação.
    """
    total_gaps = 0
    for caminho in CASOS:
        slots = json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))["slots"]
        total_gaps += sum(1 for slot in slots if "ocr_lido_atual" in slot)

    assert total_gaps == 5, (
        f"Corpus tem {total_gaps} slots com ocr_lido_atual, esperado 5. "
        "Se um gap foi fechado (OCR melhorou), remova o campo e confira o corpus. "
        "Se um gap novo apareceu, adicione ocr_lido_atual ao JSON e reavalie."
    )
