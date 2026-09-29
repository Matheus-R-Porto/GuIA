import sys

from PySide6.QtCore import QThread, Signal


class AIWorker(QThread):
    finished = Signal(str)

    def __init__(self, controller, text: str, request_sources: bool = False):
        super().__init__()
        self.controller = controller
        self.text = text
        self.request_sources = request_sources

    def run(self):
        try:
            resposta = (self.controller.request_sources() if self.request_sources
                        else self.controller.ask(self.text))
            self.finished.emit(resposta)
        except Exception as exc:
            # Loga o erro real para depuração, mas mostra mensagem amigável ao usuário
            print(f"[GuIA] Erro no AIWorker: {exc}", file=sys.stderr)
            self.finished.emit(
                "Tive um problema para responder agora. Pode tentar de novo em instantes?"
            )
