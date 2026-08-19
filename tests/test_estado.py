import glob
import pathlib
import cv2
import numpy as np
import pytest
from mistfall.estado import identificar_estado
from mistfall.tipos import EstadoTela

# Estado esperado de cada um dos onze prints, escrito a mao. O teste anterior
# varria images/*.png e so afirmava "nenhum e DESCONHECIDO": os sete prints de
# lista poderiam todos virar OUTRA_CATEGORIA que ele passava.
ESTADO_ESPERADO = {
    "adaga-tres-broche-dois-lanterna-rede-padrao": EstadoTela.LISTA,
    "broche-dragao-orbe-codice-padrao": EstadoTela.LISTA,
    "broche-tres-adaga-lanterna-rede-padrao": EstadoTela.LISTA,
    "broche-tres-dragao-padrao": EstadoTela.LISTA,
    "cheio-1": EstadoTela.LISTA,
    "cheio-2": EstadoTela.LISTA,
    "cheio-3": EstadoTela.LISTA,
    "dragao-um-rede-padrao": EstadoTela.LISTA,
    "lanterna-dragao-orbe-rede": EstadoTela.LISTA,
    "rede-dois-dragao-padrao": EstadoTela.LISTA,
    # Primeira captura vinda da maquina do jogo, e nao do corpus montado a mao.
    "sete-itens-ocr-227-como-297": EstadoTela.LISTA,
    "janela": EstadoTela.JANELA_CONFIRMACAO,
    # Capturada no meio da animacao de abertura: o modal esta 69 px acima da
    # posicao final, e por isso os tres campos numericos caem sobre fundo
    # vazio. O estado ja e reconhecivel — e justamente esse o problema.
    "janela-em-animacao-rede-260": EstadoTela.JANELA_CONFIRMACAO,
    "reset-forja": EstadoTela.OUTRA_CATEGORIA,
    "reset-chave": EstadoTela.OUTRA_CATEGORIA,
    "venda-stash-2": EstadoTela.VENDA,
    "venda-stash-3": EstadoTela.VENDA,
    "tela-venda-resgatar": EstadoTela.VENDA,
    "modal-venda-broche": EstadoTela.JANELA_VENDA,
    "modal-venda-resgatar": EstadoTela.JANELA_VENDA,
    "loading-modal-venda": EstadoTela.JANELA_VENDA,
}

@pytest.mark.parametrize("nome,esperado", sorted(ESTADO_ESPERADO.items()))
def test_classifica_a_tela(nome, esperado):
    assert identificar_estado(cv2.imread(f"images/{nome}.png")) is esperado

def test_todo_print_do_corpus_tem_estado_declarado():
    # Sem isto, um print novo entraria em images/ sem ninguem dizer o que ele e,
    # e o teste acima continuaria verde por nao saber que ele existe.
    do_disco = {pathlib.Path(c).stem for c in glob.glob("images/*.png")}
    assert do_disco == set(ESTADO_ESPERADO)

def test_todos_os_estados_reconheciveis_aparecem_no_corpus():
    # O teste antigo se chamava "mutuamente exclusivos" e nao verificava nada
    # disso. O que da para afirmar de verdade e que o corpus exercita os tres.
    assert set(ESTADO_ESPERADO.values()) == {
        EstadoTela.LISTA,
        EstadoTela.JANELA_CONFIRMACAO,
        EstadoTela.OUTRA_CATEGORIA,
        EstadoTela.VENDA,
        EstadoTela.JANELA_VENDA,
    }

# --- destaque na linha errada do menu -----------------------------------------
#
# A regiao de menu antiga tinha 340 linhas e media "existe alguma linha destacada
# aqui", nao "qual Categoria esta selecionada". Estes prints sinteticos movem o
# destaque de reset-forja.png para linhas vizinhas de Material de Construcao —
# justamente as Categorias que o Reset escolheria — e cobram OUTRA_CATEGORIA.
#
# Faixa de origem do destaque em reset-forja.png: y 736-804 (Material de Forja).
DESTAQUE_ORIGEM = (736, 804)

def _com_destaque_na_linha(y_destino: int) -> np.ndarray:
    forja = cv2.imread("images/reset-forja.png")
    y0, y1 = DESTAQUE_ORIGEM
    sintetico = forja.copy()
    sintetico[y_destino : y_destino + (y1 - y0), 80:460] = forja[y0:y1, 80:460]
    return sintetico

@pytest.mark.parametrize("y_destino", [592, 520, 448])
def test_destaque_em_outra_linha_do_menu_nao_e_lista(y_destino):
    # Medido com a regiao antiga (80, 380, 360, 720): y 592 dava menu=37.33 e
    # y 520 dava 36.97, ambos dentro de MENU_MATERIAL — LISTA, errado. O bot
    # acharia que ja tinha voltado para Material de Construcao.
    assert identificar_estado(_com_destaque_na_linha(y_destino)) is EstadoTela.OUTRA_CATEGORIA

def test_reset_forja_intacto_continua_outra_categoria():
    # Contraprova do teste acima: a imagem de origem, sem nenhuma colagem.
    assert identificar_estado(cv2.imread("images/reset-forja.png")) is EstadoTela.OUTRA_CATEGORIA

# --- telas que nao sao o Leilao -----------------------------------------------

@pytest.mark.parametrize("valor", [0, 128, 255])
def test_imagem_de_cor_chapada_e_desconhecida(valor):
    img = np.full((1440, 2560, 3), valor, dtype=np.uint8)
    assert identificar_estado(img) is EstadoTela.DESCONHECIDO

@pytest.mark.parametrize("largura,altura", [(3840, 2160), (1920, 1080)])
def test_recusa_resolucao_diferente_em_vez_de_dizer_desconhecido(largura, altura):
    # DESCONHECIDO significa "tela 2560x1440 que nao reconheci", e o guardrail
    # conta essas telas. Resolucao errada e outra coisa, e e erro (ADR-0002).
    img = np.zeros((altura, largura, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2560x1440"):
        identificar_estado(img)
