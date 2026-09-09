"""Realce de sintaxe (Pygments) para blocos de código nas respostas da IA.

QLabel já renderiza markdown simples nativamente (negrito, listas, blocos de
código monoespaçados) via Qt.MarkdownText, mas sem cor nenhuma dentro do
código. Aqui a estratégia é: extrair os blocos cercados por ``` do texto,
deixar o Qt (QTextDocument.setMarkdown) converter o RESTO do markdown pra
HTML normalmente, e substituir cada bloco de código pelo HTML gerado pelo
Pygments (cores inline, sem depender de CSS externo — QLabel só renderiza
HTML com estilo inline). O bloco de código segue o tema claro/escuro do
app (ver `_PALETTES`) — visual estilo "janela de código" (ChatGPT/GitHub),
mas com cores próprias pra cada tema em vez de ficar sempre escuro.

Cada bloco ganha um cabeçalho com o nome da linguagem e um link "Copiar" —
QLabel não permite embutir um QPushButton de verdade dentro de rich text,
mas SUPORTA `<a href="...">` clicável via o sinal `linkActivated`; é assim
que o botão de copiar funciona (ver MessageBubble._on_link_activated).
"""
import html as html_module
import re

from PySide6.QtGui import QFont, QTextDocument
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from i18n import t

# Sem underscore nem caracteres que o parser de markdown do Qt possa tentar
# interpretar (ênfase, links) — só letras e dígitos entre @@.
_PLACEHOLDER = "@@GUIACODEBLOCK{}@@"
_FENCE_RE = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)

# Paleta por tema — o estilo do Pygments dita as cores dos tokens (palavra
# reservada, string, etc.); o resto (fundo, borda, cabeçalho, link) é
# escolhido à mão pra combinar com o tema claro/escuro do app.
_PALETTES = {
    "dark": {
        "pygments_style": "monokai",
        "header_bg": "#2D2D2D", "header_text": "#ABB2BF",
        "body_bg": "#1E1E1E", "body_text": "#F8F8F2",
        "copy_link": "#7FB0E0", "border": "#3A3A3A",
    },
    "light": {
        "pygments_style": "friendly",
        "header_bg": "#EAEEF2", "header_text": "#57606A",
        "body_bg": "#F6F8FA", "body_text": "#24292F",
        "copy_link": "#1565C0", "border": "#D0D7DE",
    },
}

_FORMATTERS = {
    theme: HtmlFormatter(noclasses=True, style=paleta["pygments_style"], nowrap=False)
    for theme, paleta in _PALETTES.items()
}

# Pygments já emite <pre style="line-height: 125%;">, não <pre> puro —
# substitui a tag inteira (não só insere um atributo) pra evitar duas
# declarações de "style" conflitantes na mesma tag.
_PRE_TAG_RE = re.compile(r"<pre[^>]*>")


def _get_lexer(lang: str, code: str):
    lang = (lang or "").strip().lower()
    if lang:
        try:
            return get_lexer_by_name(lang)
        except ClassNotFound:
            pass
    try:
        return guess_lexer(code)
    except ClassNotFound:
        return TextLexer()


def _highlight_block(index: int, lang: str, code: str, size_pt: int, theme: str) -> str:
    code = code.strip("\n")
    paleta = _PALETTES[theme]
    lexer = _get_lexer(lang, code)
    body_html = highlight(code, lexer, _FORMATTERS[theme])
    # O Qt NÃO preserva quebras de linha "cruas" dentro de <pre> ao
    # reanalisar o HTML pra exibir — mesmo com `white-space: pre-wrap` no
    # CSS, um `\n` literal dentro do texto vira espaço/nada (comportamento
    # normal de HTML, onde newline de código-fonte não é quebra de linha
    # visual). Confirmado testando com QTextDocument().setHtml(...) e
    # comparando o texto de volta: as linhas do Pygments (separadas por
    # `\n` puro) colapsavam numa string só. Fix: cada `\n` do código vira
    # um `<br>` explícito — só assim o Qt quebra a linha de verdade.
    body_html = body_html.replace("\n", "<br>")

    pre_style = (
        f"margin:0; background-color:{paleta['body_bg']}; color:{paleta['body_text']}; "
        f"padding:12px; border:1px solid {paleta['border']}; border-top:none; "
        f"border-radius:0 0 8px 8px; white-space:pre-wrap; word-break:break-word; "
        f"font-family:Consolas,monospace; font-size:{size_pt}pt; line-height:135%;"
    )
    body_html = _PRE_TAG_RE.sub(f'<pre style="{pre_style}">', body_html, count=1)

    lang_label = html_module.escape(lang.strip() or lexer.name)
    header_style = (
        f"background-color:{paleta['header_bg']}; border:1px solid {paleta['border']}; "
        f"border-bottom:none; border-radius:8px 8px 0 0;"
    )
    cell_style = (
        f"color:{paleta['header_text']}; padding:6px 12px; "
        f"font-family:Consolas,monospace; font-size:{size_pt}pt;"
    )
    copy_style = f"color:{paleta['copy_link']}; text-decoration:none; font-weight:bold;"
    header = (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="{header_style}"><tr>'
        f'<td style="{cell_style}">{lang_label}</td>'
        f'<td align="right" style="{cell_style}">'
        f'<a href="guia-copy:{index}" style="{copy_style}">{t("code_copy_link")}</a>'
        f'</td></tr></table>'
    )
    return header + body_html


def has_code_block(text: str) -> bool:
    return bool(_FENCE_RE.search(text or ""))


def render_with_code_highlighting(
    markdown_text: str, font: QFont | None = None, theme: str = "dark"
) -> tuple[str, list[str]]:
    """Converte markdown (com blocos ```lang ... ```) em HTML pronto pra
    QLabel em modo Qt.RichText. Blocos de código são realçados pelo Pygments
    (cores e fundo seguindo `theme`, "light" ou "dark") e ganham cabeçalho
    (linguagem + link "Copiar"); o resto do texto é convertido pelo parser
    de markdown nativo do Qt.

    Retorna (html, code_blocks) — code_blocks[i] é o texto puro (sem tags)
    do bloco de código de índice i, na ordem em que aparecem; quem chama
    usa isso pra implementar o clique em "Copiar" (href="guia-copy:{i}").
    """
    theme = theme if theme in _PALETTES else "dark"
    blocos = []

    def _extrair(m):
        blocos.append((m.group(1), m.group(2)))
        # Quebras de linha em branco ANTES e DEPOIS, sempre — mesmo que o
        # texto original não tivesse (a IA nem sempre deixa linha em branco
        # antes da cerca de código). Sem isso, se o placeholder ficar colado
        # em texto vizinho na mesma linha, o parser de markdown do Qt funde
        # tudo num <p> só, e o replace abaixo (que espera o placeholder
        # sozinho dentro do <p>) não bate — o bloco de código nunca vira
        # elemento irmão do parágrafo, e as quebras de linha internas dele
        # somem na renderização.
        return f"\n\n{_PLACEHOLDER.format(len(blocos) - 1)}\n\n"

    texto_sem_codigo = _FENCE_RE.sub(_extrair, markdown_text)

    doc = QTextDocument()
    if font is not None:
        doc.setDefaultFont(font)
    doc.setMarkdown(texto_sem_codigo)
    html = doc.toHtml()

    size_pt = font.pointSize() if font is not None and font.pointSize() > 0 else 10
    codigos = []
    for i, (lang, code) in enumerate(blocos):
        codigos.append(code.strip("\n"))
        bloco_html = _highlight_block(i, lang, code, size_pt, theme)
        placeholder = _PLACEHOLDER.format(i)
        # O conversor de markdown do Qt embrulha qualquer texto solto num
        # <p style="white-space: pre-wrap; ...">...</p> — se o bloco de
        # código ficar ANINHADO dentro desse <p>, o Qt colapsa as quebras
        # de linha internas do <pre> ao renderizar (HTML inválido: bloco
        # dentro de parágrafo). Por isso o replace é do <p>...</p> INTEIRO,
        # não só do texto do placeholder — o bloco de código vira um
        # elemento irmão, não filho, do parágrafo.
        html = re.sub(rf"<p[^>]*>{re.escape(placeholder)}</p>", bloco_html, html)

    return html, codigos
