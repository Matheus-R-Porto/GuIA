import webbrowser
from datetime import date

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from i18n import t
from ui.workers import LibrarySearchWorker

_BUTTON_ROW_HEIGHT = 46
_YEAR_MIN = 1900
_YEAR_MAX = date.today().year

# Valor especial do QSpinBox de ano == "sem filtro nesse lado da faixa" —
# mostrado como "—" em vez de um número (ver setSpecialValueText abaixo).
_YEAR_UNSET = _YEAR_MIN - 1


def _language_options():
    return [
        (t("lang_filter_any"), None),
        (t("lang_filter_pt"), "pt"),
        (t("lang_filter_en"), "en"),
        (t("lang_filter_es"), "es"),
    ]


class _ArticleCard(QFrame):
    """Um resultado de busca. Clicar no card expande (animação, igual à de
    abrir/fechar a sidebar) e revela os botões de ação — "Abrir no site"
    abre o navegador padrão do usuário direto na fonte real; "Conversar no
    chat" leva a conversa com a IA já sabendo do artigo. (Antes era só
    passar o mouse por cima, mas ficava instável/"bugado" — clique é mais
    previsível.)"""

    startChatRequested = Signal(dict)

    def __init__(self, article: dict, parent=None):
        super().__init__(parent)
        self.article = article
        self.setObjectName("ArticleCard")
        self.setCursor(Qt.PointingHandCursor)
        # WA_Hover só pro destaque visual leve no CSS (:hover) ao passar o
        # mouse — indicando que é clicável; a revelação dos botões em si é
        # por clique, não mais por hover.
        self.setAttribute(Qt.WA_Hover, True)
        self._expanded = False
        self._anim = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title = QLabel(article["title"])
        title.setFont(QFont("Open Sans", 13, QFont.DemiBold))
        title.setWordWrap(True)
        layout.addWidget(title)

        meta_parts = []
        if article.get("authors"):
            meta_parts.append(article["authors"])
        if article.get("year"):
            meta_parts.append(str(article["year"]))
        if meta_parts:
            meta = QLabel(" — ".join(meta_parts))
            meta.setObjectName("LibraryTagLabel")
            meta.setFont(QFont("Open Sans", 10))
            meta.setWordWrap(True)
            layout.addWidget(meta)

        abstract = article.get("abstract") or t("lab_no_abstract_fallback")
        if len(abstract) > 320:
            abstract = abstract[:320].rstrip() + "…"
        abstract_label = QLabel(abstract)
        abstract_label.setFont(QFont("Open Sans", 11))
        abstract_label.setWordWrap(True)
        layout.addWidget(abstract_label)

        self.button_row = QWidget()
        self.button_row.setObjectName("ArticleCardButtonRow")
        btn_layout = QHBoxLayout(self.button_row)
        btn_layout.setContentsMargins(0, 6, 0, 0)
        btn_layout.setSpacing(10)

        open_btn = QPushButton(t("lab_open_site_btn"))
        open_btn.setObjectName("DialogSecondaryButton")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setEnabled(bool(article.get("url")))
        open_btn.clicked.connect(self._on_open_clicked)

        chat_btn = QPushButton(t("lab_chat_about_btn"))
        chat_btn.setObjectName("DialogPrimaryButton")
        chat_btn.setCursor(Qt.PointingHandCursor)
        chat_btn.clicked.connect(lambda: self.startChatRequested.emit(self.article))

        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(chat_btn)
        btn_layout.addStretch(1)
        layout.addWidget(self.button_row)

        # Começa fechado (altura 0, mas presente no layout) — clicar no
        # card anima até a altura natural da linha de botões, revelando-a.
        self.button_row.setMaximumHeight(0)

    def _on_open_clicked(self):
        url = self.article.get("url")
        if url:
            webbrowser.open(url)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_expanded()
        super().mousePressEvent(event)

    def _toggle_expanded(self):
        self._expanded = not self._expanded
        target = _BUTTON_ROW_HEIGHT if self._expanded else 0

        self._anim = QPropertyAnimation(self.button_row, b"maximumHeight", self)
        self._anim.setDuration(180)
        self._anim.setStartValue(self.button_row.maximumHeight())
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(QEasingCurve.InOutQuart)
        self._anim.start()


class LibraryWidget(QWidget):
    """Biblioteca: busca de artigos científicos reais por palavra-chave
    (API pública, sem RAG) — página cheia embutida na área de conteúdo,
    mesmo padrão do Laboratório (banco de questões)."""

    startChatAboutArticleRequested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: LibrarySearchWorker | None = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 20, 32, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        subtitle = QLabel(t("lab_subtitle"))
        subtitle.setObjectName("LibraryTagLabel")
        subtitle.setFont(QFont("Open Sans", 13, QFont.DemiBold))
        header.addWidget(subtitle, 1, Qt.AlignLeft | Qt.AlignVCenter)

        title = QLabel(t("sidebar_menu_biblioteca"))
        title.setObjectName("LibraryTitleLabel")
        title.setFont(QFont("Roboto", 20, QFont.Bold))
        header.addWidget(title, 0, Qt.AlignRight | Qt.AlignVCenter)
        outer.addLayout(header)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("lab_search_placeholder"))
        self.search_edit.setFont(QFont("Open Sans", 12))
        self.search_edit.setMinimumHeight(40)
        self.search_edit.returnPressed.connect(self._on_search_clicked)

        self.search_btn = QPushButton(t("lab_search_btn"))
        self.search_btn.setObjectName("DialogPrimaryButton")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.setMinimumWidth(100)
        self.search_btn.clicked.connect(self._on_search_clicked)

        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.search_btn)
        outer.addLayout(search_row)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(10)

        year_label = QLabel(t("lab_year_label"))
        year_label.setObjectName("LibraryTagLabel")
        filters_row.addWidget(year_label)

        self.year_from_spin = QSpinBox()
        self.year_from_spin.setRange(_YEAR_UNSET, _YEAR_MAX)
        self.year_from_spin.setSpecialValueText("—")
        self.year_from_spin.setValue(_YEAR_UNSET)
        self.year_from_spin.setMinimumHeight(36)
        filters_row.addWidget(self.year_from_spin)

        until_label = QLabel(t("lab_year_until"))
        until_label.setObjectName("LibraryTagLabel")
        filters_row.addWidget(until_label)

        self.year_to_spin = QSpinBox()
        self.year_to_spin.setRange(_YEAR_UNSET, _YEAR_MAX)
        self.year_to_spin.setSpecialValueText("—")
        self.year_to_spin.setValue(_YEAR_UNSET)
        self.year_to_spin.setMinimumHeight(36)
        filters_row.addWidget(self.year_to_spin)

        filters_row.addSpacing(14)

        lang_label = QLabel(t("lab_language_label"))
        lang_label.setObjectName("LibraryTagLabel")
        filters_row.addWidget(lang_label)

        self._language_options = _language_options()
        self.language_combo = QComboBox()
        for texto, _codigo in self._language_options:
            self.language_combo.addItem(texto)
        self.language_combo.setMinimumHeight(36)
        filters_row.addWidget(self.language_combo)

        filters_row.addStretch(1)
        outer.addLayout(filters_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("LibraryTagLabel")
        self.status_label.hide()
        outer.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("LibraryScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(12)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.results_container)

        outer.addWidget(self.scroll, 1)

    def _on_search_clicked(self):
        query = self.search_edit.text().strip()
        if not query or self._worker is not None:
            return

        year_from = self.year_from_spin.value()
        year_to = self.year_to_spin.value()
        year_from = year_from if year_from != _YEAR_UNSET else None
        year_to = year_to if year_to != _YEAR_UNSET else None
        _, language = self._language_options[self.language_combo.currentIndex()]

        self._clear_results()
        self.search_btn.setEnabled(False)
        self.status_label.setText(t("lab_searching_status"))
        self.status_label.show()

        self._worker = LibrarySearchWorker(query, year_from=year_from, year_to=year_to, language=language)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_search_finished(self, resultado: dict | None):
        self._worker = None
        self.search_btn.setEnabled(True)

        if resultado is None:
            # 429 mesmo após backoff — bem diferente de "sem resultados",
            # merece mensagem própria.
            self.status_label.setText(t("lab_rate_limited_status"))
            return

        artigos = resultado["articles"]
        if not artigos:
            self.status_label.setText(t("lab_no_results_status"))
            return

        total = resultado["total"]
        if self.language_combo.currentIndex() != 0:
            # Filtro de idioma é aproximado e aplicado só na página já
            # buscada — "total" da API é de ANTES desse filtro, então os
            # dois números podem divergir; deixamos isso explícito.
            self.status_label.setText(
                t("lab_results_with_lang_filter_template", shown=len(artigos), total=total)
            )
            self.status_label.show()
        else:
            self.status_label.setText(t("lab_results_count_template", total=total))
            self.status_label.show()

        for artigo in artigos:
            card = _ArticleCard(artigo)
            card.startChatRequested.connect(self.startChatAboutArticleRequested.emit)
            self.results_layout.addWidget(card)

    def _clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
