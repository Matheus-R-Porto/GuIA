import httpx
import pytest
import sources
from i18n import t
from library import references


def response(status, payload=None):
    return httpx.Response(status, json=payload or {}, request=httpx.Request('GET', 'https://example.org'))


def crossref_item():
    return {'title': ['C4 photosynthesis and photorespiration'], 'DOI': '10.1234/example',
            'author': [{'given': 'Ana', 'family': 'Silva'}], 'published': {'date-parts': [[2024, 1]]}}


@pytest.mark.parametrize('failure', ['limit', 'timeout', 'network', 'empty', 'invalid', 'http'])
def test_primary_failure_uses_crossref(monkeypatch, failure):
    calls = []
    monkeypatch.setattr(references.config, 'SEMANTIC_SCHOLAR_API_KEY', 'fake-test-key')
    def get(url, **kwargs):
        calls.append((url, kwargs))
        if 'semanticscholar' in url:
            if failure == 'timeout': raise httpx.ReadTimeout('test')
            if failure == 'network': raise httpx.ConnectError('test')
            return response({'limit': 429, 'http': 503}.get(failure, 200),
                            {'data': []} if failure == 'empty' else {'unexpected': True})
        assert 'x-api-key' not in kwargs['headers']
        return response(200, {'message': {'items': [crossref_item()]}})
    monkeypatch.setattr(httpx, 'get', get)
    result = references.search_references('C4 photosynthesis')
    assert result['provider'] == 'Crossref'
    assert len(calls) == 2  # bounded requests; no repeated calls to a limited service
    assert result['articles'][0] == {'title': 'C4 photosynthesis and photorespiration',
                                    'authors': 'Ana Silva', 'year': 2024,
                                    'url': 'https://doi.org/10.1234/example'}


def test_successful_primary_does_not_call_fallback(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return response(200, {'data': [{'title': 'Paper', 'url': 'https://example.org/paper'}]})
    monkeypatch.setattr(httpx, 'get', get)
    assert references.search_references('C4')['provider'] == 'Semantic Scholar'
    assert len(calls) == 1


def test_both_services_fail_explains_reason(monkeypatch):
    monkeypatch.setattr(httpx, 'get', lambda *a, **kw: response(429))
    text = sources.find_sources('question', 'answer', lambda *a: 'C4 photosynthesis')
    assert 'Semantic Scholar' in text and 'Crossref' in text
    assert t('sources_status_rate_limited') in text
    assert t('sources_unavailable') in text


def test_results_identify_actual_database(monkeypatch):
    def get(url, **kwargs):
        return (response(429) if 'semanticscholar' in url else
                response(200, {'message': {'items': [crossref_item()]}}))
    monkeypatch.setattr(httpx, 'get', get)
    text = sources.find_sources('question', 'answer', lambda *a: 'C4 photosynthesis')
    assert t('sources_provider', provider='Crossref') in text
    assert '(https://doi.org/10.1234/example)' in text
    assert t('sources_caveat') in text


def test_query_failure_is_distinct_and_does_not_search(monkeypatch):
    def fail(*a): raise RuntimeError('test')
    def unexpected(*a, **kw): raise AssertionError('must not search')
    monkeypatch.setattr(sources, 'search_articles', unexpected)
    assert sources.find_sources('q', 'a', fail) == t('sources_query_failed')


def test_empty_results_are_distinct_from_errors(monkeypatch):
    def get(url, **kwargs):
        return response(200, {'data': []} if 'semanticscholar' in url else {'message': {'items': []}})
    monkeypatch.setattr(httpx, 'get', get)
    assert references.search_references('unknown')['status'] == 'empty'


def test_bad_metadata_does_not_produce_fake_link(monkeypatch):
    def get(url, **kwargs):
        return (response(429) if 'semanticscholar' in url else
                response(200, {'message': {'items': [{'title': ['Bad'], 'URL': 'javascript:alert(1)'}]}}))
    monkeypatch.setattr(httpx, 'get', get)
    assert references.search_references('C4')['articles'] == []
