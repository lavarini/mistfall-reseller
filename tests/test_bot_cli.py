"""O CLI do laco. Nao importa windows: a suite roda no macOS."""

from ferramentas.bot_cli import montar_parser


def test_o_parser_aceita_pasta_config_e_espera_modal():
    args = montar_parser().parse_args(
        ["--pasta", "sessao", "--config", "outro.toml", "--espera-modal", "150"])
    assert args.pasta == "sessao"
    assert args.config == "outro.toml"
    assert args.espera_modal == 150


def test_a_pasta_padrao_nao_e_a_do_piloto():
    # Duas ferramentas, dois destinos: o bot nao pode sobrescrever a pasta de
    # depuracao do mistfall-piloto.
    assert montar_parser().parse_args([]).pasta != "execucao"
