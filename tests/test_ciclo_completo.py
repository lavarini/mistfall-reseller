import dataclasses
import json
import random
import time
from collections import deque
from types import SimpleNamespace

import numpy as np

from mistfall.ciclo_venda import DesfechoSessaoVenda, SessaoVenda
from mistfall.compra_visao import MensagemCompra
from mistfall.fluxo import ModoFluxo, estado_inicial
from mistfall.navegacao import ResultadoNavegacao
from mistfall.piloto import Desfecho, Resultado, Ritmo
from mistfall.tipos import CapacidadeVenda
from mistfall.venda import RitmoVenda

from mistfall.ciclo_completo import (
    DesfechoSessaoCompleta,
    executar_ciclo_completo,
)


RITMO_COMPRA = Ritmo.instantaneo()
RITMO_VENDA = RitmoVenda.instantaneo()


class InterruptorRoteirizado:
    def __init__(self, respostas=()):
        self._respostas = deque(respostas)
        self.inicios = 0
        self.perguntas = 0

    def esperar_inicio(self):
        self.inicios += 1

    def pediram_parada(self):
        self.perguntas += 1
        return self._respostas.popleft() if self._respostas else False


def _resultado(desfecho, *, ouro=1000, preco=100):
    resultado = Resultado(desfecho, ouro_observado=ouro)
    if desfecho is Desfecho.COMPRA_ENVIADA:
        from mistfall.tipos import ItemAlvo, Listagem

        resultado.listagem = Listagem(0, 0, ItemAlvo.BROCHE, preco)
    return resultado


def _preparar(monkeypatch, resultados, mensagens=None, venda=None, vendas=None):
    import mistfall.ciclo_completo as completo

    resultados = deque(resultados)
    fila_de_vendas = deque(vendas or [])
    mensagens = deque(mensagens or [MensagemCompra.NENHUMA] * len(resultados))
    chamadas = []
    frame_atual = [0]

    def executar(*args, **kwargs):
        frame_atual[0] += 1
        kwargs["observador_frame_inicial"](
            np.full((1, 1, 3), frame_atual[0], dtype=np.uint8)
        )
        chamadas.append("compra")
        return resultados.popleft()

    def detectar(_frame):
        return mensagens.popleft() if mensagens else MensagemCompra.NENHUMA

    monkeypatch.setattr(completo, "executar", executar)
    monkeypatch.setattr(completo, "detectar_mensagem_compra", detectar)
    monkeypatch.setattr(
        completo,
        "garantir_filtro_roxo",
        lambda *args: chamadas.append("filtro_inicial")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "ir_para_venda",
        lambda *args: chamadas.append("ir_venda")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "ir_para_compra",
        lambda *args: chamadas.append("ir_compra")
        or ResultadoNavegacao(True, np.zeros((1, 1, 3), dtype=np.uint8), ""),
    )
    monkeypatch.setattr(
        completo,
        "resetar_categoria",
        lambda *args, **kwargs: chamadas.append("reset") or True,
    )
    def vender(*args, **kwargs):
        chamadas.append("venda")
        if fila_de_vendas:
            return fila_de_vendas.popleft()
        return venda or SessaoVenda(DesfechoSessaoVenda.ARMAZEM_ESGOTADO)

    monkeypatch.setattr(completo, "executar_venda_parcial", vender)
    return chamadas


def _config(**ajustes):
    from mistfall.config import Config
    from mistfall.tipos import ItemAlvo

    return Config(precos_alvo={ItemAlvo.BROCHE: 188}, **ajustes)


def _executar(tmp_path, interruptor, config=None):
    return executar_ciclo_completo(
        object(), object(), config or _config(), tmp_path, interruptor,
        RITMO_COMPRA, RITMO_VENDA, random.Random(42),
    )


def test_comeca_em_comprar_validando_o_filtro_e_espera_f3_uma_vez(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(monkeypatch, [])
    interruptor = InterruptorRoteirizado([True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.desfecho is DesfechoSessaoCompleta.PAROU
    assert interruptor.inicios == 1
    assert chamadas == ["filtro_inicial"]


def test_compra_rapida_reseta_so_sem_intencao_e_nao_faz_venda_voluntaria(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(monkeypatch, [
        _resultado(Desfecho.COMPRA_ENVIADA),
        _resultado(Desfecho.NADA_COMPRAVEL, ouro=900),
        _resultado(Desfecho.COMPRA_ENVIADA, ouro=900),
    ])
    interruptor = InterruptorRoteirizado([False] * 3 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.RAPIDO
    assert sessao.compras_enviadas == 2
    assert chamadas.count("reset") == 1
    assert "venda" not in chamadas


def test_inventario_cheio_entra_em_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [
            _resultado(Desfecho.COMPRA_ENVIADA),
            _resultado(Desfecho.NADA_COMPRAVEL, ouro=1000),
        ],
        [MensagemCompra.NENHUMA, MensagemCompra.INVENTARIO_CHEIO],
    )
    interruptor = InterruptorRoteirizado([False] * 3 + [True])

    _executar(tmp_path, interruptor)

    assert chamadas.count("venda") == 1
    assert chamadas.index("ir_venda") < chamadas.index("venda")


def test_tres_intervalos_lentos_entram_em_venda(monkeypatch, tmp_path):
    intencao = lambda: _resultado(Desfecho.COMPRA_ENVIADA)
    reset = lambda: _resultado(Desfecho.NADA_COMPRAVEL)
    resultados = (
        [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
        + [reset() for _ in range(3)]
        + [intencao()]
    )
    chamadas = _preparar(monkeypatch, resultados)
    interruptor = InterruptorRoteirizado([False] * 14 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.LENTO
    assert chamadas.count("venda") == 1


def test_cinco_resets_consecutivos_entram_em_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL) for _ in range(5)],
    )
    interruptor = InterruptorRoteirizado([False] * 6 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.modo is ModoFluxo.LENTO
    assert chamadas.count("reset") == 5
    assert chamadas.count("venda") == 1


def test_retorno_da_venda_restaura_comprar_e_filtro_roxo(
    monkeypatch, tmp_path,
):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    _executar(tmp_path, interruptor)

    assert chamadas[-3:] == ["ir_venda", "venda", "ir_compra"]


def test_venda_de_45_preserva_saldo_55_de_um_estoque_100(
    monkeypatch, tmp_path,
):
    import mistfall.ciclo_completo as completo

    venda = SessaoVenda(
        DesfechoSessaoVenda.CAPACIDADE_CHEIA,
        unidades_listadas=45,
    )
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    monkeypatch.setattr(
        completo, "estado_inicial", lambda: estado_inicial(estoque_estimado=100)
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.estado.estoque_estimado == 55
    assert sessao.unidades_listadas == 45


def test_f4_para_durante_compra_ou_venda(monkeypatch, tmp_path):
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.PAROU)],
    )
    sessao_compra = _executar(
        tmp_path / "compra", InterruptorRoteirizado([False])
    )
    assert sessao_compra.desfecho is DesfechoSessaoCompleta.PAROU
    assert "venda" not in chamadas

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        SessaoVenda(DesfechoSessaoVenda.PAROU),
    )
    sessao_venda = _executar(
        tmp_path / "venda", InterruptorRoteirizado([False] * 2)
    )
    assert sessao_venda.desfecho is DesfechoSessaoCompleta.PAROU
    assert chamadas[-2:] == ["ir_venda", "venda"]
    assert "ir_compra" not in chamadas


def test_cinco_abortos_consecutivos_encerram_a_sessao_com_o_motivo(
    monkeypatch, tmp_path,
):
    resultados = [
        Resultado(Desfecho.ABORTOU, motivo=f"pre-voo ilegivel {n}", ouro_observado=1000)
        for n in range(1, 6)
    ]
    chamadas = _preparar(monkeypatch, resultados)
    interruptor = InterruptorRoteirizado([False] * 5)

    sessao = _executar(tmp_path, interruptor)

    assert sessao.desfecho is DesfechoSessaoCompleta.ABORTOU
    assert sessao.motivo == "pre-voo ilegivel 5"
    assert chamadas.count("compra") == 5
    assert "venda" not in chamadas


def test_um_resultado_que_nao_e_abortou_zera_o_contador_de_abortos(
    monkeypatch, tmp_path,
):
    def aborto(n):
        return Resultado(
            Desfecho.ABORTOU, motivo=f"pre-voo ilegivel {n}", ouro_observado=1000,
        )

    resultados = (
        [aborto(n) for n in range(1, 5)]
        + [_resultado(Desfecho.NADA_COMPRAVEL)]
        + [aborto(n) for n in range(5, 9)]
    )
    chamadas = _preparar(monkeypatch, resultados)
    interruptor = InterruptorRoteirizado([False] * 9 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.desfecho is DesfechoSessaoCompleta.PAROU
    assert chamadas.count("compra") == 9
    assert chamadas.count("reset") == 1


def test_grava_eventos_do_fluxo_completo_em_jsonl_na_pasta_da_sessao(
    monkeypatch, tmp_path,
):
    # Mesmo roteiro de test_venda_de_45_preserva_saldo_55_de_um_estoque_100:
    # uma unica Volta que junta inventario cheio, Reset e uma Venda parcial de
    # 45 unidades. Cada aplicar() dessa Volta precisa virar uma linha em
    # eventos-do-fluxo.jsonl, na pasta da propria sessao — sem tocar em
    # telemetria-ouro.jsonl nem tempos-do-laco.jsonl, que este coordenador
    # nunca escreve.
    import mistfall.ciclo_completo as completo

    venda = SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=45)
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    monkeypatch.setattr(
        completo, "estado_inicial", lambda: estado_inicial(estoque_estimado=100)
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    _executar(tmp_path, interruptor)

    caminho = tmp_path / "eventos-do-fluxo.jsonl"
    assert caminho.exists(), "coordenador nao escreveu eventos-do-fluxo.jsonl"
    linhas = [json.loads(linha) for linha in caminho.read_text().splitlines()]

    assert [linha["motivo_transicao"] for linha in linhas] == [
        "vender_por_inventario_cheio",
        "continuar_compra",
        # venda_encerrada e a Janela sendo reagendada: acao neutra que sempre
        # devolve continuar_compra, como retorno_compra logo abaixo.
        "continuar_compra",
        "continuar_venda",
        "continuar_compra",
    ]
    assert [linha["evento"] for linha in linhas] == [
        "mensagem_inventario_cheio",
        "reset_executado",
        "venda_encerrada",
        "unidades_listadas",
        "retorno_compra",
    ]
    assert all(linha["volta"] == 1 for linha in linhas)
    assert all(linha["modo"] == "rapido" for linha in linhas)

    ultima = linhas[-1]
    assert ultima["estoque_estimado"] == 55
    assert ultima["unidades_listadas"] == 45

    assert not (tmp_path / "telemetria-ouro.jsonl").exists()
    assert not (tmp_path / "tempos-do-laco.jsonl").exists()


def test_venda_real_com_estoque_inicial_de_producao_nao_derruba_a_sessao(
    monkeypatch, tmp_path,
):
    # Producao comeca com `estoque_estimado = 0`, como a spec manda, e no
    # regime rapido a unica Venda que existe e a disparada pelo toast de
    # inventario cheio. Ela lista unidades que a contagem interna nunca viu.
    # Sem saturacao isso levantava ValueError dentro do laco, e o
    # `completo_cli` traduzia para "problema de ambiente" com codigo 2.
    # Note que este teste NAO faz monkeypatch de `estado_inicial`.
    venda = SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=45)
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert sessao.desfecho is DesfechoSessaoCompleta.PAROU
    assert sessao.estado.estoque_estimado == 0
    assert sessao.unidades_listadas == 45


def test_a_volta_de_venda_registra_capacidade_observada_e_retorno_a_compra(
    monkeypatch, tmp_path,
):
    # `capacidade_atualizada` e `retorno_compra` existiam no contrato do fluxo
    # e nunca tinham chamador: a chave `capacidade_observada` do JSONL saia
    # `null` em toda linha de toda sessao real.
    venda = SessaoVenda(
        DesfechoSessaoVenda.CAPACIDADE_CHEIA,
        unidades_listadas=45,
        capacidade_final=CapacidadeVenda(12, 40),
    )
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    sessao = _executar(tmp_path, interruptor)

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "eventos-do-fluxo.jsonl").read_text().splitlines()
    ]
    assert [linha["evento"] for linha in linhas] == [
        "mensagem_inventario_cheio",
        "reset_executado",
        "venda_encerrada",
        "unidades_listadas",
        "capacidade_atualizada",
        "retorno_compra",
    ]
    assert linhas[-1]["capacidade_observada"] == [12, 40]
    assert sessao.estado.capacidade_observada == (12, 40)


def test_venda_sem_capacidade_lida_nao_emite_capacidade_atualizada(
    monkeypatch, tmp_path,
):
    # `capacidade_final` fica None quando a Venda nem chegou a ler `X/Y`;
    # emitir o evento nesse caso gravaria uma Capacidade inventada.
    venda = SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=45)
    _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
        venda,
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    sessao = _executar(tmp_path, interruptor)

    linhas = [
        json.loads(linha)
        for linha in (tmp_path / "eventos-do-fluxo.jsonl").read_text().splitlines()
    ]
    assert "capacidade_atualizada" not in [linha["evento"] for linha in linhas]
    assert sessao.estado.capacidade_observada is None


def test_nao_reseta_a_categoria_quando_a_mesma_volta_ja_decidiu_vender(
    monkeypatch, tmp_path,
):
    # A ida a Venda e a volta por `ir_para_compra` ja restauram a Categoria e
    # recarregam a Listagem: o Reset desta Volta seria clique jogado fora.
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL)],
        [MensagemCompra.INVENTARIO_CHEIO],
    )
    interruptor = InterruptorRoteirizado([False] * 2 + [True])

    _executar(tmp_path, interruptor)

    assert "reset" not in chamadas
    assert chamadas.count("venda") == 1


def test_grava_sessao_json_com_desfecho_e_motivo_mesmo_ao_abortar(
    monkeypatch, tmp_path,
):
    # Sem isto o operador encontra a sessao terminada sem nenhum registro do
    # porque — o modo completo era o unico dos tres que nao escrevia nada.
    import mistfall.ciclo_completo as completo

    _preparar(monkeypatch, [])
    monkeypatch.setattr(
        completo,
        "garantir_filtro_roxo",
        lambda *args: ResultadoNavegacao(None, None, "Compra nao confirmou filtro roxo"),
    )

    sessao = _executar(tmp_path, InterruptorRoteirizado([True]))

    assert sessao.desfecho is DesfechoSessaoCompleta.ABORTOU
    dados = json.loads((tmp_path / "sessao.json").read_text(encoding="utf-8"))
    assert dados["desfecho"] == "abortou"
    assert dados["motivo"] == "Compra nao confirmou filtro roxo"
    assert dados["compras_enviadas"] == 0
    assert dados["estado"]["estoque_estimado"] == 0
    assert dados["estado"]["modo"] == "rapido"
    # A pressa e o contador que devolve o regime ao rapido; sem ela no
    # diagnostico nao da para explicar depois por que a Venda por saldo
    # disparou (ou deixou de disparar) numa sessao sem supervisao.
    assert dados["estado"]["pontos_de_pressa"] == 0


def test_conta_os_baus_na_primeira_venda_e_reusa_nas_seguintes(monkeypatch, tmp_path):
    # A contagem sai da propria Venda: a primeira conta e devolve o total, e o
    # coordenador o repassa. Recontar a cada Venda desperdicaria a leitura.
    import mistfall.ciclo_completo as completo

    _preparar(
        monkeypatch,
        [
            _resultado(Desfecho.COMPRA_ENVIADA),
            _resultado(Desfecho.NADA_COMPRAVEL, ouro=1000),
            _resultado(Desfecho.COMPRA_ENVIADA),
            _resultado(Desfecho.NADA_COMPRAVEL, ouro=900),
        ] + [_resultado(Desfecho.NADA_COMPRAVEL, ouro=900)] * 8,
        [
            MensagemCompra.NENHUMA,
            MensagemCompra.INVENTARIO_CHEIO,
            MensagemCompra.NENHUMA,
            MensagemCompra.INVENTARIO_CHEIO,
        ],
    )
    totais_recebidos = []

    def vender(*args, **kwargs):
        totais_recebidos.append(kwargs.get("total_baus"))
        return SessaoVenda(
            DesfechoSessaoVenda.ARMAZEM_ESGOTADO, vendas=1,
            unidades_listadas=3, total_baus=6,
        )

    monkeypatch.setattr(completo, "executar_venda_parcial", vender)
    interruptor = InterruptorRoteirizado([False] * 7 + [True])

    sessao = _executar(tmp_path, interruptor)

    assert totais_recebidos == [0, 6]
    assert sessao.total_baus == 6


def test_sessao_json_registra_o_total_de_baus_contado(monkeypatch, tmp_path):
    # A contagem e feita uma vez e vale a sessao inteira. Se sair errada, o
    # relatorio e o unico lugar onde isso fica visivel depois.
    import mistfall.ciclo_completo as completo

    _preparar(
        monkeypatch,
        [
            _resultado(Desfecho.COMPRA_ENVIADA),
            _resultado(Desfecho.NADA_COMPRAVEL, ouro=1000),
        ] + [_resultado(Desfecho.NADA_COMPRAVEL, ouro=900)] * 8,
        [MensagemCompra.NENHUMA, MensagemCompra.INVENTARIO_CHEIO],
    )
    monkeypatch.setattr(
        completo,
        "executar_venda_parcial",
        lambda *args, **kwargs: SessaoVenda(
            DesfechoSessaoVenda.ARMAZEM_ESGOTADO, vendas=1,
            unidades_listadas=3, total_baus=6,
        ),
    )

    _executar(tmp_path, InterruptorRoteirizado([False] * 5 + [True]))

    dados = json.loads((tmp_path / "sessao.json").read_text(encoding="utf-8"))
    assert dados["total_baus"] == 6


def test_ouro_abaixo_do_piso_manda_vender_mesmo_no_regime_rapido(monkeypatch, tmp_path):
    # O buraco da #24: com o Ouro esgotado as Listagens no Preco-alvo continuam
    # aparecendo, entao o regime nunca vira lento, e nada e comprado, entao o
    # Inventario nunca enche. Os dois gatilhos antigos ficam inalcancaveis.
    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.COMPRA_ENVIADA, ouro=250)] * 10,
        [MensagemCompra.NENHUMA] * 10,
    )

    _executar(tmp_path, InterruptorRoteirizado([False] * 3 + [True]))

    assert "venda" in chamadas
    assert chamadas.index("ir_venda") < chamadas.index("venda")


def test_compra_enviada_espera_a_lista_se_reorganizar_antes_da_proxima_volta(
    monkeypatch, tmp_path,
):
    """A Volta seguinte a uma Compra le a lista DEPOIS de ela se reorganizar.

    Sem isso a varredura pega a lista velha, decide um slot que ja mudou de
    dono e o clique compra outra Listagem. E a mesma protecao que `ciclo.py`
    ja aplica no `mistfall-bot` — ver docs/superpowers/specs/
    2026-08-15-espera-pos-compra-design.md.
    """
    import mistfall.ciclo_completo as completo

    esperas = []
    monkeypatch.setattr(
        completo,
        "time",
        SimpleNamespace(monotonic=time.monotonic, sleep=esperas.append),
    )
    _preparar(monkeypatch, [
        _resultado(Desfecho.COMPRA_ENVIADA),
        _resultado(Desfecho.NADA_COMPRAVEL, ouro=900),
    ])
    ritmo = dataclasses.replace(
        Ritmo.instantaneo(),
        espera_entre_voltas=0.15,
        espera_apos_compra=(0.65, 0.75),
    )

    executar_ciclo_completo(
        object(), object(), _config(), tmp_path,
        InterruptorRoteirizado([False] * 2 + [True]),
        ritmo, RITMO_VENDA, random.Random(42),
    )

    assert len(esperas) == 2
    assert 0.65 <= esperas[0] <= 0.75
    assert esperas[1] == 0.15


def test_reset_com_armazem_cheio_vende_quando_a_janela_abre(monkeypatch, tmp_path):
    # O defeito que originou tudo: em regime lento, com o Armazem cheio e o
    # Leilao seco, o gatilho por saldo so era consultado em evento de Compra,
    # e o bot resetava indefinidamente sem nunca ir vender.
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 4,
        venda=SessaoVenda(DesfechoSessaoVenda.ARMAZEM_ESGOTADO, unidades_listadas=45),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 5 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=0))

    assert chamadas.count("venda") >= 1


def test_janela_fechada_segura_a_venda_do_regime_lento(monkeypatch, tmp_path):
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        # Sete Voltas de Compra, nao seis: a primeira ja vende (Janela aberta
        # na largada) e ainda assim precisa da sua propria leitura de Compra;
        # as seis seguintes so encontram a Janela fechada.
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 7,
        venda=SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=0),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 8 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=3600))

    # A primeira Venda passa (Janela aberta na largada); a Janela fecha por
    # uma hora e nenhuma outra pode acontecer, mesmo com o saldo acima do lote.
    assert chamadas.count("venda") == 1


def test_capacidade_cheia_nao_trava_a_venda_para_sempre(monkeypatch, tmp_path):
    # O trinco antigo: uma Venda que voltava sem listar nada suspendia o
    # gatilho por saldo ate uma Venda listar alguma coisa — que nunca
    # acontecia, porque a suspensao impedia a Venda.
    import mistfall.ciclo_completo as completo
    from mistfall.tipos import LOTE_DE_VENDA_EM_UNIDADES

    chamadas = _preparar(
        monkeypatch,
        [_resultado(Desfecho.NADA_COMPRAVEL, ouro=1000)] * 6,
        venda=SessaoVenda(DesfechoSessaoVenda.CAPACIDADE_CHEIA, unidades_listadas=0),
    )
    monkeypatch.setattr(
        completo,
        "estado_inicial",
        lambda: estado_inicial(
            modo=ModoFluxo.LENTO, estoque_estimado=LOTE_DE_VENDA_EM_UNIDADES + 15,
        ),
    )
    interruptor = InterruptorRoteirizado([False] * 12 + [True])

    _executar(tmp_path, interruptor, _config(intervalo_da_janela_s=0))

    assert chamadas.count("venda") >= 2
