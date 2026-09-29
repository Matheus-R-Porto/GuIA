from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox,
    QScrollArea, QScrollBar, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget,
)

import theme
import user_config
from config import HARD_MAX_INPUT_CHARS, MAX_USER_CHARS
from i18n import t
from ui.widgets import ChatInputPanel, MessageBubble, SidebarWidget, QuizWidget
from ui.workers import AIWorker, TitleWorker

_DEFAULT_WELCOME_TEXT = t("welcome_default")


class GuiAWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.first_message_sent = False
        self.input_drop_anim = None
        self.worker = None
        self.title_worker = None
        self.loading_bubble = None
        self.is_waiting_response = False
        self.syncing_external_scroll = False
        self.syncing_internal_scroll = False
        self._pending_first_message = None
        self._quiz_open = False

        self.max_send_chars = MAX_USER_CHARS
        self.max_input_chars = HARD_MAX_INPUT_CHARS

        self.init_ui()
        self.load_styles()
        self.refresh_conversation_list()
        self.showMaximized()
        QTimer.singleShot(0, self.update_responsive_ui)
        QTimer.singleShot(0, self.update_overlay_positions)
        QTimer.singleShot(0, self.update_chat_scroll_ui)

    def load_styles(self):
        sheet = theme.stylesheet(
            user_config.get("theme", "light"),
            accent=user_config.get("accent_color", "#1565C0"),
        )
        self.setStyleSheet(sheet)
        # O Laboratório fica muitas camadas abaixo (QScrollArea + QStackedWidget
        # + botões criados em tempo de execução) — a herança automática do
        # stylesheet da janela não estava chegando de forma confiável nela
        # (mesmo bug que fazia os diálogos precisarem de setStyleSheet
        # explícito). Aplicar direto nela também resolve.
        self.quiz_widget.setStyleSheet(sheet)

    def apply_theme(self):
        """Re-aplica o tema atual (chamado ao salvar nas configurações)."""
        self.load_styles()

    def init_ui(self):
        self.setWindowTitle(t("app_window_title"))
        self.resize(1200, 800)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.newChatRequested.connect(self.handle_new_chat)
        self.sidebar.sidebarToggled.connect(self.on_sidebar_toggled)
        self.sidebar.sidebarWidthChanged.connect(self.on_sidebar_width_changed)
        self.sidebar.settingsRequested.connect(self.open_settings)
        self.sidebar.quizRequested.connect(self.open_quiz)
        self.sidebar.conversationSelected.connect(self.handle_load_conversation)
        self.sidebar.conversationRenameRequested.connect(self.handle_rename_conversation)
        self.sidebar.conversationDeleteRequested.connect(self.handle_delete_conversation)
        self.sidebar.conversationMoveToProjectRequested.connect(self.handle_move_to_project)

        self.content_area = QFrame()
        self.content_area.setObjectName("ContentArea")
        self.content_area.setStyleSheet("background: transparent;")

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.top_spacer = QWidget()
        self.top_spacer.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.welcome_label = QLabel(_DEFAULT_WELCOME_TEXT)
        self.welcome_label.setObjectName("WelcomeLabel")
        self.welcome_label.setFont(QFont("Roboto", 32, QFont.Bold))
        self.welcome_label.setAlignment(Qt.AlignCenter)
        # Quebra linha em vez de estourar a janela — precisa pra textos
        # dinâmicos longos, tipo o título de um artigo do Laboratório
        # ("Vamos conversar sobre \"...\"?").
        self.welcome_label.setWordWrap(True)
        # 1400, não 1000: o texto padrão ("Como GuIA pode te ajudar hoje?")
        # sozinho já precisa de ~1290px a 32pt — um teto menor forçava
        # quebra de linha nele também, sem necessidade.
        self.welcome_label.setMaximumWidth(1400)

        self.bottom_spacer = QWidget()
        self.bottom_spacer.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.chat_area = QWidget()
        self.chat_area_layout = QHBoxLayout(self.chat_area)
        self.chat_area_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_area_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ChatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.hide()

        self.scroll_content = QWidget()
        self.messages_layout = QVBoxLayout(self.scroll_content)
        self.messages_layout.setContentsMargins(18, 20, 18, 18)
        self.messages_layout.setSpacing(15)
        self.messages_layout.addStretch(1)
        self.scroll.setWidget(self.scroll_content)

        self.chat_scroll_column = QWidget()
        self.chat_scroll_column.setFixedWidth(40)
        self.chat_scroll_column_layout = QVBoxLayout(self.chat_scroll_column)
        self.chat_scroll_column_layout.setContentsMargins(0, 18, 0, 140)
        self.chat_scroll_column_layout.setAlignment(Qt.AlignHCenter)

        self.chat_scroll_up_btn = QToolButton()
        self.chat_scroll_up_btn.setObjectName("ScrollArrowButton")
        self.chat_scroll_up_btn.setText("▲")
        self.chat_scroll_up_btn.setFixedSize(18, 16)
        self.chat_scroll_up_btn.clicked.connect(self.scroll_chat_up)

        self.chat_outer_scrollbar = QScrollBar(Qt.Vertical)
        self.chat_outer_scrollbar.setObjectName("ChatOuterScrollBar")
        self.chat_outer_scrollbar.setFixedWidth(20)
        self.chat_outer_scrollbar.valueChanged.connect(self.sync_chat_external_to_internal)

        self.chat_scroll_down_btn = QToolButton()
        self.chat_scroll_down_btn.setObjectName("ScrollArrowButton")
        self.chat_scroll_down_btn.setText("▼")
        self.chat_scroll_down_btn.setFixedSize(18, 16)
        self.chat_scroll_down_btn.clicked.connect(self.scroll_chat_down)

        self.chat_scroll_column_layout.addWidget(self.chat_scroll_up_btn, 0, Qt.AlignHCenter)
        self.chat_scroll_column_layout.addWidget(self.chat_outer_scrollbar, 1, Qt.AlignHCenter)
        self.chat_scroll_column_layout.addWidget(self.chat_scroll_down_btn, 0, Qt.AlignHCenter)

        self.chat_area_layout.addWidget(self.scroll, 1)
        self.chat_area_layout.addWidget(self.chat_scroll_column, 0)

        chat_sb = self.scroll.verticalScrollBar()
        chat_sb.valueChanged.connect(self.sync_chat_internal_to_external)
        chat_sb.valueChanged.connect(self.update_chat_scroll_ui)
        chat_sb.rangeChanged.connect(self.update_chat_scroll_ui)

        self.content_layout.addWidget(self.top_spacer, 1)
        # Sem Qt.AlignHCenter aqui de propósito: com esse flag, o layout
        # dimensiona o label pelo sizeHint() "livre" (sem largura definida)
        # em vez de esticar até maximumWidth — isso quebrava o cálculo de
        # altura do texto quebrado em 2 linhas (texto ficava sobreposto,
        # a altura reservada era a de 1 linha só). O label já se
        # centraliza sozinho via setAlignment(Qt.AlignCenter).
        self.content_layout.addWidget(self.welcome_label)
        self.content_layout.addWidget(self.chat_area, 1)
        self.content_layout.addWidget(self.bottom_spacer, 1)

        self.quiz_widget = QuizWidget()
        self.quiz_widget.chatAboutQuestionRequested.connect(self.handle_start_quiz_chat)
        self.content_layout.addWidget(self.quiz_widget, 1)
        self.quiz_widget.hide()

        self.input_overlay = QWidget(self.content_area)
        self.input_overlay.setAttribute(Qt.WA_StyledBackground, True)

        self.input_wrapper_layout = QHBoxLayout(self.input_overlay)
        self.input_wrapper_layout.setContentsMargins(0, 12, 0, 24)
        self.input_wrapper_layout.setSpacing(0)

        self.input_panel = ChatInputPanel(
            max_send_chars=self.max_send_chars,
            max_input_chars=self.max_input_chars,
        )
        self.input_panel.sourcesRequested.connect(self.handle_request_sources)
        self.input_panel.sendRequested.connect(self.handle_send)
        self.input_panel.heightChanged.connect(self.on_input_panel_height_changed)

        self.input_wrapper_layout.addStretch()
        self.input_wrapper_layout.addWidget(self.input_panel)
        self.input_wrapper_layout.addStretch()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

        self.update_input_overlay_height()
        self.update_chat_bottom_spacing()
        self.update_input_scroll_ui()
        self.update_chat_scroll_ui()
        self.set_busy_state(False)

    # --- resize / layout ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_responsive_ui)
        QTimer.singleShot(0, self.update_overlay_positions)
        QTimer.singleShot(0, self.update_chat_bottom_spacing)
        QTimer.singleShot(0, self.update_chat_scroll_ui)

    def on_sidebar_toggled(self, _expanded):
        QTimer.singleShot(0, lambda: self.on_sidebar_width_changed(self.sidebar.width()))

    def on_sidebar_width_changed(self, _width):
        self.update_responsive_ui()
        self.update_overlay_positions()
        self.update_chat_bottom_spacing()
        self.update_chat_scroll_ui()

    def on_input_panel_height_changed(self):
        self.update_input_overlay_height()
        QTimer.singleShot(0, self.update_overlay_positions)
        QTimer.singleShot(0, self.update_chat_bottom_spacing)

    def update_input_overlay_height(self):
        self.input_overlay.setFixedHeight(self.input_panel.height() + 36)

    def get_input_width(self):
        content_width = self.content_area.width()
        factor = 0.78 if self.sidebar.sidebar_expanded else 0.82
        if not self.isMaximized() and self.width() < 1400:
            factor = 0.72 if self.sidebar.sidebar_expanded else 0.76
        return max(520, min(int(content_width * factor), 1100))

    def get_input_final_rect(self):
        w = self.get_input_width()
        h = self.input_overlay.height()
        x = max(0, (self.content_area.width() - w) // 2)
        y = self.content_area.height() - h - 24
        return QRect(x, y, w, h)

    def get_input_initial_rect(self):
        w = self.get_input_width()
        h = self.input_overlay.height()
        x = max(0, (self.content_area.width() - w) // 2)
        label_geo = self.welcome_label.geometry()
        y = min(label_geo.bottom() + 28, self.content_area.height() - h - 40)
        return QRect(x, y, w, h)

    def get_chat_bottom_spacing(self):
        overlay_height = self.input_overlay.height() or self.input_panel.height() + 36
        return overlay_height + 18

    def update_chat_bottom_spacing(self):
        self.chat_area_layout.setContentsMargins(0, 0, 0, self.get_chat_bottom_spacing())
        self.messages_layout.setContentsMargins(18, 20, 18, 18)
        self.chat_scroll_column_layout.setContentsMargins(0, 18, 0, 18)
        self.chat_area_layout.invalidate()
        self.chat_area.updateGeometry()
        self.scroll.updateGeometry()
        self.scroll_content.updateGeometry()
        self.update_chat_scroll_ui()

    def update_overlay_positions(self):
        if self.content_area.width() <= 0 or self.content_area.height() <= 0:
            return
        rect = self.get_input_final_rect() if self.first_message_sent else self.get_input_initial_rect()
        self.input_overlay.setGeometry(rect)

    def update_responsive_ui(self):
        compact = self.width() < 1400 and not self.isMaximized()
        self.sidebar.logo.setFont(QFont("Roboto", 20 if compact else 24, QFont.Bold))
        self.welcome_label.setFont(QFont("Roboto", 26 if compact else 32, QFont.Bold))
        base_size = user_config.chat_font_size()
        self.input_panel.input_field.setFont(QFont("Open Sans", base_size - (2 if compact else 1)))
        for btn in self.sidebar.menu_buttons:
            btn.setFont(QFont("Roboto", 11 if compact else 12))
        self.input_panel.setFixedWidth(self.get_input_width())
        self.refresh_bubble_widths()
        self.update_input_overlay_height()

    # --- first message animation ---

    def animate_first_message_transition(self):
        start_rect = self.get_input_initial_rect()
        self.input_overlay.setGeometry(start_rect)
        self.input_overlay.raise_()
        end_rect = self.get_input_final_rect()

        self.input_drop_anim = QPropertyAnimation(self.input_overlay, b"geometry", self)
        self.input_drop_anim.setDuration(220)
        self.input_drop_anim.setStartValue(start_rect)
        self.input_drop_anim.setEndValue(end_rect)
        self.input_drop_anim.setEasingCurve(QEasingCurve.InOutQuart)
        self.input_drop_anim.finished.connect(self.finish_first_transition)
        self.input_drop_anim.start()
        QTimer.singleShot(20, self.activate_chat_layout)

    def activate_chat_layout(self):
        # chat_area normalmente já está visível por padrão (só é escondido
        # de propósito ao entrar no Laboratório/Biblioteca, via
        # _hide_chat_area()) — mas se o 1º envio dessa "sessão" de chat
        # acontece logo depois de sair de uma dessas telas (ex: "Conversar
        # no chat" a partir de um artigo), chat_area pode continuar
        # escondido nesse ponto. Reexibir aqui, de forma explícita, garante
        # que a área de mensagens sempre apareça, independente de onde o
        # usuário estava antes.
        self.chat_area.show()
        self.scroll.show()
        self.top_spacer.hide()
        self.welcome_label.hide()
        self.bottom_spacer.hide()
        self.content_area.updateGeometry()
        self.scroll.updateGeometry()
        self.chat_scroll_column.setVisible(True)
        self.update_chat_bottom_spacing()
        self.update_chat_scroll_ui()

    def finish_first_transition(self):
        self.update_overlay_positions()
        self.update_chat_bottom_spacing()

    # --- scroll sync ---

    def sync_chat_internal_to_external(self):
        if self.syncing_external_scroll:
            return
        sb = self.scroll.verticalScrollBar()
        self.syncing_internal_scroll = True
        self.chat_outer_scrollbar.setMinimum(sb.minimum())
        self.chat_outer_scrollbar.setMaximum(sb.maximum())
        self.chat_outer_scrollbar.setPageStep(sb.pageStep())
        self.chat_outer_scrollbar.setValue(sb.value())
        self.syncing_internal_scroll = False

    def sync_chat_external_to_internal(self, value):
        if self.syncing_internal_scroll:
            return
        sb = self.scroll.verticalScrollBar()
        self.syncing_external_scroll = True
        sb.setValue(value)
        self.syncing_external_scroll = False

    def update_input_scroll_ui(self):
        self.input_panel.update_input_scroll_ui()

    def update_chat_scroll_ui(self):
        sb = self.scroll.verticalScrollBar()
        has_scroll = sb.maximum() > sb.minimum()
        self.chat_scroll_column.setVisible(self.first_message_sent and has_scroll)

        if not has_scroll:
            self.chat_outer_scrollbar.setMinimum(0)
            self.chat_outer_scrollbar.setMaximum(0)
            self.chat_outer_scrollbar.setValue(0)
            for btn in (self.chat_scroll_up_btn, self.chat_scroll_down_btn):
                btn.setProperty("edge", False)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            return

        self.sync_chat_internal_to_external()
        at_top = sb.value() <= sb.minimum() + 1
        at_bottom = sb.value() >= sb.maximum() - 1
        for btn, edge in [(self.chat_scroll_up_btn, at_top), (self.chat_scroll_down_btn, at_bottom)]:
            btn.setProperty("edge", edge)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def scroll_chat_up(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.value() - max(40, sb.singleStep() * 3))

    def scroll_chat_down(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.value() + max(40, sb.singleStep() * 3))

    # --- state ---

    def set_busy_state(self, busy: bool):
        self.is_waiting_response = busy
        self.input_panel.set_busy(busy)
        self.sidebar.set_busy(busy)
        self.input_panel.set_sources_available(self.controller.can_request_sources())

    # --- handlers ---

    def open_settings(self):
        from ui.dialogs import SettingsDialog
        dlg = SettingsDialog(self.controller, self)
        dlg.setStyleSheet(self.styleSheet())
        dlg.saved.connect(self.controller.reload_settings)
        dlg.saved.connect(self.apply_theme)
        dlg.saved.connect(self.apply_font_size)
        dlg.switchProfileRequested.connect(self.handle_switch_profile)
        dlg.exec()

    def open_quiz(self):
        if self.is_waiting_response or self._quiz_open:
            return
        self._quiz_open = True
        self._hide_chat_area()
        self.quiz_widget.show()
        # Reexibir um widget que já tinha conteúdo (voltando de outra tela)
        # pode renderizar 1 frame com geometria desatualizada antes do
        # layout assentar de vez — força recalcular já e de novo assim que
        # o loop de eventos processar a exibição.
        self.quiz_widget.updateGeometry()
        QTimer.singleShot(0, self.quiz_widget.updateGeometry)

    def handle_start_quiz_chat(self, question: dict, selected: str):
        if self.is_waiting_response:
            return
        conversation_id = self.controller.start_quiz_chat(question, selected)
        self._reset_chat_ui()
        self._pending_first_message = None
        self.handle_load_conversation(conversation_id, force=True)
        self.refresh_conversation_list()
        self.input_panel.input_field.setFocus()

    def close_quiz(self):
        if not self._quiz_open:
            return
        self._quiz_open = False
        self.quiz_widget.hide()
        self._show_chat_area()

    def _hide_chat_area(self):
        self.top_spacer.hide()
        self.welcome_label.hide()
        self.chat_area.hide()
        self.bottom_spacer.hide()
        self.input_overlay.hide()

    def _show_chat_area(self):
        if self.first_message_sent:
            self.chat_area.show()
        else:
            self.top_spacer.show()
            self.welcome_label.show()
            self.bottom_spacer.show()
        self.input_overlay.show()
        self.update_overlay_positions()
        self.update_chat_bottom_spacing()
        self.update_chat_scroll_ui()

    def handle_switch_profile(self):
        from ui.dialogs import LoginDialog
        login = LoginDialog(self.controller, self)
        login.setStyleSheet(self.styleSheet())
        if login.exec() == LoginDialog.Accepted:
            self.handle_new_chat()
            self.refresh_conversation_list()

    def handle_new_chat(self):
        if self.is_waiting_response:
            return
        # Reseta antes de fechar o Laboratório para restaurar a tela correta.
        self._reset_chat_ui()
        if self._quiz_open:
            self.close_quiz()
        self.controller.new_chat()
        self.welcome_label.setText(_DEFAULT_WELCOME_TEXT)

    def _reset_chat_ui(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.first_message_sent = False
        self.input_panel.clear_text()
        self.scroll.hide()
        self.chat_scroll_column.hide()
        self.top_spacer.show()
        self.welcome_label.show()
        self.bottom_spacer.show()
        self.update_input_overlay_height()
        self.update_overlay_positions()
        self.update_chat_bottom_spacing()
        self.sidebar.set_active_conversation(None)
        self.input_panel.set_sources_available(False)

    def closeEvent(self, event):
        if any(w is not None and w.isRunning() for w in (self.worker, self.title_worker)):
            event.ignore()
            return
        self.controller.close()
        super().closeEvent(event)

    # --- histórico de conversas ---

    def refresh_conversation_list(self):
        conversations = self.controller.list_conversations()
        self.sidebar.set_conversations(
            [{"id": c["id"], "title": c["title"]} for c in conversations]
        )
        self.sidebar.set_active_conversation(self.controller.current_conversation_id)

    def handle_load_conversation(self, conversation_id: int, force: bool = False):
        if self.is_waiting_response:
            return
        if (not force and self.controller.current_conversation_id == conversation_id
                and not self._quiz_open):
            return
        if self._quiz_open:
            self.close_quiz()

        messages = self.controller.load_conversation(conversation_id)
        self.input_panel.set_sources_available(self.controller.can_request_sources())

        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for m in messages:
            bubble = MessageBubble(
                m["content"], self.get_max_bubble_width(), is_user=(m["role"] == "user"),
                font_size=user_config.chat_font_size(),
            )
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        self.input_panel.clear_text()
        self.first_message_sent = True
        self.activate_chat_layout()
        self.update_overlay_positions()
        self.scroll_to_bottom()
        self.sidebar.set_active_conversation(conversation_id)
        # Mesmo motivo do add_message(): os balões acima foram criados ANTES
        # de activate_chat_layout() mostrar o scroll — a largura calculada
        # ali pode estar errada (baseada num viewport ainda não assentado).
        QTimer.singleShot(0, self.refresh_bubble_widths)

    def handle_rename_conversation(self, conversation_id: int, new_title: str):
        self.controller.rename_conversation(conversation_id, new_title)

    def handle_delete_conversation(self, conversation_id: int):
        confirm = QMessageBox.question(
            self, t("delete_conversation_title"),
            t("delete_conversation_body"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        was_active = self.controller.current_conversation_id == conversation_id
        self.controller.delete_conversation(conversation_id)
        if was_active:
            self.handle_new_chat()
        self.refresh_conversation_list()

    def handle_move_to_project(self, conversation_id: int):
        QMessageBox.information(
            self, t("coming_soon_title"),
            t("coming_soon_projects_body"),
        )

    def on_title_generated(self, conversation_id: int, title: str):
        self.controller.rename_conversation(conversation_id, title)
        self.refresh_conversation_list()
        self.title_worker = None

    def handle_request_sources(self):
        if self.is_waiting_response or not self.controller.can_request_sources():
            return
        self.add_message(t("sources_request"), is_user=True)
        self.loading_bubble = MessageBubble(
            t("sources_loading"), self.get_max_bubble_width(),
            is_user=False, is_loading=True,
            font_size=user_config.chat_font_size(),
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.loading_bubble)
        self.scroll_to_bottom()
        self.set_busy_state(True)
        self.worker = AIWorker(self.controller, t("sources_request"), request_sources=True)
        self.worker.finished.connect(self.on_ai_response)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def handle_send(self):
        if self.is_waiting_response:
            return
        raw_text = self.input_panel.get_text()
        text = raw_text.strip()
        if not text:
            return
        if len(raw_text) > self.max_send_chars:
            exceeded = len(raw_text) - self.max_send_chars
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(t("message_too_long_title"))
            msg.setText(t("message_too_long_body", exceeded=exceeded))
            msg.exec()
            return

        if not self.first_message_sent:
            self.first_message_sent = True
            self.animate_first_message_transition()

        self.add_message(text, is_user=True)
        self.input_panel.clear_text()

        self.loading_bubble = MessageBubble(
            t("thinking_label"), self.get_max_bubble_width(), is_user=False, is_loading=True,
            font_size=user_config.chat_font_size(),
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.loading_bubble)
        self.scroll_to_bottom()
        self.set_busy_state(True)

        # Se ainda não há conversa ativa, esta troca vai criar uma — guarda a
        # mensagem para gerar um título melhor (via modelo) depois da resposta.
        if self.controller.current_conversation_id is None:
            self._pending_first_message = text

        self.worker = AIWorker(self.controller, text)
        self.worker.finished.connect(self.on_ai_response)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def on_ai_response(self, response: str):
        if self.loading_bubble is not None:
            self.loading_bubble.stop_loading()
            self.messages_layout.removeWidget(self.loading_bubble)
            self.loading_bubble.deleteLater()
            self.loading_bubble = None
        self.add_message(response, is_user=False)
        self.worker = None
        self.set_busy_state(False)
        self.input_panel.input_field.setFocus()

        self.refresh_conversation_list()

        if self._pending_first_message is not None:
            conversation_id = self.controller.current_conversation_id
            first_message = self._pending_first_message
            self._pending_first_message = None
            if conversation_id is not None:
                self.title_worker = TitleWorker(self.controller, conversation_id, first_message)
                self.title_worker.finished.connect(self.on_title_generated)
                self.title_worker.finished.connect(self.title_worker.deleteLater)
                self.title_worker.start()

    def add_message(self, text: str, is_user: bool = True):
        bubble = MessageBubble(
            text, self.get_max_bubble_width(), is_user=is_user,
            font_size=user_config.chat_font_size(),
        )
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        # Na 1ª mensagem de uma conversa nova, o scroll ainda pode não estar
        # com layout assentado nesse exato instante (só é mostrado 20ms
        # depois, em animate_first_message_transition -> activate_chat_layout)
        # — get_max_bubble_width() pode calcular com base numa largura
        # provisória errada, que "gruda" no balão pra sempre (nada mais
        # recalcula depois). Corrige logo que o layout assentar.
        QTimer.singleShot(0, self.refresh_bubble_widths)

    def get_max_bubble_width(self):
        # Teto (não largura fixa): MessageBubble usa QSizePolicy.Maximum, ou
        # seja, o balão encolhe pro tamanho do conteúdo e só usa até esse
        # teto quando o texto realmente precisa do espaço todo.
        available = self.scroll.viewport().width() or self.content_area.width()
        return max(260, int(available * 0.65))

    def apply_font_size(self):
        """Reaplica o tamanho de fonte atual (chamado ao salvar nas configurações)."""
        size = user_config.chat_font_size()
        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            widget = item.widget() if item else None
            if isinstance(widget, MessageBubble):
                font = widget.label.font()
                font.setPointSize(size)
                widget.label.setFont(font)
        self.update_responsive_ui()

    def refresh_bubble_widths(self):
        max_w = self.get_max_bubble_width()
        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            if item and isinstance(item.widget(), MessageBubble):
                item.widget().set_max_width(max_w)

    def _do_scroll_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def scroll_to_bottom(self):
        # Balões em Markdown mudam de altura após renderizar; rola algumas vezes
        # para acompanhar o ajuste final de layout em respostas longas.
        for delay in (0, 60, 180):
            QTimer.singleShot(delay, self._do_scroll_bottom)
        QTimer.singleShot(200, self.update_chat_scroll_ui)
