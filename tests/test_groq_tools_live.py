"""
Teste ao vivo das 3 ferramentas no Groq.
Objetivo: verificar se o modelo chama cada tool no cenário certo.
Tokens estimados: ~500-800 por cenário (3 cenários = ~2 400 tokens total).

Marcado com @pytest.mark.live: precisa da lib "groq" instalada e de
GROQ_API_KEY configurada — chama a API de verdade, gasta tokens de verdade.
Roda por padrão (mesmo comportamento de antes), mas pode ser excluído com
"pytest -m 'not live'" num ambiente/CI sem chave, sem que isso pareça um bug
na suíte (era o que acontecia antes: ImportError na coleta por falta da lib).
"""
import json
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

groq_module = pytest.importorskip("groq", reason="lib 'groq' não instalada — teste ao vivo pulado")
from groq import Groq, BadRequestError
from config import GROQ_API_KEY, GROQ_MODEL
from tools import ALL_TOOLS, run_tool
from prompt import SYSTEM_PROMPT_COMPACT as SYSTEM_PROMPT
from providers.groq_provider import _parse_xml_tool_calls

pytestmark = pytest.mark.live

if not GROQ_API_KEY:
    pytest.skip("GROQ_API_KEY não configurada — teste ao vivo pulado", allow_module_level=True)

_MAX_TOOL_ROUNDS = 5


def _run(messages: list[dict]) -> tuple[str, list[str]]:
    """Envia conversa e retorna (resposta_final, ferramentas_chamadas)."""
    client = Groq(api_key=GROQ_API_KEY)
    convo = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    tools_called: list[str] = []

    for _ in range(_MAX_TOOL_ROUNDS):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=convo,
                temperature=0.3,
                max_tokens=400,
                tools=ALL_TOOLS,
                tool_choice="auto",
            )
        except BadRequestError as exc:
            body = exc.body or {}
            error = body.get("error", {}) if isinstance(body, dict) else {}
            if error.get("code") != "tool_use_failed":
                raise
            failed = error.get("failed_generation", "")
            calls = _parse_xml_tool_calls(failed)
            if not calls:
                raise RuntimeError(f"Formato de tool call desconhecido: {failed}") from exc
            print(f"  [fallback XML] ferramentas detectadas: {[c['name'] for c in calls]}")
            fake_base = "fb"
            convo.append({
                "role": "assistant", "content": "",
                "tool_calls": [
                    {"id": f"{fake_base}_{i}", "type": "function",
                     "function": {"name": c["name"], "arguments": json.dumps(c["args"])}}
                    for i, c in enumerate(calls)
                ],
            })
            for i, c in enumerate(calls):
                tools_called.append(c["name"])
                result = run_tool(c["name"], c["args"])
                print(f"  [tool] {c['name']}({c['args']}) -> {result}")
                convo.append({"role": "tool", "tool_call_id": f"{fake_base}_{i}", "content": result})
            continue

        choice = resp.choices[0]
        msg = choice.message

        if msg.tool_calls:
            convo.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                tools_called.append(tc.function.name)
                args = json.loads(tc.function.arguments or "{}")
                result = run_tool(tc.function.name, args)
                print(f"  [tool] {tc.function.name}({args}) -> {result}")
                convo.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue

        return (msg.content or "").strip(), tools_called

    return "ERRO: limite de rodadas", tools_called


def _header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_calculator():
    _header("1. CALCULADORA — parábola com resposta errada do aluno")
    msgs = [
        {"role": "user", "content": "estou estudando a função f(x) = 2x² + 5x + 3"},
        {"role": "assistant", "content": "Qual é o valor de x no vértice que você encontrou?"},
        {"role": "user", "content": "calculei x = -1,25 e deu f(-1,25) = -6,375"},
    ]
    resposta, tools = _run(msgs)
    print(f"\n  GuIA: {resposta}")
    print(f"\n  Ferramentas chamadas: {tools}")
    ok = "calcular" in tools
    print(f"  {'OK' if ok else 'FALHOU'} — {'chamou calcular' if ok else 'NAO chamou calcular'}")
    return ok


def test_converter():
    _header("2. CONVERSOR — conversao obscura (atm para Pa)")
    msgs = [
        {"role": "user", "content": "estou resolvendo química: a pressão é 2,5 atm, converti para Pascal e deu 152000 Pa, está correto?"},
    ]
    resposta, tools = _run(msgs)
    print(f"\n  GuIA: {resposta}")
    print(f"\n  Ferramentas chamadas: {tools}")
    ok = "converter" in tools
    print(f"  {'OK' if ok else 'FALHOU'} — {'chamou converter' if ok else 'NAO chamou converter'}")
    return ok


def test_periodic_table():
    _header("3. TABELA PERIÓDICA — aluno não sabe a massa do ferro")
    msgs = [
        {"role": "user", "content": "estou resolvendo um exercício de química com ferro"},
        {"role": "assistant", "content": "O que você já sabe sobre o ferro como elemento? Qual é o seu símbolo?"},
        {"role": "user", "content": "sei que é Fe, Z=26, mas não sei a massa atômica"},
    ]
    resposta, tools = _run(msgs)
    print(f"\n  GuIA: {resposta}")
    print(f"\n  Ferramentas chamadas: {tools}")
    ok = "elemento" in tools
    print(f"  {'OK' if ok else 'FALHOU'} — {'chamou elemento' if ok else 'NAO chamou elemento'}")
    return ok


if __name__ == "__main__":
    resultados = []
    resultados.append(("Calculadora",    test_calculator()))
    resultados.append(("Conversor",      test_converter()))
    resultados.append(("Tab. Periódica", test_periodic_table()))

    print(f"\n{'='*60}")
    print("  RESULTADO FINAL")
    print('='*60)
    for nome, ok in resultados:
        status = "PASSOU" if ok else "FALHOU"
        print(f"  {status}  {nome}")
    aprovados = sum(1 for _, ok in resultados if ok)
    print(f"\n  {aprovados}/{len(resultados)} ferramentas ativadas corretamente")
