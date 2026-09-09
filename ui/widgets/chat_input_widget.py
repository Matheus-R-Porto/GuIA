from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextOption
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollBar, QSizePolicy, QToolButton, QToolTip, QVBoxLayout, QWidget,
)

import user_config
from config import HARD_MAX_INPUT_CHARS, MAX_USER_CHARS
from i18n import t
from .enter_text_edit import EnterTextEdit


class ChatInputPanel(QFrame):
    sendRequested = Signal()
    heightChanged = Signal()

    def __init__(self, max_send_chars: int = MAX_USER_CHARS, max_input_chars: int = HARD_MAX_INPUT_CHARS, parent=None):
        super().__init__(parent)
        self.setObjectName("InputContainer")
        self.max_send_chars = max_send_chars
        self.max_input_chars = max_input_chars
        self.is_waiting_response = False
        self.syncing_external_scroll = False
        self.syncing_internal_scroll = False

        self._build_ui()
        self._connect_signals()
        self.adjust_height()
        self.update_input_scroll_ui()
        self.update_char_counter(0)
        self.update_send_button_state()

    def _build_ui(self):
        self.input_main_layout = QHBoxLayout(self)
        self.input_main_layout.setContentsMargins(0, 0, 9, 0)
        self.input_main_layout.setSpacing(0)

        self.left_side = QWidget()
        self.left_side_layout = QVBoxLayout(self.left_side)
        self.left_side_layout.setContentsMargins(0, 0, 0, 0)
        self.left_side_layout.setSpacing(0)

        self.top_area = QWidget()
        self.top_area.setObjectName("InputTopArea")
        self.top_area_layout = QHBoxLayout(self.top_area)
        self.top_area_layout.setContentsMargins(24, 14, 8, 0)
        self.top_area_layout.setSpacing(8)

        self.input_field = EnterTextEdit(hard_limit=self.max_input_chars)
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText(t("chat_input_placeholder"))
        self.input_field.setFont(QFont("Open Sans", user_config.chat_font_size() - 1))
        self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_field.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.input_field.setAcceptRichText(False)
        self.input_field.setMinimumHeight(50)
        self.input_field.setMaximumHeight(124)
        self.top_area_layout.addWidget(self.input_field, 1)

        self.footer_area = QWidget()
        self.footer_area.setObjectName("InputFooterArea")
        self.footer_area.setFixedHeight(45)

        self.footer_area_layout = QHBoxLayout(self.footer_area)
        self.footer_area_layout.setContentsMargins(24, 0, 16, 8)
        self.footer_area_layout.setSpacing(0)

        self.char_counter = QLabel(t("chars_remaining_template", n=self.max_send_chars))
        self.char_counter.setObjectName("CharCounterLabel")
        self.char_counter.hide()

        self.footer_area_layout.addStretch(1)
        self.footer_area_layout.addWidget(self.char_counter, 0, Qt.AlignVCenter)

        self.left_side_layout.addWidget(self.top_area, 1)
        self.left_side_layout.addWidget(self.footer_area, 0)

        self.right_column = QWidget()
        self.right_column.setObjectName("RightColumn")
        self.right_column.setFixedWidth(40)

        self.right_column_layout = QVBoxLayout(self.right_column)
        self.right_column_layout.setContentsMargins(0, 0, 0, 0)
        self.right_column_layout.setSpacing(0)

        self.right_top_area = QWidget()
        self.right_top_layout = QVBoxLayout(self.right_top_area)
        self.right_top_layout.setContentsMargins(0, 10, 0, 0)
        self.right_top_layout.setAlignment(Qt.AlignHCenter)

        self.scroll_stack = QWidget()
        self.scroll_stack.setFixedWidth(20)
        self.scroll_stack_layout = QVBoxLayout(self.scroll_stack)
        self.scroll_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_stack_layout.setAlignment(Qt.AlignHCenter)

        self.scroll_up_btn = QToolButton()
        self.scroll_up_btn.setObjectName("ScrollArrowButton")
        self.scroll_up_btn.setText("▲")
        self.scroll_up_btn.setFixedSize(18, 16)

        self.outer_scrollbar = QScrollBar(Qt.Vertical)
        self.outer_scrollbar.setObjectName("OuterInputScrollBar")
        self.outer_scrollbar.setFixedWidth(20)

        self.scroll_down_btn = QToolButton()
        self.scroll_down_btn.setObjectName("ScrollArrowButton")
        self.scroll_down_btn.setText("▼")
        self.scroll_down_btn.setFixedSize(18, 16)

        self.scroll_stack_layout.addWidget(self.scroll_up_btn, 0, Qt.AlignHCenter)
        self.scroll_stack_layout.addWidget(self.outer_scrollbar, 1, Qt.AlignHCenter)
        self.scroll_stack_layout.addWidget(self.scroll_down_btn, 0, Qt.AlignHCenter)
        self.right_top_layout.addWidget(self.scroll_stack, 1, Qt.AlignHCenter)

        self.right_bottom_area = QWidget()
        self.right_bottom_area.setFixedHeight(45)
        self.right_bottom_layout = QHBoxLayout(self.right_bottom_area)
        self.right_bottom_layout.setContentsMargins(0, 0, 0, 8)
        self.right_bottom_layout.setAlignment(Qt.AlignHCenter)

        self.send_btn = QPushButton("➜")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setFixedSize(28, 28)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.right_bottom_layout.addWidget(self.send_btn, 0, Qt.AlignHCenter | Qt.AlignVCenter)

        self.right_column_layout.addWidget(self.right_top_area, 1)
        self.right_column_layout.addWidget(self.right_bottom_area, 0)

        self.input_main_layout.addWidget(self.left_side, 1)
        self.input_main_layout.addWidget(self.right_column, 0)

        internal_sb = self.input_field.verticalScrollBar()
        internal_sb.setFixedWidth(0)
        internal_sb.setStyleSheet("width: 0px;")

    def _connect_signals(self):
        self.input_field.sendRequested.connect(self.sendRequested.emit)
        self.send_btn.clicked.connect(self.sendRequested.emit)
        self.input_field.textChanged.connect(self.adjust_height)
        self.input_field.textChanged.connect(self.update_send_button_state)
        self.input_field.charCountChanged.connect(self.update_char_counter)
        self.input_field.hardLimitReached.connect(self.on_hard_limit_reached)

        internal_sb = self.input_field.verticalScrollBar()
        internal_sb.rangeChanged.connect(self.update_input_scroll_ui)
        internal_sb.valueChanged.connect(self.sync_internal_to_external)
        internal_sb.valueChanged.connect(self.update_input_scroll_ui)

        self.outer_scrollbar.valueChanged.connect(self.sync_external_to_internal)
        self.scroll_up_btn.clicked.connect(self.scroll_input_up)
        self.scroll_down_btn.clicked.connect(self.scroll_input_down)

    def set_busy(self, busy: bool):
        self.is_waiting_response = busy
        self.input_field.setReadOnly(busy)
        self.update_send_button_state()

    def get_text(self) -> str:
        return self.input_field.toPlainText()

    def current_length(self) -> int:
        return len(self.input_field.toPlainText())

    def clear_text(self):
        self.input_field.clear()
        self.adjust_height()
        self.update_char_counter(0)
        self.update_send_button_state()

    def adjust_height(self):
        doc_height = self.input_field.document().size().height()
        target = max(50, min(int(doc_height + 4), 124))
        self.input_field.setFixedHeight(target)
        self.setFixedHeight(target + 45 + 14)
        QTimer.singleShot(0, self.update_input_scroll_ui)
        self.heightChanged.emit()

    def update_send_button_state(self):
        has_text = bool(self.input_field.toPlainText().strip())
        self.send_btn.setEnabled(has_text and not self.is_waiting_response)

    def update_char_counter(self, count=None):
        if count is None:
            count = self.current_length()
        remaining = self.max_send_chars - count
        if count < 1800:
            self.char_counter.hide()
            return
        self.char_counter.show()
        self.char_counter.setText(t("chars_remaining_template", n=remaining))
        self.char_counter.setProperty("warning", 0 <= remaining <= 200)
        self.char_counter.setProperty("exceeded", remaining < 0)
        self.char_counter.style().unpolish(self.char_counter)
        self.char_counter.style().polish(self.char_counter)

    def on_hard_limit_reached(self):
        QToolTip.showText(
            self.input_field.mapToGlobal(self.input_field.rect().bottomRight()),
            t("chars_hard_limit_tooltip", n=self.max_input_chars),
        )

    def sync_internal_to_external(self):
        if self.syncing_external_scroll:
            return
        sb = self.input_field.verticalScrollBar()
        self.syncing_internal_scroll = True
        self.outer_scrollbar.setMinimum(sb.minimum())
        self.outer_scrollbar.setMaximum(sb.maximum())
        self.outer_scrollbar.setPageStep(sb.pageStep())
        self.outer_scrollbar.setValue(sb.value())
        self.syncing_internal_scroll = False

    def sync_external_to_internal(self, value):
        if self.syncing_internal_scroll:
            return
        sb = self.input_field.verticalScrollBar()
        self.syncing_external_scroll = True
        sb.setValue(value)
        self.syncing_external_scroll = False

    def update_input_scroll_ui(self):
        sb = self.input_field.verticalScrollBar()
        has_scroll = sb.maximum() > sb.minimum()
        self.scroll_stack.setVisible(has_scroll)
        if not has_scroll:
            return
        self.sync_internal_to_external()
        at_top = sb.value() <= sb.minimum() + 1
        at_bottom = sb.value() >= sb.maximum() - 1
        for btn, edge in [(self.scroll_up_btn, at_top), (self.scroll_down_btn, at_bottom)]:
            btn.setProperty("edge", edge)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def scroll_input_up(self):
        sb = self.input_field.verticalScrollBar()
        sb.setValue(sb.value() - sb.singleStep() * 3)

    def scroll_input_down(self):
        sb = self.input_field.verticalScrollBar()
        sb.setValue(sb.value() + sb.singleStep() * 3)
