import numpy as np
import pytest
from mistfall.geometria import (
    caixa_slot, conferir_resolucao, regiao_icone, recorte_preco,
    TODOS_OS_SLOTS, RESOLUCAO,
    CATEGORIA_CHAVE, CATEGORIA_MATERIAL_CONSTRUCAO, CATEGORIA_MATERIAL_FORJA,
    area_clique_categoria, area_clique_slot,
)

def test_existem_doze_slots():
    assert len(TODOS_OS_SLOTS) == 12

def test_primeiro_slot_comeca_nas_constantes_medidas():
    x0, y0, x1, y1 = caixa_slot(0, 0)
    assert (x0, y0) == (459, 287)

def test_colunas_nao_se_sobrepoem():
    esquerda = caixa_slot(0, 0)
    direita = caixa_slot(0, 1)
    assert esquerda[2] <= direita[0]

def test_linhas_avancam_pelo_passo_medido():
    topos = [caixa_slot(i, 0)[1] for i in range(6)]
    passos = [b - a for a, b in zip(topos, topos[1:])]
    assert all(178 <= p <= 179 for p in passos), passos

def test_todos_os_slots_cabem_na_resolucao():
    largura, altura = RESOLUCAO
    for linha, coluna in TODOS_OS_SLOTS:
        x0, y0, x1, y1 = caixa_slot(linha, coluna)
        assert 0 <= x0 < x1 <= largura
        assert 0 <= y0 < y1 <= altura

def test_recortes_tem_o_tamanho_medido():
    img = np.zeros((1440, 2560, 3), dtype=np.uint8)
    assert regiao_icone(img, 0, 0).shape[:2] == (116, 128)
    assert recorte_preco(img, 0, 0).shape[:2] == (45, 80)

def test_recorte_rejeita_resolucao_errada():
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        regiao_icone(img, 0, 0)

def test_conferir_resolucao_aceita_a_resolucao_medida():
    # Literal escrito a mao: 2560 de largura por 1440 de altura, nessa ordem.
    conferir_resolucao(np.zeros((1440, 2560, 3), dtype=np.uint8))

def test_categorias_vizinhas_mantem_x_e_avancam_72_px():
    x_construcao, y_construcao = CATEGORIA_MATERIAL_CONSTRUCAO
    x_forja, y_forja = CATEGORIA_MATERIAL_FORJA
    assert x_construcao == x_forja == 220
    assert y_construcao == 705
    assert y_forja - y_construcao == 72
    assert CATEGORIA_CHAVE == (220, 849)

@pytest.mark.parametrize("largura,altura", [(3840, 2160), (1920, 1080), (1440, 2560)])
def test_conferir_resolucao_recusa_qualquer_outra(largura, altura):
    # (1440, 2560) na lista de proposito: e a resolucao certa com largura e
    # altura trocadas, e tambem tem de ser recusada.
    img = np.zeros((altura, largura, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match=f"recebi {largura}x{altura}"):
        conferir_resolucao(img)


def test_area_de_clique_do_slot_fica_ao_redor_do_centro():
    x0, y0, x1, y1 = caixa_slot(2, 1)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    assert area_clique_slot(2, 1) == (cx - 20, cy - 26, cx + 20, cy + 26)


@pytest.mark.parametrize(
    "centro",
    [CATEGORIA_MATERIAL_CONSTRUCAO, CATEGORIA_MATERIAL_FORJA, CATEGORIA_CHAVE],
)
def test_area_de_clique_da_categoria_fica_ao_redor_do_centro(centro):
    cx, cy = centro
    assert area_clique_categoria(centro) == (
        cx - 60, cy - 18, cx + 60, cy + 18,
    )
