import html
import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

import bug_report
import quiz
from i18n import t

_TODOS = t("option_all")
# Largura máxima da figura da questão (quando houver) — o conteúdo da
# página de questão já usa uma coluna de leitura confortável, não a tela
# toda; a figura acompanha essa largura pra não ficar desproporcional.
_IMAGE_MAX_WIDTH = 520
# Largura máxima de cada alternativa-imagem (ex: questão com 5 gráficos
# como alternativa, não só texto) — menor que _IMAGE_MAX_WIDTH porque
# várias ficam lado a lado na tela ao mesmo tempo.
_ALT_IMAGE_MAX_WIDTH = 260
# Alternativas-imagem ficam em grade (3 por linha: A,B,C / D,E) em vez de
# empilhadas verticalmente — pedido do Matheus, mais fácil de comparar os
# gráficos lado a lado. Alternativas de texto continuam numa coluna só
# (mesma grade, só que com 1 coluna).
_ALT_IMAGE_COLUMNS = 3

# Marcação leve *texto* -> itálico, usada no enunciado/explicação pra
# destacar variáveis matemáticas soltas no meio da prosa (ex: "lado *a*
# com o vértice B") — sem isso, uma letra solta minúscula parece erro de
# digitação em vez de variável (foi exatamente o que o Matheus reportou
# na questão 51). Um caractere Unicode "itálico matemático" dedicado
# existiria, mas depende da fonte instalada ter esse glifo (risco real,
# sem garantia); HTML <i> é itálico de verdade da mesma fonte, sempre
# funciona. Escapa o texto ANTES de aplicar a marcação, pra nunca
# interpretar um "<"/"&" real do enunciado como HTML por engano.
_ITALIC_MARKER_RE = re.compile(r"\*(.+?)\*")


def _render_rich(text: str) -> str:
    escapado = html.escape(text).replace("\n", "<br>")
    return _ITALIC_MARKER_RE.sub(r"<i>\1</i>", escapado)


class _CurrentPageStack(QStackedWidget):
    """QStackedWidget cujo sizeHint()/minimumSizeHint() seguem SÓ a página
    atual, não a maior entre todas as cadastradas.

    QStackedWidget, por padrão, calcula sizeHint() como o maior entre
    TODOS os widgets cadastrados nele — de propósito, do próprio Qt, pra
    evitar que a janela "pule" de tamanho ao trocar de página. No nosso
    caso isso é o comportamento ERRADO: depois de ver uma questão com
    imagem grande, a tela de filtros (bem mais curta) ficava esticada do
    mesmo jeito.

    Uma primeira tentativa de corrigir isso marcava toda página que NÃO é
    a atual como QSizePolicy.Ignored — mas isso só resolve pela metade:
    QStackedWidget.minimumSizeHint() respeita essa policy (ignora páginas
    não-atuais), só que QStackedWidget.sizeHint() NÃO respeita (confirmado
    testando na prática — ele soma/considera as páginas ignoradas do mesmo
    jeito). Como os layouts consultam sizeHint(), o "vazamento" de altura
    de uma página grande pra outra continuava acontecendo. Sobrescrever os
    dois métodos aqui pra sempre refletir só currentWidget() resolve na
    raiz, sem depender de nenhum comportamento interno do Qt que pode
    mudar entre versões."""

    def sizeHint(self):
        atual = self.currentWidget()
        return atual.sizeHint() if atual else super().sizeHint()

    def minimumSizeHint(self):
        atual = self.currentWidget()
        return atual.minimumSizeHint() if atual else super().minimumSizeHint()


class QuizWidget(QWidget):
    """Banco de questões reais de vestibular (ENEM, UFRGS...) — ocupa a
    área de conteúdo no lugar do chat, como uma página própria (a
    navegação de volta ao chat é só pela sidebar, não tem botão dedicado
    aqui — é uma tela, não um pop-up).

    Diferente do tutor: aqui NÃO é socrático, de propósito — são questões
    objetivas de prova real, com as mesmas alternativas do original. O
    aluno escolhe uma alternativa e recebe feedback imediato (certo/errado
    + explicação), sem ser conduzido por perguntas.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._active_filters: dict = {}
        self._shown_ids: set[str] = set()
        self._current_question: dict | None = None
        self._alt_buttons: dict[str, QPushButton] = {}
        self._answered = False
        # Histórico de questões já mostradas na sessão atual de filtros —
        # permite voltar pra uma questão anterior (preservando se ela já
        # tinha sido respondida e qual alternativa foi marcada), sem
        # perder o lugar nem repetir uma nova questão aleatória por engano.
        # _history_pos aponta pro índice da questão visível agora; "next"
        # só busca uma questão nova quando já se está na ponta mais recente
        # do histórico (senão, só avança o ponteiro pra frente).
        self._history: list[dict] = []
        self._history_pos: int = -1
        # Vira True só quando a pessoa clica em "Confirmar matérias" — o
        # filtro de conteúdo (que depende da matéria) fica escondido até
        # lá, pra não reconstruir/piscar a cada caixinha de matéria clicada
        # em sequência.
        self._materias_confirmadas = False
        # Fonte durável de quais (matéria, conteúdo) estão marcados —
        # sobrevive ao ciclo "esconde enquanto não confirmado de novo"
        # (ver _refresh_conteudo_section), diferente de confiar só no
        # estado dos QCheckBox, que são destruídos/recriados a cada
        # reconstrução da seção.
        self._conteudo_selecionados: set[tuple[str, str]] = set()

        self._build_ui()
        self._refresh_ano_combo()
        self._refresh_conteudo_section()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # A largura da coluna de alternativas muda quando a janela é
        # redimensionada — reajusta a altura reservada pro texto quebrado
        # das alternativas (ver _ajustar_altura_alternativas_texto).
        if self._alt_buttons:
            QTimer.singleShot(0, self._ajustar_altura_alternativas_texto)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 20, 32, 20)
        outer.setSpacing(10)

        # --- topo: filtros (esquerda) + descrição da questão + título (direita) ---
        header = QHBoxLayout()

        # "Voltar aos filtros" morava no rodapé, ao lado dos botões de
        # navegação entre questões — mas navegar entre questões e voltar
        # pra tela de filtros são ações de natureza bem diferente (uma é
        # sequencial, a outra troca de tela inteira), então acabavam
        # competindo por espaço/atenção no mesmo lugar. Botão movido pro
        # cabeçalho, junto do título, como uma ação de nível de tela.
        self.back_to_filters_btn = QPushButton(t("quiz_back_to_filters_btn"))
        self.back_to_filters_btn.setObjectName("DialogSecondaryButton")
        self.back_to_filters_btn.setCursor(Qt.PointingHandCursor)
        self.back_to_filters_btn.setToolTip(t("library_back_to_filters_tooltip"))
        self.back_to_filters_btn.setFocusPolicy(Qt.NoFocus)
        self.back_to_filters_btn.clicked.connect(self._on_back_to_filters)
        header.addWidget(self.back_to_filters_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.tag_label = QLabel("")
        self.tag_label.setObjectName("LibraryTagLabel")
        self.tag_label.setFont(QFont("Open Sans", 15, QFont.DemiBold))
        # Precisa quebrar linha: desde que o texto passou a incluir
        # "conteudo: detalhe" (às vezes bem longo, ex: matérias como
        # Física), sem isso o label não encolhia — ficava com uma única
        # linha gigante, empurrando o título "Laboratório" pra fora da
        # tela e esticando a página inteira na horizontal.
        self.tag_label.setWordWrap(True)
        self.tag_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Sem flag de alinhamento aqui de propósito — mesmo bug já visto no
        # welcome_label do chat: addWidget(..., Qt.AlignX) faz o Qt usar o
        # sizeHint() "livre" do label em vez de heightForWidth(), então a
        # altura reservada pra 2+ linhas fica curta demais e o texto
        # sobrepõe o conteúdo abaixo. O label já se alinha sozinho via
        # setAlignment() acima.
        header.addWidget(self.tag_label, 1)

        title = QLabel(t("sidebar_menu_laboratorio"))
        title.setObjectName("LibraryTitleLabel")
        title.setFont(QFont("Roboto", 20, QFont.Bold))
        header.addWidget(title, 0, Qt.AlignRight | Qt.AlignVCenter)
        outer.addLayout(header)

        # --- meio: conteúdo (rola se precisar; ocupa toda a largura) ---
        # Objeto com objectName + regra global no style.qss (não
        # setStyleSheet local!) — um QScrollArea com stylesheet PRÓPRIO
        # quebra a herança do tema pros widgets dentro dele (achado real:
        # era exatamente isso que fazia a caixa da alternativa, os combos e
        # o botão "Começar" não aparecerem — todos são descendentes do
        # scroll). Mesmo padrão já usado em ChatScroll no guia_window.py.
        self.scroll = QScrollArea()
        self.scroll.setObjectName("LibraryScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.stack = _CurrentPageStack()
        self.stack.addWidget(self._build_filter_page())
        self.stack.addWidget(self._build_question_page())
        self.stack.currentChanged.connect(self._on_page_changed)
        self.scroll.setWidget(self.stack)

        outer.addWidget(self.scroll, 1)

        # --- rodapé: questão anterior (esquerda) + próxima questão (direita) ---
        # "Voltar aos filtros" saiu daqui (foi pro cabeçalho) — o lugar
        # abriu pro par natural do botão de avançar: navegar pra questão
        # ANTERIOR do histórico da sessão atual (não confundir com voltar
        # à tela de filtros).
        self.footer = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("NextQuestionButton")
        self.back_btn.setFont(QFont("Roboto", 20, QFont.Bold))
        self.back_btn.setFixedSize(52, 52)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setToolTip(t("library_previous_question_tooltip"))
        self.back_btn.setFocusPolicy(Qt.NoFocus)
        self.back_btn.clicked.connect(self._on_previous_clicked)
        self.footer.addWidget(self.back_btn, 0, Qt.AlignLeft)

        self.footer.addStretch(1)

        # Botão de report fica no meio do rodapé — contextual à questão
        # atual (o email já sai preenchido com id/matéria/enunciado), pra
        # o Matheus poder corrigir depois se alguma resposta estiver
        # errada. Não manda nada sozinho: só abre o cliente de email
        # padrão do usuário (ver bug_report.py) — sem senha/API key
        # nenhuma guardada no app, que vai virar um .exe distribuído.
        self.report_btn = QPushButton(t("quiz_report_button"))
        self.report_btn.setObjectName("DialogSecondaryButton")
        self.report_btn.setCursor(Qt.PointingHandCursor)
        self.report_btn.setFocusPolicy(Qt.NoFocus)
        self.report_btn.clicked.connect(self._on_report_clicked)
        self.footer.addWidget(self.report_btn, 0, Qt.AlignCenter)

        self.footer.addStretch(1)

        self.next_btn = QPushButton("→")
        self.next_btn.setObjectName("NextQuestionButton")
        self.next_btn.setFont(QFont("Roboto", 20, QFont.Bold))
        self.next_btn.setFixedSize(52, 52)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setToolTip(t("library_next_question_tooltip"))
        self.next_btn.setFocusPolicy(Qt.NoFocus)
        self.next_btn.clicked.connect(self._on_next_clicked)
        self.footer.addWidget(self.next_btn, 0, Qt.AlignRight)

        outer.addLayout(self.footer)
        self._set_footer_visible(False)

    def _set_footer_visible(self, visible: bool):
        self.back_btn.setVisible(visible)
        self.next_btn.setVisible(visible)
        self.report_btn.setVisible(visible)
        # Não é fisicamente parte do rodapé (mora no cabeçalho), mas seguem
        # a mesma regra de visibilidade: só aparece na página da questão.
        self.back_to_filters_btn.setVisible(visible)
        if visible:
            self._update_previous_button_state()

    def _on_page_changed(self, index: int):
        self._set_footer_visible(index == 1)
        if index == 0:
            self.tag_label.setText("")
        # O tamanho reportado pra página (sem "vazar" altura de uma página
        # grande pra outra menor ao trocar) já é resolvido por
        # _CurrentPageStack.sizeHint()/minimumSizeHint() — só precisa
        # avisar os layouts pra reconsultar depois da troca.
        self.stack.updateGeometry()
        self.scroll.updateGeometry()
        QTimer.singleShot(0, self.stack.updateGeometry)
        QTimer.singleShot(0, self.scroll.updateGeometry)

    # --- página 1: filtros ---

    def _build_filter_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 24, 0, 0)
        outer.setSpacing(16)

        # form centralizado, mas bem mais largo que uma coluna estreita —
        # usa boa parte da página em vez de deixar espaço vazio do lado.
        form_row = QHBoxLayout()
        form_row.addStretch(1)

        container = QWidget()
        container.setMinimumWidth(560)
        container.setMaximumWidth(900)
        form = QVBoxLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(14)

        subtitle = QLabel(t("library_choose_filters_label"))
        subtitle.setFont(QFont("Open Sans", 12))
        subtitle.setWordWrap(True)
        form.addWidget(subtitle)

        # --- matérias (coluna esquerda) + conteúdo (coluna direita),
        # lado a lado. O conteúdo depende da matéria escolhida, então fica
        # visualmente "preso" a ela — mas só passa a aparecer depois que a
        # pessoa CONFIRMA a seleção de matérias (botão dedicado), não a
        # cada clique numa caixinha — evita a seção de conteúdo inteira
        # sendo reconstruída/piscando toda vez que se marca mais uma
        # matéria antes de terminar de escolher todas.
        colunas_row = QHBoxLayout()
        colunas_row.setSpacing(28)

        materia_col_widget = QWidget()
        materia_col_widget.setMinimumWidth(200)
        materia_col_widget.setMaximumWidth(240)
        materia_col = QVBoxLayout(materia_col_widget)
        materia_col.setContentsMargins(0, 0, 0, 0)
        materia_col.setSpacing(6)

        self.materia_label = QLabel(t("library_subject_label"))
        self.materia_label.setFont(QFont("Open Sans", 11, QFont.DemiBold))
        materia_col.addWidget(self.materia_label)

        # "Selecionar todas" — sem essa opção explícita, a única forma de
        # incluir todas as matérias era deixar tudo desmarcado, o que não
        # é nada óbvio de descobrir sozinho.
        self.materia_select_all_cb = QCheckBox(t("library_select_all"))
        self.materia_select_all_cb.setFont(QFont("Open Sans", 10))
        self.materia_select_all_cb.setCursor(Qt.PointingHandCursor)
        self.materia_select_all_cb.stateChanged.connect(self._on_select_all_materias_toggled)
        materia_col.addWidget(self.materia_select_all_cb)

        self._materia_checks: dict[str, QCheckBox] = {}
        for materia in quiz.list_materias():
            cb = QCheckBox(materia)
            cb.setFont(QFont("Open Sans", 11))
            cb.setCursor(Qt.PointingHandCursor)
            cb.stateChanged.connect(self._on_materia_toggled)
            self._materia_checks[materia] = cb
            materia_col.addWidget(cb)

        materia_col.addSpacing(6)
        self.confirmar_materias_btn = QPushButton(t("library_confirm_subjects_btn"))
        self.confirmar_materias_btn.setObjectName("DialogSecondaryButton")
        self.confirmar_materias_btn.setCursor(Qt.PointingHandCursor)
        self.confirmar_materias_btn.setFocusPolicy(Qt.NoFocus)
        self.confirmar_materias_btn.clicked.connect(self._on_confirmar_materias_clicked)
        materia_col.addWidget(self.confirmar_materias_btn)
        materia_col.addStretch(1)

        # Conteúdo agrupado por matéria (título + caixas por matéria
        # marcada, com respiro visual entre grupos) em vez de uma lista só
        # em ordem alfabética geral, onde um conteúdo de Biologia podia
        # cair no meio de dois conteúdos de Física por acaso do alfabeto.
        # Reconstruído em _refresh_conteudo_section().
        conteudo_col_widget = QWidget()
        conteudo_col = QVBoxLayout(conteudo_col_widget)
        conteudo_col.setContentsMargins(0, 0, 0, 0)
        conteudo_col.setSpacing(6)

        self.conteudo_label = QLabel(t("library_content_label"))
        self.conteudo_label.setFont(QFont("Open Sans", 11, QFont.DemiBold))
        conteudo_col.addWidget(self.conteudo_label)

        self.conteudo_hint_label = QLabel("")
        self.conteudo_hint_label.setObjectName("CharCounterLabel")
        self.conteudo_hint_label.setFont(QFont("Open Sans", 10))
        self.conteudo_hint_label.setWordWrap(True)
        conteudo_col.addWidget(self.conteudo_hint_label)

        self.conteudo_container = QWidget()
        self.conteudo_layout = QVBoxLayout(self.conteudo_container)
        self.conteudo_layout.setContentsMargins(0, 0, 0, 0)
        self.conteudo_layout.setSpacing(10)
        conteudo_col.addWidget(self.conteudo_container)
        conteudo_col.addStretch(1)
        self._conteudo_checks: dict[tuple[str, str], QCheckBox] = {}

        colunas_row.addWidget(materia_col_widget)
        colunas_row.addWidget(conteudo_col_widget, 1)
        form.addLayout(colunas_row)

        # --- vestibulares: caixas de marcação numa linha (poucos valores
        # esperados, cabe horizontal em vez de grade), com o mesmo atalho
        # de "selecionar todos".
        self.vestibular_label = QLabel(t("library_exam_label"))
        self.vestibular_label.setFont(QFont("Open Sans", 11, QFont.DemiBold))
        form.addWidget(self.vestibular_label)

        self._vestibular_checks: dict[str, QCheckBox] = {}
        vestibular_row = QHBoxLayout()
        vestibular_row.setSpacing(14)
        self.vestibular_select_all_cb = QCheckBox(t("library_select_all"))
        self.vestibular_select_all_cb.setFont(QFont("Open Sans", 10))
        self.vestibular_select_all_cb.setCursor(Qt.PointingHandCursor)
        self.vestibular_select_all_cb.stateChanged.connect(self._on_select_all_vestibulares_toggled)
        vestibular_row.addWidget(self.vestibular_select_all_cb)
        for vestibular in quiz.list_vestibulares():
            cb = QCheckBox(vestibular)
            cb.setFont(QFont("Open Sans", 11))
            cb.setCursor(Qt.PointingHandCursor)
            cb.stateChanged.connect(self._on_vestibular_toggled)
            self._vestibular_checks[vestibular] = cb
            vestibular_row.addWidget(cb)
        vestibular_row.addStretch(1)
        form.addLayout(vestibular_row)

        # --- ano: continua seleção única (combo) — não é o que foi pedido
        # pra virar múltipla escolha, e por ora só existe um ano por
        # vestibular processado, então uma grade de caixas ficaria vazia
        # à toa. Repovoado conforme os vestibulares marcados.
        self.ano_label = QLabel(t("library_year_label"))
        self.ano_label.setFont(QFont("Open Sans", 11, QFont.DemiBold))
        self.ano_combo = QComboBox()
        self.ano_combo.setFont(QFont("Open Sans", 11))
        self.ano_combo.setMinimumHeight(34)
        form.addWidget(self.ano_label)
        form.addWidget(self.ano_combo)

        self.filter_error_label = QLabel("")
        self.filter_error_label.setObjectName("CharCounterLabel")
        self.filter_error_label.setProperty("exceeded", True)
        self.filter_error_label.setWordWrap(True)
        self.filter_error_label.hide()
        form.addWidget(self.filter_error_label)

        form_row.addWidget(container)
        form_row.addStretch(1)
        outer.addLayout(form_row)
        outer.addStretch(1)

        # "Começar" fixo no rodapé, canto inferior direito — mesmo padrão
        # visual do botão de próxima questão, só que maior e com texto.
        start_footer = QHBoxLayout()
        start_footer.addStretch(1)
        start_btn = QPushButton(t("library_start_btn"))
        start_btn.setObjectName("PrimaryButton")
        start_btn.setFont(QFont("Roboto", 13, QFont.DemiBold))
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setMinimumSize(160, 52)
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._on_start_clicked)
        start_footer.addWidget(start_btn)
        outer.addLayout(start_footer)

        return page

    def _checked_materias(self) -> list[str]:
        return [m for m, cb in self._materia_checks.items() if cb.isChecked()]

    def _checked_vestibulares(self) -> list[str]:
        return [v for v, cb in self._vestibular_checks.items() if cb.isChecked()]

    def _on_select_all_materias_toggled(self):
        marcar = self.materia_select_all_cb.isChecked()
        for cb in self._materia_checks.values():
            cb.blockSignals(True)
            cb.setChecked(marcar)
            cb.blockSignals(False)
        self._on_materia_toggled()

    def _on_materia_toggled(self):
        # Sincroniza "selecionar todas" pra refletir se, por marcação
        # manual caixa a caixa, todas acabaram ficando marcadas mesmo sem
        # usar o atalho — sem bloquear os sinais aqui, marcar/desmarcar
        # essa caixa disparia esse mesmo handler de novo (loop).
        todas = bool(self._materia_checks) and all(cb.isChecked() for cb in self._materia_checks.values())
        self.materia_select_all_cb.blockSignals(True)
        self.materia_select_all_cb.setChecked(todas)
        self.materia_select_all_cb.blockSignals(False)
        # Qualquer mudança na seleção de matérias invalida uma confirmação
        # anterior — o conteúdo só volta a aparecer depois de confirmar de
        # novo, pra nunca deixar visível/marcável o conteúdo de uma
        # matéria que acabou de ser desmarcada.
        self._materias_confirmadas = False
        self._refresh_conteudo_section()

    def _on_confirmar_materias_clicked(self):
        self._materias_confirmadas = True
        self._refresh_conteudo_section()

    def _on_select_all_vestibulares_toggled(self):
        marcar = self.vestibular_select_all_cb.isChecked()
        for cb in self._vestibular_checks.values():
            cb.blockSignals(True)
            cb.setChecked(marcar)
            cb.blockSignals(False)
        self._on_vestibular_toggled()

    def _on_vestibular_toggled(self):
        todas = bool(self._vestibular_checks) and all(cb.isChecked() for cb in self._vestibular_checks.values())
        self.vestibular_select_all_cb.blockSignals(True)
        self.vestibular_select_all_cb.setChecked(todas)
        self.vestibular_select_all_cb.blockSignals(False)
        self._refresh_ano_combo()
        # O conteúdo disponível por matéria pode variar por vestibular —
        # mesma lógica de invalidar a confirmação anterior.
        self._materias_confirmadas = False
        self._refresh_conteudo_section()

    def _refresh_ano_combo(self):
        vestibulares = self._checked_vestibulares()
        self.ano_combo.clear()
        self.ano_combo.addItem(_TODOS)
        self.ano_combo.addItems(str(a) for a in quiz.list_anos(vestibulares or None))

    def _refresh_conteudo_section(self):
        # Atualiza a fonte durável de seleção a partir dos checkboxes que
        # existem AGORA (antes de destruí-los), e descarta a seleção de
        # qualquer matéria que não esteja mais marcada. Precisa ser feito
        # aqui (não só guardar localmente pra reaplicar no mesmo rebuild)
        # porque a seção fica ESCONDIDA (checkboxes destruídos) sempre que
        # a confirmação é invalidada — sem um lugar durável pra guardar a
        # seleção, ela se perdia nesse intervalo entre desconfirmar e
        # confirmar de novo.
        for par, cb in self._conteudo_checks.items():
            if cb.isChecked():
                self._conteudo_selecionados.add(par)
            else:
                self._conteudo_selecionados.discard(par)
        materias_marcadas_agora = set(self._checked_materias())
        self._conteudo_selecionados = {
            par for par in self._conteudo_selecionados if par[0] in materias_marcadas_agora
        }

        while self.conteudo_layout.count():
            item = self.conteudo_layout.takeAt(0)
            widget = item.widget()
            if widget:
                # hide() + setParent(None) tiram o widget da árvore/pintura
                # imediatamente — deleteLater() sozinho não é confiável a
                # tempo aqui (mesma causa raiz do ghosting já corrigido nos
                # botões de alternativa da questão).
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._conteudo_checks = {}

        materias_marcadas = self._checked_materias()
        self.confirmar_materias_btn.setEnabled(bool(materias_marcadas))
        if not materias_marcadas:
            self.conteudo_container.hide()
            self.conteudo_hint_label.setText(t("library_content_hint_sem_materia"))
            self.conteudo_hint_label.show()
            return

        if not self._materias_confirmadas:
            # Matérias marcadas, mas ainda não confirmadas — de propósito,
            # não reconstrói/mostra as caixas de conteúdo a cada clique
            # isolado numa matéria, só depois que a pessoa confirma a
            # seleção (evita a seção de conteúdo "piscando" e mudando de
            # tamanho a cada matéria marcada em sequência).
            self.conteudo_container.hide()
            self.conteudo_hint_label.setText(t("library_content_hint_nao_confirmado"))
            self.conteudo_hint_label.show()
            return

        vestibulares_marcados = self._checked_vestibulares()
        agrupado = quiz.list_conteudos_agrupados(
            materias=materias_marcadas, vestibulares=vestibulares_marcados or None,
        )

        colunas = 1
        for materia in sorted(materias_marcadas):
            conteudos = agrupado.get(materia, [])
            if not conteudos:
                continue

            # um grupo = um único widget filho de conteudo_layout (título +
            # grade de caixas), pra entrar/sair da árvore de widgets como
            # uma unidade só na hora de limpar (ver loop de limpeza acima).
            grupo = QWidget()
            grupo_layout = QVBoxLayout(grupo)
            grupo_layout.setContentsMargins(0, 0, 0, 0)
            grupo_layout.setSpacing(4)

            titulo = QLabel(materia)
            titulo.setObjectName("ConteudoGrupoLabel")
            titulo.setFont(QFont("Open Sans", 10, QFont.DemiBold))
            grupo_layout.addWidget(titulo)

            grade = QGridLayout()
            grade.setSpacing(4)
            for indice, conteudo in enumerate(conteudos):
                cb = QCheckBox(conteudo)
                cb.setFont(QFont("Open Sans", 10))
                cb.setCursor(Qt.PointingHandCursor)
                if (materia, conteudo) in self._conteudo_selecionados:
                    cb.setChecked(True)
                self._conteudo_checks[(materia, conteudo)] = cb
                grade.addWidget(cb, indice // colunas, indice % colunas)
            grupo_layout.addLayout(grade)

            self.conteudo_layout.addWidget(grupo)

        self.conteudo_container.show()
        self.conteudo_hint_label.hide()

    def _current_filters(self) -> dict:
        materias = set(self._checked_materias())
        vestibulares = set(self._checked_vestibulares())
        # Agrupado por matéria (não um set achatado): uma matéria marcada
        # sem nenhum conteúdo seu marcado precisa continuar SEM restrição
        # de conteúdo — só entra no dict a matéria que de fato tem pelo
        # menos um conteúdo próprio marcado. Sem isso, marcar conteúdo só
        # de Física (com Biologia também marcada, mas sem conteúdo próprio
        # selecionado) excluiria TODAS as questões de Biologia por engano
        # (nenhum conteúdo de Biologia bate com um nome de conteúdo de
        # Física). Ver quiz.repository._bate_conteudo.
        conteudo_por_materia: dict[str, set[str]] = {}
        for (materia, conteudo), cb in self._conteudo_checks.items():
            if cb.isChecked():
                conteudo_por_materia.setdefault(materia, set()).add(conteudo)
        ano = self.ano_combo.currentText()
        return {
            "materia": materias or None,
            "conteudo": conteudo_por_materia or None,
            "vestibular": vestibulares or None,
            "ano": int(ano) if ano and ano != _TODOS else None,
        }

    def _show_filter_error(self, message: str):
        self.filter_error_label.setText(message)
        self.filter_error_label.style().unpolish(self.filter_error_label)
        self.filter_error_label.style().polish(self.filter_error_label)
        self.filter_error_label.show()

    def _on_start_clicked(self):
        filters = self._current_filters()
        if quiz.count_questions(**filters) == 0:
            self._show_filter_error(t("library_no_questions_status"))
            return
        self.filter_error_label.hide()
        self._active_filters = filters
        self._shown_ids = set()
        self._history = []
        self._history_pos = -1
        self._load_next_question()

    # --- página 2: questão ---

    def _build_question_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignTop)

        self.enunciado_label = QLabel("")
        self.enunciado_label.setTextFormat(Qt.RichText)
        self.enunciado_label.setFont(QFont("Open Sans", 14))
        self.enunciado_label.setWordWrap(True)
        layout.addWidget(self.enunciado_label)

        # Figura da questão (recortada da prova original) — só algumas
        # questões têm (q.get("imagem")); escondida por padrão.
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignHCenter)
        self.image_label.hide()
        layout.addWidget(self.image_label)

        self.alt_container = QWidget()
        self.alt_layout = QGridLayout(self.alt_container)
        self.alt_layout.setContentsMargins(0, 0, 0, 0)
        self.alt_layout.setSpacing(10)
        layout.addWidget(self.alt_container)

        self.explanation_label = QLabel("")
        self.explanation_label.setObjectName("LibraryExplanationLabel")
        self.explanation_label.setTextFormat(Qt.RichText)
        self.explanation_label.setFont(QFont("Open Sans", 12))
        self.explanation_label.setWordWrap(True)
        self.explanation_label.hide()
        layout.addWidget(self.explanation_label)

        layout.addStretch(1)
        return page

    def _load_next_question(self):
        question = quiz.get_random_question(exclude_ids=self._shown_ids, **self._active_filters)
        if question is None:
            self.stack.setCurrentIndex(0)
            self._show_filter_error(t("library_no_more_questions_status"))
            return
        self._shown_ids.add(question["id"])
        self._history.append({"question": question, "answered": False, "selected": None})
        self._history_pos = len(self._history) - 1
        self._current_question = question
        self._answered = False
        self._render_question()
        self.stack.setCurrentIndex(1)
        self._update_previous_button_state()

    def _show_history_entry(self):
        # Reexibe uma questão já vista antes na sessão (navegação "questão
        # anterior"/"próxima"), em vez de buscar uma nova aleatória —
        # preserva o estado de respondida (cores certo/errado + explicação)
        # exatamente como a pessoa deixou, sem resetar nada.
        entrada = self._history[self._history_pos]
        self._current_question = entrada["question"]
        self._render_question()
        self._answered = entrada["answered"]
        if entrada["answered"]:
            self._apply_answered_feedback(entrada["selected"])
        self._update_previous_button_state()

    def _update_previous_button_state(self):
        # Só faz sentido voltar se existir uma questão anterior no
        # histórico desta sessão de filtros (não volta pra tela de
        # filtros — isso agora é uma ação separada, no cabeçalho).
        self.back_btn.setEnabled(self._history_pos > 0)

    def _render_question(self):
        q = self._current_question
        self.tag_label.setText(f"{q['vestibular']} {q['ano']} — {q['materia']} — {q['conteudo']}: {q['detalhe']}")
        self.enunciado_label.setText(_render_rich(q["enunciado"]))
        self.explanation_label.hide()
        self.explanation_label.setText("")

        imagem = q.get("imagem")
        if imagem:
            pixmap = QPixmap(str(quiz.image_path(imagem)))
            if not pixmap.isNull():
                if pixmap.width() > _IMAGE_MAX_WIDTH:
                    pixmap = pixmap.scaledToWidth(_IMAGE_MAX_WIDTH, Qt.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
                self.image_label.show()
            else:
                self.image_label.hide()
        else:
            self.image_label.hide()

        while self.alt_layout.count():
            item = self.alt_layout.takeAt(0)
            widget = item.widget()
            if widget:
                # deleteLater() sozinho não é suficiente aqui: o evento de
                # exclusão adiada podia não ser processado a tempo (mesmo
                # depois de vários processEvents()), deixando o botão
                # antigo "fantasma" — ainda filho de alt_container, ainda
                # pintável — e causando um ghosting visual real (texto da
                # alternativa antiga sobreposto ao da nova) ao navegar
                # rápido entre questões. hide() + setParent(None) tiram o
                # widget da árvore/pintura NA HORA; deleteLater() só cuida
                # da limpeza final do objeto.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._alt_buttons = {}

        eh_imagem = q.get("alternativas_tipo") == "imagem"
        colunas = _ALT_IMAGE_COLUMNS if eh_imagem else 1
        for indice, (letra, valor) in enumerate(q["alternativas"].items()):
            btn = self._build_alt_image_button(letra, valor) if eh_imagem else self._build_alt_text_button(letra, valor)
            btn.clicked.connect(lambda _checked=False, letra_=letra: self._on_alternative_clicked(letra_))
            self.alt_layout.addWidget(btn, indice // colunas, indice % colunas)
            self._alt_buttons[letra] = btn
            # Botão criado em tempo de execução (depois que a janela já foi
            # exibida) — força reavaliação do estilo pra garantir que a
            # caixa apareça já na primeira renderização, sem depender só da
            # herança automática do stylesheet nessa profundidade de
            # aninhamento (QScrollArea + QStackedWidget).
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if not eh_imagem:
            # QGridLayout não propaga height-for-width através da fronteira
            # de um QWidget com layout próprio (aqui, o QPushButton com o
            # QLabel quebrado dentro) — o botão fica "cego" pra altura real
            # que o texto quebrado precisa, mesmo o QLabel calculando certo
            # sozinho. Sem isso, o texto longo era cortado (sem reticências,
            # sem aviso) em vez de mostrar a segunda linha. Corrige na mão,
            # depois que o layout já rodou uma vez e os botões já têm a
            # largura real de coluna (só aí heightForWidth() dá um valor
            # que faz sentido).
            QTimer.singleShot(0, self._ajustar_altura_alternativas_texto)

    def _ajustar_altura_alternativas_texto(self):
        for btn in self._alt_buttons.values():
            layout = btn.layout()
            if layout is None or layout.count() == 0:
                continue
            label = layout.itemAt(0).widget()
            if not isinstance(label, QLabel) or label.width() <= 0:
                continue
            margens = layout.contentsMargins()
            altura_texto = label.heightForWidth(label.width())
            altura_total = altura_texto + margens.top() + margens.bottom()
            btn.setMinimumHeight(max(42, altura_total))

    def _build_alt_text_button(self, letra: str, texto: str) -> QPushButton:
        # QPushButton não quebra linha no próprio texto — alternativas
        # longas (comuns em Geografia/Química) simplesmente estouravam a
        # largura do botão, esticando a página inteira e forçando uma barra
        # de rolagem horizontal. Fix: o texto vai num QLabel filho, com
        # wordWrap ligado, dentro de um layout interno do botão — o clique
        # continua funcionando no QPushButton em volta normalmente.
        btn = QPushButton()
        btn.setObjectName("AlternativeButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(42)
        btn.setFocusPolicy(Qt.NoFocus)

        layout = QHBoxLayout(btn)
        # Margens explícitas porque o padding do QSS (12px 16px) não é
        # respeitado de forma confiável quando o botão passa a ter um
        # layout/filho próprio — sem isso, o texto ficava colado na borda.
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(f"{letra}) {texto}")
        label.setFont(QFont("Open Sans", 12))
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(label)
        return btn

    def _build_alt_image_button(self, letra: str, arquivo: str) -> QToolButton:
        # Pra questões em que as ALTERNATIVAS são imagens (ex: "qual gráfico
        # representa a função?", não só o enunciado) — QPushButton não
        # suporta ícone acima do texto, então usa QToolButton, que suporta
        # nativamente (ToolButtonTextUnderIcon). O resto (clique, estado
        # certo/errado via property "state") funciona igual ao botão de
        # texto — ver QToolButton#AlternativeButton no style.qss.
        btn = QToolButton()
        btn.setObjectName("AlternativeButton")
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setText(f"({letra})")
        btn.setFont(QFont("Open Sans", 12, QFont.DemiBold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        pixmap = QPixmap(str(quiz.image_path(arquivo)))
        if not pixmap.isNull():
            if pixmap.width() > _ALT_IMAGE_MAX_WIDTH:
                pixmap = pixmap.scaledToWidth(_ALT_IMAGE_MAX_WIDTH, Qt.SmoothTransformation)
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(pixmap.size())
        return btn

    def _on_alternative_clicked(self, letra: str):
        if self._answered:
            return
        self._answered = True
        if self._history_pos >= 0:
            entrada = self._history[self._history_pos]
            entrada["answered"] = True
            entrada["selected"] = letra
        self._apply_answered_feedback(letra)

    def _apply_answered_feedback(self, letra: str):
        # Pinta as alternativas de certo/errado e mostra a explicação —
        # usado tanto num clique de verdade quanto ao reexibir uma questão
        # já respondida antes (navegação "questão anterior"/"próxima").
        q = self._current_question
        correta = q["resposta_correta"]

        for l, btn in self._alt_buttons.items():
            btn.setEnabled(False)
            if l == correta:
                btn.setProperty("state", "correct")
            elif l == letra:
                btn.setProperty("state", "incorrect")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if letra == correta:
            texto = t("library_correct_feedback_template", explicacao=q["explicacao"])
        else:
            texto = t("library_incorrect_feedback_template", correta=correta, explicacao=q["explicacao"])
        self.explanation_label.setText(_render_rich(texto))
        self.explanation_label.show()

    def _on_next_clicked(self):
        # Só busca uma questão nova quando já se está na ponta mais
        # recente do histórico — se a pessoa voltou uma ou mais questões,
        # "próxima" primeiro reavança pelo que já foi visto, sem sortear
        # uma questão nova por engano.
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self._show_history_entry()
        else:
            self._load_next_question()

    def _on_previous_clicked(self):
        if self._history_pos > 0:
            self._history_pos -= 1
            self._show_history_entry()

    def _on_back_to_filters(self):
        self.stack.setCurrentIndex(0)

    def _on_report_clicked(self):
        q = self._current_question
        if q is None:
            return
        enunciado_limpo = q["enunciado"].replace("*", "")
        assunto = t("quiz_report_email_subject", id=q["id"])
        corpo = t(
            "quiz_report_email_body",
            id=q["id"], vestibular=q["vestibular"], ano=q["ano"], materia=q["materia"],
            conteudo=q["conteudo"], detalhe=q["detalhe"], resposta_correta=q["resposta_correta"],
            enunciado=enunciado_limpo,
        )
        # Tenta abrir o cliente de email padrão (funciona pra quem tem um
        # configurado), mas não é garantido — testado na prática: sem
        # cliente de email associado ao mailto: no Windows, isso só abre o
        # navegador padrão sem fazer nada útil. Por isso SEMPRE mostra
        # também o diálogo com o texto pronto pra copiar — esse sim
        # funciona não importa o que o usuário tem instalado.
        bug_report.open_report_email(assunto, corpo)
        from ui.dialogs import ReportBugDialog
        dialog = ReportBugDialog(assunto, corpo, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()
