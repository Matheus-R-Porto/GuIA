from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from i18n import t


class LoginDialog(QDialog):
    """Seleciona ou cria um perfil local antes de abrir o GuIA.

    Três telas internas (QStackedWidget): seletor de perfis, criação de
    perfil (nome e senha) e confirmação de senha.
    Perfis locais, não contas de rede — cada pessoa que usa o mesmo PC tem
    seu próprio histórico de conversas.
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("SettingsDialog")  # reaproveita o estilo do painel de config
        self.setWindowTitle(t("login_window_title"))
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.FramelessWindowHint, True)

        self._pending_user_id = None
        self._build_ui()
        self._refresh_picker()

        if not self.controller.list_profiles():
            self._show_create_page(allow_back=False)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        title = QLabel("GuIA")
        title.setFont(QFont("Roboto", 18, QFont.Bold))
        outer.addWidget(title)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_picker_page())
        self.stack.addWidget(self._build_create_page())
        self.stack.addWidget(self._build_password_page())

    # --- página 1: seletor de perfis ---

    def _build_picker_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        subtitle = QLabel(t("login_who_question"))
        subtitle.setFont(QFont("Open Sans", 12))
        layout.addWidget(subtitle)

        self.profile_list = QListWidget()
        self.profile_list.setFont(QFont("Open Sans", 12))
        self.profile_list.setMinimumHeight(160)
        self.profile_list.itemDoubleClicked.connect(lambda _: self._on_enter_clicked())
        layout.addWidget(self.profile_list, 1)

        btn_row = QHBoxLayout()
        create_btn = QPushButton(t("login_create_profile_btn"))
        create_btn.setObjectName("DialogSecondaryButton")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setMinimumHeight(34)
        create_btn.clicked.connect(lambda: self._show_create_page(allow_back=True))

        enter_btn = QPushButton(t("login_enter_btn"))
        enter_btn.setObjectName("DialogPrimaryButton")
        enter_btn.setCursor(Qt.PointingHandCursor)
        enter_btn.setMinimumHeight(34)
        enter_btn.setDefault(True)
        enter_btn.clicked.connect(self._on_enter_clicked)

        btn_row.addWidget(create_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(enter_btn)
        layout.addLayout(btn_row)

        return page

    def _refresh_picker(self):
        self.profile_list.clear()
        for profile in self.controller.list_profiles():
            label = profile["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, profile["id"])
            item.setData(Qt.UserRole + 1, profile["has_password"])
            self.profile_list.addItem(item)
        if self.profile_list.count():
            self.profile_list.setCurrentRow(0)

    def _on_enter_clicked(self):
        item = self.profile_list.currentItem()
        if item is None:
            return
        user_id = item.data(Qt.UserRole)
        has_password = item.data(Qt.UserRole + 1)
        if has_password:
            self._show_password_page(user_id)
        else:
            self.controller.set_active_user(user_id)
            self.accept()

    # --- página 2: criar perfil ---

    def _build_create_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        subtitle = QLabel(t("login_new_profile_label"))
        subtitle.setFont(QFont("Open Sans", 12))
        layout.addWidget(subtitle)

        self.create_name_edit = QLineEdit()
        self.create_name_edit.setFont(QFont("Open Sans", 11))
        self.create_name_edit.setPlaceholderText(t("login_name_placeholder"))
        self.create_name_edit.setMinimumHeight(34)
        layout.addWidget(self.create_name_edit)

        self.create_password_edit = QLineEdit()
        self.create_password_edit.setFont(QFont("Open Sans", 11))
        self.create_password_edit.setPlaceholderText(t("login_password_placeholder"))
        self.create_password_edit.setEchoMode(QLineEdit.Password)
        self.create_password_edit.setMinimumHeight(34)
        layout.addWidget(self.create_password_edit)

        self.create_password_confirm_edit = QLineEdit()
        self.create_password_confirm_edit.setFont(QFont("Open Sans", 11))
        self.create_password_confirm_edit.setPlaceholderText(t("login_confirm_password_placeholder"))
        self.create_password_confirm_edit.setEchoMode(QLineEdit.Password)
        self.create_password_confirm_edit.setMinimumHeight(34)
        layout.addWidget(self.create_password_confirm_edit)

        self.create_error_label = QLabel("")
        self.create_error_label.setObjectName("CharCounterLabel")
        self.create_error_label.setProperty("exceeded", True)
        self.create_error_label.setWordWrap(True)
        self.create_error_label.hide()
        layout.addWidget(self.create_error_label)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        self.create_back_btn = QPushButton(t("back_btn"))
        self.create_back_btn.setObjectName("DialogSecondaryButton")
        self.create_back_btn.setCursor(Qt.PointingHandCursor)
        self.create_back_btn.setMinimumHeight(34)
        self.create_back_btn.clicked.connect(self._show_picker_page)

        create_confirm_btn = QPushButton(t("login_create_profile_confirm_btn"))
        create_confirm_btn.setObjectName("DialogPrimaryButton")
        create_confirm_btn.setCursor(Qt.PointingHandCursor)
        create_confirm_btn.setMinimumHeight(34)
        create_confirm_btn.setDefault(True)
        create_confirm_btn.clicked.connect(self._on_create_clicked)

        btn_row.addWidget(self.create_back_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(create_confirm_btn)
        layout.addLayout(btn_row)

        return page

    def _show_create_page(self, allow_back: bool):
        self.create_name_edit.clear()
        self.create_password_edit.clear()
        self.create_password_confirm_edit.clear()
        self.create_error_label.hide()
        self.create_back_btn.setVisible(allow_back)
        self.stack.setCurrentIndex(1)
        self.create_name_edit.setFocus()

    def _on_create_clicked(self):
        name = self.create_name_edit.text().strip()
        password = self.create_password_edit.text()
        confirm = self.create_password_confirm_edit.text()

        if not name:
            self._show_create_error(t("login_error_no_name"))
            return
        if not password:
            self._show_create_error(t("login_error_no_password"))
            return
        if password != confirm:
            self._show_create_error(t("login_error_password_mismatch"))
            return

        profile = self.controller.create_profile(name, password)
        self.controller.set_active_user(profile["id"])
        self.accept()

    def _show_create_error(self, message: str):
        self.create_error_label.setText(message)
        self.create_error_label.style().unpolish(self.create_error_label)
        self.create_error_label.style().polish(self.create_error_label)
        self.create_error_label.show()

    # --- página 3: confirmar senha ---

    def _build_password_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.password_prompt_label = QLabel("")
        self.password_prompt_label.setFont(QFont("Open Sans", 12))
        layout.addWidget(self.password_prompt_label)

        self.password_edit = QLineEdit()
        self.password_edit.setFont(QFont("Open Sans", 11))
        self.password_edit.setPlaceholderText(t("login_password_placeholder"))
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(34)
        self.password_edit.returnPressed.connect(self._on_password_confirm_clicked)
        layout.addWidget(self.password_edit)

        self.password_error_label = QLabel(t("login_error_wrong_password"))
        self.password_error_label.setObjectName("CharCounterLabel")
        self.password_error_label.setProperty("exceeded", True)
        self.password_error_label.hide()
        layout.addWidget(self.password_error_label)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(t("cancel_btn"))
        cancel_btn.setObjectName("DialogSecondaryButton")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setMinimumHeight(34)
        cancel_btn.clicked.connect(self._show_picker_page)

        confirm_btn = QPushButton(t("login_enter_btn"))
        confirm_btn.setObjectName("DialogPrimaryButton")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setMinimumHeight(34)
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self._on_password_confirm_clicked)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        return page

    def _show_password_page(self, user_id: int):
        self._pending_user_id = user_id
        item = self.profile_list.currentItem()
        name = item.text() if item else ""
        self.password_prompt_label.setText(t("login_password_of_template", name=name))
        self.password_edit.clear()
        self.password_error_label.hide()
        self.stack.setCurrentIndex(2)
        self.password_edit.setFocus()

    def _on_password_confirm_clicked(self):
        password = self.password_edit.text()
        if self.controller.check_password(self._pending_user_id, password):
            self.controller.set_active_user(self._pending_user_id)
            self.accept()
        else:
            self.password_error_label.show()
            self.password_edit.clear()
            self.password_edit.setFocus()

    # --- navegação ---

    def _show_picker_page(self):
        self._refresh_picker()
        self.stack.setCurrentIndex(0)
