"""Rede de segurança contra respostas em notação LaTeX.

O prompt instrui a IA a nunca usar LaTeX (só símbolos Unicode: √, ², Δ...),
mas na prática o modelo às vezes volta pro formato LaTeX mesmo assim —
sobretudo em cálculo/integral e em equações muito comuns nos dados de
treino. Isso não é um bug do app: é o modelo "esquecendo" a instrução em
respostas longas. Como o balão de chat só renderiza Markdown (não LaTeX),
uma resposta assim aparece pro aluno cheia de "\\[", "\\frac{...}",
"x^{2}" — visualmente quebrada.

Esta função roda em cima da resposta, DEPOIS que ela volta do modelo, e
converte os padrões LaTeX mais comuns para texto puro/Unicode equivalente.
Não é um parser de LaTeX completo (não cobre aninhamento profundo de
chaves) — cobre os casos observados na prática, o que é suficiente aqui.
"""
import re

_SUP_DIGITS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻",
}
_SUB_DIGITS = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋",
}

# Comandos LaTeX -> símbolo Unicode equivalente. Ordem importa: comandos mais
# específicos (ex: \rightarrow) antes de substrings que outros contêm.
_SYMBOL_MAP = [
    (r"\\pm", "±"), (r"\\mp", "∓"),
    (r"\\times", "×"), (r"\\div", "÷"), (r"\\cdot", "·"),
    (r"\\leq", "≤"), (r"\\geq", "≥"), (r"\\neq", "≠"), (r"\\approx", "≈"),
    (r"\\infty", "∞"),
    (r"\\Longrightarrow", "⇒"), (r"\\longrightarrow", "→"), (r"\\Rightarrow", "⇒"),
    (r"\\implies", "⇒"), (r"\\iff", "⇔"),
    (r"\\ldots", "…"), (r"\\dots", "…"), (r"\\cdots", "⋯"),
    (r"\\le\b", "≤"), (r"\\ge\b", "≥"), (r"\\ne\b", "≠"),
    (r"\\rightarrow", "→"), (r"\\to", "→"), (r"\\in\b", "∈"),
    (r"\\int", "∫"), (r"\\sum", "Σ"), (r"\\prod", "Π"),
    (r"\\Delta", "Δ"), (r"\\delta", "δ"),
    (r"\\pi\b", "π"), (r"\\theta", "θ"), (r"\\alpha", "α"), (r"\\beta", "β"),
    (r"\\lambda", "λ"), (r"\\mu", "μ"), (r"\\sigma", "σ"), (r"\\phi", "φ"),
    (r"\\omega", "ω"), (r"\\Omega", "Ω"),
    (r"\\sqrt", "√"),  # \sqrt sem chaves (raro, mas evita deixar a barra solta)
    # comandos de espaçamento/estilo sem equivalente visual — apenas remove
    (r"\\displaystyle", ""), (r"\\left", ""), (r"\\right", ""),
    (r"\\,", " "), (r"\\;", " "), (r"\\:", " "), (r"\\!", ""), (r"\\ ", " "),
    (r"\\qquad", "  "), (r"\\quad", " "),
]


_SIMPLE = re.compile(r"(?:\\[A-Za-z]+|[A-Za-z0-9π√²³.,])+")


def _frac_sub(match: re.Match) -> str:
    a, b = match.group(1).strip(), match.group(2).strip()
    if _SIMPLE.fullmatch(a) and _SIMPLE.fullmatch(b):
        return f"{a}/{b}"  # frações simples: 1/3, π/3
    return f"({a})/({b})"


def _sqrt_braces_sub(match: re.Match) -> str:
    degree, radicand = match.group("deg"), match.group("rad")
    prefix = f"{degree}" if degree else ""
    return f"{prefix}√({radicand})"


def _pow_sub(match: re.Match) -> str:
    content = match.group(1)
    if re.fullmatch(r"[+-]?\d+", content):
        return "".join(_SUP_DIGITS.get(c, c) for c in content)
    if re.fullmatch(r"[A-Za-z0-9]{1,3}", content):
        return f"^{content}"
    return f"^({content})"


def _sub_sub(match: re.Match) -> str:
    content = match.group(1)
    if re.fullmatch(r"[+-]?\d+", content):
        return "".join(_SUB_DIGITS.get(c, c) for c in content)
    if re.fullmatch(r"[0-9]+(,[0-9]+)+", content):
        return "".join(_SUB_DIGITS.get(c, c) for c in content)  # x₁,₂
    if re.fullmatch(r"[A-Za-z0-9]{1,8}", content):
        return f"_{content}"
    return f"_({content})"


_MATRIX_ENV = re.compile(r"\\begin\{([pbvBV]?matrix)\}(.*?)\\end\{\1\}", re.DOTALL)


def _matrix_block(match: re.Match) -> str:
    """\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix} -> bloco de código alinhado."""
    rows = [r.strip() for r in re.split(r"\\\\", match.group(2)) if r.strip()]
    cells = [[strip_latex(c.strip()) for c in row.split("&")] for row in rows]
    if not cells:
        return ""
    ncols = max(len(r) for r in cells)
    widths = [max(len(r[j]) if j < len(r) else 0 for r in cells) for j in range(ncols)]
    lines = ["[ " + "  ".join((r[j] if j < len(r) else "").rjust(widths[j]) for j in range(ncols)) + " ]"
             for r in cells]
    return "\n```\n" + "\n".join(lines) + "\n```\n"


def strip_latex(text: str) -> str:
    """Converte notação LaTeX comum em texto puro/Unicode. Se o texto não
    contém nenhum comando LaTeX (sem barra invertida), retorna sem alterações
    — não mexe em respostas normais."""
    if text:
        # "9{,}81" é a vírgula decimal do LaTeX; aparece mesmo sem nenhum comando com barra.
        text = text.replace("{,}", ",")
    if not text or "\\" not in text:
        return text

    # Matrizes viram bloco de código alinhado (o chat não renderiza LaTeX).
    blocks: list[str] = []

    def _stash(m: re.Match) -> str:
        blocks.append(_matrix_block(m))
        return f"\x00M{len(blocks) - 1}\x00"

    result = _MATRIX_ENV.sub(_stash, text)
    # \text{cm}, \mathrm{x}, \mathbf{A}, \operatorname{tr}: mantém só o conteúdo.
    for _ in range(3):
        result = re.sub(r"\\(?:text|textbf|textit|mathrm|mathbf|mathit|operatorname|mbox)\{([^{}]*)\}",
                        r"\1", result)

    # \begin{cases}/\end{cases}: mantém o conteúdo, descarta o envelope.
    result = re.sub(r"\\begin\{[a-z*]+\}", "", result)
    result = re.sub(r"\\end\{[a-z*]+\}", "", result)

    # \sqrt{...} e ^{...}/_{...} são resolvidos ANTES de \frac, porque
    # ambos costumam aparecer aninhados dentro do numerador/denominador de
    # uma fração (ex: \frac{-b \pm \sqrt{\Delta}}{2a}) — resolvê-los primeiro
    # remove as chaves internas e permite que o regex (não-recursivo) de
    # \frac capture o conteúdo corretamente na etapa seguinte.
    #
    # Mas ^{...} e \sqrt{...} também podem estar aninhados ENTRE SI (ex: a
    # fórmula de Bhaskara real, \sqrt{\,b^{2}-4ac\,} — a potência b^{2} fica
    # DENTRO do radical). O regex de \sqrt exige que não haja chaves no seu
    # conteúdo, então se ^{...} não for resolvido antes, o \sqrt nunca
    # casa, sobra `{}` cru, e o \frac por sua vez também não casa (efeito
    # cascata). Por isso repetimos o par (potência/subscrito, depois raiz)
    # em loop até estabilizar, cobrindo qualquer ordem de aninhamento entre
    # os dois antes de seguir para \frac.
    for _ in range(4):
        before = result
        result = re.sub(r"\^\{([^{}]*)\}", _pow_sub, result)
        result = re.sub(r"_\{([^{}]*)\}", _sub_sub, result)
        result = re.sub(r"\\sqrt\[(?P<deg>[^\]]*)\]\{(?P<rad>[^{}]*)\}", _sqrt_braces_sub, result)
        result = re.sub(r"\\sqrt\{([^{}]*)\}", lambda m: f"√({m.group(1)})", result)
        if result == before:
            break

    # Sobrescrito/subscrito de um único caractere sem chaves: x^2, x_1
    result = re.sub(r"\^(\d)", lambda m: _SUP_DIGITS.get(m.group(1), m.group(1)), result)
    result = re.sub(r"_(\d)", lambda m: _SUB_DIGITS.get(m.group(1), m.group(1)), result)

    # \frac{a}{b} -> (a)/(b). Roda algumas vezes para pegar frações em sequência
    # (não cobre frações aninhadas dentro de outra fração).
    for _ in range(3):
        new_result = re.sub(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}", _frac_sub, result)
        if new_result == result:
            break
        result = new_result

    for pattern, repl in _SYMBOL_MAP:
        result = re.sub(pattern, repl, result)

    # Quebra de linha do LaTeX ("\\" ou "\\[2mm]") -> quebra de linha real.
    result = re.sub(r"\\\\(\[[^\]]*\])?", "\n", result)

    # Delimitadores de fórmula: \[ \] \( \) e $$ $ — remove, mantém o conteúdo.
    result = re.sub(r"\\\[|\\\]|\\\(|\\\)", "", result)
    result = result.replace("$$", "").replace("$", "")

    # Colapsa espaços/linhas em branco extras deixados pelas remoções acima.
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    for i, block in enumerate(blocks):
        result = result.replace(f"\x00M{i}\x00", block)
    return result.strip()
