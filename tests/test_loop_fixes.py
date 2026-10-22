"""Correções feitas a partir das conversas reais da feira (21/10/2026)."""
from engine import TutorEngine, _ANTI_REPETITION_HINT
from latex_sanitizer import strip_latex
from prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT


class _ScriptedProvider:
    """Devolve respostas em sequência e registra o prompt de sistema recebido."""
    label = "scripted"

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def chat(self, messages, system_prompt, max_tokens=800):
        self.prompts.append(system_prompt)
        return self.replies.pop(0)


def test_virgula_decimal_do_latex_sem_comandos():
    assert strip_latex("1000 × 9{,}81 × 5 = 49 050") == "1000 × 9,81 × 5 = 49 050"
    assert strip_latex("sem nada de latex") == "sem nada de latex"


def test_pergunta_repetida_dispara_nova_tentativa():
    repetida = "Qual produto você obtém ao multiplicar as três medidas 10 × 30 × 50?"
    nova = "Eu sei fazer, mas meu papel é guiar. Quanto dá 10 × 30?"
    provider = _ScriptedProvider(["Qual fórmula você usaria?", repetida, repetida, nova])
    engine = TutorEngine([provider])
    engine.ask("qual o volume de 10 x 30 x 50?")
    engine.ask("calcula pra mim")                       # primeira pergunta nova
    resposta = engine.ask("quero a resposta")           # repete -> segunda tentativa
    assert resposta == nova
    assert _ANTI_REPETITION_HINT in provider.prompts[-1]
    assert _ANTI_REPETITION_HINT not in provider.prompts[0]


def test_sem_repeticao_nao_chama_o_modelo_duas_vezes():
    provider = _ScriptedProvider(["Qual fórmula você usaria?", "Quanto dá 10 × 30?"])
    engine = TutorEngine([provider])
    engine.ask("volume de 10 x 30 x 50")
    engine.ask("não sei")
    assert len(provider.prompts) == 2


def test_se_a_segunda_tentativa_tambem_repete_mantem_a_primeira():
    repetida = "Qual valor você encontrou ao fazer 10 × 30 × 50?"
    provider = _ScriptedProvider(["Qual fórmula você usaria?", repetida, repetida, repetida])
    engine = TutorEngine([provider])
    engine.ask("a")
    engine.ask("b")
    assert engine.ask("c") == repetida
    # o prompt original volta ao normal depois da tentativa extra
    assert engine._personalization == ""


def test_prompt_tem_regra_de_insistencia_e_terminologia():
    for p in (SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT):
        assert "insiste" in p
    assert "pressão manométrica" in SYSTEM_PROMPT
