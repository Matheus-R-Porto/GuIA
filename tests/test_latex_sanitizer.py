from latex_sanitizer import strip_latex


def test_texto_normal_sem_backslash_nao_e_alterado():
    texto = "Isso é uma resposta normal, com x_teste e a^b literal."
    assert strip_latex(texto) == texto


def test_delimitadores_de_formula_removidos():
    assert strip_latex(r"\[x^{2}-5x+6=0\]") == "x²-5x+6=0"


def test_frac_com_sqrt_aninhado():
    entrada = r"x_{1,2}= \frac{-b \pm \sqrt{\Delta}}{2a}"
    assert strip_latex(entrada) == "x_(1,2)= (-b ± √(Δ))/(2a)"


def test_quebra_de_linha_dupla_barra():
    entrada = "a = 1" + "\\" * 2 + "[2mm]\nb = -5" + "\\" * 2 + "[2mm]\nc = 6"
    saida = strip_latex(entrada)
    assert "\\" not in saida
    assert "a = 1" in saida and "b = -5" in saida and "c = 6" in saida


def test_potencia_aninhada_dentro_de_raiz_dentro_de_fracao():
    # Bhaskara real (achado por revisão externa): ^{2} aninhado dentro de
    # \sqrt{...}, por sua vez aninhado dentro de \frac{...}{...}. Se a ordem
    # de resolução for errada, nem o \sqrt nem o \frac casam e sobra LaTeX cru.
    entrada = r"x = \frac{-b \pm \sqrt{\,b^{2} - 4ac\,}}{2a}"
    saida = strip_latex(entrada)
    assert "\\" not in saida
    assert "{" not in saida and "}" not in saida
    assert "b²" in saida


def test_simbolos_gregos_e_operadores():
    entrada = r"\Delta = b^{2} - 4ac, \quad \pi \approx 3.14"
    saida = strip_latex(entrada)
    assert "Δ" in saida and "π" in saida and "≈" in saida
    assert "\\" not in saida
