"""Provider genérico para qualquer API compatível com OpenAI.

Cobre Groq, OpenAI, OpenRouter, Together, e o próprio LM Studio — todos expõem
o mesmo formato /chat/completions. O usuário informa base_url + chave + modelo
nas configurações. Reutiliza o tratamento de ferramentas e o fix da tag
<function> do groq_provider.
"""
import json
import sys

from openai import OpenAI, BadRequestError

from config import STUDY_MODE, STUDY_TEMPERATURE
from tools import ALL_TOOLS, run_tool
from providers.groq_provider import _parse_xml_tool_calls, _FUNCTION_TAG_CLEANUP_RE


class OpenAICompatibleProvider:
    _MAX_TOOL_ROUNDS = 5

    def __init__(self, base_url: str, api_key: str, model: str):
        if not (base_url and api_key and model):
            raise ValueError("Configuração de API incompleta (base_url, chave e modelo).")
        self.model = model
        self.label = f"api/{model}"
        self._client = OpenAI(base_url=base_url.rstrip("/"), api_key=api_key)

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 800) -> str:
        temperature = STUDY_TEMPERATURE if STUDY_MODE else 0.3
        convo = [{"role": "system", "content": system_prompt}] + list(messages)

        for _ in range(self._MAX_TOOL_ROUNDS):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=convo,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=ALL_TOOLS,
                    tool_choice="auto",
                )
            except BadRequestError as exc:
                # Alguns modelos (ex: llama no Groq) emitem tool call em XML inválido
                # e o servidor rejeita com 400 tool_use_failed.
                body = getattr(exc, "body", None) or {}
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if error.get("code") != "tool_use_failed":
                    raise
                calls = _parse_xml_tool_calls(error.get("failed_generation", ""))
                if not calls:
                    raise
                convo.append({"role": "assistant", "content": "", "tool_calls": [
                    {"id": f"fb_{i}", "type": "function",
                     "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                    for i, c in enumerate(calls)]})
                for i, c in enumerate(calls):
                    convo.append({"role": "tool", "tool_call_id": f"fb_{i}",
                                  "content": run_tool(c["name"], c["args"])})
                continue

            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                convo.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls]})
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    convo.append({"role": "tool", "tool_call_id": tc.id,
                                  "content": run_tool(tc.function.name, args)})
                continue

            content = (msg.content or "").strip()

            # llama às vezes escreve a tool call como texto — detecta, executa e refaz.
            if "<function" in content:
                calls = _parse_xml_tool_calls(content)
                if calls:
                    convo.append({"role": "assistant", "content": "", "tool_calls": [
                        {"id": f"in_{i}", "type": "function",
                         "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                        for i, c in enumerate(calls)]})
                    for i, c in enumerate(calls):
                        convo.append({"role": "tool", "tool_call_id": f"in_{i}",
                                      "content": run_tool(c["name"], c["args"])})
                    continue
                content = _FUNCTION_TAG_CLEANUP_RE.sub("", content).strip()

            if choice.finish_reason == "length":
                raise RuntimeError("Resposta truncada pelo limite de tokens.")
            if not content:
                raise RuntimeError("Resposta vazia recebida do modelo.")
            return content

        raise RuntimeError("Limite de rodadas de ferramenta atingido.")
