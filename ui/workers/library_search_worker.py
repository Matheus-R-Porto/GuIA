import sys

from PySide6.QtCore import QThread, Signal

import library


class LibrarySearchWorker(QThread):
    """Busca artigos em background — chama uma API externa (rede), não pode
    travar a UI enquanto espera resposta."""
    # object, não dict: library.search_articles pode retornar None (limite
    # de requisições da API, 429) — Signal(dict) não carrega None direito.
    finished = Signal(object)

    def __init__(self, query: str, year_from: int | None = None, year_to: int | None = None,
                 language: str | None = None):
        super().__init__()
        self.query = query
        self.year_from = year_from
        self.year_to = year_to
        # 'pt', 'en', 'es' ou None (qualquer idioma, sem filtro).
        self.language = language

    def run(self):
        try:
            resultado = library.search_articles(self.query, year_from=self.year_from, year_to=self.year_to)
        except Exception as exc:
            print(f"[GuIA] Erro no LibrarySearchWorker: {exc}", file=sys.stderr)
            resultado = {"articles": [], "total": 0}

        if resultado is not None and self.language:
            # Filtro de idioma é aproximado e feito só na página já buscada
            # (a API não tem esse filtro) — por isso "total" continua sendo
            # o total ANTES do filtro de idioma; a UI precisa deixar isso
            # claro pro usuário, já que os dois números podem divergir.
            resultado = dict(resultado)
            resultado["articles"] = [
                artigo for artigo in resultado["articles"]
                if library.guess_language(artigo.get("abstract") or artigo.get("title") or "") == self.language
            ]

        self.finished.emit(resultado)
