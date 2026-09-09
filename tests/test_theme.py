import theme


def test_cor_padrao_mantem_o_azul_original():
    qss_light = theme.stylesheet("light")
    assert "#1565C0" in qss_light
    assert "rgba(21, 101, 192," in qss_light


def test_cor_customizada_troca_forma_hex_no_tema_claro():
    qss = theme.stylesheet("light", accent="#00A86B")
    assert "#1565C0" not in qss
    assert "#00A86B" in qss


def test_cor_customizada_troca_forma_rgba():
    qss = theme.stylesheet("light", accent="#00A86B")
    # #00A86B -> rgb(0, 168, 107)
    assert "rgba(21, 101, 192," not in qss
    assert "rgba(0, 168, 107," in qss


def test_cor_customizada_no_tema_escuro_fica_clareada_para_contraste():
    qss_dark = theme.stylesheet("dark", accent="#00A86B")
    # não deve sobrar nem o azul padrão nem o verde puro sem clareamento
    assert "#1565C0" not in qss_dark
    assert "#5AA2E8" not in qss_dark  # variante escura do azul padrão
    assert "#00A86B" not in qss_dark  # foi clareado, não usado puro
    # rgba continua com o RGB exato escolhido (não é clareado, por design)
    assert "rgba(0, 168, 107," in qss_dark


def test_cor_padrao_explicita_nao_muda_nada():
    assert theme.stylesheet("light", accent="#1565C0") == theme.stylesheet("light")
    assert theme.stylesheet("dark", accent=None) == theme.stylesheet("dark")
