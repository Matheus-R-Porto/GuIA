from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QSizePolicy, QToolButton

from ui.widgets.quiz_widget import QuizWidget, _render_rich

# QLabel/QFontMetrics precisam de uma QApplication instanciada.
_app = QApplication.instance() or QApplication([])


def test_marcacao_asterisco_vira_italico_html():
    assert _render_rich("lado *a* com o vértice B") == "lado <i>a</i> com o vértice B"


def test_texto_sem_marcacao_fica_igual_so_com_quebras_convertidas():
    assert _render_rich("Texto normal sem variável nenhuma.") == "Texto normal sem variável nenhuma."


def test_quebra_de_linha_vira_br():
    assert _render_rich("Linha 1\n\nLinha 2") == "Linha 1<br><br>Linha 2"


def test_caracteres_html_especiais_sao_escapados():
    # "a > b" não pode virar HTML de verdade por engano.
    resultado = _render_rich("Se a > b, então x < 5 & y")
    assert "<" not in resultado.replace("&lt;", "").replace("&amp;", "")
    assert "a &gt; b" in resultado
    assert "x &lt; 5" in resultado
    assert "&amp; y" in resultado


def test_multiplas_marcacoes_na_mesma_string():
    resultado = _render_rich("*a*√3 + *a*√3 = 2*a*√3")
    assert resultado == "<i>a</i>√3 + <i>a</i>√3 = 2<i>a</i>√3"


def test_questao_51_real_tem_marcacao_e_renderiza_com_italico():
    import json
    from pathlib import Path

    questoes_path = Path(__file__).resolve().parent.parent / "quiz" / "questoes.json"
    questoes = json.loads(questoes_path.read_text(encoding="utf-8"))
    q51 = next(q for q in questoes if q["id"] == "ufrgs-2023-mat-51")

    widget = QuizWidget()
    widget._current_question = q51
    widget._render_question()

    assert widget.enunciado_label.textFormat() == Qt.RichText
    assert "<i>a</i>" in widget.enunciado_label.text()


def test_alternativas_texto_usam_qpushbutton():
    widget = QuizWidget()
    widget._current_question = {
        "id": "teste-texto", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": "um", "B": "dois"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()

    assert isinstance(widget._alt_buttons["A"], QPushButton)
    label = widget._alt_buttons["A"].layout().itemAt(0).widget()
    assert label.text() == "A) um"
    assert label.wordWrap() is True
    assert "Z: W" in widget.tag_label.text()


def test_alternativas_texto_ficam_em_coluna_unica():
    widget = QuizWidget()
    widget._current_question = {
        "id": "teste-texto", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": "um", "B": "dois", "C": "três"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()

    for letra, linha_esperada in (("A", 0), ("B", 1), ("C", 2)):
        indice = widget.alt_layout.indexOf(widget._alt_buttons[letra])
        linha, coluna, *_ = widget.alt_layout.getItemPosition(indice)
        assert (linha, coluna) == (linha_esperada, 0)


def _fabrica_png(caminho):
    from PySide6.QtGui import QPixmap as _QPixmap
    _QPixmap(10, 10).save(str(caminho))


def test_alternativas_imagem_usam_qtoolbutton_com_icone(tmp_path, monkeypatch):
    import quiz

    # Fabrica um PNG mínimo de verdade (não pode ser um arquivo vazio —
    # QPixmap precisa conseguir decodificar algo real).
    _fabrica_png(tmp_path / "alt_a.png")
    monkeypatch.setattr(quiz, "image_path", lambda nome: tmp_path / nome)

    widget = QuizWidget()
    widget._current_question = {
        "id": "teste-imagem", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Qual gráfico representa a função?",
        "alternativas_tipo": "imagem",
        "alternativas": {"A": "alt_a.png"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()

    btn = widget._alt_buttons["A"]
    assert isinstance(btn, QToolButton)
    assert btn.text() == "(A)"
    assert not btn.icon().isNull()


def test_alternativas_imagem_ficam_em_grade_de_3_colunas(tmp_path, monkeypatch):
    import quiz

    for letra in "ABCDE":
        _fabrica_png(tmp_path / f"alt_{letra}.png")
    monkeypatch.setattr(quiz, "image_path", lambda nome: tmp_path / nome)

    widget = QuizWidget()
    widget._current_question = {
        "id": "teste-grade", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Qual gráfico representa a função?",
        "alternativas_tipo": "imagem",
        "alternativas": {l: f"alt_{l}.png" for l in "ABCDE"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()

    # A, B, C na primeira linha; D, E na segunda — grade 3 colunas.
    posicoes_esperadas = {"A": (0, 0), "B": (0, 1), "C": (0, 2), "D": (1, 0), "E": (1, 1)}
    for letra, (linha_esperada, coluna_esperada) in posicoes_esperadas.items():
        indice = widget.alt_layout.indexOf(widget._alt_buttons[letra])
        linha, coluna, *_ = widget.alt_layout.getItemPosition(indice)
        assert (linha, coluna) == (linha_esperada, coluna_esperada), letra


def test_voltar_aos_filtros_nao_herda_altura_de_questao_com_imagem_grande():
    """Regressão: QStackedWidget calcula sizeHint() como o da MAIOR página
    entre TODAS as cadastradas, não só a visível (comportamento documentado
    do próprio Qt) — sem corrigir isso, depois de ver uma questão com
    imagem grande, a tela de filtros (bem mais curta) ficava esticada do
    mesmo jeito, empurrando o botão "Começar" pra baixo."""
    widget = QuizWidget()
    altura_filtros_original = widget.stack.sizeHint().height()

    questao_com_imagem_grande = {
        "id": "teste-imagem-grande", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": "um", "B": "dois"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._current_question = questao_com_imagem_grande
    widget._render_question()
    # Simula um label de imagem bem alto, tipo uma questão com figura grande
    # (ex: o gráfico da questão 58) — sem precisar de um arquivo de verdade.
    # _render_question() esconde image_label quando a questão não tem
    # "imagem" (não é o caso real que queremos simular), então mostra na
    # mão DEPOIS do render pra garantir que a altura conte no sizeHint()
    # (um QLabel escondido é ignorado pelo cálculo de tamanho do layout).
    widget.image_label.show()
    widget.image_label.setMinimumHeight(900)
    widget.stack.setCurrentIndex(1)
    altura_com_imagem = widget.stack.sizeHint().height()
    assert altura_com_imagem > altura_filtros_original  # confirma que a página cresceu de verdade

    widget._on_back_to_filters()
    altura_depois_de_voltar = widget.stack.sizeHint().height()
    assert altura_depois_de_voltar == altura_filtros_original


def test_tag_label_quebra_linha_em_vez_de_estourar_a_pagina_na_horizontal():
    """Regressão: desde que tag_label passou a mostrar "conteudo: detalhe"
    (às vezes bem longo, ex: "Eletromagnetismo: campo magnético: movimento
    circular de partículas carregadas"), sem quebra de linha o texto virava
    uma única linha gigante — empurrava o título "Laboratório" pra fora da
    tela e esticava a página inteira na horizontal, cortando o botão de
    próxima questão."""
    assert QuizWidget().tag_label.wordWrap() is True


def test_tag_label_com_texto_longo_nao_sobrepoe_conteudo_abaixo():
    """Regressão nº 2 do mesmo bug: só ligar wordWrap não bastou — o
    tag_label estava sendo adicionado ao layout do cabeçalho com uma flag
    de alinhamento (Qt.AlignLeft | Qt.AlignVCenter) no próprio addWidget().
    Isso faz o Qt usar o sizeHint() "livre" (largura natural, 1 linha) em
    vez de consultar heightForWidth() pra decidir a altura reservada —
    mesmo bug já visto antes no welcome_label do chat. Resultado: a altura
    reservada ficava menor que a altura real do texto quebrado em 2 linhas,
    e a segunda linha sobrepunha o conteúdo (enunciado) logo abaixo."""
    widget = QuizWidget()
    widget.resize(1200, 800)
    widget.show()
    _app.processEvents()

    widget._current_question = {
        "id": "teste-tag-longo", "vestibular": "UFRGS", "ano": 2023, "materia": "Física",
        "conteudo": "Eletrodinâmica",
        "detalhe": "circuitos: força eletromotriz e resistência interna — um detalhe propositalmente longo",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": "um", "B": "dois"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()
    widget.stack.setCurrentIndex(1)
    for _ in range(5):
        _app.processEvents()

    label = widget.tag_label
    assert label.height() == label.heightForWidth(label.width())


def test_botao_de_report_abre_email_com_dados_da_questao(monkeypatch):
    chamadas = []
    import bug_report
    from ui.dialogs import ReportBugDialog
    monkeypatch.setattr(bug_report, "open_report_email", lambda assunto, corpo: chamadas.append((assunto, corpo)))
    # O diálogo de fallback (copiar texto) é modal — .exec() travaria o
    # teste esperando alguém fechar a janela. Substitui por um no-op.
    monkeypatch.setattr(ReportBugDialog, "exec", lambda self: None)

    widget = QuizWidget()
    widget._current_question = {
        "id": "ufrgs-2023-mat-99", "vestibular": "UFRGS", "ano": 2023, "materia": "Matemática",
        "conteudo": "Álgebra", "detalhe": "teste",
        "enunciado": "Quanto vale *a* + *b*?",
        "alternativas": {"A": "1", "B": "2"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()

    widget._on_report_clicked()

    assert len(chamadas) == 1
    assunto, corpo = chamadas[0]
    assert "ufrgs-2023-mat-99" in assunto
    assert "ufrgs-2023-mat-99" in corpo
    assert "Matemática" in corpo
    assert "Álgebra: teste" in corpo
    # a marcação de itálico (*a*) não deve vazar pro corpo do email em
    # texto puro — só faz sentido na renderização rica da tela.
    assert "*" not in corpo
    assert "Quanto vale a + b?" in corpo


def test_botao_de_report_nao_quebra_sem_questao_atual():
    widget = QuizWidget()
    widget._on_report_clicked()  # não deve levantar exceção


def test_alternativa_de_texto_longa_quebra_linha_sem_estourar_a_largura():
    """Regressão: alternativas longas (comuns em Geografia/Química) não
    quebravam dentro do QPushButton — o texto estourava a largura do botão,
    esticando a página inteira e forçando uma barra de rolagem horizontal
    que não deveria existir. Corrigido embutindo um QLabel com wordWrap
    dentro do botão + reajuste manual de altura via heightForWidth (Qt não
    propaga height-for-width através de QPushButton dentro de QGridLayout)."""
    widget = QuizWidget()
    widget.resize(700, 900)
    widget.show()
    _app.processEvents()

    texto_longo = (
        "Um texto de alternativa propositalmente bem longo, do tamanho de "
        "uma alternativa real de Geografia ou Química, pra garantir que "
        "precise quebrar em mais de uma linha dentro do botão."
    )
    widget._current_question = {
        "id": "teste-alt-longa", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": texto_longo, "B": "curta"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._render_question()
    widget.stack.setCurrentIndex(1)
    for _ in range(20):
        _app.processEvents()
    widget._ajustar_altura_alternativas_texto()
    _app.processEvents()

    btn = widget._alt_buttons["A"]
    label = btn.layout().itemAt(0).widget()
    assert label.wordWrap() is True
    # a altura do botão precisa acompanhar o texto quebrado (não pode ficar
    # travada na altura mínima de uma linha só, senão o texto é cortado).
    assert btn.height() > 42
    assert widget.scroll.horizontalScrollBar().maximum() == 0


def _questao_fake(id_, resposta="A"):
    return {
        "id": id_, "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": f"Enunciado da questão {id_}",
        "alternativas": {"A": "um", "B": "dois"},
        "resposta_correta": resposta, "explicacao": "explicação qualquer",
    }


def test_botao_questao_anterior_comeca_desabilitado_na_primeira_questao(monkeypatch):
    import quiz
    monkeypatch.setattr(quiz, "get_random_question", lambda **kw: _questao_fake("q1"))

    widget = QuizWidget()
    widget._load_next_question()

    assert widget._current_question["id"] == "q1"
    assert widget.back_btn.isEnabled() is False


def test_botao_questao_anterior_habilita_depois_de_avancar(monkeypatch):
    import quiz
    fabricadas = iter([_questao_fake("q1"), _questao_fake("q2")])
    monkeypatch.setattr(quiz, "get_random_question", lambda **kw: next(fabricadas))

    widget = QuizWidget()
    widget._load_next_question()
    widget._on_next_clicked()

    assert widget._current_question["id"] == "q2"
    assert widget.back_btn.isEnabled() is True


def test_voltar_questao_preserva_estado_de_respondida(monkeypatch):
    import quiz
    fabricadas = iter([_questao_fake("q1"), _questao_fake("q2")])
    monkeypatch.setattr(quiz, "get_random_question", lambda **kw: next(fabricadas))

    widget = QuizWidget()
    widget._load_next_question()  # q1
    widget._on_alternative_clicked("B")  # errada, de propósito
    assert widget._alt_buttons["B"].isEnabled() is False

    widget._on_next_clicked()  # q2, nova e ainda não respondida
    assert widget._current_question["id"] == "q2"
    assert widget._answered is False
    assert widget._alt_buttons["A"].isEnabled() is True

    widget._on_previous_clicked()  # volta pra q1
    assert widget._current_question["id"] == "q1"
    assert widget._answered is True
    assert widget._alt_buttons["B"].property("state") == "incorrect"
    assert widget._alt_buttons["A"].property("state") == "correct"
    # widget nunca foi show()n de verdade nesse teste, então isVisible()
    # sempre seria False (depende da cadeia de pais estar visível) —
    # isHidden() reflete o último show()/hide() chamado no próprio label.
    assert widget.explanation_label.isHidden() is False


def test_proxima_depois_de_voltar_nao_sorteia_questao_nova(monkeypatch):
    import quiz
    fabricadas = iter([_questao_fake("q1"), _questao_fake("q2")])
    monkeypatch.setattr(quiz, "get_random_question", lambda **kw: next(fabricadas))

    widget = QuizWidget()
    widget._load_next_question()  # q1
    widget._on_next_clicked()  # q2 (nova, consome o iterador)
    widget._on_previous_clicked()  # volta pra q1
    widget._on_next_clicked()  # deveria reavançar pra q2, não sortear outra

    assert widget._current_question["id"] == "q2"


def test_botao_voltar_aos_filtros_fica_no_cabecalho_e_funciona():
    widget = QuizWidget()
    widget.stack.setCurrentIndex(1)
    assert widget.stack.currentIndex() == 1

    widget.back_to_filters_btn.click()

    assert widget.stack.currentIndex() == 0


def test_stack_sizeHint_segue_so_a_pagina_atual():
    """Regressão: QStackedWidget.sizeHint() (diferente de
    minimumSizeHint()) NÃO respeita QSizePolicy.Ignored nas páginas não
    atuais — confirmado testando na prática. A tentativa anterior de
    corrigir o "vazamento" de altura (marcar página não-atual como
    Ignored) só funcionava por coincidência em alguns casos; o
    QStackedWidget real usado por QuizWidget agora sobrescreve
    sizeHint()/minimumSizeHint() pra sempre refletir só currentWidget()."""
    widget = QuizWidget()
    altura_filtros = widget.stack.sizeHint().height()

    questao = {
        "id": "teste-imagem-grande", "vestibular": "X", "ano": 2020, "materia": "Y",
        "conteudo": "Z", "detalhe": "W",
        "enunciado": "Enunciado qualquer",
        "alternativas": {"A": "um", "B": "dois"},
        "resposta_correta": "A", "explicacao": "explicação qualquer",
    }
    widget._current_question = questao
    widget._render_question()
    widget.image_label.show()
    widget.image_label.setMinimumHeight(900)
    widget.stack.setCurrentIndex(1)
    assert widget.stack.sizeHint().height() > altura_filtros

    widget._on_back_to_filters()
    assert widget.stack.sizeHint().height() == altura_filtros


# --- filtros: caixas de marcação múltipla escolha ---

def test_nenhuma_materia_marcada_esconde_secao_de_conteudo():
    widget = QuizWidget()
    assert widget.conteudo_container.isHidden() is True
    assert widget.confirmar_materias_btn.isEnabled() is False


def test_marcar_materia_sem_confirmar_ainda_nao_mostra_conteudo():
    """Regressão: o conteúdo só deve aparecer depois que a pessoa clica em
    "Confirmar matérias" — não a cada matéria marcada em sequência (evita
    a seção piscando/mudando de tamanho o tempo todo)."""
    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)

    assert widget.conteudo_container.isHidden() is True
    assert widget._conteudo_checks == {}
    assert widget.confirmar_materias_btn.isEnabled() is True


def test_confirmar_materias_mostra_conteudo_agrupado_por_materia():
    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)
    widget._on_confirmar_materias_clicked()

    assert widget.conteudo_container.isHidden() is False
    materias_com_checkbox = {materia for materia, _conteudo in widget._conteudo_checks}
    assert materias_com_checkbox == {"Física"}


def test_mudar_materia_depois_de_confirmar_esconde_conteudo_de_novo():
    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)
    widget._on_confirmar_materias_clicked()
    assert widget.conteudo_container.isHidden() is False

    widget._materia_checks["Biologia"].setChecked(True)

    assert widget.conteudo_container.isHidden() is True
    assert widget._materias_confirmadas is False


def test_selecionar_todas_as_materias_marca_tudo():
    widget = QuizWidget()
    widget.materia_select_all_cb.setChecked(True)
    assert all(cb.isChecked() for cb in widget._materia_checks.values())

    widget.materia_select_all_cb.setChecked(False)
    assert not any(cb.isChecked() for cb in widget._materia_checks.values())


def test_marcar_manualmente_todas_as_materias_marca_selecionar_todas():
    widget = QuizWidget()
    for cb in widget._materia_checks.values():
        cb.setChecked(True)
    assert widget.materia_select_all_cb.isChecked() is True

    next(iter(widget._materia_checks.values())).setChecked(False)
    assert widget.materia_select_all_cb.isChecked() is False


def test_selecao_de_conteudo_persiste_ao_marcar_outra_materia_e_reconfirmar():
    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)
    widget._on_confirmar_materias_clicked()
    conteudo_fisica = next(c for (m, c) in widget._conteudo_checks if m == "Física")
    widget._conteudo_checks[("Física", conteudo_fisica)].setChecked(True)

    widget._materia_checks["Biologia"].setChecked(True)  # invalida a confirmação
    widget._on_confirmar_materias_clicked()  # reconfirma com Física + Biologia

    assert widget._conteudo_checks[("Física", conteudo_fisica)].isChecked() is True


def test_desmarcar_materia_remove_seus_conteudos_marcados():
    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)
    widget._on_confirmar_materias_clicked()
    conteudo_fisica = next(c for (m, c) in widget._conteudo_checks if m == "Física")
    widget._conteudo_checks[("Física", conteudo_fisica)].setChecked(True)

    widget._materia_checks["Física"].setChecked(False)

    assert ("Física", conteudo_fisica) not in widget._conteudo_checks


def test_filtros_marcar_materia_conteudo_de_outra_materia_fica_irrestrito():
    """Regressão do bug real encontrado ao testar: marcar Física + Biologia
    e só o conteúdo de Física excluía TODAS as questões de Biologia (o
    filtro de conteúdo era um set achatado, aplicado globalmente pra
    qualquer matéria). Biologia, sem conteúdo próprio marcado, precisa
    continuar irrestrita."""
    import quiz

    widget = QuizWidget()
    widget._materia_checks["Física"].setChecked(True)
    widget._materia_checks["Biologia"].setChecked(True)
    widget._on_confirmar_materias_clicked()
    conteudo_fisica = next(c for (m, c) in widget._conteudo_checks if m == "Física")
    widget._conteudo_checks[("Física", conteudo_fisica)].setChecked(True)

    filtros = widget._current_filters()
    assert filtros["conteudo"] == {"Física": {conteudo_fisica}}

    total = quiz.count_questions(**filtros)
    esperado = (
        quiz.count_questions(materia="Física", conteudo=conteudo_fisica)
        + quiz.count_questions(materia="Biologia")
    )
    assert total == esperado


def test_current_filters_sem_nenhuma_marcacao_e_tudo_none():
    widget = QuizWidget()
    filtros = widget._current_filters()
    assert filtros == {"materia": None, "conteudo": None, "vestibular": None, "ano": None}
