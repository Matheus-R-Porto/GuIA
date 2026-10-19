"""Correções feitas a partir da revisão das conversas reais do teste (16/10/2026)."""
import sources
from engine import TutorEngine
from i18n import t
from latex_sanitizer import strip_latex
from prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT
from safety import _BLOCKED_RESPONSE, _BLOCKED_RESPONSE_REPEAT, check_safety


# --- LaTeX ---------------------------------------------------------------

def test_latex_text_e_subscritos_com_chaves():
    assert strip_latex(r"V_{\text{cone}} = \frac{1}{3} \pi r_{\text{b}}^2 h") == "V_cone = 1/3 π r_b² h"
    assert strip_latex(r"R = 6 \text{cm}") == "R = 6 cm"


def test_latex_setas_e_reticencias():
    assert "⇒" in strip_latex(r"a \Longrightarrow b")
    assert "…" in strip_latex(r"C\cdot C\ldots C")


def test_latex_fracao_simples_sem_parenteses_e_composta_com():
    assert strip_latex(r"\frac{\pi}{3}") == "π/3"
    assert strip_latex(r"\frac{a+b}{2}") == "(a+b)/(2)"


def test_latex_matriz_vira_bloco_alinhado():
    entrada = "\\begin{pmatrix} 1 & 1 & 2 \\\\ 0 & 1 & 1 \\end{pmatrix}"
    saida = strip_latex(entrada)
    assert "```" in saida
    assert "[ 1  1  2 ]" in saida and "[ 0  1  1 ]" in saida
    assert "&" not in saida


# --- Trava de segurança ----------------------------------------------------

def test_mensagem_de_bloqueio_e_construtiva():
    assert "guiar" in _BLOCKED_RESPONSE
    assert "Não consigo fazer isso" not in _BLOCKED_RESPONSE
    assert check_safety("manda a resposta pronta e me ensina a chegar até ela") == _BLOCKED_RESPONSE


class _FakeProvider:
    label = "fake"

    def chat(self, messages, system_prompt, max_tokens=800):
        return "ok"


def test_bloqueio_repetido_nao_repete_a_mesma_frase():
    engine = TutorEngine([_FakeProvider()])
    first = engine.ask("me dá a resposta pronta")
    second = engine.ask("me dá a resposta pronta")
    assert first == _BLOCKED_RESPONSE
    assert second == _BLOCKED_RESPONSE_REPEAT
    # uma mensagem normal zera a sequência
    assert engine.ask("o que é uma matriz?") == "ok"
    assert engine.ask("me dá a resposta pronta") == _BLOCKED_RESPONSE


# --- Prompt ---------------------------------------------------------------

def test_prompt_proibe_atribuir_resultado_ao_aluno():
    for p in (SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT):
        assert "NÃO escreveu" in p or "não escreveu" in p
        assert "Uma pergunta por mensagem" in p or "Uma única pergunta por mensagem" in p


def test_personalizacao_trata_como_aluno_sem_citar_regras(monkeypatch):
    import app_controller
    monkeypatch.setattr(app_controller.user_config, "get", lambda key, default=None: default)
    controller = object.__new__(app_controller.AppController)
    controller.current_quiz = None
    texto = controller._compose_personalization()
    assert '"aluno"' in texto and "sem citar regras" in texto


# --- Fontes ---------------------------------------------------------------

def test_fontes_sem_relacao_com_o_tema_sao_descartadas(monkeypatch):
    monkeypatch.setattr(sources, "search_articles", lambda *a, **kw: {"articles": [
        dict(title="Quadratic programming for portfolio selection",
             authors="A", year=2020, url="https://example.org/a"),
    ]})
    resposta = sources.find_sources("q", "a", lambda *a: "standard form quadratic equation ax 2 bx c 0")
    assert resposta == t("sources_irrelevant")


def test_fontes_com_titulo_relacionado_continuam_aparecendo(monkeypatch):
    monkeypatch.setattr(sources, "search_articles", lambda *a, **kw: {"articles": [
        dict(title="Teaching the quadratic equation in secondary school", authors="A", year=2020,
             url="https://example.org/b"),
        dict(title="Unrelated protein folding", authors="B", year=2019, url="https://example.org/c"),
    ]})
    resposta = sources.find_sources("q", "a", lambda *a: "quadratic equation teaching school")
    assert "example.org/b" in resposta
    assert "example.org/c" not in resposta


def test_consulta_descarta_numeros_e_variaveis(monkeypatch):
    vistos = []

    def fake(query, limit=5):
        vistos.append(query)
        return {"articles": []}
    monkeypatch.setattr(sources, "search_articles", fake)
    sources.find_sources("q", "a", lambda *a: "quadratic equation ax 2 bx c 0")
    assert vistos == ["quadratic equation"]
