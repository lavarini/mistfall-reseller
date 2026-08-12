import cv2
import numpy as np
from mistfall.geometria import conferir_resolucao
from mistfall.tipos import EstadoTela

REGIAO_CENTRO = (900, 500, 1700, 950)

# Exatamente a linha "Material de Construcao" do menu lateral, e mais nada.
#
# A regiao anterior era (80, 380, 360, 720): 340 linhas, das quais so as 60 de
# baixo carregavam sinal (delta 36 pontos em y 690-720, exatamente 0.00 acima de
# y 660). A media dizia "existe alguma linha destacada nessa faixa", nao "qual
# Categoria esta selecionada". Medido colando o destaque de reset-forja.png em
# outra linha do menu: destaque na linha de y 592 dava menu=37.33 e destaque na
# de y 520 dava 36.97 — ambos dentro da faixa de Material de Construcao, ou
# seja, LISTA. Forja e Chave so acertavam por cairem fora da faixa; as vizinhas
# imediatas de Material de Construcao, que sao as escolhas naturais do Reset,
# davam falso LISTA e o bot acharia que ja tinha voltado.
#
# Perfil vertical medido: o bloco da linha vai de y 664 a y 732 (destaque com
# pico em y 700-710); a de cima termina em 660 e a de baixo, Material de Forja,
# comeca em 736. O recorte horizontal 80-360 e o de melhor separacao medida
# (delta 24.5, razao 1.83); esticar ate x 440, onde o destaque ainda alcanca,
# piora para delta 20.4.
REGIAO_MENU = (80, 664, 360, 732)

# Brilho medio de REGIAO_MENU medido nos dez prints:
#   7 prints de lista ........ 53.99  (Material de Construcao com destaque)
#   reset-forja, reset-chave . 29.45  (Material de Construcao sem destaque)
#   janela ................... 26.60  (o modal escurece a tela inteira)
# Os 7 prints de lista sao byte-identicos nessa regiao, entao sao 3 amostras
# distintas, nao 10 — por isso os testes tambem usam prints sinteticos.
#
# Brilho medio de REGIAO_CENTRO nos mesmos prints: lista 12.1-13.3, reset
# 11.5-13.0, janela 4.95.

# Cada estado exige evidencia positiva em ambas as regioes.
# Janela de Confirmacao escurece o centro para 4.95 e o menu para 26.60.
CENTRO_JANELA_MAX = 8.0
MENU_JANELA = (20.0, 34.0)

# Lista: centro normal, menu com o destaque de Material de Construcao.
CENTRO_LISTA = (9.0, 18.0)
MENU_MATERIAL = (45.0, 62.0)

# Outra Categoria: centro normal, menu sem o destaque nessa linha.
# 26.60 (janela) e 29.45 (reset) ficam a 2.85 um do outro, entao MENU_JANELA e
# MENU_OUTRA_CATEGORIA se sobrepoem — o menu nao separa esses dois. Quem separa
# e REGIAO_CENTRO (4.95 contra 11.5-13.0), e por isso a Janela e testada antes.
MENU_OUTRA_CATEGORIA = (24.0, 36.0)

def _brilho(img: np.ndarray, regiao: tuple[int, int, int, int]) -> float:
    x0, y0, x1, y1 = regiao
    return float(cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).mean())

def _dentro_faixa(valor: float, faixa: tuple[float, float]) -> bool:
    return faixa[0] <= valor <= faixa[1]

def identificar_estado(img: np.ndarray) -> EstadoTela:
    # Resolucao errada e erro, nao DESCONHECIDO: DESCONHECIDO significa "tela
    # 2560x1440 que nao reconheci", e o guardrail conta essas telas.
    conferir_resolucao(img)
    centro = _brilho(img, REGIAO_CENTRO)
    menu = _brilho(img, REGIAO_MENU)

    # Janela de Confirmacao: centro muito escuro E menu numa faixa intermediaria.
    if centro < CENTRO_JANELA_MAX and _dentro_faixa(menu, MENU_JANELA):
        return EstadoTela.JANELA_CONFIRMACAO

    # Lista: centro normal E menu muito claro (Material de Construcao).
    if _dentro_faixa(centro, CENTRO_LISTA) and _dentro_faixa(menu, MENU_MATERIAL):
        return EstadoTela.LISTA

    # Outra Categoria: centro normal E menu moderado.
    if _dentro_faixa(centro, CENTRO_LISTA) and _dentro_faixa(menu, MENU_OUTRA_CATEGORIA):
        return EstadoTela.OUTRA_CATEGORIA

    # Qualquer outra combinacao: desconhecido.
    return EstadoTela.DESCONHECIDO
