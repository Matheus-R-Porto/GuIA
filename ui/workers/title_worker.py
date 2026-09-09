import sys

from PySide6.QtCore import QThread, Signal


class TitleWorker(QThread):
    """Gera (via modelo) um título melhor para a conversa, em background —
    não deve travar a UI nem atrasar o envio da mensagem."""
    finished = Signal(int, str)  # conversation_id, título gerado

    def __init__(self, controller, conversation_id: int, first_message: str):
        super().__init__()
        self.controller = controller
        self.conversation_id = conversation_id
        self.first_message = first_message

    def run(self):
        try:
            title = self.controller.generate_title(self.first_message)
        except Exception as exc:
            print(f"[GuIA] Erro no TitleWorker: {exc}", file=sys.stderr)
            return
        self.finished.emit(self.conversation_id, title)
