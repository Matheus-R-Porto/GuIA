"""Real bibliographic search for a chat answer; results are not proof of a claim."""
import re
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


def find_sources(question, answer, query_builder):
    try:
        query = query_builder(question, answer).strip()
    except Exception:
        return t('sources_query_failed')
    if not query or query.upper() == 'NONE':
        return t('sources_no_claim')
    # Bound and sanitize model-generated search terms, not bibliographic data.
    query = ' '.join(re.findall(r"[\w-]+", query)[:16])[:200]
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
