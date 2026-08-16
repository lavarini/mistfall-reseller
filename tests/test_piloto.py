import dataclasses
import json
import random
from types import SimpleNamespace

import cv2
import pytest

from mistfall.config import Config
from mistfall.geometria import area_clique_slot
from mistfall.perifericos.falso import MaoFalsa, TelaFalsa
from mistfall.piloto import (Desfecho, Resultado, Ritmo, _conferir_a_janela,
                             executar)
from mistfall.tipos import ItemAlvo, Listagem

LISTA = "images/broche-dragao-orbe-codice-padrao.png"
JANELA_DRAGAO = "fixtures/sinteticas/janela-dragao-246.png"

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
    return TelaFalsa([LISTA])


JA = Ritmo.instantaneo()  # nenhum teste espera de verdade

def test_caminho_feliz_compra(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPRA_ENVIADA

def _dentro(ponto, area):
    x, y = ponto
    x0, y0, x1, y1 = area
    return x0 <= x <= x1 and y0 <= y <= y1


def test_caminho_feliz_clica_na_area_segura_do_slot_certo(tmp_path):
    mao = MaoFalsa()
    resultado = executar(
        roteiro_feliz(), mao, cfg(), tmp_path,
        ritmo=JA, sorteio=random.Random(1),
    )
    ponto = mao.acoes[0][1:]
    assert _dentro(
        ponto,
        area_clique_slot(resultado.listagem.linha, resultado.listagem.coluna),
    )


def _clique_com_semente(tmp_path, semente):
    mao = MaoFalsa()
    executar(
        roteiro_feliz(), mao, cfg(), tmp_path / str(semente),
        ritmo=JA, sorteio=random.Random(semente),
    )
    return mao.acoes[0][1:]


def test_sementes_variadas_produzem_mais_de_um_ponto_de_listagem(tmp_path):
    pontos = {_clique_com_semente(tmp_path, s) for s in range(10)}
    assert len(pontos) > 1


def test_mesma_semente_reproduz_o_clique_da_listagem(tmp_path):
    assert _clique_com_semente(tmp_path / "a", 91) == _clique_com_semente(
        tmp_path / "b", 91,
    )


def test_clique_injetado_independe_do_random_global(tmp_path):
    random.seed(1)
    primeiro = _clique_com_semente(tmp_path / "a", 73)
    random.seed(999)
    segundo = _clique_com_semente(tmp_path / "b", 73)
    assert primeiro == segundo


def test_modo_simulado_nao_sorteia_coordenada(tmp_path, monkeypatch):
    def falhar(*_args):
        raise AssertionError("nao deveria sortear clique simulado")

    monkeypatch.setattr("mistfall.piloto.sortear_ponto", falhar)
    resultado = executar(
        roteiro_feliz(), MaoFalsa(), cfg(), tmp_path,
        simular=True, ritmo=JA, sorteio=random.Random(1),
    )
    assert resultado.desfecho is Desfecho.SIMULOU

def test_caminho_feliz_aperta_espaco_e_nunca_esc(tmp_path):
    mao = MaoFalsa()
    executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert nomes == ["clicar", "apertar_espaco"]

def test_caminho_feliz_registra_os_numeros(tmp_path):
    r = executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert r.ouro_observado == 66160
    assert r.listagem.item is ItemAlvo.DRAGAO

def test_caminho_feliz_salva_os_prints(tmp_path):
    executar(roteiro_feliz(), MaoFalsa(), cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    assert sorted(p.name for p in tmp_path.glob("*.png")) == ["00-pre-voo.png"]
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
    assert r.ouro_observado == 66160

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

# ---------------------------------------------------------------------------
# Leitura ilegivel dentro da Janela: cada campo apagado em sua propria fixture.
# Sem uma fixture por campo, apagar a conferencia inteira nao derruba teste
# nenhum — e o bot aperta Espaco sem saber o que esta comprando.

JANELA_PRECO_ILEGIVEL = "fixtures/sinteticas/janela-dragao-preco-ilegivel.png"
JANELA_QTD_ILEGIVEL = "fixtures/sinteticas/janela-dragao-quantidade-ilegivel.png"
JANELA_TOTAL_ILEGIVEL = "fixtures/sinteticas/janela-dragao-total-ilegivel.png"
JANELA_ESPELHO_246 = "fixtures/sinteticas/janela-espelho-246.png"
JANELA_TOTAL_250 = "fixtures/sinteticas/janela-dragao-246-total-250.png"
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

def test_compra_sem_a_Janela_aparecer_no_roteiro_da_tela(tmp_path):
    tela = TelaFalsa([LISTA])
    mao = MaoFalsa()
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA, sorteio=random.Random(1))
    nomes = [a[0] for a in mao.acoes]
    assert r.desfecho is Desfecho.COMPRA_ENVIADA, r.motivo
    assert nomes == ["clicar", "apertar_espaco"]
    assert "apertar_esc" not in nomes

def test_espaco_encerra_a_compra_sem_captura_posterior(tmp_path):
    tela = TelaFalsa([LISTA])
    mao = MaoFalsa()
    r = executar(tela, mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert tela.capturas_feitas == 1
    assert [acao[0] for acao in mao.acoes] == ["clicar", "apertar_espaco"]

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


from mistfall.perifericos.falso import InterruptorFalso


def test_sem_interruptor_o_piloto_se_comporta_como_antes(tmp_path):
    # Guarda os 286: o parametro novo tem default None, e com ele nada muda.
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1))
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert mao.acoes[0][0] == "clicar"


def test_parada_antes_do_clique_nao_clica(tmp_path):
    mao = MaoFalsa()
    r = executar(roteiro_feliz(), mao, cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(1),
                 interruptor=InterruptorFalso(parar_na_pergunta=1))
    assert r.desfecho is Desfecho.PAROU
    # O ponto da abordagem cooperativa: F3 durante a varredura nao pode
    # deixar o bot completar mais uma Compra.
    assert mao.acoes == []


def test_o_ritmo_separa_espera_comum_e_espera_apos_compra():
    assert Ritmo().espera_entre_voltas == 0.15
    assert Ritmo().espera_apos_compra == (0.65, 0.75)
    assert Ritmo.instantaneo().espera_entre_voltas == 0.0
    assert Ritmo.instantaneo().espera_apos_compra == (0.0, 0.0)

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

def test_ouro_ilegivel_e_telemetria_e_nao_aborto(tmp_path, monkeypatch):
    import mistfall.piloto as piloto
    real = piloto.analisar_inicial

    def sem_ouro(img, **kwargs):
        resultado = real(img, **kwargs)
        return dataclasses.replace(resultado, ouro_observado=None)

    monkeypatch.setattr(piloto, "analisar_inicial", sem_ouro)
    r = executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert r.ouro_observado is None


def test_ouro_ilegivel_e_publicado_uma_vez_sem_impedir_compra(tmp_path, monkeypatch):
    import mistfall.piloto as piloto
    real = piloto.analisar_inicial

    def sem_ouro(img, **kwargs):
        resultado = real(img, **kwargs)
        return dataclasses.replace(resultado, ouro_observado=None)

    monkeypatch.setattr(piloto, "analisar_inicial", sem_ouro)
    observacoes = []
    mao = MaoFalsa()
    r = executar(
        TelaFalsa([LISTA]), mao, cfg(), tmp_path, ritmo=JA,
        observador_ouro=lambda ouro, _monotonic, _horario: observacoes.append(ouro),
    )

    assert observacoes == [None]
    assert r.desfecho is Desfecho.COMPRA_ENVIADA
    assert [acao[0] for acao in mao.acoes] == ["clicar", "apertar_espaco"]


def test_publica_observacao_com_instante_da_captura(tmp_path):
    vistos = []
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             observador_ouro=lambda ouro, monotonic, horario:
                 vistos.append((ouro, monotonic, horario)))
    assert len(vistos) == 1
    ouro, monotonic, horario = vistos[0]
    assert ouro == 66160
    assert monotonic > 0
    assert horario.tzinfo is not None


def test_relatorio_remove_campos_da_confirmacao_do_ouro(tmp_path):
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA)
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert dados["ouro_observado"] == 66160
    for campo in ("ouro_antes", "ouro_depois", "preco_total_esperado",
                  "confirmacao_do_ouro"):
        assert campo not in dados and campo not in dados["tempos"]

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
    # Comparar apenas o resultado nao prova que o helper entrou no caminho.
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
    import mistfall.analise as analise
    from mistfall.tipos import Listagem

    slots = [(linha, coluna) for linha in range(6) for coluna in range(2)]
    precos = [188, 215, 218, 237, 241, 246, 253, 268, 281, 281, 313, 357]
    fora_de_ordem = [
        Listagem(linha=linha, coluna=coluna, item=None,
                 preco_unitario=24 if (linha, coluna) == (2, 0) else preco)
        for (linha, coluna), preco in zip(slots, precos)
    ]
    def varrer(_img, tempos):
        tempos.update(itens=0.0, preparo_folha=0.0, tesseract_precos=0.0)
        return fora_de_ordem

    monkeypatch.setattr(analise, "varrer_bruto", varrer)

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

def test_o_relatorio_separa_processamento_e_esperas(tmp_path):
    r = executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
                 sorteio=random.Random(99))
    assert set(r.tempos) == {
        "captura_pre_voo", "gravacao_pre_voo", "estado", "ouro",
        "varredura_total", "itens", "preparo_folha", "tesseract_precos",
        "analise_inicial_parede", "conferencia_e_decisao",
        "pausa_antes_do_clique", "clique", "espera_modal", "espaco",
    }
    assert all(ms >= 0 for ms in r.tempos.values())


def test_conferencia_e_decisao_exclui_montagem_diagnostica(
        tmp_path, monkeypatch):
    import mistfall.piloto as piloto

    class Relogio:
        valor = 0.0

        def agora(self):
            return self.valor

        def avancar(self):
            self.valor += 1.0

    class BrutaComDiagnosticoLento:
        linha = 0
        coluna = 0
        item = ItemAlvo.BROCHE

        @property
        def preco_unitario(self):
            relogio.avancar()
            return 188

    relogio = Relogio()
    bruta = BrutaComDiagnosticoLento()
    escolhida = Listagem(0, 0, ItemAlvo.BROCHE, 188)
    monkeypatch.setattr(
        piloto, "time",
        SimpleNamespace(monotonic=relogio.agora, sleep=lambda _segundos: None),
    )
    monkeypatch.setattr(
        piloto, "analisar_inicial",
        lambda *_a, **_k: SimpleNamespace(
            ouro_observado=66160, brutas=[bruta], tempos={}),
    )
    monkeypatch.setattr(piloto, "conferir_ordenacao", lambda _brutas: [escolhida])
    monkeypatch.setattr(piloto, "escolher", lambda *_a: escolhida)

    r = executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path,
                 simular=True, ritmo=JA)

    assert r.tempos["conferencia_e_decisao"] == 0

def test_o_tempo_por_etapa_vai_para_o_json(tmp_path):
    executar(TelaFalsa([LISTA]), MaoFalsa(), cfg(), tmp_path, ritmo=JA,
             sorteio=random.Random(99))
    dados = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    assert set(dados["tempos"]) == {
        "captura_pre_voo", "gravacao_pre_voo", "estado", "ouro",
        "varredura_total", "itens", "preparo_folha", "tesseract_precos",
        "analise_inicial_parede", "conferencia_e_decisao",
        "pausa_antes_do_clique", "clique", "espera_modal", "espaco",
    }
