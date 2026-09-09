import sys

from engine import TutorEngine, quick_title
from chat_exporter import export_chat
from providers import (
    GroqProvider, LMStudioProvider, OpenAIProvider, OpenAICompatibleProvider,
)
from config import OPENAI_API_KEY, GROQ_API_KEY, GROQ_MODEL, OPENAI_MODEL
import user_config
import db
from lang_detect import detect_language


def _api_signature() -> tuple:
    return (
        user_config.get("api_base_url", ""),
        user_config.get("api_key", ""),
        user_config.get("api_model", ""),
    )


class AppController:
    def __init__(self):
        self._model_info = ""
        providers = self._build_providers()
        if not providers:
            raise RuntimeError(
                "Nenhum provider disponível. Configure uma chave de API nas "
                "configurações, defina GROQ_API_KEY no .env ou inicie o LM Studio."
            )
        self._api_sig = _api_signature()
        self._engine = TutorEngine(providers=providers)
        self.user_id = None
        self.user_role = None
        self.current_mode = "aluno"
        self.current_conversation_id = None
        self.current_article = None
        self.reload_settings()

        db.init_db()
        db.seed_test_institution()

    # --- perfis / login ---

    def list_profiles(self) -> list[dict]:
        return db.list_users()

    def create_profile(self, name: str, password: str, institution_code: str = "") -> dict:
        return db.create_user(name, password, institution_code)

    def check_password(self, user_id: int, password: str) -> bool:
        return db.check_user_password(user_id, password)

    def set_active_user(self, user_id: int):
        """Troca o perfil ativo — limpa a conversa em memória (cada perfil
        tem seu próprio histórico, não faz sentido misturar contexto)."""
        user = db.get_user(user_id)
        if user is None:
            raise ValueError(f"Perfil {user_id} não encontrado.")
        self.user_id = user["id"]
        self.user_role = user["role"]
        self.current_conversation_id = None
        self.current_article = None
        self._engine.clear_history()
        # Sempre volta pro modo aluno numa sessão nova, mesmo pra quem é
        # professor — evita continuar sem querer no modo direto (sem o
        # guard socrático) por ter esquecido ligado da vez anterior.
        self.set_mode("aluno")

    def set_mode(self, mode: str):
        """Troca entre "aluno" (padrão, socrático) e "professor" (assistente
        direto). "professor" só é aceito se o perfil ativo tiver essa role —
        o modo nunca é o que destrava o papel, é o oposto: o papel (validado
        por código de instituição) é que autoriza o modo."""
        if mode == "professor" and self.user_role != "professor":
            mode = "aluno"
        self.current_mode = mode
        self._engine.set_mode(mode)
        self._engine.set_personalization(self._compose_personalization())

    def _build_providers(self) -> list:
        """Monta a lista de providers na ordem de prioridade.

        1. API configurada pelo usuário (settings) — se completa.
        2. Caso contrário, providers do .env (dev): OpenAI, Groq.
        3. LM Studio local sempre por último (fallback grátis).
        """
        providers = []
        self._model_info = ""

        base, key, model = _api_signature()
        if base and key and model:
            try:
                providers.append(OpenAICompatibleProvider(base, key, model))
                self._model_info = f"api/{model}"
            except Exception as e:
                print(f"[GuIA] API do usuário indisponível: {e}", file=sys.stderr)
        else:
            if OPENAI_API_KEY:
                try:
                    providers.append(OpenAIProvider())
                    if not self._model_info:
                        self._model_info = f"openai/{OPENAI_MODEL}"
                except Exception as e:
                    print(f"[GuIA] OpenAI indisponível: {e}", file=sys.stderr)
            if GROQ_API_KEY:
                try:
                    providers.append(GroqProvider())
                    if not self._model_info:
                        self._model_info = f"groq/{GROQ_MODEL}"
                except Exception as e:
                    print(f"[GuIA] Groq indisponível: {e}", file=sys.stderr)

        try:
            candidate = LMStudioProvider()
            candidate.ping()
            providers.append(candidate)
            if not self._model_info:
                self._model_info = "lmstudio/local"
        except Exception as e:
            print(f"[GuIA] LM Studio indisponível: {e}", file=sys.stderr)

        return providers

    def _compose_personalization(self, detected_lang: str | None = None) -> str:
        """Monta o trecho de personalização do prompt a partir do user_config.

        Ponto único onde os itens de config que influenciam o comportamento do
        tutor (nome, nível de ensino, futuramente idioma) são reunidos.
        """
        parts = []

        name = user_config.get("user_name", "").strip()
        if name:
            parts.append(
                f"O nome do aluno é {name}. Use o nome dele de forma natural ao longo da "
                f"conversa — sempre na saudação inicial e ao validar, elogiar ou encorajar "
                f"(ex.: \"Boa, {name}!\"). Não precisa usar em toda frase, mas faça com que "
                f"fique claro que você sabe o nome dele. Nunca invente outro nome."
            )

        if self.current_mode == "library" and self.current_article:
            art = self.current_article
            info = f"Título: {art.get('title', '')}\n"
            if art.get("authors"):
                info += f"Autores: {art['authors']}\n"
            if art.get("year"):
                info += f"Ano: {art['year']}\n"
            if art.get("abstract"):
                info += f"Resumo: {art['abstract']}\n"
            parts.append(
                "O aluno está discutindo o seguinte artigo científico, que ele "
                "encontrou na busca da Biblioteca:\n" + info +
                "Use esse contexto pra guiar a conversa desde a primeira "
                "resposta — não pergunte qual artigo é, você já sabe."
            )

        # O nível de ensino calibra a FORMA da dica socrática — não faz
        # sentido no modo professor, que já responde de forma direta.
        if self.current_mode != "professor":
            level_names = {"fundamental": "fundamental", "medio": "médio", "superior": "superior"}
            level = user_config.get("education_level", "")
            if level in level_names:
                parts.append(
                    f"O aluno está no ensino {level_names[level]}. Ajuste o vocabulário e a "
                    f"profundidade das explicações e dicas a esse nível — mais simples e concreto "
                    f"nos níveis iniciais, mais aprofundado nos avançados. Isso muda APENAS a "
                    f"forma da dica; nunca entregue a resposta pronta, seja qual for o nível."
                )
            else:
                # Modo automático: sem nível informado, o GuIA infere pela conversa.
                parts.append(
                    "Nenhum nível de ensino foi informado: deduza o nível do aluno pela forma "
                    "como ele escreve e pergunta, e ajuste o vocabulário e a profundidade "
                    "dinamicamente ao longo da conversa. Isso muda APENAS a forma da explicação "
                    "e das dicas; nunca entregue a resposta pronta, seja qual for o nível."
                )

        lang_names = {"pt": "português", "en": "inglês", "es": "espanhol"}
        lang = user_config.get("response_language", "auto")
        if lang in lang_names:
            parts.append(
                f"Responda SEMPRE em {lang_names[lang]}, independentemente do idioma em "
                f"que o aluno escrever."
            )
        elif detected_lang in lang_names:
            # Modo automático com idioma detectado na última mensagem: reforça
            # explicitamente, porque o prompt inteiro em português tende a
            # "puxar" o modelo de volta ao português em mensagens curtas.
            parts.append(
                f"A mensagem mais recente do aluno está em {lang_names[detected_lang]}. "
                f"Responda nesse mesmo idioma."
            )
        # "auto" sem detecção clara não injeta nada — o modelo decide sozinho.

        if not parts:
            return ""
        return "\n\n[Personalização]\n" + "\n".join(parts)

    def reload_settings(self):
        """Relê as preferências do usuário e aplica no engine (sem reiniciar)."""
        self._engine.set_personalization(self._compose_personalization())
        # Só reconstrói providers se a config de API mudou (evita re-pingar à toa).
        if _api_signature() != self._api_sig:
            new_providers = self._build_providers()
            if new_providers:
                self._engine.set_providers(new_providers)
                self._api_sig = _api_signature()

    def ask(self, text: str) -> str:
        stripped = text.strip()

        if stripped and user_config.get("response_language", "auto") == "auto":
            detected = detect_language(stripped)
            if detected:
                self._engine.set_personalization(self._compose_personalization(detected))

        response = self._engine.ask(text)

        if not stripped:
            return response  # entrada vazia: nada a persistir (engine também ignora)

        if self.current_conversation_id is None:
            self.current_conversation_id = db.create_conversation(
                self.user_id, title=quick_title(stripped), provider_used=self._model_info
            )

        user_message_id = db.add_message(self.current_conversation_id, "user", stripped)
        db.add_message(self.current_conversation_id, "assistant", response)

        if self._engine.last_block_pattern is not None:
            db.log_safety_block(user_message_id, self._engine.last_block_pattern)

        return response

    def generate_title(self, first_message: str) -> str:
        """Gera (via modelo) um título melhor para a conversa atual."""
        return self._engine.generate_title(first_message)

    def rename_conversation(self, conversation_id: int, title: str):
        db.rename_conversation(conversation_id, title)

    def delete_conversation(self, conversation_id: int):
        db.delete_conversation(conversation_id)
        if self.current_conversation_id == conversation_id:
            self.current_conversation_id = None
            self._engine.clear_history()

    def list_conversations(self) -> list[dict]:
        return db.list_conversations(self.user_id)

    def load_conversation(self, conversation_id: int) -> list[dict]:
        """Carrega uma conversa salva: repassa o histórico para o engine (para
        que a continuação tenha contexto) e retorna as mensagens para a UI."""
        messages = db.get_conversation_messages(conversation_id)
        self._engine.load_history(messages)
        self.current_conversation_id = conversation_id
        return messages

    def new_chat(self):
        self._auto_export()
        self._engine.clear_history()
        self.current_conversation_id = None
        # "Novo Chat" comum sai do modo library (que só faz sentido atrelado
        # a um artigo específico) — evita continuar sem querer nesse modo
        # numa conversa qualquer, sem contexto de artigo nenhum.
        if self.current_mode == "library":
            self.current_article = None
            self.set_mode("aluno")

    def start_library_chat(self, article: dict):
        """Inicia uma conversa nova já no modo Biblioteca, com o contexto
        do artigo (título, autores, resumo) injetado na personalização —
        a IA já "sabe" do artigo desde a primeira resposta, sem precisar
        de RAG: o resumo cabe tranquilo no espaço de contexto normal."""
        self._auto_export()
        self._engine.clear_history()
        self.current_conversation_id = None
        self.current_article = article
        self.set_mode("library")

    def close(self):
        self._auto_export()

    def _auto_export(self):
        history = self._engine.get_history()
        if history:
            used = self._engine.get_providers_used()
            model_info = ", ".join(used) if used else self._model_info
            export_chat(history, fmt="txt", model_info=model_info)
