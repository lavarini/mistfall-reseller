import dataclasses
import json
import random
from dataclasses import replace

import cv2
import pytest

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
    )

def roteiro_feliz():
    # pre-voo, apos o clique (modal), apos o Espaco (lista com Ouro debitado)
    return TelaFalsa([LISTA, JANELA_DRAGAO, LISTA_DEBITADA])


JA = Ritmo.instantaneo()  # nenhum teste espera de verdade

def test_caminho_feliz_compra(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPROU

def test_caminho_feliz_clica_no_slot_certo(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert mao.acoes[0] == ("clicar", 1975, 721)

def test_caminho_feliz_aperta_espaco_e_nunca_esc(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert nomes == ["clicar", "apertar_espaco"]

def test_caminho_feliz_registra_os_numeros(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert r.ouro_antes == 66160
    assert r.ouro_depois == 65914
    assert r.preco_total_esperado == 246
    assert r.listagem.item is ItemAlvo.DRAGAO

def test_caminho_feliz_salva_os_prints(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert len(list(tmp_path.glob("*.png"))) >= 3
    assert (tmp_path / "relatorio.json").exists()


JANELA_ESPELHO = "images/janela.png"          # modal com item que nao e alvo
LISTA_SEM_NADA = "images/lanterna-dragao-orbe-rede.png"  # nada compravel
RESET = "images/reset-forja.png"              # outra Categoria

def test_icone_e_preco_divergentes_aborta_pelo_preco(tmp_path):
    # O modal mostra Espelho Adornado (nao e Item-alvo) cobrando 237;
    # decidimos comprar Dragao a 246. Diverge nos dois, mas o icone deixou
    # de ser portao — quem aborta agora e o Preco Unitario.
    mao = MaoFalsa()
    tela = TelaFalsa([LISTA, JANELA_ESPELHO])
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert nomes[-1] == "apertar_esc"
    assert "modal cobra" in r.motivo

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
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, simular=True, ritmo=JA, sorteio=random.Random(1))
    assert mao.acoes == []
    assert r.listagem.item is ItemAlvo.DRAGAO
    assert r.ouro_antes == 66160

def test_modo_simulado_tem_desfecho_proprio(tmp_path):
    # Nao pode ser nada_compravel: o roteiro usa esse desfecho como portao
    # ("se nao bater, pare aqui"), e a simulacao ACHOU uma Listagem.
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, simular=True, ritmo=JA, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.SIMULOU
    assert r.desfecho is not Desfecho.NADA_COMPRAVEL

def test_todo_aborto_salva_relatorio(tmp_path):
    executar(TelaFalsa([RESET]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert (tmp_path / "relatorio.json").exists()

JANELA_DRAGAO_999 = "fixtures/sinteticas/janela-dragao-999.png"
JANELA_DRAGAO_QTD_5 = "fixtures/sinteticas/janela-dragao-246-qtd-5.png"
JANELA_ORBE_246 = "fixtures/sinteticas/janela-orbe-246.png"

def test_preco_divergente_isolado_aperta_esc_e_nunca_espaco(tmp_path):
    # Item bate (Dragao), so o Preco Unitario diverge (999 contra 246).
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA, JANELA_DRAGAO_999]), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert "apertar_esc" in nomes
    assert "modal cobra" in r.motivo

def test_quantidade_divergente_isolada_aperta_esc_e_nunca_espaco(tmp_path):
    # Item e Preco Unitario batem, so a Quantidade diverge (5 em vez de 1).
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA, JANELA_DRAGAO_QTD_5]), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert "apertar_esc" in nomes
    assert "Quantidade e" in r.motivo

def test_icone_divergente_nao_impede_a_compra(tmp_path):
    # Preco Unitario, Quantidade e Preco Total batem (246, 1, 246); so o
    # Icone diverge (Orbe em vez de Dragao). O icone saiu do portao: o
    # piloto segue, aperta Espaco e conclui a Compra.
    mao = MaoFalsa()
    tela = TelaFalsa([LISTA, JANELA_ORBE_246, LISTA_DEBITADA])
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert "apertar_esc" not in nomes
    assert "apertar_espaco" in nomes
    assert r.desfecho is Desfecho.COMPROU

def test_ouro_que_cai_valor_inesperado_e_reportado(tmp_path):
    # Depois do Espaco a tela mostra um print real cujo Ouro e 64735, nao
    # os 65914 esperados. A Compra aconteceu, mas a queda nao bate.
    OUTRA_LISTA = "images/broche-tres-adaga-lanterna-rede-padrao.png"  # Ouro 64735
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, OUTRA_LISTA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPROU
    assert r.ouro_depois == 64735
    assert "esperava 246" in r.motivo


# ---------------------------------------------------------------------------
# Leitura ilegivel dentro da Janela: cada campo apagado em sua propria fixture.
# Sem uma fixture por campo, apagar a conferencia inteira nao derruba teste
# nenhum — e o bot aperta Espaco sem saber o que esta comprando.

JANELA_PRECO_ILEGIVEL = "fixtures/sinteticas/janela-dragao-preco-ilegivel.png"
JANELA_QTD_ILEGIVEL = "fixtures/sinteticas/janela-dragao-quantidade-ilegivel.png"
JANELA_TOTAL_ILEGIVEL = "fixtures/sinteticas/janela-dragao-total-ilegivel.png"
JANELA_ESPELHO_246 = "fixtures/sinteticas/janela-espelho-246.png"
JANELA_TOTAL_250 = "fixtures/sinteticas/janela-dragao-246-total-250.png"
LISTA_OURO_ILEGIVEL = "fixtures/sinteticas/lista-ouro-ilegivel.png"

@pytest.mark.parametrize("fixture, pedaco_do_motivo", [
    (JANELA_PRECO_ILEGIVEL, "Preco Unitario ilegivel"),
    (JANELA_QTD_ILEGIVEL, "Quantidade ilegivel"),
    (JANELA_TOTAL_ILEGIVEL, "Preco Total ilegivel"),
    # Total que nao fecha com 1 x Preco Unitario.
    (JANELA_TOTAL_250, "nao fecha"),
])
def test_leitura_suspeita_no_modal_aperta_esc_e_nunca_espaco(
        tmp_path, fixture, pedaco_do_motivo):
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA, fixture]), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.ABORTOU
    assert "apertar_espaco" not in nomes
    assert nomes[-1] == "apertar_esc"
    assert pedaco_do_motivo in r.motivo, r.motivo

def test_ouro_inicial_ilegivel_aborta_antes_de_clicar(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA_OURO_ILEGIVEL]), mao, cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.ABORTOU
    assert "Ouro inicial ilegivel" in r.motivo
    assert mao.acoes == []

# ---------------------------------------------------------------------------
# Confirmacao pelo Ouro.

ESPERA_DE_VERDADE = replace(JA, teto_espera_ouro=1.0)

def test_ouro_ainda_nao_debitado_continua_esperando(tmp_path):
    # O frame logo apos o Espaco ainda mostra o Ouro antigo (o jogo debita
    # com atraso); o seguinte ja mostra o debito. Quem para na primeira
    # leitura legivel reporta Compra com queda zero.
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, LISTA, LISTA_DEBITADA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path, ritmo=ESPERA_DE_VERDADE, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPROU
    assert r.ouro_depois == 65914
    assert r.motivo == ""

def test_ouro_que_nunca_se_move_nao_e_compra(tmp_path):
    # Espaco apertado e o Ouro parado ate o teto: e "o Espaco nao registrou",
    # que e a pergunta numero 1 da viagem. Nao pode sair como COMPROU.
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, LISTA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path, ritmo=ESPERA_DE_VERDADE, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.OURO_NAO_CAIU
    assert r.desfecho is not Desfecho.COMPROU
    assert r.ouro_antes == 66160
    assert r.ouro_depois == 66160


# ---------------------------------------------------------------------------
# O relatorio e o produto desta branch.

class TelaQueExplodeDepoisDoPrimeiroFrame:
    """Serve a lista e depois estoura, como um mss que morre no meio."""

    def __init__(self) -> None:
        self.capturas = 0

    def capturar(self):
        self.capturas += 1
        if self.capturas > 1:
            raise RuntimeError("mss caiu")
        return cv2.imread(LISTA)

def test_excecao_depois_do_clique_ainda_escreve_o_relatorio(tmp_path):
    mao = MaoFalsa()
    with pytest.raises(RuntimeError):
        executar(TelaQueExplodeDepoisDoPrimeiroFrame(), mao, cfg(), tmp_path,
                 ritmo=JA)
    assert [a[0] for a in mao.acoes] == ["clicar"]  # o bot ja mexeu no jogo
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "abortou"
    assert "explodiu" in dados["motivo"]
    assert "mss caiu" in dados["motivo"]

def test_relatorio_guarda_o_que_o_modal_mostrava_mesmo_abortando(tmp_path):
    executar(TelaFalsa([LISTA, JANELA_ESPELHO_246]), MaoFalsa(), cfg(),
             tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "abortou"
    assert dados["item_no_modal"] is None
    assert dados["preco_no_modal"] == 246
    assert dados["quantidade_no_modal"] == 1
    assert dados["preco_total_esperado"] == 246

def test_relatorio_guarda_os_sete_scores_do_icone(tmp_path):
    # Aborto por icone e o desfecho mais provavel da execucao no Windows, e
    # sem os scores o operador volta so com "o modal mostra None".
    executar(TelaFalsa([LISTA, JANELA_ESPELHO_246]), MaoFalsa(), cfg(),
             tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert set(dados["scores_do_icone"]) == {
        "broche", "adaga", "lanterna", "orbe", "dragao", "rede", "codice"}
    assert all(0.0 <= s <= 1.0 for s in dados["scores_do_icone"].values())
    assert 0.85 <= dados["escala_do_icone"] <= 1.15

def test_relatorio_guarda_os_doze_slots_mesmo_sem_nada_compravel(tmp_path):
    # O desfecho nada_compravel era o mais opaco de todos: dizia que nao havia
    # Listagem abaixo do Preco-alvo e nao dizia o que tinha lido para concluir
    # isso. Sem os slots, diagnosticar exige reprocessar o PNG a mao.
    executar(TelaFalsa([LISTA_SEM_NADA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "nada_compravel"
    assert len(dados["slots"]) == 12
    assert [(s["linha"], s["coluna"]) for s in dados["slots"]] == [
        (linha, coluna) for linha in range(6) for coluna in range(2)]


def test_a_varredura_repassa_os_trabalhadores_configurados_ao_helper(monkeypatch, tmp_path):
    # Achado do review final: config.trabalhadores ficava pelo caminho entre a
    # Config e varrer_bruto, entao a varredura sempre corria com o padrao (4)
    # mesmo com trabalhadores=1 configurado como saida de emergencia. Este
    # espiao fica em mistfall.leilao, que e onde varrer_bruto de fato chama
    # mapear — nao em mistfall.piloto, que so espiona as leituras do modal.
    import mistfall.leilao as leilao
    from mistfall.paralelo import mapear as mapear_real

    recebidos = []

    def espiao(funcao, itens, trabalhadores):
        recebidos.append(trabalhadores)
        return mapear_real(funcao, itens, trabalhadores)

    monkeypatch.setattr(leilao, "mapear", espiao)
    config = dataclasses.replace(cfg(), trabalhadores=7)  # nem 4 (padrao), nem 1
    executar(TelaFalsa([LISTA_SEM_NADA]), MaoFalsa(), config, tmp_path, ritmo=JA)
    assert 7 in recebidos, f"trabalhadores configurado (7) nao chegou ao helper: {recebidos}"


def test_as_leituras_do_modal_passam_pelo_helper_de_paralelismo(monkeypatch, tmp_path):
    # Sem isto o teste de equivalencia abaixo passaria trivialmente: as tres
    # leituras sequenciais dao o mesmo resultado que as paralelas, entao so
    # comparar resultado nao prova que o helper entrou no caminho.
    import mistfall.piloto as piloto
    from mistfall.paralelo import mapear as mapear_real

    chamadas = []

    def espiao(funcao, itens, trabalhadores):
        itens = list(itens)
        chamadas.append(len(itens))
        return mapear_real(funcao, itens, trabalhadores)

    monkeypatch.setattr(piloto, "mapear", espiao)
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert 3 in chamadas, "as tres leituras do modal nao passaram pelo mapear"

def test_conferencia_do_modal_bate_entre_paralelo_e_sequencial(tmp_path):
    def rodar(trabalhadores, pasta):
        config = dataclasses.replace(cfg(), trabalhadores=trabalhadores)
        return executar(roteiro_feliz(), MaoFalsa(), config, pasta, ritmo=JA, sorteio=random.Random(1))
    um = rodar(1, tmp_path / "um")
    quatro = rodar(4, tmp_path / "quatro")
    assert (um.item_no_modal, um.preco_no_modal, um.quantidade_no_modal,
            um.preco_total_esperado) == (
           quatro.item_no_modal, quatro.preco_no_modal, quatro.quantidade_no_modal,
           quatro.preco_total_esperado)
    assert um.desfecho is quatro.desfecho

def test_relatorio_mostra_o_preco_bruto_que_a_conferencia_derrubou(tmp_path):
    # A regra de ordenacao e contagiosa de proposito: uma leitura fora de ordem
    # invalida os vizinhos. Guardar so o preco conferido deixaria o relatorio
    # cheio de null sem dizer qual numero causou a queda — que e exatamente o
    # que precisa ser lido para consertar o OCR.
    executar(TelaFalsa([LISTA_SEM_NADA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    derrubados = [s for s in dados["slots"]
                  if s["preco_bruto"] is not None and s["preco_conferido"] is None]
    assert derrubados, "nesta tela a conferencia derruba slots; o bruto tem de sobreviver"

def test_ritmo_padrao_espera_a_janela_por_dez_segundos():
    # A spec pede 10 s. Numa execucao unica, esperar de graca nao custa nada;
    # abortar por uma primeira carga de UI mais lenta custa a viagem.
    assert Ritmo().teto_espera_janela == 10.0
    assert Ritmo().intervalo_entre_perguntas == 0.1

def test_o_piloto_nao_depende_do_random_global(tmp_path):
    # Com semente injetada, mexer no random global nao pode mudar a escolha.
    import random as global_random
    global_random.seed(1)
    um = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                  sorteio=random.Random(42)).listagem.item
    global_random.seed(999)
    dois = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                    sorteio=random.Random(42)).listagem.item
    assert um is dois

def test_sorteio_injetado_torna_a_escolha_deterministica(tmp_path):
    escolhas = {
        executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99)).listagem.item
        for _ in range(5)
    }
    assert len(escolhas) == 1

def test_o_relatorio_registra_o_tempo_de_cada_etapa(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99))
    assert set(r.tempos) >= {"pre_voo", "varredura", "modal"}
    assert all(v >= 0 for v in r.tempos.values())

def test_o_tempo_por_etapa_vai_para_o_json(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             sorteio=random.Random(99))
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert "tempos" in dados and "varredura" in dados["tempos"]
