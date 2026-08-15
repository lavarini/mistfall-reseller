"""Cobertura de `carregar_config`.

Estes numeros decidem gasto de ouro real e nunca tinham passado pela suite.
Os Precos-alvo sao literais escritos a mao, conferidos contra config.toml.
"""
import pytest
from mistfall.config import carregar_config, validar_precos_venda
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

def test_todo_item_alvo_tem_preco_alvo_no_config_do_projeto():
    # Item-alvo sem Preco-alvo nunca e comprado: `escolher` o ignora em silencio.
    assert set(carregar_config("config.toml").precos_alvo) == set(ItemAlvo)

def test_carrega_os_sete_precos_de_venda_do_config_do_projeto():
    config = carregar_config("config.toml")
    assert config.precos_venda == {
        ItemAlvo.BROCHE: 226,
        ItemAlvo.ADAGA: 239,
        ItemAlvo.LANTERNA: 281,
        ItemAlvo.DRAGAO: 295,
        ItemAlvo.ORBE: 304,
        ItemAlvo.REDE: 312,
        ItemAlvo.CODICE: 338,
    }
    validar_precos_venda(config)

def test_compra_aceita_config_sem_precos_de_venda(tmp_path):
    config = carregar_config(escrever(tmp_path, "[precos_alvo]\nbroche = 188\n"))
    assert config.precos_venda == {}

def test_venda_exige_os_sete_precos(tmp_path):
    config = carregar_config(escrever(
        tmp_path,
        "[precos_alvo]\nbroche = 188\n[precos_venda]\nbroche = 226\n",
    ))
    with pytest.raises(ValueError, match="faltam Precos de Venda"):
        validar_precos_venda(config)

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

@pytest.mark.parametrize("valor", ['"226"', "true", "0", "-226"])
def test_preco_de_venda_invalido_e_recusado(tmp_path, valor):
    caminho = escrever(
        tmp_path,
        f"[precos_alvo]\nbroche = 188\n[precos_venda]\nbroche = {valor}\n",
    )
    with pytest.raises(ValueError, match=r"precos_venda.*broche"):
        carregar_config(caminho)

def test_item_desconhecido_em_precos_de_venda_e_recusado(tmp_path):
    caminho = escrever(
        tmp_path,
        "[precos_alvo]\nbroche = 188\n[precos_venda]\nespelho = 237\n",
    )
    with pytest.raises(ValueError, match=r"precos_venda.*espelho"):
        carregar_config(caminho)

def test_arquivo_inexistente_diz_qual_arquivo(tmp_path):
    with pytest.raises(ValueError, match="nao-existe.toml"):
        carregar_config(tmp_path / "nao-existe.toml")

def test_toml_invalido_diz_qual_arquivo(tmp_path):
    caminho = escrever(tmp_path, "[precos_alvo\nbroche = 188\n")
    with pytest.raises(ValueError, match=r"config\.toml"):
        carregar_config(caminho)

def test_config_real_nao_declara_fracao_de_sanidade():
    assert not hasattr(carregar_config("config.toml"), "fracao_sanidade")

def test_config_real_declara_trabalhadores():
    assert carregar_config("config.toml").trabalhadores == 4

def test_trabalhadores_ausente_usa_o_padrao(tmp_path):
    arquivo = tmp_path / "c.toml"
    arquivo.write_text("[precos_alvo]\nbroche = 188\n", encoding="utf-8")
    assert carregar_config(arquivo).trabalhadores == 4

def test_trabalhadores_invalido_diz_o_arquivo_e_a_chave(tmp_path):
    arquivo = tmp_path / "c.toml"
    arquivo.write_text("trabalhadores = 0\n[precos_alvo]\nbroche = 188\n", encoding="utf-8")
    with pytest.raises(ValueError, match="trabalhadores"):
        carregar_config(arquivo)
