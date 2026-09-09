from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, STUDY_MODE, STUDY_TEMPERATURE


class OpenAIProvider:
    label = f"openai/{OPENAI_MODEL}"

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não definida no .env")
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 800) -> str:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        temperature = STUDY_TEMPERATURE if STUDY_MODE else 0.4
        response = self._client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()

        if choice.finish_reason == "length":
            raise RuntimeError("Resposta truncada pelo limite de tokens.")

        if not content:
            raise RuntimeError("Resposta vazia recebida do modelo.")

        return content
