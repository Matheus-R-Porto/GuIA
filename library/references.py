"""Reference lookup with bounded requests and an independent public fallback.

Crossref API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
Only provider metadata supplies bibliographic identifiers and links.
"""
import logging
from urllib.parse import quote, urlsplit

import httpx
import config

log = logging.getLogger(__name__)
_TIMEOUT = 10.0


def _request(url, params, headers=None):
    try:
        response = httpx.get(url, params=params, headers=headers or {}, timeout=_TIMEOUT)
        if response.status_code == 429:
            return None, 'rate_limited'
        response.raise_for_status()
        data = response.json()
        return (data, 'ok') if isinstance(data, dict) else (None, 'invalid_response')
    except httpx.TimeoutException:
        return None, 'timeout'
    except httpx.HTTPStatusError:
        return None, 'http_error'
    except httpx.HTTPError:
        return None, 'network_error'
    except (ValueError, TypeError):
        return None, 'invalid_response'


def _valid_url(url):
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def _semantic(query, limit):
    headers = {'x-api-key': config.SEMANTIC_SCHOLAR_API_KEY} if config.SEMANTIC_SCHOLAR_API_KEY else {}
    data, status = _request('https://api.semanticscholar.org/graph/v1/paper/search',
                            {'query': query, 'limit': limit, 'fields': 'title,authors,year,url'}, headers)
    if data is None:
        return [], status
    if not isinstance(data.get('data'), list):
        return [], 'invalid_response'
    articles = []
    for item in data['data']:
        if not isinstance(item, dict) or not isinstance(item.get('title'), str):
            continue
        title, url = item['title'].strip(), item.get('url')
        if not title or not _valid_url(url):
            continue
        authors = item.get('authors') or []
        articles.append({'title': title, 'url': url, 'year': item.get('year'),
                         'authors': ', '.join(str(a.get('name', '')) for a in authors if isinstance(a, dict))})
    return articles[:limit], 'ok' if articles else 'empty'


def _crossref(query, limit):
    data, status = _request('https://api.crossref.org/works',
                           {'query.bibliographic': query, 'rows': limit,
                            'filter': 'type:journal-article'},
                           {'User-Agent': 'GuIA/1.0 (educational reference search)'})
    if data is None:
        return [], status
    message = data.get('message')
    if not isinstance(message, dict) or not isinstance(message.get('items'), list):
        return [], 'invalid_response'
    articles = []
    for item in message['items']:
        if not isinstance(item, dict):
            continue
        titles = item.get('title') or []
        title = titles[0] if isinstance(titles, list) and titles else ''
        doi = item.get('DOI')
        url = 'https://doi.org/' + quote(doi, safe='/') if isinstance(doi, str) and doi.startswith('10.') else item.get('URL')
        if not isinstance(title, str) or not title.strip() or not _valid_url(url):
            continue
        authors = item.get('author') or []
        author_names = [str(a.get('name') or ' '.join(str(a.get(k) or '') for k in ('given', 'family'))).strip()
                        for a in authors if isinstance(a, dict)]
        date = item.get('published') or item.get('issued') or {}
        parts = date.get('date-parts', []) if isinstance(date, dict) else []
        year = parts[0][0] if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] else None
        articles.append({'title': title.strip(), 'url': url, 'year': year,
                         'authors': ', '.join(name for name in author_names if name)})
    return articles[:limit], 'ok' if articles else 'empty'


def search_references(query, limit=5):
    query = query.strip()
    if not query:
        return {'articles': [], 'status': 'empty', 'provider': '', 'attempts': {}}
    attempts = {}
    for name, search in (('Semantic Scholar', _semantic), ('Crossref', _crossref)):
        try:
            articles, status = search(query, limit)
        except (TypeError, ValueError, KeyError, AttributeError):
            articles, status = [], 'invalid_response'
        attempts[name] = status
        if articles:
            return {'articles': articles, 'status': 'ok', 'provider': name, 'attempts': attempts}
        # Never log query contents, credentials, request headers or response bodies.
        log.info('Reference search: service=%s status=%s', name, status)
    status = 'empty' if all(s == 'empty' for s in attempts.values()) else 'unavailable'
    return {'articles': [], 'status': status, 'provider': '', 'attempts': attempts}
