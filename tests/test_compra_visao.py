import subprocess

import cv2
import numpy as np
import pytest

from mistfall.compra_visao import (
    MensagemCompra,
    detectar_mensagem_compra,
    filtro_roxo_ativo,
)


# Prints reais da aba Comprar. Vivem em `images/` — e nao na pasta de uma
# sessao de execucao — porque sao a unica prova de que `MensagemCompra.SUCESSO`
# funciona, e esse detector e o sinal primario de confirmacao de Compra do
# coordenador do fluxo completo.
COMPRA_REALIZADA = "images/compra-realizada.png"
LISTA_SEM_TOAST = "images/lista-sem-toast.png"
SEM_FILTRO = "images/sem-filtro.png"


def _imagem(caminho: str):
    imagem = cv2.imread(caminho)
    assert imagem is not None
    return imagem


def test_detecta_toast_de_inventario_cheio():
    # Trocar a classificacao dessa mensagem por SUCESSO faria a Compra seguir
    # como se o item tivesse sido guardado, apesar do Inventario estar cheio.
    assert (
        detectar_mensagem_compra(_imagem("images/cheio-2.png"))
        is MensagemCompra.INVENTARIO_CHEIO
    )


def test_detecta_toast_de_compra_realizada():
    # Sem esta classificacao, uma compra concluida fica indistinguivel de uma
    # tentativa que ainda nao respondeu.
    assert (
        detectar_mensagem_compra(
            _imagem(COMPRA_REALIZADA)
        )
        is MensagemCompra.SUCESSO
    )


def test_lista_sem_toast_nao_tem_mensagem_de_compra():
    assert (
        detectar_mensagem_compra(_imagem(LISTA_SEM_TOAST))
        is MensagemCompra.NENHUMA
    )


def test_regiao_central_clara_sem_palavra_de_toast_nao_e_mensagem_de_compra():
    sem_toast = _imagem(LISTA_SEM_TOAST)
    sem_toast[345:385, 950:1800] = 255

    assert detectar_mensagem_compra(sem_toast) is MensagemCompra.NENHUMA


def test_detecta_filtro_roxo_e_recusa_variante_sem_icone_roxo():
    com_filtro = _imagem("images/cheio-2.png")
    sem_filtro = com_filtro.copy()
    sem_filtro[205:255, 775:825] = com_filtro[205:255, 735:785]

    assert filtro_roxo_ativo(com_filtro)
    assert not filtro_roxo_ativo(sem_filtro)


def test_as_fixtures_do_toast_de_compra_estao_versionadas():
    # Num clone limpo, ou em CI, um PNG que so existe nesta maquina faz os
    # tres testes acima morrerem no `assert imagem is not None`. `git
    # ls-files` e a unica pergunta que distingue os dois casos.
    for caminho in (COMPRA_REALIZADA, LISTA_SEM_TOAST, SEM_FILTRO):
        conferencia = subprocess.run(
            ["git", "ls-files", "--error-unmatch", caminho],
            capture_output=True,
        )
        assert conferencia.returncode == 0, f"{caminho} nao esta versionado"


def test_filtro_roxo_recusa_resolucao_fora_do_padrao():
    # ADR-0002: a deteccao e acoplada a 2560x1440. Sem o guardrail o recorte
    # sai vazio, `.mean()` devolve `nan` e a funcao responde `False` — uma
    # falha silenciosa que faria o fluxo clicar no filtro para sempre.
    with pytest.raises(ValueError, match="2560x1440"):
        filtro_roxo_ativo(np.zeros((1080, 1920, 3), dtype=np.uint8))


def test_filtro_roxo_desligado_na_tela_real():
    # O losango roxo selecionado ganha borda branca e um tique dourado por
    # cima. Medir "quanto roxo ha na caixa" le o sinal ao contrario: com o
    # filtro LIGADO o roxo cai (0.053), porque a marca o cobre; com ele
    # DESLIGADO o losango fica cheio de roxo (0.116). O detector antigo
    # respondia True nos dois estados, entao o filtro nunca era clicado.
    sem_filtro = cv2.imread("images/sem-filtro.png")
    assert sem_filtro is not None
    assert not filtro_roxo_ativo(sem_filtro)


def test_filtro_roxo_ligado_continua_detectado():
    com_filtro = cv2.imread("images/broche-tres-dragao-padrao.png")
    assert com_filtro is not None
    assert filtro_roxo_ativo(com_filtro)
