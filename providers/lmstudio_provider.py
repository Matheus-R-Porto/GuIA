import httpx
from config import LMSTUDIO_BASE_URL, LMSTUDIO_MODEL
from prompt import SYSTEM_PROMPT, SYSTEM_PROMPT_COMPACT


class LMStudioProvider:
    label = f"lmstudio/{LMSTUDIO_MODEL}"

    def __init__(self):
        self._base_url = LMSTUDIO_BASE_URL.rstrip("/")

    def ping(self):
        """Lança exceção se o servidor não estiver acessível."""
        httpx.get(f"{self._base_url}/models", timeout=3.0).raise_for_status()

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 400) -> str:
        # Usa prompt compacto — modelos locais pequenos seguem melhor instruções curtas.
        # O engine pode anexar uma personalização (ex: nome do aluno) ao SYSTEM_PROMPT;
        # trocamos a base para a compacta, mas preservamos esse trecho extra do final.
        # Chamadas que usam um prompt PRÓPRIO (ex: geração de título, que não é o
        # tutor) não começam com SYSTEM_PROMPT — nesse caso usamos o prompt como veio,
        # em vez de forçar o prompt compacto do tutor por cima dele.
        if system_prompt and system_prompt.startswith(SYSTEM_PROMPT):
            extra = system_prompt[len(SYSTEM_PROMPT):]
            base = SYSTEM_PROMPT_COMPACT + extra
        else:
            base = system_prompt or SYSTEM_PROMPT_COMPACT
        # /no_think desativa o modo de raciocínio extendido do Qwen3 (muito mais rápido)
        full_messages = [{"role": "system", "content": base + "\n/no_think"}] + messages
        payload = {
            "model": LMSTUDIO_MODEL,
            "messages": full_messages,
            "temperature": 0.5,
            "max_tokens": max_tokens,
            # Desativa modo de raciocínio extendido do Qwen3 (evita timeout por <think> longo)
            "enable_thinking": False,
        }
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            timeout=180.0,  # 3 minutos — modelos locais podem ser lentos
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
