import re

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QFont, QFontMetrics, QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy

import code_highlighter
import user_config
from i18n import t

_ZERO_WIDTH_SPACE = "​"
# Padding/borda do balão a descontar da largura disponível antes de medir
# quantos caracteres cabem por linha — valor EXATO (não estimado), somado
# a partir do QSS de UserBubbleLabel/BotBubbleLabel (padding: 15px 18px,
# ou seja 18px de cada lado = 36px) + borda (1px de cada lado = 2px) +
# margens do QHBoxLayout do QFrame (8px de cada lado = 16px). Total: 54px.
_BUBBLE_CHROME_PADDING = 54
# Folga fixa pequena (não uma porcentagem!) só pra absorver arredondamento
# entre a medição (QFontMetrics) e o layout real — uma porcentagem cresce
# junto com a largura do balão e sobra um vão visível em balões largos; um
# valor fixo em pixels não tem esse problema.
_SAFETY_MARGIN_PX = 4


def _greedy_break_word(word: str, metrics: QFontMetrics, max_px: int) -> str:
    """Quebra uma "palavra" sem espaço em pedaços que cabem em max_px
    pixels, usando a largura REAL da fonte (busca binária por caractere,
    não uma estimativa por média) — cada pedaço usa o máximo de caracteres
    que realmente cabe na linha, sem sobrar espaço vazio nem estourar."""
    if metrics.horizontalAdvance(word) <= max_px:
        return word
    pedacos = []
    i, n = 0, len(word)
    while i < n:
        lo, hi, melhor = 1, n - i, 1
        while lo <= hi:
            meio = (lo + hi) // 2
            if metrics.horizontalAdvance(word[i:i + meio]) <= max_px:
                melhor = meio
                lo = meio + 1
            else:
                hi = meio - 1
        pedacos.append(word[i:i + melhor])
        i += melhor
    return _ZERO_WIDTH_SPACE.join(pedacos)


def _ideal_bubble_width(text: str, font: QFont, max_width: int, min_content_px: int = 80) -> int:
    """Acha a MENOR largura (até max_width) que ainda produz o mesmo número
    de linhas que usar a largura máxima inteira — evita tanto texto
    "espremido" (Qt às vezes escolhe uma largura menor do que precisa pra
    quebrar o texto, resultando em linhas curtas demais e desnecessárias)
    quanto balão maior que o necessário pra pouco texto. Isso substitui
    confiar no QLabel pra decidir sozinho a largura (QSizePolicy.Maximum +
    sizeHint não garante a largura mais "natural" pro conteúdo — na
    prática às vezes escolhe algo mais estreito do que devia)."""
    metrics = QFontMetrics(font)
    content_max = max(min_content_px, max_width - _BUBBLE_CHROME_PADDING)

    def altura_em(largura_conteudo: int) -> int:
        rect = metrics.boundingRect(0, 0, largura_conteudo, 100000, Qt.TextWordWrap, text)
        return rect.height()

    linha_unica = metrics.horizontalAdvance(text.replace("\n", " "))
    if linha_unica <= content_max:
        return min(max_width, linha_unica + _BUBBLE_CHROME_PADDING + _SAFETY_MARGIN_PX)

    altura_alvo = altura_em(content_max)
    lo, hi, melhor = min_content_px, content_max, content_max
    while lo <= hi:
        meio = (lo + hi) // 2
        if altura_em(meio) <= altura_alvo:
            melhor = meio
            hi = meio - 1
        else:
            lo = meio + 1
    return min(max_width, melhor + _BUBBLE_CHROME_PADDING + _SAFETY_MARGIN_PX)


def _insert_break_hints(text: str, font: QFont, max_width: int) -> str:
    """Insere espaços de largura zero dentro de "palavras" sem nenhum
    espaço (ex: texto colado sem pontuação, tipo "asdasdasdasdasd...") nos
    pontos exatos em que a linha deixaria de caber — calculado pela largura
    real da fonte. QLabel.setWordWrap(True) só quebra em espaços; o espaço
    de largura zero é invisível mas continua sendo um caractere de quebra
    válido pra qualquer motor de texto do Qt (diferente de propriedades CSS
    como overflow-wrap, cujo suporte varia entre versões do Qt)."""
    metrics = QFontMetrics(font)
    max_px = max(20, max_width - _BUBBLE_CHROME_PADDING - _SAFETY_MARGIN_PX)
    partes = re.split(r"(\s+)", text)
    resultado = []
    for parte in partes:
        if parte and not parte[0].isspace():
            parte = _greedy_break_word(parte, metrics, max_px)
        resultado.append(parte)
    return "".join(resultado)


class MessageBubble(QFrame):
    def __init__(self, text: str, max_width: int, is_user: bool = True, is_loading: bool = False, font_size: int = 14):
        super().__init__()
        self.is_user = is_user
        self.is_loading = is_loading
        self.base_text = text
        self.dots = 0
        self._code_blocks: list[str] = []
        self._rich_html: str | None = None
        self._copy_feedback_timer: QTimer | None = None

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.label.setOpenExternalLinks(False)
        self.label.linkActivated.connect(self._on_link_activated)
        self.label.setFont(QFont("Open Sans", font_size))
        # Alinhado à esquerda (padrão de mensagem de chat, tipo ChatGPT) —
        # era centralizado antes pra dividir uma folga residual de poucos
        # pixels dos dois lados, mas centralizar QUEBRA a leitura de bloco
        # de código (cada linha de código, por ter largura diferente, ficava
        # com recuo diferente — nada a ver com indentação real do código).
        # A folga residual (poucos pixels, arredondamento) agora fica só do
        # lado direito — imperceptível, e a leitura correta do código pesa
        # muito mais.
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Maximum (não Fixed) por padrão: mensagem curta abraça o conteúdo.
        # Vira Fixed (largura máxima cheia) em _render_text() quando o
        # texto precisa quebrar linha — ver _needs_wrapping().
        self.label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        if is_loading:
            self.label.setWordWrap(False)
            self.label.setMinimumWidth(190)

        if is_user:
            self.label.setObjectName("UserBubbleLabel")
            self.layout.addStretch(1)
            self.layout.addWidget(self.label, 0, Qt.AlignRight)
        else:
            self.label.setObjectName("BotBubbleLabel")
            # Formato de texto (Markdown puro vs Rich Text com blocos de
            # código realçados) é decidido por mensagem em _render_text(),
            # já que depende do conteúdo (tem ``` ou não).
            self.layout.addWidget(self.label, 0, Qt.AlignLeft)
            self.layout.addStretch(1)

        self._max_width = max_width
        self._render_text()

        if is_loading:
            self.loading_timer = QTimer(self)
            self.loading_timer.timeout.connect(self.update_loading_text)
            self.loading_timer.start(500)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

    def _render_text(self):
        if self.is_loading:
            self.label.setText(self.base_text)
            self.label.setMaximumWidth(max(self._max_width, 220))
            return

        font = self.label.font()
        forcou_quebra_no_meio_de_palavra = False
        if self.is_user:
            texto_exibido = _insert_break_hints(self.base_text, font, self._max_width)
            self.label.setText(texto_exibido)
            forcou_quebra_no_meio_de_palavra = _ZERO_WIDTH_SPACE in texto_exibido
        elif code_highlighter.has_code_block(self.base_text):
            self.label.setTextFormat(Qt.RichText)
            self._rich_html, self._code_blocks = code_highlighter.render_with_code_highlighting(
                self.base_text, font, theme=user_config.get("theme", "light")
            )
            self.label.setText(self._rich_html)
        else:
            self.label.setTextFormat(Qt.MarkdownText)
            self.label.setText(self.base_text)

        if forcou_quebra_no_meio_de_palavra:
            # Só o caso patológico (uma "palavra" única maior que o balão
            # inteiro, sem espaço nenhum pra quebrar) precisa da largura
            # máxima cheia, sem meio-termo — é o único jeito de manter a
            # altura do balão razoável nesse caso.
            self.label.setMinimumWidth(self._max_width)
            self.label.setMaximumWidth(self._max_width)
        else:
            # Texto normal (com espaços de verdade): calcula a largura
            # exata em vez de deixar o QLabel decidir sozinho — na prática
            # ele às vezes escolhe uma largura menor do que o ideal,
            # quebrando em linhas curtas demais sem necessidade.
            largura = _ideal_bubble_width(self.base_text, font, self._max_width)
            self.label.setMinimumWidth(largura)
            self.label.setMaximumWidth(largura)

    def set_max_width(self, max_width: int):
        self._max_width = max_width
        # A largura mudou (ex: redimensionar a janela) — os pontos de
        # quebra e a decisão abraça/preenche precisam ser recalculados.
        self._render_text()
        self.updateGeometry()

    def _on_link_activated(self, href: str):
        url = QUrl(href)
        if url.scheme() in ("https", "http") and url.host():
            QDesktopServices.openUrl(url)
            return
        # Os links internos de "Copiar" pertencem a cada
        # bloco de código (ver code_highlighter.py) — href no formato
        # "guia-copy:{índice}", apontando pro código puro correspondente.
        if not href.startswith("guia-copy:"):
            return
        try:
            indice = int(href.split(":", 1)[1])
            codigo = self._code_blocks[indice]
        except (ValueError, IndexError):
            return
        QApplication.clipboard().setText(codigo)
        self._show_copied_feedback(indice)

    def _show_copied_feedback(self, indice: int):
        # QLabel não tem estado de botão de verdade (é só um link dentro de
        # rich text) — o feedback "Copiado" é feito trocando o texto do
        # link específico no HTML já renderizado, exibindo por um tempo, e
        # depois voltando pro HTML original salvo em _render_text().
        if self._rich_html is None:
            return
        padrao = re.compile(rf'(href="guia-copy:{indice}"[^>]*>)[^<]*(</a>)')
        html_com_feedback = padrao.sub(rf"\g<1>{t('code_copied_label')}\g<2>", self._rich_html)
        self.label.setText(html_com_feedback)

        if self._copy_feedback_timer is not None:
            self._copy_feedback_timer.stop()
        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.timeout.connect(self._restore_copy_link_text)
        self._copy_feedback_timer.start(1500)

    def _restore_copy_link_text(self):
        if self._rich_html is not None:
            self.label.setText(self._rich_html)

    def stop_loading(self):
        if self.is_loading and hasattr(self, "loading_timer"):
            self.loading_timer.stop()

    def update_loading_text(self):
        self.dots = (self.dots + 1) % 4
        self.label.setText(f"{self.base_text}{'.' * self.dots}")
