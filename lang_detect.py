"""Detecção leve de idioma (PT/EN/ES) para o modo automático de resposta.

Não é um detector estatístico de propósito geral — é afinado para o caso que
importa aqui: mensagens curtas de chat (saudações, frases comuns), onde o
prompt de sistema inteiro em português tende a "puxar" o modelo para
responder em português mesmo quando o aluno escreveu em outro idioma.
"""
import re

_EXACT_GREETINGS = {
    "en": {"hello", "hi", "hey", "howdy", "good morning", "good afternoon", "good evening", "yo"},
    "es": {"hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "que tal", "qué tal"},
    "pt": {"oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "eae", "e ai", "e aí", "salve"},
}

_MARKER_WORDS = {
    "en": {
        "hello", "hi", "hey", "the", "you", "your", "is", "are", "what", "how",
        "please", "thanks", "thank", "help", "want", "need", "can", "could",
        "would", "and", "with", "for", "understand", "explain", "study",
    },
    "es": {
        "hola", "cómo", "como", "está", "esta", "gracias", "ayuda", "quiero",
        "necesito", "puedes", "podrías", "estudiar", "explicar", "entender",
        "tú", "tu", "usted", "qué",
    },
    "pt": {
        "olá", "ola", "você", "voce", "está", "esta", "obrigado", "obrigada",
        "ajuda", "quero", "preciso", "pode", "poderia", "estudar", "explicar",
        "entender", "não", "nao", "então", "entao", "isso",
    },
}


def detect_language(text: str) -> str | None:
    """Retorna 'pt', 'en' ou 'es' se identificar com razoável confiança, ou
    None se a mensagem for curta/ambígua demais — nesse caso quem chama deve
    manter o idioma já em uso, em vez de forçar algo incerto."""
    normalized = text.strip().lower().strip("!?.,;:¡¿")
    if not normalized:
        return None

    for lang, greetings in _EXACT_GREETINGS.items():
        if normalized in greetings:
            return lang

    words = set(re.findall(r"[a-zà-úñ]+", normalized))
    if not words:
        return None

    scores = {lang: len(words & markers) for lang, markers in _MARKER_WORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_lang, best_score = ranked[0]
    second_score = ranked[1][1]

    # Exige um mínimo de sinal e uma vantagem clara sobre o segundo colocado
    # (evita "chutar" em mensagens ambíguas entre PT/ES, que compartilham
    # muito vocabulário).
    if best_score >= 2 and best_score > second_score:
        return best_lang
    return None
