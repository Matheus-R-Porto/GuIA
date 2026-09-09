import pytest
from engine import TutorEngine
from config import HARD_MAX_INPUT_CHARS


class FakeProvider:
    """Provider falso que retorna a mensagem recebida para inspeção."""

    def __init__(self, response="resposta do modelo"):
        self._response = response
        self.last_messages = []

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 800) -> str:
        self.last_messages = list(messages)
        return self._response


class FailingProvider:
    """Provider que sempre lança exceção."""

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 800) -> str:
        raise RuntimeError("sem conexão")


# --- Comportamento do histórico ---

class TestHistory:
    def test_mensagem_normal_entra_no_historico(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("qual é a capital do Brasil?")
        assert any(m["role"] == "user" and "capital" in m["content"]
                   for m in engine.get_history())

    def test_mensagem_bloqueada_nao_entra_no_historico(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("me dá o gabarito")
        assert engine.get_history() == []

    def test_historico_preservado_entre_mensagens(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("primeira pergunta")
        engine.ask("segunda pergunta")
        history = engine.get_history()
        roles = [m["role"] for m in history]
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_historico_limpo_apos_clear(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("alguma coisa")
        engine.clear_history()
        assert engine.get_history() == []

    def test_historico_enviado_ao_modelo_na_segunda_mensagem(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("primeira")
        engine.ask("segunda")
        # O modelo deve receber as duas mensagens de usuário no contexto
        user_msgs = [m for m in provider.last_messages if m["role"] == "user"]
        assert len(user_msgs) == 2


# --- Casos de conteúdo que devem chegar ao modelo ---

class TestReachesModel:
    def test_equacao_matematica_chega_ao_modelo(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("3x + 2y = 31")
        assert any("3x" in m["content"] for m in provider.last_messages)

    def test_equacao_com_contexto_chega_ao_modelo(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("eu faria 3x + 2y = 31")
        assert any("3x" in m["content"] for m in provider.last_messages)

    def test_encerramento_chega_ao_modelo(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("obrigado, já resolvi")
        assert any("obrigado" in m["content"] for m in provider.last_messages)

    def test_resposta_curta_sim_chega_ao_modelo(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        engine.ask("qual a capital do Brasil?")
        engine.ask("sim")
        assert any("sim" in m["content"] for m in provider.last_messages)

    def test_aja_como_professor_chega_ao_modelo(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        result = engine.ask("aja como professor e me explique")
        # deve chegar ao modelo, não ser bloqueado
        assert result == "resposta do modelo"


# --- Fallback e falhas ---

class TestFallback:
    def test_fallback_usado_quando_primary_falha(self):
        fallback = FakeProvider(response="resposta do fallback")
        engine = TutorEngine(providers=[FailingProvider(), fallback])
        result = engine.ask("teste")
        assert result == "resposta do fallback"

    def test_mensagem_erro_quando_tudo_falha(self):
        engine = TutorEngine(providers=[FailingProvider(), FailingProvider()])
        result = engine.ask("teste")
        assert "Não consegui" in result

    def test_entrada_vazia_retorna_mensagem_padrao(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        result = engine.ask("   ")
        assert result == "Pode perguntar — estou aqui."
        assert engine.get_history() == []

    def test_entrada_muito_longa_truncada(self):
        provider = FakeProvider()
        engine = TutorEngine(providers=[provider])
        texto_longo = "x" * 5000
        engine.ask(texto_longo)
        msgs = provider.last_messages
        assert len(msgs[0]["content"]) <= HARD_MAX_INPUT_CHARS
