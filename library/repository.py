"""Library — busca de artigos científicos reais por palavra-chave, exibido
na UI como "Biblioteca".

Usa a API pública do Semantic Scholar (gratuita, com chave própria — ver
config.SEMANTIC_SCHOLAR_API_KEY). Sem RAG aqui — só busca + metadados
(título, autores, ano, resumo, link) com referência sempre rastreável até
a fonte real. Conversar sobre o artigo com a IA usa o resumo (abstract)
injetado no contexto, não o texto completo do artigo.
"""
import re
import time

import httpx

import config

_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,year,abstract,url"
# 10s era curto demais — a API pública às vezes demora mais que isso pra
# responder, especialmente em horários de pico do pool compartilhado.
_TIMEOUT = 25.0

# Backoff exponencial para 429: tenta de novo antes de desistir — mesmo com
# chave de API, picos passageiros podem acontecer. 3 tentativas extras com
# 1s, 2s, 4s entre elas (~7s no pior caso) — curto o suficiente pra não
# travar a UI, longo o suficiente pra absorver um pico momentâneo.
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0


def search_articles(
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    _sleep=time.sleep,
) -> dict | None:
    """Busca artigos por palavra-chave, com filtro opcional de faixa de anos.

    Retorna {"articles": [...], "total": N} — "total" é o total de artigos
    que batem com a busca na API (pode ser maior que len(articles), que é só
    a página atual). Retorna {"articles": [], "total": 0} em caso de busca
    vazia, sem resultados de verdade, ou falha de rede/API (a UI não deve
    travar por causa de uma API externa fora do ar). Retorna None quando a
    API continua bloqueando por limite de requisições (429) mesmo após
    backoff exponencial, OU quando a requisição estoura o tempo limite —
    distinguir esses casos de "sem resultados" evita que o usuário ache que
    a busca não achou nada quando na verdade é só limite/lentidão temporária
    (quem chama pode mostrar uma mensagem diferente, orientando tentar de
    novo em vez de sugerir que a palavra-chave não tem resultado)."""
    query = (query or "").strip()
    if not query:
        return {"articles": [], "total": 0}

    params = {"query": query, "limit": limit, "fields": _FIELDS}
    if year_from or year_to:
        params["year"] = f"{year_from or ''}-{year_to or ''}"

    headers = {"x-api-key": config.SEMANTIC_SCHOLAR_API_KEY} if config.SEMANTIC_SCHOLAR_API_KEY else {}

    tentativa = 0
    while True:
        try:
            response = httpx.get(_API_URL, params=params, headers=headers, timeout=_TIMEOUT)
        except httpx.TimeoutException:
            # Estouro de tempo é temporário (API lenta, rede do usuário) —
            # mesmo tratamento do 429: None, não "sem resultados".
            return None
        except httpx.HTTPError:
            return {"articles": [], "total": 0}

        if response.status_code == 429:
            tentativa += 1
            if tentativa > _MAX_RETRIES:
                return None
            _sleep(_BASE_DELAY_SECONDS * (2 ** (tentativa - 1)))
            continue

        try:
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return {"articles": [], "total": 0}
        break

    resultados = []
    for item in data.get("data", []):
        authors = ", ".join(
            a.get("name", "") for a in (item.get("authors") or []) if a.get("name")
        )
        title = (item.get("title") or "").strip()
        if not title:
            continue
        resultados.append({
            "title": title,
            "authors": authors,
            "year": item.get("year"),
            "abstract": (item.get("abstract") or "").strip(),
            "url": item.get("url") or "",
        })
    return {"articles": resultados, "total": data.get("total", len(resultados))}


# --- Detecção de idioma do artigo (filtro aproximado, client-side) ---
#
# A API do Semantic Scholar não tem parâmetro de filtro por idioma nem
# devolve o idioma nos metadados — então o filtro de idioma da UI é feito
# aqui, depois da busca, olhando pro texto (resumo, ou título se não houver
# resumo). Não é um detector estatístico de propósito geral: é afinado pra
# palavras funcionais bem distintas entre PT/EN/ES em prosa acadêmica longa
# (diferente de lang_detect.py, que é afinado pra saudações curtas de chat).
# Como é aproximado, cobre bem os 3 idiomas mais comuns em produção
# científica (inglês, português, espanhol) mas pode errar ou não reconhecer
# outros idiomas — aceitável para um filtro de conveniência, não uma busca
# exata.
_LANGUAGE_MARKERS = {
    "en": {"the", "and", "with", "this", "that", "were", "from", "these", "between", "using", "based"},
    "pt": {"não", "nao", "são", "sao", "também", "tambem", "então", "entao", "além", "alem", "através", "atraves", "estudo", "resultados"},
    "es": {"qué", "que", "cómo", "como", "también", "tambien", "más", "mas", "años", "anos", "así", "asi", "resultados"},
}


def guess_language(text: str) -> str | None:
    """Retorna 'en', 'pt' ou 'es' com base em palavras funcionais comuns no
    texto, ou None se não houver sinal suficiente pra decidir com confiança
    (texto curto demais, ou idioma fora desses três)."""
    words = set(re.findall(r"[a-zà-úñ]+", (text or "").lower()))
    if not words:
        return None

    scores = {lang: len(words & markers) for lang, markers in _LANGUAGE_MARKERS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_lang, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score >= 2 and best_score > second_score:
        return best_lang
    return None
