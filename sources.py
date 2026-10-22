"""Real bibliographic search for a chat answer; results are not proof of a claim."""
import re
import unicodedata
from urllib.parse import urlsplit, quote

import httpx

from library.references import search_references as search_articles
from i18n import t, _STRINGS

_WIKI_URL = 'https://pt.wikipedia.org/w/rest.php/v1/search/page'
_WIKI_HEADERS = {
    # A Wikimedia exige um User-Agent descritivo com forma de contato (robot policy).
    'User-Agent': 'GuIA-tutor/1.0 (https://github.com/Matheus-R-Porto/GuIA; projeto escolar IFSul Sapiranga) httpx',
    'Accept': 'application/json',
}


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
              'analysis', 'based', 'into', 'about', 'their', 'between', 'form', 'standard',
              'para', 'com', 'uma', 'dos', 'das', 'como', 'que', 'sobre', 'ensino'}


def _fold(text):
    return unicodedata.normalize('NFD', str(text).lower()).encode('ascii', 'ignore').decode()


def _keywords(query):
    words = [_fold(w) for w in re.findall(r"[\w]+", query)]
    return [w for w in words if len(w) > 2 and not w.isdigit() and w not in _STOPWORDS]


def _is_relevant(title, keywords):
    """Pelo menos 60% dos termos da busca (mínimo 2) aparecem no título."""
    if len(keywords) < 2:
        return True
    folded = _fold(title)
    hits = sum(1 for k in keywords if k[:6] in folded)   # raiz curta: plural/flexão
    return hits >= max(2, -(-len(keywords) * 3 // 5))


def _clean_terms(query, limit=12):
    # Números e termos de 1-2 letras (restos de fórmulas como "ax 2 bx c 0") só poluem a busca.
    words = re.findall(r"[\w-]+", query)
    terms = [w for w in words if len(w) > 2 and not w.isdigit()] or words
    return ' '.join(terms[:limit])[:200]


def _split_queries(raw):
    """O modelo devolve 'consulta em português | consulta em inglês'. Sem '|', só há a em inglês."""
    if '|' in raw:
        pt, en = raw.split('|', 1)
        return _clean_terms(pt), _clean_terms(en)
    return '', _clean_terms(raw)


def _valid_url(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def search_wikipedia(query, limit=3):
    """Páginas da Wikipédia em português (ajuda a estudar o tema). None se a busca falhar."""
    try:
        response = httpx.get(_WIKI_URL, params={'q': query, 'limit': limit + 2},
                             headers=_WIKI_HEADERS, timeout=8.0)
        response.raise_for_status()
        pages = response.json().get('pages', [])
    except Exception:
        return None
    found = []
    for page in pages:
        key = page.get('key')
        if not key:
            continue
        found.append(dict(title=page.get('title') or key,
                          description=page.get('description') or '',
                          url='https://pt.wikipedia.org/wiki/' + quote(key, safe='()_,-.~')))
    return found


def _wiki_lines(pt_query):
    if not pt_query:
        return []
    pages = search_wikipedia(pt_query)
    if not pages:
        return []
    keywords = _keywords(pt_query)
    scored = []
    for order, page in enumerate(pages):
        if not _valid_url(page['url']):
            continue
        folded_title = _fold(page['title'])
        folded_all = _fold(page['title'] + ' ' + page['description'])
        if keywords and not any(k[:6] in folded_all for k in keywords):
            continue
        hits = sum(1 for k in keywords if k[:6] in folded_title)
        scored.append((-hits, order, page))
    scored.sort(key=lambda item: item[:2])     # mais termos no título primeiro; empate: ordem da busca
    lines = []
    for _, _, page in scored[:3]:
        desc = f" — {_plain(page['description'])}" if page['description'] else ''
        lines.append(f"- [{_plain(page['title'])}]({page['url']}){desc}")
    return lines


def _academic(query):
    """Devolve (linhas, mensagem_de_erro). Linhas vazias => usar a mensagem."""
    try:
        result = search_articles(query, limit=5)
    except Exception:
        return [], t('sources_unavailable')
    if result is None:
        return [], t('sources_unavailable')
    if result.get('status') == 'unavailable':
        reasons = [f"{name}: {t('sources_status_' + status)}"
                   for name, status in result.get('attempts', {}).items()]
        return [], t('sources_unavailable') + ('\n\n' + '; '.join(reasons) if reasons else '')
    articles = []
    seen = set()
    for article in result['articles']:
        url = article.get('url', '')
        if _valid_url(url) and url not in seen:
            articles.append(article)
            seen.add(url)
    if not articles:
        return [], t('sources_not_found')
    # Descarta resultados cujo título não tem relação com os termos buscados.
    keywords = _keywords(query)
    relevant = [a for a in articles if _is_relevant(a.get('title', ''), keywords)]
    if not relevant:
        return [], t('sources_irrelevant')
    lines = [t('sources_query', query=_plain(query))]
    if result.get('provider'):
        lines.append(t('sources_provider', provider=result['provider']))
    for article in relevant:
        url = quote(article['url'], safe=':/?=&%+@#;,-._~')
        lines.append(f"- [{_plain(article['title'])}]({url}) — "
                     f"{_plain(article.get('authors'))} "
                     f"({_plain(article.get('year') or '—')})")
    return lines, ''


def find_sources(question, answer, query_builder):
    try:
        raw = query_builder(question, answer).strip()
    except Exception:
        return t('sources_query_failed')
    if not raw or raw.upper() == 'NONE':
        return t('sources_no_claim')
    # Bound and sanitize model-generated search terms, not bibliographic data.
    pt_query, query = _split_queries(raw)
    if not query and not pt_query:
        return t('sources_no_claim')
    wiki = _wiki_lines(pt_query)
    academic, message = _academic(query) if query else ([], t('sources_not_found'))
    if not wiki:
        if not academic:
            return message
        return '\n\n'.join([t('sources_heading'), t('sources_caveat')] + academic)
    lines = [t('sources_heading'), t('sources_caveat'), t('sources_wiki_heading')] + wiki
    if academic:
        lines += [t('sources_academic_heading')] + academic
    return '\n\n'.join(lines)
