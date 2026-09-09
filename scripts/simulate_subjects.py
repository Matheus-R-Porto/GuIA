"""
simulate_subjects.py - Compara o comportamento do GuIA entre diferentes
materias escolares, para identificar onde o metodo socratico funciona melhor.
"""
import sys
import time
sys.path.insert(0, ".")

from providers.groq_provider import GroqProvider
from engine import TutorEngine

SCENARIOS = [
    {"materia": "Matematica (Exatas)", "turnos": [
        "como eu resolvo uma equacao de primeiro grau, tipo 2x + 4 = 10?",
        "eu acho que preciso isolar o x, mas nao sei o que fazer com o 4",
        "entao eu subtraio 4 dos dois lados?",
        "ai fica 2x = 6, dai divido por 2?",
        "entendi, x = 3! valeu",
    ]},
    {"materia": "Fisica (Exatas)", "turnos": [
        "o que e a primeira lei de newton?",
        "acho que tem a ver com objetos parados continuarem parados",
        "e se o objeto ja estiver em movimento, o que acontece?",
        "entao ele continua em movimento reto e constante a menos que algo o pare?",
        "entendi, isso é a inercia",
    ]},
    {"materia": "Quimica (Exatas)", "turnos": [
        "o que e um atomo neutro?",
        "acho que e quando ele nao tem carga",
        "mas o atomo tem protons e eletrons, como isso da carga zero?",
        "entao se o numero de protons e igual ao de eletrons fica neutro?",
        "faz sentido, obrigado",
    ]},
    {"materia": "Portugues (Linguagens)", "turnos": [
        "qual a diferenca entre sujeito e predicado?",
        "acho que sujeito é quem faz a acao",
        "e o predicado seria o resto da frase?",
        "tipo na frase 'o cachorro correu no parque', cachorro é sujeito e o resto é predicado?",
        "entendi, obrigado",
    ]},
    {"materia": "Historia (Humanas)", "turnos": [
        "por que a Revolucao Francesa aconteceu?",
        "acho que tinha a ver com desigualdade entre as classes sociais",
        "e o rei tambem gastava muito dinheiro?",
        "entao foi uma combinacao de crise economica e desigualdade social?",
        "ficou mais claro, valeu",
    ]},
    {"materia": "Geografia (Humanas)", "turnos": [
        "o que causa as estacoes do ano?",
        "acho que e por causa da distancia da terra ao sol",
        "mas a terra nao tem uma orbita quase circular?",
        "entao deve ser a inclinacao do eixo da terra?",
        "entendi, obrigado",
    ]},
    {"materia": "Biologia (Exatas/Bio)", "turnos": [
        "qual a diferenca entre celula animal e vegetal?",
        "acho que a vegetal tem parede celular e a animal nao",
        "e a vegetal tambem tem cloroplasto?",
        "entao a vegetal faz fotossintese por causa do cloroplasto?",
        "faz sentido, obrigado",
    ]},
    {"materia": "Filosofia (Humanas)", "turnos": [
        "o que Platão queria dizer com o mito da caverna?",
        "acho que tem a ver com pessoas que so veem sombras e pensam que é a realidade",
        "e quem sai da caverna representa o que?",
        "entao seria alguem que busca conhecimento alem das aparencias?",
        "entendi, valeu",
    ]},
    {"materia": "Ingles (Linguagens)", "turnos": [
        "qual a diferenca entre present perfect e simple past em ingles?",
        "acho que o simple past e algo que aconteceu e terminou",
        "e o present perfect seria algo que ainda tem efeito agora?",
        "tipo 'I have lived here for 5 years' versus 'I lived there for 5 years'?",
        "entendi a diferenca, obrigado",
    ]},
]


def avaliar(turnos_log: list[dict]) -> dict:
    respostas = [t["guia"] for t in turnos_log]
    todas = " ".join(respostas).lower()

    metrics = {}
    # 1. Quantas respostas usam pergunta (excluindo a ultima, que pode ser encerramento)
    perguntas = sum(1 for r in respostas[:-1] if "?" in r)
    metrics["perguntas_por_turno"] = f"{perguntas}/{len(respostas)-1}"

    # 2. Tamanho medio das respostas (proxy de objetividade)
    tam_medio = sum(len(r) for r in respostas) / len(respostas)
    metrics["tamanho_medio_chars"] = round(tam_medio)

    # 3. Validacao positiva presente
    metrics["valida_aluno"] = any(
        p in todas for p in ["correto", "exato", "isso", "muito bem", "certo", "ótimo", "perfeito", "isso mesmo"]
    )

    # 4. Nao entregou a resposta antes do aluno chegar la (heuristica: primeira resposta tem "?")
    metrics["primeira_resposta_pergunta"] = "?" in respostas[0]

    return metrics


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("  GuIA -- COMPARATIVO ENTRE MATERIAS (Groq)")
    print("#"*60)

    resultados = []
    for i, scenario in enumerate(SCENARIOS, 1):
        provider = GroqProvider()
        engine = TutorEngine(providers=[provider])
        print(f"\n[{i}/{len(SCENARIOS)}] {scenario['materia']}")
        print("-"*60)

        log = []
        for msg in scenario["turnos"]:
            print(f"\n  [Aluno]: {msg}")
            try:
                resp = engine.ask(msg)
                print(f"  [GuIA]:  {resp}")
                log.append({"user": msg, "guia": resp})
            except Exception as e:
                print(f"  [ERRO]: {e}")
                log.append({"user": msg, "guia": f"ERRO: {e}"})
            time.sleep(1.5)

        metrics = avaliar(log)
        resultados.append({"materia": scenario["materia"], "metrics": metrics})
        time.sleep(1)

    print("\n\n" + "="*60)
    print("RELATORIO COMPARATIVO")
    print("="*60)
    for r in resultados:
        print(f"\n{r['materia']}")
        for k, v in r["metrics"].items():
            print(f"  {k}: {v}")
