from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTextEdit

from config import HARD_MAX_INPUT_CHARS


class EnterTextEdit(QTextEdit):
    sendRequested = Signal()
    charCountChanged = Signal(int)
    hardLimitReached = Signal()

    def __init__(self, hard_limit: int = HARD_MAX_INPUT_CHARS, parent=None):
        super().__init__(parent)
        self.hard_limit = hard_limit
        self.textChanged.connect(self._enforce_hard_limit)

    def _emit_count(self):
        self.charCountChanged.emit(len(self.toPlainText()))

    def _enforce_hard_limit(self):
        text = self.toPlainText()
        if len(text) <= self.hard_limit:
            self._emit_count()
            return

        cursor = self.textCursor()
        old_pos = cursor.position()

        self.blockSignals(True)
        self.setPlainText(text[:self.hard_limit])
        self.blockSignals(False)

        cursor = self.textCursor()
        cursor.setPosition(min(old_pos, self.hard_limit))
        self.setTextCursor(cursor)

        self.hardLimitReached.emit()
        self.charCountChanged.emit(self.hard_limit)

    def insertFromMimeData(self, source):
        text = source.text()
        if not text:
            return

        current_text = self.toPlainText()
        cursor = self.textCursor()
        selected_text = cursor.selectedText().replace(" ", "\n")

        effective_len = len(current_text) - len(selected_text)
        remaining = self.hard_limit - effective_len

        if remaining <= 0:
            self.hardLimitReached.emit()
            return

        cursor.insertText(text[:remaining])
        self.setTextCursor(cursor)
        self.charCountChanged.emit(len(self.toPlainText()))

        if len(text) > remaining:
            self.hardLimitReached.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.sendRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
