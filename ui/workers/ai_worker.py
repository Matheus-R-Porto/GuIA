import sys

from PySide6.QtCore import QThread, Signal


class AIWorker(QThread):
    finished = Signal(str)

    def __init__(self, controller, text: str):
        super().__init__()
        self.controller = controller
        self.text = text

    def run(self):
        try:
            resposta = self.controller.ask(self.text)
            self.finished.emit(resposta)
        except Exception as exc:
            # Loga o erro real para depuração, mas mostra mensagem amigável ao usuário
            print(f"[GuIA] Erro no AIWorker: {exc}", file=sys.stderr)
            self.finished.emit(
                "Tive um problema para responder agora. Pode tentar de novo em instantes?"
            )
