from mistfall.config import Config
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import Desfecho, Ritmo, executar
from mistfall.tipos import ItemAlvo

LISTA = "images/broche-dragao-orbe-codice-padrao.png"
JANELA_DRAGAO = "fixtures/sinteticas/janela-dragao-246.png"
LISTA_DEBITADA = "fixtures/sinteticas/lista-ouro-65914.png"

def cfg():
    return Config(
        precos_alvo={
            ItemAlvo.BROCHE: 188, ItemAlvo.ADAGA: 199, ItemAlvo.LANTERNA: 234,
            ItemAlvo.DRAGAO: 246, ItemAlvo.ORBE: 253, ItemAlvo.REDE: 260,
            ItemAlvo.CODICE: 281,
        },
        fracao_sanidade=0.25,
    )

def roteiro_feliz():
    # pre-voo, apos o clique (modal), apos o Espaco (lista com Ouro debitado)
    return TelaFalsa([LISTA, JANELA_DRAGAO, LISTA_DEBITADA])


JA = Ritmo.instantaneo()  # nenhum teste espera de verdade

def test_caminho_feliz_compra(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.COMPROU

def test_caminho_feliz_clica_no_slot_certo(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA)
    assert mao.acoes[0] == ("clicar", 1975, 721)

def test_caminho_feliz_aperta_espaco_e_nunca_esc(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA)
    nomes = [a[0] for a in mao.acoes]
    assert nomes == ["clicar", "apertar_espaco"]

def test_caminho_feliz_registra_os_numeros(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert r.ouro_antes == 66160
    assert r.ouro_depois == 65914
    assert r.preco_total_esperado == 246
    assert r.listagem.item is ItemAlvo.DRAGAO

def test_caminho_feliz_salva_os_prints(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert len(list(tmp_path.glob("*.png"))) >= 3
    assert (tmp_path / "relatorio.json").exists()


JANELA_ESPELHO = "images/janela.png"          # modal com item que nao e alvo
LISTA_SEM_NADA = "images/lanterna-dragao-orbe-rede.png"  # nada compravel
RESET = "images/reset-forja.png"              # outra Categoria

def test_item_divergente_aperta_esc_e_nunca_espaco(tmp_path):
    # O modal mostra Espelho Adornado; decidimos comprar Dragao.
    mao = MaoFalsa()
    tela = TelaFalsa([LISTA, JANELA_ESPELHO])
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA)
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert nomes[-1] == "apertar_esc"

def test_janela_que_nao_abre_aborta_sem_apertar_nada(tmp_path):
    # A tela nunca vira modal: fica na lista.
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA, LISTA]), mao, cfg(), tmp_path, ritmo=JA)
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert nomes == ["clicar"]
    assert r.segundos_ate_a_janela is not None

def test_nada_compravel_sai_limpo_sem_clicar(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA_SEM_NADA]), mao, cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.NADA_COMPRAVEL
    assert mao.acoes == []

def test_pre_voo_em_outra_categoria_aborta(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([RESET]), mao, cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.ABORTOU
    assert "outra_categoria" in r.motivo
    assert mao.acoes == []

def test_pre_voo_com_modal_aberto_aborta(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([JANELA_ESPELHO]), mao, cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.ABORTOU
    assert mao.acoes == []

def test_modo_simulado_nao_toca_em_nada(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, simular=True, ritmo=JA)
    assert mao.acoes == []
    assert r.listagem.item is ItemAlvo.DRAGAO
    assert r.ouro_antes == 66160

def test_todo_aborto_salva_relatorio(tmp_path):
    executar(TelaFalsa([RESET]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert (tmp_path / "relatorio.json").exists()

def test_ouro_que_cai_valor_inesperado_e_reportado(tmp_path):
    # Depois do Espaco a tela mostra um print real cujo Ouro e 64735, nao
    # os 65914 esperados. A Compra aconteceu, mas a queda nao bate.
    OUTRA_LISTA = "images/broche-tres-adaga-lanterna-rede-padrao.png"  # Ouro 64735
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, OUTRA_LISTA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.COMPROU
    assert r.ouro_depois == 64735
    assert "esperava 246" in r.motivo
