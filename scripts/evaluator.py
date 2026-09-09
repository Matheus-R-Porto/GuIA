"""
Avaliador offline de conversas do GuIA.
Lê os chat_logs em JSON e avalia cada conversa contra a rubrica socrática.
Não toca no caminho ao vivo.

Uso:
    python evaluator.py --logs-dir chat_logs/ --output resultados.csv
"""

import json
import csv
import argparse
from pathlib import Path
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

RUBRICA_PROMPT = """
Você é um avaliador de tutoria socrática. Analise a conversa abaixo e retorne
SOMENTE um JSON com as seguintes chaves (sem texto adicional, sem markdown):

{
  "socratico": 0,
  "autonomia": 0,
  "engajamento": 0,
  "escopo": 0,
  "num_pistas": 0,
  "num_trocas": 0,
  "aluno_chegou": false,
  "observacao": ""
}

Escala de cada dimensão (0, 1 ou 2):
- socratico: 0=entregou resposta direta, 1=resposta parcial com pergunta, 2=conduziu sem entregar
- autonomia: 0=aluno não chegou à resposta, 1=chegou com muita ajuda, 2=chegou com pouca ajuda
- engajamento: 0=aluno desistiu ou saiu do tema, 1=respondeu pouco, 2=demonstrou esforço real
- escopo: 0=saiu do escopo educacional, 1=redirecionou com rigidez, 2=redirecionou com leveza
- num_pistas: contagem numérica de pistas dadas pelo tutor
- num_trocas: total de pares pergunta/resposta na conversa
- aluno_chegou: true se o aluno chegou à resposta por conta própria
- observacao: uma frase de observação opcional

Conversa:
{conversa}
"""


def formatar_conversa(history: list[dict]) -> str:
    linhas = []
    for msg in history:
        papel = "Aluno" if msg["role"] == "user" else "GuIA"
        linhas.append(f"{papel}: {msg['content']}")
    return "\n".join(linhas)


def avaliar_conversa(client: Groq, history: list[dict]) -> dict:
    conversa_fmt = formatar_conversa(history)
    prompt = RUBRICA_PROMPT.replace("{conversa}", conversa_fmt)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()

    # Remover possíveis blocos de código markdown
    raw = raw.strip("```json").strip("```").strip()
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="Avaliador offline do GuIA")
    parser.add_argument("--logs-dir", default="chat_logs", help="Pasta com os arquivos JSON")
    parser.add_argument("--output", default="resultados.csv", help="Arquivo CSV de saída")
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir)
    arquivos = sorted(logs_dir.glob("*.json"))

    if not arquivos:
        print(f"Nenhum arquivo JSON encontrado em {logs_dir}")
        return

    client = Groq(api_key=GROQ_API_KEY)
    resultados = []

    for arq in arquivos:
        print(f"Avaliando {arq.name}...", end=" ")
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            history = dados.get("messages", [])
            model_used = dados.get("model_used", "desconhecido")

            if len(history) < 2:
                print("pulado (conversa muito curta)")
                continue

            nota = avaliar_conversa(client, history)
            nota["arquivo"] = arq.name
            nota["model_used"] = model_used
            nota["exported_at"] = dados.get("exported_at", "")
            resultados.append(nota)
            print(f"ok (socrático={nota['socratico']}, autonomia={nota['autonomia']})")

        except Exception as e:
            print(f"ERRO: {e}")

    if not resultados:
        print("Nenhum resultado gerado.")
        return

    campos = [
        "arquivo", "exported_at", "model_used",
        "socratico", "autonomia", "engajamento", "escopo",
        "num_pistas", "num_trocas", "aluno_chegou", "observacao"
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(resultados)

    print(f"\nResultados salvos em: {args.output}")
    print(f"Total avaliado: {len(resultados)} conversas")


if __name__ == "__main__":
    main()
