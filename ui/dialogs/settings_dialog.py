from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout,
)

import user_config
from i18n import t


class SettingsDialog(QDialog):
    """Janela de configurações do GuIA: tratamento, tema e chave de API."""
    saved = Signal()
    switchProfileRequested = Signal()

    # Presets de provedor: nome -> (base_url, modelo sugerido)
    _PRESETS = {
        "Groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
        "OpenAI": ("https://api.openai.com/v1", "gpt-4o-mini"),
        "OpenRouter": ("https://openrouter.ai/api/v1", ""),
    }

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("SettingsDialog")
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(760)
        # Remove a barra de título nativa do SO (fecha via botões ou Esc).
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(14)

        title = QLabel(t("settings_title"))
        title.setFont(QFont("Roboto", 18, QFont.Bold))
        outer.addWidget(title)

        # Duas colunas lado a lado (esquerda: perfil/idiomas/fonte; direita:
        # aparência/IA) — o painel tinha ficado alto demais numa coluna só,
        # cortando o botão "Salvar" fora da tela em telas menores.
        columns = QHBoxLayout()
        columns.setSpacing(28)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        outer.addLayout(columns, 1)

        # --- Tratamento ---
        name_label = QLabel(t("settings_name_question"))
        name_label.setFont(QFont("Open Sans", 11))
        self.name_edit = QLineEdit()
        self.name_edit.setFont(QFont("Open Sans", 11))
        self.name_edit.setPlaceholderText(t("settings_name_placeholder"))
        self.name_edit.setText(user_config.get("user_name", ""))
        self.name_edit.setMaxLength(40)
        self.name_edit.setMinimumHeight(34)
        left.addWidget(name_label)
        left.addWidget(self.name_edit)

        # --- Modo (só aparece para quem é professor) ---
        self.mode_combo = None
        if self.controller.user_role == "professor":
            mode_label = QLabel(t("settings_mode_label"))
            mode_label.setFont(QFont("Open Sans", 11))
            self.mode_combo = QComboBox()
            self.mode_combo.setFont(QFont("Open Sans", 11))
            self.mode_combo.addItems([t("role_aluno"), t("role_professor")])
            self.mode_combo.setCurrentIndex(
                1 if self.controller.current_mode == "professor" else 0
            )
            self.mode_combo.setMinimumHeight(34)
            left.addWidget(mode_label)
            left.addWidget(self.mode_combo)

        # --- Nível de ensino ---
        level_label = QLabel(t("settings_level_label"))
        level_label.setFont(QFont("Open Sans", 11))
        self.level_combo = QComboBox()
        self.level_combo.setFont(QFont("Open Sans", 11))
        self.level_combo.addItems(
            [t("option_auto"), t("level_fundamental"), t("level_medio"), t("level_superior")]
        )
        self._LEVELS = ["", "fundamental", "medio", "superior"]
        current_level = user_config.get("education_level", "")
        self.level_combo.setCurrentIndex(
            self._LEVELS.index(current_level) if current_level in self._LEVELS else 0
        )
        self.level_combo.setMinimumHeight(34)
        left.addWidget(level_label)
        left.addWidget(self.level_combo)

        # --- Idioma das respostas ---
        lang_label = QLabel(t("settings_response_lang_label"))
        lang_label.setFont(QFont("Open Sans", 11))
        self.lang_combo = QComboBox()
        self.lang_combo.setFont(QFont("Open Sans", 11))
        # Nomes nativos dos idiomas (autônimos) — não traduzidos de propósito,
        # igual a um seletor de idioma normal (o nome do idioma não muda
        # conforme o idioma da interface).
        self.lang_combo.addItems([t("option_auto"), "Português", "English", "Español"])
        self._LANGS = ["auto", "pt", "en", "es"]
        current_lang = user_config.get("response_language", "auto")
        self.lang_combo.setCurrentIndex(
            self._LANGS.index(current_lang) if current_lang in self._LANGS else 0
        )
        self.lang_combo.setMinimumHeight(34)
        left.addWidget(lang_label)
        left.addWidget(self.lang_combo)

        # --- Idioma da interface ---
        ui_lang_label = QLabel(t("settings_ui_language_label"))
        ui_lang_label.setFont(QFont("Open Sans", 11))
        self.ui_lang_combo = QComboBox()
        self.ui_lang_combo.setFont(QFont("Open Sans", 11))
        self.ui_lang_combo.addItems(["Português", "English", "Español"])
        self._UI_LANGS = ["pt", "en", "es"]
        current_ui_lang = user_config.get("ui_language", "pt")
        self.ui_lang_combo.setCurrentIndex(
            self._UI_LANGS.index(current_ui_lang) if current_ui_lang in self._UI_LANGS else 0
        )
        self.ui_lang_combo.setMinimumHeight(34)
        left.addWidget(ui_lang_label)
        left.addWidget(self.ui_lang_combo)

        ui_lang_note = QLabel(t("settings_ui_language_restart_note"))
        ui_lang_note.setObjectName("LibraryTagLabel")
        ui_lang_note.setFont(QFont("Open Sans", 9))
        ui_lang_note.setWordWrap(True)
        left.addWidget(ui_lang_note)

        # --- Tamanho da fonte ---
        font_label = QLabel(t("settings_font_label"))
        font_label.setFont(QFont("Open Sans", 11))
        self.font_combo = QComboBox()
        self.font_combo.setFont(QFont("Open Sans", 11))
        self.font_combo.addItems([t("font_small"), t("font_medium"), t("font_large")])
        self._FONT_SIZES = ["small", "medium", "large"]
        current_font = user_config.get("font_size", "medium")
        self.font_combo.setCurrentIndex(
            self._FONT_SIZES.index(current_font) if current_font in self._FONT_SIZES else 1
        )
        self.font_combo.setMinimumHeight(34)
        left.addWidget(font_label)
        left.addWidget(self.font_combo)
        left.addStretch(1)

        # --- Tema ---
        theme_label = QLabel(t("settings_theme_label"))
        theme_label.setFont(QFont("Open Sans", 11))
        self.theme_combo = QComboBox()
        self.theme_combo.setFont(QFont("Open Sans", 11))
        self.theme_combo.addItems([t("theme_light"), t("theme_dark")])
        self.theme_combo.setCurrentIndex(
            1 if user_config.get("theme", "light") == "dark" else 0
        )
        self.theme_combo.setMinimumHeight(34)
        right.addWidget(theme_label)
        right.addWidget(self.theme_combo)

        # --- Cor de ênfase ---
        accent_label = QLabel(t("settings_accent_label"))
        accent_label.setFont(QFont("Open Sans", 11))
        self._accent_color = user_config.get("accent_color", "#1565C0")
        self.accent_btn = QPushButton()
        self.accent_btn.setCursor(Qt.PointingHandCursor)
        self.accent_btn.setMinimumHeight(34)
        self.accent_btn.clicked.connect(self._on_pick_accent_color)
        self._update_accent_button()
        right.addWidget(accent_label)
        right.addWidget(self.accent_btn)

        # --- IA / Chave de API (opcional) ---
        api_label = QLabel(t("settings_api_label"))
        api_label.setFont(QFont("Open Sans", 11))
        api_label.setWordWrap(True)
        right.addWidget(api_label)

        self._PROVIDER_LOCAL = t("provider_local")
        self._PROVIDER_CUSTOM = t("provider_custom")

        self.provider_combo = QComboBox()
        self.provider_combo.setFont(QFont("Open Sans", 11))
        self.provider_combo.addItems(
            [self._PROVIDER_LOCAL, "Groq", "OpenAI", "OpenRouter", self._PROVIDER_CUSTOM]
        )
        self.provider_combo.setMinimumHeight(34)
        right.addWidget(self.provider_combo)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setFont(QFont("Open Sans", 10))
        self.base_url_edit.setPlaceholderText(t("settings_base_url_placeholder"))
        self.base_url_edit.setText(user_config.get("api_base_url", ""))
        self.base_url_edit.setMinimumHeight(30)
        right.addWidget(self.base_url_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setFont(QFont("Open Sans", 10))
        self.api_key_edit.setPlaceholderText(t("settings_api_key_placeholder"))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setText(user_config.get("api_key", ""))
        self.api_key_edit.setMinimumHeight(30)
        right.addWidget(self.api_key_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setFont(QFont("Open Sans", 10))
        self.model_edit.setPlaceholderText(t("settings_model_placeholder"))
        self.model_edit.setText(user_config.get("api_model", ""))
        self.model_edit.setMinimumHeight(30)
        right.addWidget(self.model_edit)

        # Seleciona o provedor no combo conforme a base_url salva; conecta o
        # handler só DEPOIS, para o load não sobrescrever os campos salvos.
        self.provider_combo.setCurrentText(self._detect_provider(user_config.get("api_base_url", "")))
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        right.addStretch(1)

        # --- Trocar perfil (linha própria, largura toda) ---
        switch_profile_btn = QPushButton(t("switch_profile_btn"))
        switch_profile_btn.setObjectName("DialogSecondaryButton")
        switch_profile_btn.setCursor(Qt.PointingHandCursor)
        switch_profile_btn.setMinimumHeight(34)
        switch_profile_btn.clicked.connect(self._on_switch_profile_clicked)
        outer.addWidget(switch_profile_btn)

        # --- Botões ---
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton(t("cancel_btn"))
        self.cancel_btn.setObjectName("DialogSecondaryButton")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(34)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(t("save_btn"))
        self.save_btn.setObjectName("DialogPrimaryButton")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setMinimumHeight(34)
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        outer.addLayout(btn_row)

    def _detect_provider(self, base_url: str) -> str:
        if not base_url:
            return self._PROVIDER_LOCAL
        for name, (preset_base, _) in self._PRESETS.items():
            if base_url.rstrip("/") == preset_base.rstrip("/"):
                return name
        return self._PROVIDER_CUSTOM

    def _on_provider_changed(self, name: str):
        if name == self._PROVIDER_LOCAL:
            self.base_url_edit.clear()
            self.model_edit.clear()
            return
        if name == self._PROVIDER_CUSTOM:
            return
        base, model = self._PRESETS.get(name, ("", ""))
        self.base_url_edit.setText(base)
        if model:
            self.model_edit.setText(model)

    def _update_accent_button(self):
        self.accent_btn.setText(self._accent_color)
        self.accent_btn.setStyleSheet(
            f"background-color: {self._accent_color}; color: #FFFFFF; "
            f"border-radius: 6px; padding: 6px;"
        )

    def _on_pick_accent_color(self):
        cor = QColorDialog.getColor(QColor(self._accent_color), self, t("settings_accent_dialog_title"))
        if cor.isValid():
            self._accent_color = cor.name().upper()
            self._update_accent_button()

    def _on_switch_profile_clicked(self):
        self.switchProfileRequested.emit()
        self.reject()

    def _on_save(self):
        if self.mode_combo is not None:
            new_mode = "professor" if self.mode_combo.currentIndex() == 1 else "aluno"
            self.controller.set_mode(new_mode)
        user_config.set("user_name", self.name_edit.text().strip())
        user_config.set("education_level", self._LEVELS[self.level_combo.currentIndex()])
        user_config.set("response_language", self._LANGS[self.lang_combo.currentIndex()])
        user_config.set("ui_language", self._UI_LANGS[self.ui_lang_combo.currentIndex()])
        user_config.set("font_size", self._FONT_SIZES[self.font_combo.currentIndex()])
        user_config.set("theme", "dark" if self.theme_combo.currentIndex() == 1 else "light")
        user_config.set("accent_color", self._accent_color)
        user_config.set("api_base_url", self.base_url_edit.text().strip())
        user_config.set("api_key", self.api_key_edit.text().strip())
        user_config.set("api_model", self.model_edit.text().strip())
        user_config.save()
        self.saved.emit()
        self.accept()
