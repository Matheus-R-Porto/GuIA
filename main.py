import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from app_controller import AppController
from ui.dialogs import LoginDialog
from ui.windows import GuiAWindow
import theme
import user_config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GuIA")
    # Fusion em vez do estilo nativo do Windows: o estilo nativo tem um
    # rasterizador de border-radius com artefato visível (borda com
    # intensidade desigual em 8 pontos, nos ângulos cardeais/diagonais, nos
    # botões circulares) — Fusion é o estilo embutido no Qt (sem dependência
    # nova) com suporte mais consistente a QSS customizado.
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet(user_config.get("theme", "light")))

    try:
        controller = AppController()
    except RuntimeError as e:
        QMessageBox.critical(None, "Erro de configuração", str(e))
        sys.exit(1)

    profiles = controller.list_profiles()
    if len(profiles) == 1 and not profiles[0]["has_password"]:
        # Único perfil e sem senha: entra direto, sem fricção (comportamento
        # de antes do Login existir).
        controller.set_active_user(profiles[0]["id"])
    else:
        login = LoginDialog(controller)
        if login.exec() != LoginDialog.Accepted:
            sys.exit(0)

    window = GuiAWindow(controller)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
