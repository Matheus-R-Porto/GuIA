import json
import re
import sys

from groq import Groq, BadRequestError
from config import GROQ_API_KEY, GROQ_MODEL, STUDY_MODE, STUDY_TEMPERATURE
from tools import ALL_TOOLS, run_tool

# Regex para capturar tool calls no formato hermes/XML que o llama às vezes emite.
# O llama produz isso de duas formas distintas:
#   Formato A: <function=nome>{...}</function>  ou  <function="nome">{...}</function>
#              (nome no atributo, argumentos DENTRO da tag)
#   Formato B: <function>nome</function>{...}
#              (nome como texto, argumentos DEPOIS do fechamento) — visto nos logs reais
_XML_TOOL_RE = re.compile(
    r'<function[=\s]"?(?P<name>[a-z_]+)"?\s*>?\s*(?P<args>\{.*?\})\s*</function>',
    re.DOTALL | re.IGNORECASE,
)
_XML_TOOL_RE_ALT = re.compile(
    r'<function>\s*(?P<name>[a-z_]+)\s*</function>\s*(?P<args>\{.*?\})',
    re.DOTALL | re.IGNORECASE,
)
# Remove qualquer resíduo de tag <function> do texto final, para nunca vazar na tela.
_FUNCTION_TAG_CLEANUP_RE = re.compile(
    r'<function[^>]*>.*?</function>\s*(?:\{.*?\})?',
    re.DOTALL | re.IGNORECASE,
)


def _parse_xml_tool_calls(text: str) -> list[dict] | None:
    """Parseia tool calls em formato XML que o llama gera incorretamente.

    Funciona tanto para o `failed_generation` (quando o Groq rejeita com 400)
    quanto para o conteúdo da resposta (quando o llama escreve a tag como texto
    comum, sem disparar erro). Cobre os formatos A e B descritos acima.
    """
    if not text:
        return None
    calls = []
    for rx in (_XML_TOOL_RE, _XML_TOOL_RE_ALT):
        for name, args_str in rx.findall(text):
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}
            calls.append({"name": name.strip('"'), "args": args})
    return calls or None


class GroqProvider:
    label = f"groq/{GROQ_MODEL}"
    _MAX_TOOL_ROUNDS = 5

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY não definida no .env")
        self._client = Groq(api_key=GROQ_API_KEY)

    def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 800) -> str:
        temperature = STUDY_TEMPERATURE if STUDY_MODE else 0.3
        convo = [{"role": "system", "content": system_prompt}] + list(messages)

        for _ in range(self._MAX_TOOL_ROUNDS):
            try:
                response = self._client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=convo,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=ALL_TOOLS,
                    tool_choice="auto",
                )
            except BadRequestError as exc:
                # llama às vezes emite tool calls em formato XML inválido.
                # Groq rejeita com 400; extraímos o failed_generation e executamos manualmente.
                body = exc.body or {}
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if error.get("code") != "tool_use_failed":
                    raise
                failed = error.get("failed_generation", "")
                calls = _parse_xml_tool_calls(failed)
                if not calls:
                    raise RuntimeError(f"Falha na chamada de ferramenta (formato desconhecido): {failed}") from exc
                print(f"[groq_provider] fallback XML tool-call: {[c['name'] for c in calls]}", file=sys.stderr)
                # Injeta resultados como mensagem de ferramenta sintética e recomeça
                fake_id_base = "fallback_tc"
                tool_calls_msg = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": f"{fake_id_base}_{i}", "type": "function",
                         "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                        for i, c in enumerate(calls)
                    ],
                }
                convo.append(tool_calls_msg)
                for i, c in enumerate(calls):
                    convo.append({
                        "role": "tool",
                        "tool_call_id": f"{fake_id_base}_{i}",
                        "content": run_tool(c["name"], c["args"]),
                    })
                continue

            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                convo.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    convo.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": run_tool(tc.function.name, args),
                    })
                continue

            content = (msg.content or "").strip()

            # O llama às vezes escreve a tool call como TEXTO no conteúdo, sem
            # disparar o erro 400 — então passava direto e vazava na tela
            # (ex.: "<function>calcular</function>{...}"). Detecta, executa de
            # fato e refaz a rodada para obter uma resposta limpa.
            if "<function" in content:
                calls = _parse_xml_tool_calls(content)
                if calls:
                    print(
                        f"[groq_provider] tool-call inline no conteúdo: {[c['name'] for c in calls]}",
                        file=sys.stderr,
                    )
                    fake_id_base = "inline_tc"
                    convo.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"id": f"{fake_id_base}_{i}", "type": "function",
                             "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                            for i, c in enumerate(calls)
                        ],
                    })
                    for i, c in enumerate(calls):
                        convo.append({
                            "role": "tool",
                            "tool_call_id": f"{fake_id_base}_{i}",
                            "content": run_tool(c["name"], c["args"]),
                        })
                    continue
                # Não deu para parsear: ao menos remove a tag para não vazar.
                content = _FUNCTION_TAG_CLEANUP_RE.sub("", content).strip()

            if choice.finish_reason == "length":
                raise RuntimeError("Resposta truncada pelo limite de tokens.")
            if not content:
                raise RuntimeError("Resposta vazia recebida do modelo.")
            return content

        raise RuntimeError("Limite de rodadas de ferramenta atingido.")
