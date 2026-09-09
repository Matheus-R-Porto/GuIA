import user_config
from i18n import _STRINGS, t


def test_idioma_padrao_e_portugues(monkeypatch):
    monkeypatch.setattr(user_config, "get", lambda key, default=None: "pt")
    assert t("cancel_btn") == "Cancelar"


def test_troca_de_idioma_muda_o_texto(monkeypatch):
    monkeypatch.setattr(user_config, "get", lambda key, default=None: "en")
    assert t("cancel_btn") == "Cancel"
    monkeypatch.setattr(user_config, "get", lambda key, default=None: "es")
    assert t("cancel_btn") == "Cancelar"  # espanhol e português coincidem aqui


def test_placeholder_e_preenchido():
    assert "{" not in t("message_too_long_body", exceeded=42)
    assert "42" in t("message_too_long_body", exceeded=42)


def test_chave_desconhecida_devolve_a_propria_chave():
    assert t("essa_chave_nao_existe") == "essa_chave_nao_existe"


def test_catalogo_completo_pt_en_es():
    """Toda entrada do catálogo precisa ter as 3 traduções — evita esquecer
    um idioma ao adicionar uma chave nova."""
    faltando = [
        chave for chave, traducoes in _STRINGS.items()
        if not all(traducoes.get(lang) for lang in ("pt", "en", "es"))
    ]
    assert faltando == []


def test_templates_tem_os_mesmos_placeholders_nos_3_idiomas():
    """Um template que usa {nome} em pt precisa usar o mesmo {nome} em en/es
    (senão t(key, **kwargs) quebra com KeyError num idioma só)."""
    import re
    placeholder_re = re.compile(r"\{(\w+)\}")
    for chave, traducoes in _STRINGS.items():
        conjuntos = {lang: set(placeholder_re.findall(texto)) for lang, texto in traducoes.items()}
        primeiro = next(iter(conjuntos.values()))
        assert all(s == primeiro for s in conjuntos.values()), f"placeholders divergentes em {chave!r}: {conjuntos}"
