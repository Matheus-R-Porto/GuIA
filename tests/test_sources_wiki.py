import sources
from i18n import t


def _no_academic(monkeypatch):
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': []})


def test_wikipedia_aparece_primeiro_para_tema_escolar(monkeypatch):
    monkeypatch.setattr(sources, 'search_wikipedia', lambda q, limit=3: [
        dict(title='Equação linear', description='Expressão matemática',
             url='https://pt.wikipedia.org/wiki/Equa%C3%A7%C3%A3o_linear'),
        dict(title='Frango à passarinho', description='petisco',
             url='https://pt.wikipedia.org/wiki/Frango'),
    ])
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': [
        dict(title='Teaching linear equation in school', authors='A', year=2020,
             url='https://example.org/p')]})
    resposta = sources.find_sources('q', 'a', lambda *a: 'equação linear | linear equation school teaching')
    assert t('sources_wiki_heading') in resposta
    assert '[Equação linear](https://pt.wikipedia.org/wiki/Equa%C3%A7%C3%A3o_linear)' in resposta
    assert 'Frango' not in resposta                      # sem relação com o tema
    assert t('sources_academic_heading') in resposta
    assert resposta.index(t('sources_wiki_heading')) < resposta.index(t('sources_academic_heading'))


def test_so_wikipedia_quando_artigos_nao_servem(monkeypatch):
    monkeypatch.setattr(sources, 'search_wikipedia', lambda q, limit=3: [
        dict(title='Crase', description='acento', url='https://pt.wikipedia.org/wiki/Crase')])
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': [
        dict(title='Roma customary law', authors='B', year=2019, url='https://example.org/r')]})
    resposta = sources.find_sources('q', 'a', lambda *a: 'crase | Portuguese grave accent usage')
    assert '[Crase](https://pt.wikipedia.org/wiki/Crase)' in resposta
    assert 'example.org/r' not in resposta
    assert t('sources_academic_heading') not in resposta


def test_wikipedia_fora_do_ar_nao_quebra(monkeypatch):
    monkeypatch.setattr(sources, 'search_wikipedia', lambda q, limit=3: None)
    _no_academic(monkeypatch)
    assert sources.find_sources('q', 'a', lambda *a: 'crase | grave accent') == t('sources_not_found')


def test_sem_barra_vertical_funciona_como_antes(monkeypatch):
    chamadas = []
    monkeypatch.setattr(sources, 'search_wikipedia', lambda *a, **kw: chamadas.append(a) or [])
    _no_academic(monkeypatch)
    assert sources.find_sources('q', 'a', lambda *a: 'sleep memory') == t('sources_not_found')
    assert chamadas == []
