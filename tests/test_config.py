"""Cobertura de `carregar_config`.

Estes numeros decidem gasto de ouro real e nunca tinham passado pela suite.
Os Precos-alvo sao literais escritos a mao, conferidos contra config.toml.
"""
import pytest
from mistfall.config import carregar_config
from mistfall.tipos import ItemAlvo

def escrever(tmp_path, texto):
    caminho = tmp_path / "config.toml"
    caminho.write_text(texto, encoding="utf-8")
    return caminho

# --- o arquivo de verdade -----------------------------------------------------

def test_carrega_os_sete_precos_alvo_do_config_do_projeto():
    config = carregar_config("config.toml")
    assert config.precos_alvo == {
        ItemAlvo.BROCHE: 188,
        ItemAlvo.ADAGA: 199,
        ItemAlvo.LANTERNA: 234,
        ItemAlvo.DRAGAO: 246,
        ItemAlvo.ORBE: 253,
        ItemAlvo.REDE: 260,
        ItemAlvo.CODICE: 281,
    }

def test_carrega_a_fracao_de_sanidade_do_config_do_projeto():
    assert carregar_config("config.toml").fracao_sanidade == 0.25

def test_todo_item_alvo_tem_preco_alvo_no_config_do_projeto():
    # Item-alvo sem Preco-alvo nunca e comprado: `escolher` o ignora em silencio.
    assert set(carregar_config("config.toml").precos_alvo) == set(ItemAlvo)

# --- casos degenerados --------------------------------------------------------

def test_secao_de_precos_alvo_ausente_diz_o_arquivo_e_a_chave(tmp_path):
    caminho = escrever(tmp_path, "fracao_sanidade = 0.25\n")
    with pytest.raises(ValueError, match=r"config\.toml.*\[precos_alvo\]"):
        carregar_config(caminho)

def test_nome_de_item_alvo_desconhecido_diz_qual_e_lista_os_validos(tmp_path):
    caminho = escrever(tmp_path, "[precos_alvo]\nespelho = 237\n")
    with pytest.raises(ValueError) as erro:
        carregar_config(caminho)
    assert "espelho" in str(erro.value)
    assert "config.toml" in str(erro.value)
    assert "broche" in str(erro.value)

def test_fracao_de_sanidade_ausente_usa_o_padrao(tmp_path):
    # 0.25 escrito a mao, nao importado de config.
    caminho = escrever(tmp_path, "[precos_alvo]\nbroche = 188\n")
    assert carregar_config(caminho).fracao_sanidade == 0.25

def test_preco_alvo_nao_inteiro_e_recusado(tmp_path):
    caminho = escrever(tmp_path, '[precos_alvo]\nbroche = "188"\n')
    with pytest.raises(ValueError, match="broche"):
        carregar_config(caminho)

def test_preco_alvo_zero_ou_negativo_e_recusado(tmp_path):
    # Preco-alvo 0 nunca compra e Preco-alvo negativo e erro de digitacao;
    # os dois sao mais uteis como erro do que como configuracao silenciosa.
    for valor in ("0", "-188"):
        caminho = escrever(tmp_path, f"[precos_alvo]\nbroche = {valor}\n")
        with pytest.raises(ValueError, match="broche"):
            carregar_config(caminho)

@pytest.mark.parametrize("valor", ["0", "1", "1.5", "-0.25"])
def test_fracao_de_sanidade_fora_de_zero_a_um_e_recusada(tmp_path, valor):
    caminho = escrever(tmp_path, f"[precos_alvo]\nbroche = 188\nfracao_sanidade = {valor}\n")
    with pytest.raises(ValueError, match="fracao_sanidade"):
        carregar_config(caminho)

def test_arquivo_inexistente_diz_qual_arquivo(tmp_path):
    with pytest.raises(ValueError, match="nao-existe.toml"):
        carregar_config(tmp_path / "nao-existe.toml")

def test_toml_invalido_diz_qual_arquivo(tmp_path):
    caminho = escrever(tmp_path, "[precos_alvo\nbroche = 188\n")
    with pytest.raises(ValueError, match=r"config\.toml"):
        carregar_config(caminho)
