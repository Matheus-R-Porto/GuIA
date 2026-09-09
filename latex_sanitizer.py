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


def _frac_sub(match: re.Match) -> str:
    return f"({match.group(1)})/({match.group(2)})"


def _sqrt_braces_sub(match: re.Match) -> str:
    degree, radicand = match.group("deg"), match.group("rad")
    prefix = f"{degree}" if degree else ""
    return f"{prefix}√({radicand})"


def _pow_sub(match: re.Match) -> str:
    content = match.group(1)
    if re.fullmatch(r"[+-]?\d+", content):
        return "".join(_SUP_DIGITS.get(c, c) for c in content)
    return f"^({content})"


def _sub_sub(match: re.Match) -> str:
    content = match.group(1)
    if re.fullmatch(r"[+-]?\d+", content):
        return "".join(_SUB_DIGITS.get(c, c) for c in content)
    return f"_({content})"


def strip_latex(text: str) -> str:
    """Converte notação LaTeX comum em texto puro/Unicode. Se o texto não
    contém nenhum comando LaTeX (sem barra invertida), retorna sem alterações
    — não mexe em respostas normais."""
    if not text or "\\" not in text:
        return text

    # \begin{cases}/\end{cases}: mantém o conteúdo, descarta o envelope.
    result = re.sub(r"\\begin\{[a-z*]+\}", "", text)
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
    return result.strip()
