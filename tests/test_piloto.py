import dataclasses
import json
import random
from dataclasses import replace

import cv2
import pytest

from mistfall.config import Config
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import (Desfecho, Resultado, Ritmo, _conferir_a_janela,
                             executar)
from mistfall.tipos import ItemAlvo, Listagem

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

def cfg_sem_alvo():
    """Precos-alvo que nenhuma Listagem do corpus atinge.

    Nenhum print do corpus e mais "nada compravel": era a leitura errada que
    fazia a conferencia de ordenacao derrubar a tela inteira, e a folha unica
    a corrigiu. O desfecho NADA_COMPRAVEL continua existindo em producao — a
    tela sem nenhum Item-alvo no Preco-alvo e comum no jogo —, entao o que
    muda e por onde o teste chega nele: pelos Precos-alvo, nao pelo print.
    """
    return dataclasses.replace(cfg(), precos_alvo={item: 1 for item in ItemAlvo})

def roteiro_feliz():
    # pre-voo e, depois do Espaco, a lista com o Ouro debitado.
    #
    # Nao ha frame de Janela: o piloto nao captura a tela entre o clique e o
    # Espaco. Um frame de modal aqui seria consumido pela leitura do Ouro, que
    # e a proxima captura, e o teste mediria outra coisa.
    return TelaFalsa([LISTA, LISTA_DEBITADA])


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
    # Duas capturas, e nao mais tres: sumiu a da Janela, que nao e mais
    # olhada. Restam o pre-voo e a tela com o Ouro debitado — as duas pontas
    # da unica conferencia que sobrou.
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert sorted(p.name for p in tmp_path.glob("*.png")) == [
        "00-pre-voo.png", "01-apos-espaco.png"]
    assert (tmp_path / "relatorio.json").exists()


JANELA_ESPELHO = "images/janela.png"          # modal com item que nao e alvo
RESET = "images/reset-forja.png"              # outra Categoria

# Os testes de divergencia no modal via `executar` sairam daqui: o piloto nao
# consulta mais a Janela, entao nao ha comportamento a afirmar nesse nivel. As
# conferencias continuam no codigo e sao exercitadas direto, no fim do arquivo.
# O mesmo vale para "a Janela nao abriu": sem deteccao, nao existe esse aborto.

def test_nada_compravel_sai_limpo_sem_clicar(tmp_path):
    mao = MaoFalsa()
    r = executar(TelaFalsa([LISTA]), mao, cfg_sem_alvo(), tmp_path, ritmo=JA)
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

def test_ouro_que_cai_valor_inesperado_e_reportado(tmp_path):
    # Depois do Espaco a tela mostra um print real cujo Ouro e 64735, nao
    # os 65914 esperados. A Compra aconteceu, mas a queda nao bate.
    #
    # Com o modal fora do caminho, esta e a unica conferencia que sobrou: o
    # esperado vem da Listagem escolhida, e a queda tem de bater com ele.
    OUTRA_LISTA = "images/broche-tres-adaga-lanterna-rede-padrao.png"  # Ouro 64735
    tela = TelaFalsa([LISTA, OUTRA_LISTA])
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
    (JANELA_DRAGAO_999, "modal cobra"),
    (JANELA_DRAGAO_QTD_5, "Quantidade e"),
])
def test_conferencia_da_janela_pega_cada_divergencia(fixture, pedaco_do_motivo):
    # A conferencia esta estacionada: ninguem a chama. Continua exercitada
    # direto para nao apodrecer enquanto espera — se um dia voltar ao caminho,
    # tem de voltar funcionando. Ver o docstring de _conferir_a_janela.
    escolhida = Listagem(linha=2, coluna=1, item=ItemAlvo.DRAGAO, preco_unitario=246)
    r = Resultado(Desfecho.ABORTOU)
    divergencia = _conferir_a_janela(cv2.imread(fixture), escolhida, r, 1)
    assert divergencia is not None, "esta fixture tem de divergir"
    assert pedaco_do_motivo in divergencia, divergencia

def test_conferencia_da_janela_aprova_o_modal_correto():
    # O contrario do teste acima: sem ele, uma conferencia que reprovasse tudo
    # passaria nos seis casos de divergencia sem ninguem perceber.
    escolhida = Listagem(linha=2, coluna=1, item=ItemAlvo.DRAGAO, preco_unitario=246)
    r = Resultado(Desfecho.ABORTOU)
    assert _conferir_a_janela(cv2.imread(JANELA_DRAGAO), escolhida, r, 1) is None

def test_conferencia_da_janela_le_o_icone_sem_reprovar_por_ele():
    # O icone saiu do portao por decisao registrada, mas continua sendo lido.
    # JANELA_ORBE_246 mostra Orbe onde escolhemos Dragao, e mesmo assim passa.
    escolhida = Listagem(linha=2, coluna=1, item=ItemAlvo.DRAGAO, preco_unitario=246)
    r = Resultado(Desfecho.ABORTOU)
    assert _conferir_a_janela(cv2.imread(JANELA_ORBE_246), escolhida, r, 1) is None
    assert r.scores_do_icone is not None, "o icone tem de continuar sendo lido"
    assert r.item_no_modal == "orbe"


# ---------------------------------------------------------------------------
# A Janela e detectavel antes de estar desenhada (#18).

JANELA_EM_ANIMACAO = "images/janela-em-animacao-rede-260.png"


# ---------------------------------------------------------------------------
# O modal nao e olhado para nada. Decisao do dono do projeto: a leitura da
# Janela e intermitente e estava custando mais do que entregava. As funcoes
# continuam no codigo, sem chamador. Ver o docstring de _conferir_a_janela.

class MaoQueAnotaQuandoApertou:
    """MaoFalsa que registra quantas capturas a tela ja tinha feito."""

    def __init__(self, tela) -> None:
        self.tela = tela
        self.acoes: list[tuple] = []
        self.capturas_ao_apertar: int | None = None

    def clicar(self, x: int, y: int) -> None:
        self.acoes.append(("clicar", x, y))

    def apertar_espaco(self) -> None:
        self.capturas_ao_apertar = self.tela.capturas_feitas
        self.acoes.append(("apertar_espaco",))

    def apertar_esc(self) -> None:
        self.acoes.append(("apertar_esc",))

def test_compra_sem_a_Janela_aparecer_no_roteiro_da_tela(tmp_path):
    # O roteiro vai do pre-voo direto para a lista com o Ouro debitado: nao ha
    # frame de Janela nenhum. O piloto compra assim mesmo, porque nao olha.
    #
    # Este roteiro seria impossivel antes: sem um frame reconhecido como
    # JANELA_CONFIRMACAO o piloto abortava com "a Janela nao abriu".
    tela = TelaFalsa([LISTA, LISTA_DEBITADA])
    mao = MaoFalsa()
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.COMPROU, r.motivo
    assert nomes == ["clicar", "apertar_espaco"]
    assert "apertar_esc" not in nomes

def test_nenhuma_captura_entre_o_clique_e_o_espaco(tmp_path):
    # A prova de que o modal nao e olhado: entre o pre-voo e o Espaco a tela
    # nao e consultada nenhuma vez. Sem isto, reintroduzir uma captura de
    # diagnostico passaria despercebido e traria o custo de volta.
    tela = TelaFalsa([LISTA, JANELA_DRAGAO, LISTA_DEBITADA])
    mao = MaoQueAnotaQuandoApertou(tela)
    executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert mao.capturas_ao_apertar == 1, "so o pre-voo deve ter sido capturado"

def test_preco_total_esperado_vem_da_listagem_e_nao_do_modal(tmp_path):
    # Com o modal fora do caminho, a queda do Ouro e a unica conferencia que
    # sobra — e o valor esperado passa a vir da Listagem escolhida, assumindo
    # Quantidade 1.
    #
    # Sem frame de Janela no roteiro, o unico lugar de onde 246 pode ter vindo
    # e a Listagem escolhida. Se ainda viesse do modal seria None, e a
    # comparacao com a queda do Ouro nunca bateria.
    tela = TelaFalsa([LISTA, LISTA_DEBITADA])
    r = executar(tela, MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1))
    assert r.preco_total_esperado == r.listagem.preco_unitario == 246
    assert r.desfecho is Desfecho.COMPROU, r.motivo

def test_a_conferencia_reprovaria_o_frame_em_animacao(tmp_path):
    # Captura real da maquina do jogo: a Janela e reconhecivel como
    # JANELA_CONFIRMACAO enquanto ainda se expande, e nessa fase esta 69 px
    # acima da posicao final, com as regioes fixas sobre fundo vazio.
    #
    # O piloto nao valida mais nada, entao isso deixou de derrubar Compra. O
    # teste fica como registro do achado: se a conferencia voltar ao caminho
    # sem que a espera cubra a animacao, ela reprova de novo.
    escolhida = Listagem(linha=3, coluna=0, item=ItemAlvo.REDE, preco_unitario=260)
    divergencia = _conferir_a_janela(
        cv2.imread(JANELA_EM_ANIMACAO), escolhida, Resultado(Desfecho.ABORTOU), 1)
    assert divergencia is not None
    assert "ilegivel" in divergencia, divergencia

def test_espera_do_modal_e_sorteada_dentro_da_faixa(tmp_path):
    # Ritmo identico em tudo, sementes diferentes: se a espera fosse fixa os
    # dois valores seriam iguais. O sorteio existe para o ritmo do bot nao
    # sair sempre com o mesmo numero.
    ritmo = dataclasses.replace(JA, espera_para_o_modal_abrir=(0.08, 0.12))
    vistos = set()
    for semente in range(12):
        r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path / str(semente),
                     ritmo=ritmo, sorteio=random.Random(semente))
        vistos.add(r.espera_do_modal_ms)
    assert len(vistos) > 1, "a espera saiu igual em 12 sementes: nao ha sorteio"
    assert all(80 <= ms <= 120 for ms in vistos), sorted(vistos)

def test_a_espera_do_modal_nunca_fica_abaixo_do_piso(tmp_path):
    # O sorteio e para cima, nunca para baixo: curto demais faz o Espaco
    # chegar antes de a Janela abrir, e a Compra se perde. O piso e o numero
    # calibrado; a variacao e so enfeite por cima dele.
    ritmo = dataclasses.replace(JA, espera_para_o_modal_abrir=(0.08, 0.12))
    for semente in range(30):
        r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path / str(semente),
                     ritmo=ritmo, sorteio=random.Random(semente))
        assert r.espera_do_modal_ms >= 80

def test_relatorio_diz_quanto_esperou_pelo_modal(tmp_path):
    # A espera vai ser calibrada por tentativas na maquina do jogo. Sem este
    # numero gravado, as pastas de execucao viram evidencia sem etiqueta: nao
    # da para saber qual tentativa produziu qual resultado.
    # Faixa degenerada, com piso e teto iguais: o sorteio so pode devolver um
    # valor, entao o teste afirma o numero exato sem depender de semente.
    ritmo = dataclasses.replace(JA, espera_para_o_modal_abrir=(0.25, 0.25))
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=ritmo,
             sorteio=random.Random(1))
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["espera_do_modal_ms"] == 250

def test_o_frame_em_animacao_realmente_engana_a_deteccao_de_estado(tmp_path):
    # A premissa do teste acima. Se um dia a deteccao de estado passar a
    # recusar o frame em animacao, o piloto ficaria esperando em vez de
    # validar cedo — e o teste acima passaria por outro motivo, calado.
    from mistfall.estado import identificar_estado
    from mistfall.tipos import EstadoTela
    assert identificar_estado(cv2.imread(JANELA_EM_ANIMACAO)) is EstadoTela.JANELA_CONFIRMACAO

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
    # O bot ja mexeu no jogo: clicou e apertou Espaco antes de a tela cair.
    assert [a[0] for a in mao.acoes] == ["clicar", "apertar_espaco"]
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "abortou"
    assert "explodiu" in dados["motivo"]
    assert "mss caiu" in dados["motivo"]

def test_relatorio_nao_traz_mais_nada_do_modal(tmp_path):
    # O modal nao e lido, entao estes campos ficam vazios de proposito. Se um
    # deles voltar a ser preenchido, alguem religou a leitura no caminho da
    # Compra — que e justamente o que foi desativado.
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             sorteio=random.Random(1))
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    for campo in ("item_no_modal", "preco_no_modal", "quantidade_no_modal",
                  "escala_do_icone", "scores_do_icone", "segundos_ate_a_janela"):
        assert dados[campo] is None, campo

def test_relatorio_guarda_os_doze_slots_mesmo_sem_nada_compravel(tmp_path):
    # O desfecho nada_compravel era o mais opaco de todos: dizia que nao havia
    # Listagem abaixo do Preco-alvo e nao dizia o que tinha lido para concluir
    # isso. Sem os slots, diagnosticar exige reprocessar o PNG a mao.
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg_sem_alvo(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "nada_compravel"
    assert len(dados["slots"]) == 12
    assert [(s["linha"], s["coluna"]) for s in dados["slots"]] == [
        (linha, coluna) for linha in range(6) for coluna in range(2)]


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
    escolhida = Listagem(linha=2, coluna=1, item=ItemAlvo.DRAGAO, preco_unitario=246)
    _conferir_a_janela(cv2.imread(JANELA_DRAGAO), escolhida, Resultado(Desfecho.ABORTOU), 2)
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

def test_relatorio_mostra_o_preco_bruto_que_a_conferencia_derrubou(monkeypatch, tmp_path):
    # A regra de ordenacao e contagiosa de proposito: uma leitura fora de ordem
    # invalida os vizinhos. Guardar so o preco conferido deixaria o relatorio
    # cheio de null sem dizer qual numero causou a queda — que e exatamente o
    # que precisa ser lido para consertar o OCR.
    #
    # Desde a leitura em folha unica nenhum print do corpus tem preco fora de
    # ordem, entao a tela que provoca a queda e montada aqui: um 24 no lugar de
    # 241, que e o erro real que o corpus registrava antes. So a leitura e
    # dublada — a conferencia que roda e a de verdade.
    import mistfall.piloto as piloto
    from mistfall.tipos import Listagem

    slots = [(linha, coluna) for linha in range(6) for coluna in range(2)]
    precos = [188, 215, 218, 237, 241, 246, 253, 268, 281, 281, 313, 357]
    fora_de_ordem = [
        Listagem(linha=linha, coluna=coluna, item=None,
                 preco_unitario=24 if (linha, coluna) == (2, 0) else preco)
        for (linha, coluna), preco in zip(slots, precos)
    ]
    monkeypatch.setattr(piloto, "varrer_bruto", lambda img: fora_de_ordem)

    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    derrubados = [s for s in dados["slots"]
                  if s["preco_bruto"] is not None and s["preco_conferido"] is None]
    assert derrubados, "nesta tela a conferencia derruba slots; o bruto tem de sobreviver"
    assert any(s["preco_bruto"] == 24 for s in derrubados), (
        "o numero que causou a queda tem de aparecer no relatorio")

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
