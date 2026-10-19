"""Real bibliographic search for a chat answer; results are not proof of a claim."""
import re
import unicodedata
from urllib.parse import urlsplit, quote

from library.references import search_references as search_articles
from i18n import t, _STRINGS


def latest_exchange(history):
    requests = set(_STRINGS['sources_request'].values())
    for index in range(len(history) - 1, 0, -1):
        answer, question = history[index], history[index - 1]
        if (answer['role'] == 'assistant' and question['role'] == 'user'
                and question['content'] not in requests):
            return question['content'], answer['content']
    return None


def _plain(text):
    # Remote metadata is text, never HTML or additional Markdown links.
    return re.sub(r'([\\`*_{}\[\]()<>#!|])', r'\\\1', ' '.join(str(text or '').split()))


_STOPWORDS = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'using', 'use', 'study',
              'analysis', 'based', 'into', 'about', 'their', 'between', 'form', 'standard'}


def _fold(text):
    return unicodedata.normalize('NFD', str(text).lower()).encode('ascii', 'ignore').decode()


def _keywords(query):
    words = [_fold(w) for w in re.findall(r"[\w]+", query)]
    return [w for w in words if len(w) > 2 and not w.isdigit() and w not in _STOPWORDS]


def _is_relevant(title, keywords):
    """Pelo menos metade dos termos da busca (mínimo 2) aparece no título."""
    if len(keywords) < 2:
        return True
    folded = _fold(title)
    hits = sum(1 for k in keywords if k[:6] in folded)   # raiz curta: plural/flexão
    return hits >= max(2, -(-len(keywords) // 2))


def find_sources(question, answer, query_builder):
    try:
        query = query_builder(question, answer).strip()
    except Exception:
        return t('sources_query_failed')
    if not query or query.upper() == 'NONE':
        return t('sources_no_claim')
    # Bound and sanitize model-generated search terms, not bibliographic data.
    # Números e termos de 1-2 letras (restos de fórmulas como "ax 2 bx c 0") só poluem a busca.
    terms = [w for w in re.findall(r"[\w-]+", query)
             if len(w) > 2 and not w.isdigit()] or re.findall(r"[\w-]+", query)
    query = ' '.join(terms[:12])[:200]
    if not query:
        return t('sources_no_claim')
    try:
        result = search_articles(query, limit=5)
    except Exception:
        return t('sources_unavailable')
    if result is None:
        return t('sources_unavailable')
    if result.get('status') == 'unavailable':
        reasons = [f"{name}: {t('sources_status_' + status)}"
                   for name, status in result.get('attempts', {}).items()]
        return t('sources_unavailable') + ('\n\n' + '; '.join(reasons) if reasons else '')
    articles = []
    seen = set()
    for article in result['articles']:
        url = article.get('url', '')
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme in ('http', 'https') and bool(parsed.hostname)
        except ValueError:
            valid = False
        if valid and url not in seen:
            articles.append(article)
            seen.add(url)
    if not articles:
        return t('sources_not_found')
    # Descarta resultados cujo título não tem relação com os termos buscados.
    keywords = _keywords(query)
    relevant = [a for a in articles if _is_relevant(a.get('title', ''), keywords)]
    if not relevant:
        return t('sources_irrelevant')
    articles = relevant
    lines = [t('sources_heading'), t('sources_caveat'),
             t('sources_query', query=_plain(query))]
    if result.get('provider'):
        lines.append(t('sources_provider', provider=result['provider']))
    for article in articles:
        url = quote(article['url'], safe=':/?=&%+@#;,-._~')
        lines.append(f"- [{_plain(article['title'])}]({url}) — "
                     f"{_plain(article.get('authors'))} "
                     f"({_plain(article.get('year') or '—')})")
    return '\n\n'.join(lines)
