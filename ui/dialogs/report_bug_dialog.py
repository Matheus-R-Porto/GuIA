from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout,
)

import bug_report
from i18n import t


class ReportBugDialog(QDialog):
    """Fallback confiável do botão "Reportar problema": mostra o texto do
    email pronto (destinatário, assunto, corpo) com um botão de copiar.

    bug_report.open_report_email() (mailto:) já foi tentado antes desta
    janela abrir — pode ter funcionado (cliente de email configurado) ou
    não ter feito nada visível (comum: gente que só usa Gmail pelo
    navegador, sem programa de email instalado no Windows). Essa janela é
    o caminho garantido: copiar e colar funciona sempre, independente do
    que o usuário tem instalado."""

    def __init__(self, subject: str, body: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")  # reaproveita o estilo do painel de config
        self.setWindowTitle(t("report_dialog_title"))
        self.setMinimumWidth(480)
        self.setWindowFlag(Qt.FramelessWindowHint, True)

        self._texto_completo = bug_report.format_report_text(subject, body)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel(t("report_dialog_title"))
        title.setFont(QFont("Roboto", 18, QFont.Bold))
        layout.addWidget(title)

        instructions = QLabel(t("report_dialog_instructions", email=bug_report.REPORT_EMAIL))
        instructions.setFont(QFont("Open Sans", 11))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self._texto_completo)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Open Sans", 10))
        self.text_edit.setMinimumHeight(220)
        layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.copy_btn = QPushButton(t("report_dialog_copy_btn"))
        self.copy_btn.setObjectName("DialogSecondaryButton")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setMinimumHeight(34)
        self.copy_btn.clicked.connect(self._on_copy_clicked)

        close_btn = QPushButton(t("close_btn"))
        close_btn.setObjectName("DialogPrimaryButton")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setMinimumHeight(34)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_copy_clicked(self):
        QApplication.clipboard().setText(self._texto_completo)
        self.copy_btn.setText(t("report_dialog_copied_label"))
        QTimer.singleShot(1500, self._restore_copy_button_text)

    def _restore_copy_button_text(self):
        self.copy_btn.setText(t("report_dialog_copy_btn"))
