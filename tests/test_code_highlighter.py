from PySide6.QtWidgets import QApplication

import code_highlighter

# QTextDocument precisa de uma QApplication instanciada (mesmo sem tela).
_app = QApplication.instance() or QApplication([])


def test_has_code_block_detecta_cerca_de_codigo():
    assert code_highlighter.has_code_block("Olha isso:\n```python\nprint(1)\n```")
    assert not code_highlighter.has_code_block("Texto sem código nenhum, só prosa normal.")


def test_render_com_bloco_de_codigo_gera_html_com_cores():
    texto = "Segue um exemplo:\n\n```python\ndef soma(a, b):\n    return a + b\n```\n\nSimples assim."
    html, codigos = code_highlighter.render_with_code_highlighting(texto)

    assert "<pre" in html
    assert "def" in html or "soma" in html
    assert "@@GUIACODEBLOCK" not in html  # placeholder sempre substituído
    assert "background-color:#1E1E1E" in html
    assert "style=" in html  # cores inline do Pygments (noclasses=True)
    assert codigos == ["def soma(a, b):\n    return a + b"]


def test_pre_nunca_fica_aninhado_dentro_de_paragrafo():
    """Regressão: o Qt colapsa as quebras de linha do <pre> quando ele fica
    aninhado dentro de um <p> (o conversor de markdown embrulha texto solto
    em <p white-space:pre-wrap>...</p> — se o bloco de código ficar preso
    lá dentro, as quebras de linha internas do código somem na renderização
    real, mesmo a string HTML parecendo correta)."""
    texto = "```python\na = 1\nb = 2\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto)
    # Não deve existir "<p ...><pre" nem "<p ...><table" (o wrapper do
    # bloco de código) na mesma sequência — senão o Qt colapsa as quebras.
    import re
    assert not re.search(r"<p[^>]*>\s*<(pre|table)", html)


def test_bloco_de_codigo_preserva_quebras_de_linha_internas():
    texto = "```python\nlinha1\nlinha2\nlinha3\n```"
    html, codigos = code_highlighter.render_with_code_highlighting(texto)
    assert codigos[0] == "linha1\nlinha2\nlinha3"
    # As 3 linhas devem aparecer como conteúdo distinto dentro do <pre>,
    # não coladas numa string só.
    pre_content = html.split("<pre", 1)[1]
    assert "linha1" in pre_content and "linha2" in pre_content and "linha3" in pre_content


def test_quebras_de_linha_sobrevivem_a_renderizacao_real_do_qt():
    """A regressão real (2026-07-27): checar só se o texto aparece em
    algum lugar do HTML NÃO pega esse bug — a string HTML podia conter
    `\\n` de verdade dentro do `<pre>` e mesmo assim o Qt colapsava tudo
    numa linha só ao RENDERIZAR (comportamento normal de HTML: newline de
    código-fonte não é quebra de linha visual, só `<br>` é). Esse teste
    reanalisa o HTML com QTextDocument — o mesmo mecanismo que o QLabel usa
    por baixo — e confere o texto puro resultante, não a string HTML crua."""
    from PySide6.QtGui import QTextDocument

    texto = "```python\nlinha1\nlinha2\nlinha3\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto)

    doc = QTextDocument()
    doc.setHtml(html)
    texto_renderizado = doc.toPlainText()

    assert "linha1\nlinha2" in texto_renderizado
    assert "linha2\nlinha3" in texto_renderizado
    assert "linha1linha2" not in texto_renderizado  # sintoma do bug original


def test_bloco_de_codigo_tem_link_de_copiar_por_indice():
    texto = "```python\nprint(1)\n```\n\n```js\nconsole.log(2)\n```"
    html, codigos = code_highlighter.render_with_code_highlighting(texto)
    assert 'href="guia-copy:0"' in html
    assert 'href="guia-copy:1"' in html
    assert codigos == ["print(1)", "console.log(2)"]


def test_render_respeita_o_tamanho_de_fonte_passado():
    from PySide6.QtGui import QFont
    texto = "```python\nx = 1\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto, font=QFont("Open Sans", 17))
    assert "font-size:17pt" in html


def test_render_preserva_texto_normal_fora_do_bloco():
    texto = "Antes.\n\n```js\nconsole.log(1);\n```\n\nDepois."
    html, _codigos = code_highlighter.render_with_code_highlighting(texto)
    assert "Antes." in html
    assert "Depois." in html


def test_render_sem_linguagem_declarada_nao_quebra():
    texto = "```\nplain text sem linguagem\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto)
    assert "<pre" in html
    assert "plain text sem linguagem" in html


def test_texto_sem_bloco_de_codigo_nao_precisa_de_realce():
    assert not code_highlighter.has_code_block("**negrito** e _itálico_ normais, sem crase tripla.")


def test_bloco_de_codigo_colado_no_texto_sem_linha_em_branco_antes():
    """Regressão real: a IA nem sempre deixa uma linha em branco antes da
    cerca de código (ex: "Aqui vai:\\n```python\\n..."). Sem forçar linha em
    branco ao redor do placeholder, o parser de markdown do Qt funde o
    texto e o placeholder no mesmo <p>, e o bloco de código nunca vira
    elemento irmão do parágrafo — as quebras de linha internas somem."""
    texto = "Aqui vai um exemplo:\n```python\nlinha1\nlinha2\n```\nDepois disso."
    html, codigos = code_highlighter.render_with_code_highlighting(texto)
    import re
    assert not re.search(r"<p[^>]*>\s*<(pre|table)", html)
    assert "@@GUIACODEBLOCK" not in html
    assert codigos == ["linha1\nlinha2"]
    assert "Aqui vai um exemplo:" in html
    assert "Depois disso." in html


def test_tema_escuro_usa_paleta_escura():
    texto = "```python\nx = 1\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto, theme="dark")
    assert "background-color:#1E1E1E" in html


def test_tema_claro_usa_paleta_clara_nao_escura():
    texto = "```python\nx = 1\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto, theme="light")
    assert "background-color:#F6F8FA" in html
    assert "background-color:#1E1E1E" not in html


def test_tema_desconhecido_cai_no_escuro_por_padrao():
    texto = "```python\nx = 1\n```"
    html, _codigos = code_highlighter.render_with_code_highlighting(texto, theme="roxo-nao-existe")
    assert "background-color:#1E1E1E" in html
