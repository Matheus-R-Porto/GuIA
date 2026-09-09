import httpx
import pytest

import library


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_busca_vazia_retorna_lista_vazia():
    assert library.search_articles("") == {"articles": [], "total": 0}
    assert library.search_articles("   ") == {"articles": [], "total": 0}


def test_busca_com_resultado_extrai_campos_certos(monkeypatch):
    payload = {
        "total": 1,
        "data": [
            {
                "title": "Efeitos do sono no aprendizado",
                "authors": [{"name": "Ana Silva"}, {"name": "Bruno Costa"}],
                "year": 2021,
                "abstract": "Um resumo qualquer.",
                "url": "https://example.com/artigo",
            }
        ],
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))

    resultado = library.search_articles("sono e aprendizado")
    assert resultado["total"] == 1
    art = resultado["articles"][0]
    assert art["title"] == "Efeitos do sono no aprendizado"
    assert art["authors"] == "Ana Silva, Bruno Costa"
    assert art["year"] == 2021
    assert art["abstract"] == "Um resumo qualquer."
    assert art["url"] == "https://example.com/artigo"


def test_busca_ignora_artigos_sem_titulo(monkeypatch):
    payload = {"data": [{"title": "", "authors": [], "year": None, "abstract": "", "url": ""}]}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(payload))
    assert library.search_articles("qualquer coisa")["articles"] == []


def test_falha_de_rede_retorna_lista_vazia_sem_travar(monkeypatch):
    def _explode(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(httpx, "get", _explode)
    assert library.search_articles("qualquer coisa") == {"articles": [], "total": 0}


def test_timeout_retorna_none_nao_lista_vazia(monkeypatch):
    """Estourar o tempo limite é temporário (API lenta, rede do usuário) —
    igual ao 429, precisa ser distinguível de "sem resultados", senão a UI
    mostra "nenhum artigo encontrado" quando na verdade é só lentidão."""
    def _timeout(*a, **k):
        raise httpx.ReadTimeout("demorou demais")

    monkeypatch.setattr(httpx, "get", _timeout)
    assert library.search_articles("qualquer coisa") is None


def test_resposta_sem_campo_data_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({}))
    assert library.search_articles("qualquer coisa")["articles"] == []


def test_filtro_de_ano_vira_parametro_year_no_formato_da_api(monkeypatch):
    chamadas = []

    def _fake_get(url, params=None, **kwargs):
        chamadas.append(params)
        return _FakeResponse({"total": 0, "data": []})

    monkeypatch.setattr(httpx, "get", _fake_get)

    library.search_articles("clima", year_from=2020, year_to=2026)
    assert chamadas[0]["year"] == "2020-2026"

    library.search_articles("clima", year_from=2020)
    assert chamadas[1]["year"] == "2020-"

    library.search_articles("clima", year_to=2020)
    assert chamadas[2]["year"] == "-2020"

    library.search_articles("clima")
    assert "year" not in chamadas[3]


def test_limite_de_requisicoes_429_retorna_none_apos_esgotar_tentativas(monkeypatch):
    """429 (limite de requisições da API gratuita) precisa ser distinguível
    de "busca sem resultados" — quem chama mostra mensagens diferentes.
    Só desiste (None) depois de esgotar o backoff exponencial."""
    chamadas = []
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse({}, status_code=429))

    resultado = library.search_articles("qualquer coisa", _sleep=lambda s: chamadas.append(s))

    assert resultado is None
    assert chamadas == [1.0, 2.0, 4.0]


def test_limite_de_requisicoes_429_tenta_de_novo_e_recupera(monkeypatch):
    """Se o 429 for passageiro, uma tentativa seguinte bem-sucedida deve
    retornar os resultados normalmente, não None."""
    payload = {"total": 1, "data": [{"title": "Artigo recuperado", "authors": [], "year": 2020,
                                      "abstract": "", "url": ""}]}
    respostas = iter([_FakeResponse({}, status_code=429), _FakeResponse(payload)])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(respostas))

    resultado = library.search_articles("qualquer coisa", _sleep=lambda s: None)

    assert resultado is not None
    assert resultado["articles"][0]["title"] == "Artigo recuperado"


def test_guess_language_reconhece_ingles():
    texto = "This study evaluates the effects of sleep on learning, using data from these students between groups."
    assert library.guess_language(texto) == "en"


def test_guess_language_reconhece_portugues():
    texto = "Este estudo não encontrou diferença significativa; os resultados também mostram que a amostra é adequada."
    assert library.guess_language(texto) == "pt"


def test_guess_language_reconhece_espanhol():
    texto = "Este estudio también evalúa cómo los resultados cambian según los años y qué factores más influyen así."
    assert library.guess_language(texto) == "es"


def test_guess_language_retorna_none_para_texto_curto_demais():
    assert library.guess_language("abc") is None
    assert library.guess_language("") is None


@pytest.mark.live
def test_busca_real_semantic_scholar():
    resultado = library.search_articles("machine learning education", limit=3)
    assert len(resultado["articles"]) > 0
    assert resultado["articles"][0]["title"]
