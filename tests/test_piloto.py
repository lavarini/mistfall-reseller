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
