import time
import sys

from prompt import SYSTEM_PROMPT, PROMPT_PROFESSOR, PROMPT_LIBRARY
from safety import check_safety_verbose
from latex_sanitizer import strip_latex
from config import MAX_HISTORY_MESSAGES, HARD_MAX_INPUT_CHARS, STUDY_MODE

_MAX_RETRIES = 5
_RETRY_DELAY = 3

_TITLE_SYSTEM_PROMPT = (
    "Você gera títulos curtos para conversas de chat. Dada a primeira mensagem "
    "do usuário, responda APENAS com um título de 2 a 5 palavras que resuma o "
    "assunto — sem aspas, sem ponto final, sem emojis, sem explicações. "
    "Exemplos de bons títulos: \"Saudação\", \"Equação do 2º grau\", "
    "\"Revolução Francesa\", \"Cálculo de área\", \"Fotossíntese\"."
)


def quick_title(text: str) -> str:
    """Título instantâneo (sem chamar o modelo), a partir das primeiras
    palavras da mensagem. Usado como título provisório e como fallback caso a
    geração via modelo falhe."""
    words = (text or "").strip().split()
    snippet = " ".join(words[:6])
    if len(snippet) > 48:
        snippet = snippet[:48].rstrip() + "…"
    if not snippet:
        return "Nova conversa"
    return snippet[:1].upper() + snippet[1:]


class TutorEngine:
    def __init__(self, providers: list, primary_provider=None, fallback_provider=None):
        if providers:
            self._providers = providers
        else:
            self._providers = [p for p in [primary_provider, fallback_provider] if p]
        self._history: list[dict] = []
        self._providers_used: set[str] = set()
        self._personalization = ""
        self._mode = "aluno"
        # Padrão de regex que disparou o bloqueio no último ask() (None se não
        # bloqueou) — lido pelo app_controller logo após ask() para registrar
        # em SafetyBlock, dado bruto para a pesquisa do TCC.
        self.last_block_pattern: str | None = None

    def set_providers(self, providers: list):
        """Troca a lista de providers (ex: quando o usuário muda a chave de API)."""
        if providers:
            self._providers = providers

    def set_personalization(self, text: str):
        """Define o trecho de personalização anexado ao prompt (nome, nível, etc.).

        A composição do texto fica no app_controller, que lê o user_config — assim
        novos itens de config (idioma, etc.) entram num lugar só.
        """
        self._personalization = text or ""

    def set_mode(self, mode: str):
        """"aluno" (padrão, tutor socrático), "professor" (assistente direto
        de planejamento — só deve ser usado com contas role="professor",
        verificadas por código de instituição; quem decide isso é o
        app_controller, não o engine) ou "library" (conversa sobre artigo
        científico da Biblioteca — socrático mais leve, disponível pra
        qualquer perfil)."""
        self._mode = mode if mode in ("aluno", "professor", "library") else "aluno"

    def ask(self, user_text: str) -> str:
        text = user_text.strip()
        self.last_block_pattern = None

        if not text:
            return "Pode perguntar — estou aqui."

        if len(text) > HARD_MAX_INPUT_CHARS:
            text = text[:HARD_MAX_INPUT_CHARS]

        blocked, pattern = check_safety_verbose(text, mode=self._mode)
        if blocked:
            self.last_block_pattern = pattern
            return blocked

        self._history.append({"role": "user", "content": text})
        self._trim_history()

        response = self._call_with_retry(self._history)

        self._history.append({"role": "assistant", "content": response})
        return response

    def load_history(self, messages: list[dict]):
        """Substitui o histórico em memória (ex: ao carregar uma conversa salva
        do banco). Aplica o mesmo corte de tamanho do histórico normal."""
        self._history = list(messages)
        self._trim_history()

    def generate_title(self, first_message: str) -> str:
        """Gera um título curto para a conversa a partir da primeira mensagem.

        Tenta os providers configurados (mesma ordem/prioridade do chat normal);
        se todos falharem, cai no título instantâneo por truncamento."""
        text = (first_message or "").strip()
        if not text:
            return "Nova conversa"

        for provider in self._providers:
            try:
                title = provider.chat(
                    [{"role": "user", "content": text[:300]}], _TITLE_SYSTEM_PROMPT
                )
                title = title.strip().strip('"').strip("'").rstrip(".")
                if title:
                    return title[:60]
            except Exception as e:
                name = type(provider).__name__
                print(f"[GuIA] geração de título falhou em {name}: {e}", file=sys.stderr)

        return quick_title(text)

    def get_history(self) -> list[dict]:
        return list(self._history)

    def clear_history(self):
        self._history.clear()
        self._providers_used.clear()

    def get_providers_used(self) -> list[str]:
        return sorted(self._providers_used)

    def _trim_history(self):
        if len(self._history) > MAX_HISTORY_MESSAGES:
            self._history = self._history[-MAX_HISTORY_MESSAGES:]

    def _call_with_retry(self, messages: list[dict]) -> str:
        if self._mode == "professor":
            base_prompt = PROMPT_PROFESSOR
        elif self._mode == "library":
            base_prompt = PROMPT_LIBRARY
        else:
            base_prompt = SYSTEM_PROMPT
        # Modo professor e modo library pedem conteúdo mais completo (plano
        # de aula/gabarito, ou explicação de conceitos de um artigo) do que
        # as respostas curtas do modo socrático — precisam de mais espaço
        # para não truncar no meio.
        max_tokens = 2000 if self._mode in ("professor", "library") else 800
        for attempt in range(_MAX_RETRIES):
            for i, provider in enumerate(self._providers):
                try:
                    response = provider.chat(
                        messages, base_prompt + self._personalization, max_tokens=max_tokens
                    )
                    if response:
                        self._providers_used.add(
                            getattr(provider, "label", type(provider).__name__)
                        )
                        return strip_latex(response)
                except Exception as e:
                    name = type(provider).__name__
                    print(f"[GuIA] {name} falhou (tentativa {attempt + 1}): {e}", file=sys.stderr)
                    if STUDY_MODE and i == 0:
                        raise RuntimeError(
                            f"[STUDY_MODE] Provider primário falhou. Erro: {e}"
                        )

            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)

        return "Não consegui obter uma resposta. Verifique sua conexão e tente novamente."
