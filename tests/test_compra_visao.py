import cv2

from mistfall.compra_visao import (
    MensagemCompra,
    detectar_mensagem_compra,
    filtro_roxo_ativo,
)


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
            _imagem("sessao/volta-0001/01-apos-espaco.png")
        )
        is MensagemCompra.SUCESSO
    )


def test_lista_sem_toast_nao_tem_mensagem_de_compra():
    assert (
        detectar_mensagem_compra(_imagem("sessao/volta-0001/00-pre-voo.png"))
        is MensagemCompra.NENHUMA
    )


def test_detecta_filtro_roxo_e_recusa_variante_sem_icone_roxo():
    com_filtro = _imagem("images/cheio-2.png")
    sem_filtro = com_filtro.copy()
    sem_filtro[205:255, 775:825] = com_filtro[205:255, 735:785]

    assert filtro_roxo_ativo(com_filtro)
    assert not filtro_roxo_ativo(sem_filtro)
