from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from config import ENABLE_EXPLORE, ENABLE_QUIZ
from i18n import t

_CONVERSATION_ID_ROLE = Qt.UserRole
_CONVERSATION_TITLE_ROLE = Qt.UserRole + 2  # título original, para reverter edição vazia


class SidebarWidget(QFrame):
    newChatRequested = Signal()
    sidebarToggled = Signal(bool)
    sidebarWidthChanged = Signal(int)
    settingsRequested = Signal()
    quizRequested = Signal()

    conversationSelected = Signal(int)
    conversationRenameRequested = Signal(int, str)  # id, novo_titulo
    conversationDeleteRequested = Signal(int)
    conversationMoveToProjectRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")

        self.sidebar_width_value = 300
        self.sidebar_expanded = True
        self.sidebar_expanded_width = 300
        self.sidebar_collapsed_width = 70
        self.anim = None

        self._build_ui()
        self.set_sidebar_width(self.sidebar_expanded_width)

    def _build_ui(self):
        self.setFixedWidth(self.sidebar_expanded_width)

        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setContentsMargins(10, 30, 10, 30)
        self.sidebar_layout.setSpacing(15)
        self.sidebar_layout.setAlignment(Qt.AlignTop)

        self.header_container = QWidget()
        self.header_container.setObjectName("HeaderContainer")
        self.header_container.setFixedHeight(50)

        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(10, 0, 10, 0)
        self.header_layout.setSpacing(0)

        self.logo = QLabel("GuIA")
        self.logo.setObjectName("LogoLabel")
        self.logo.setFont(QFont("Roboto", 24, QFont.Bold))

        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("ToggleButton")
        self.toggle_btn.setFixedSize(48, 48)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        self.header_layout.addWidget(self.logo)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.toggle_btn, 0, Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.header_container)
        self.sidebar_layout.addSpacing(20)

        self.menu_buttons = []

        menu_items = [(t("sidebar_new_chat"), "✚", "new_chat")]

        # O Laboratório mantém o banco de questões. Fontes ficam no chat.
        if ENABLE_QUIZ:
            menu_items.append((t("sidebar_menu_simulado"), "⚗", "quiz"))
        if ENABLE_EXPLORE:
            menu_items.append((t("sidebar_menu_explorar"), "⌕", None))

        for text, icon, action in menu_items:
            btn = QPushButton(f" {icon}  {text}")
            btn.setObjectName("MenuButton")
            btn.setProperty("full_text", f" {icon}  {text}")
            btn.setProperty("icon_only", icon)
            btn.setFont(QFont("Roboto", 12))
            btn.setMinimumHeight(46)
            btn.setCursor(Qt.PointingHandCursor)

            if action == "new_chat":
                self.new_chat_btn = btn
                btn.clicked.connect(self.newChatRequested.emit)
            elif action == "quiz":
                self.quiz_btn = btn
                btn.clicked.connect(self.quizRequested.emit)

            self.sidebar_layout.addWidget(btn)
            self.menu_buttons.append(btn)

        # --- Lista de conversas antigas ---
        self.sidebar_layout.addSpacing(18)

        self.conversation_list = QListWidget()
        self.conversation_list.setObjectName("ConversationList")
        self.conversation_list.setFrameShape(QListWidget.NoFrame)
        self.conversation_list.setFont(QFont("Open Sans", 11))
        self.conversation_list.setSpacing(1)
        self.conversation_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.conversation_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.conversation_list.customContextMenuRequested.connect(self._show_context_menu)
        self.conversation_list.itemClicked.connect(self._on_item_clicked)
        self.conversation_list.itemChanged.connect(self._on_item_edited)
        self.sidebar_layout.addWidget(self.conversation_list, 1)

        # Botão de configurações no rodapé da sidebar.
        settings_text = f" ⚙  {t('settings_title')}"
        self.settings_btn = QPushButton(settings_text)
        self.settings_btn.setObjectName("MenuButton")
        self.settings_btn.setProperty("full_text", settings_text)
        self.settings_btn.setProperty("icon_only", "⚙")
        self.settings_btn.setFont(QFont("Roboto", 12))
        self.settings_btn.setMinimumHeight(46)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settingsRequested.emit)
        self.sidebar_layout.addWidget(self.settings_btn)
        self.menu_buttons.append(self.settings_btn)

    # --- Conversas ---

    def set_conversations(self, conversations: list[dict]):
        """Repovoa a lista a partir de [{'id': int, 'title': str}, ...],
        na ordem em que forem passadas (mais recente primeiro, por convenção
        de quem chama)."""
        self.conversation_list.blockSignals(True)
        self.conversation_list.clear()
        for conv in conversations:
            item = QListWidgetItem(conv["title"])
            item.setData(_CONVERSATION_ID_ROLE, conv["id"])
            item.setData(_CONVERSATION_TITLE_ROLE, conv["title"])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.conversation_list.addItem(item)
        self.conversation_list.blockSignals(False)

    def set_active_conversation(self, conversation_id: int | None):
        """Destaca visualmente a conversa carregada no momento (ou nenhuma)."""
        for i in range(self.conversation_list.count()):
            item = self.conversation_list.item(i)
            item.setSelected(item.data(_CONVERSATION_ID_ROLE) == conversation_id)

    def _on_item_clicked(self, item: QListWidgetItem):
        conversation_id = item.data(_CONVERSATION_ID_ROLE)
        if conversation_id is not None:
            self.conversationSelected.emit(conversation_id)

    def _on_item_edited(self, item: QListWidgetItem):
        conversation_id = item.data(_CONVERSATION_ID_ROLE)
        new_title = item.text().strip()
        if conversation_id is None:
            return
        if new_title:
            item.setData(_CONVERSATION_TITLE_ROLE, new_title)
            self.conversationRenameRequested.emit(conversation_id, new_title)
        else:
            # Título vazio: reverte para o anterior em vez de deixar a linha
            # em branco na sidebar (o Qt já aplicou o texto vazio ao item
            # antes deste handler rodar).
            previous = item.data(_CONVERSATION_TITLE_ROLE) or ""
            self.conversation_list.blockSignals(True)
            item.setText(previous)
            self.conversation_list.blockSignals(False)

    def _show_context_menu(self, pos):
        item = self.conversation_list.itemAt(pos)
        if item is None:
            return
        conversation_id = item.data(_CONVERSATION_ID_ROLE)

        menu = QMenu(self)
        rename_action = menu.addAction(t("context_rename"))
        move_action = menu.addAction(t("context_move_to_project"))
        menu.addSeparator()
        delete_action = menu.addAction(t("context_delete"))

        chosen = menu.exec(self.conversation_list.mapToGlobal(pos))
        if chosen == rename_action:
            self.conversation_list.editItem(item)
        elif chosen == delete_action:
            self.conversationDeleteRequested.emit(conversation_id)
        elif chosen == move_action:
            self.conversationMoveToProjectRequested.emit(conversation_id)

    def get_sidebar_width(self):
        return self.sidebar_width_value

    def set_sidebar_width(self, width: int):
        width = int(width)
        self.sidebar_width_value = width
        self.setFixedWidth(width)

        collapsed = width <= 100
        self.logo.setVisible(not collapsed)
        self.conversation_list.setVisible(not collapsed)

        if collapsed:
            self.sidebar_layout.setContentsMargins(0, 30, 0, 30)
            self.sidebar_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            self.header_container.setFixedHeight(50)
            self.header_container.setMinimumWidth(48)
            self.header_container.setMaximumWidth(48)
            self.header_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setAlignment(Qt.AlignCenter)
            for btn in self.menu_buttons:
                btn.setText(btn.property("icon_only"))
                btn.setObjectName("MenuButtonCollapsed")
                btn.setMinimumSize(44, 44)
                btn.setMaximumSize(44, 44)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        else:
            self.sidebar_layout.setContentsMargins(10, 30, 10, 30)
            self.sidebar_layout.setAlignment(Qt.AlignTop)
            self.header_container.setFixedHeight(50)
            self.header_container.setMinimumWidth(0)
            self.header_container.setMaximumWidth(16777215)
            self.header_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.header_layout.setContentsMargins(10, 0, 10, 0)
            self.header_layout.setAlignment(Qt.AlignVCenter)
            for btn in self.menu_buttons:
                btn.setText(btn.property("full_text"))
                btn.setObjectName("MenuButton")
                btn.setMinimumWidth(0)
                btn.setMaximumWidth(16777215)
                btn.setMinimumHeight(46)
                btn.setMaximumHeight(16777215)
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        self.sidebarWidthChanged.emit(width)

    sidebarWidth = Property(int, get_sidebar_width, set_sidebar_width)

    def toggle_sidebar(self):
        start_val = self.sidebar_width_value
        end_val = self.sidebar_collapsed_width if self.sidebar_expanded else self.sidebar_expanded_width
        self.sidebar_expanded = not self.sidebar_expanded

        if self.anim is not None:
            self.anim.stop()

        self.anim = QPropertyAnimation(self, b"sidebarWidth")
        self.anim.setDuration(300)
        self.anim.setStartValue(start_val)
        self.anim.setEndValue(end_val)
        self.anim.setEasingCurve(QEasingCurve.InOutQuart)
        self.anim.finished.connect(lambda: self.sidebarToggled.emit(self.sidebar_expanded))
        self.anim.start()

    def set_busy(self, busy: bool):
        for btn in self.menu_buttons:
            btn.setEnabled(not busy)
        self.conversation_list.setEnabled(not busy)
