from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from ui.widgets.message_bubble import (
    MessageBubble,
    _ideal_bubble_width,
    _insert_break_hints,
    _ZERO_WIDTH_SPACE,
)

# QFontMetrics/QLabel precisam de uma QApplication instanciada (mesmo sem
# mostrar nenhuma janela) — sem isso, travava/pendurava em vez de dar erro
# claro.
_app = QApplication.instance() or QApplication([])
_FONT = QFont("Open Sans", 14)


def test_palavra_longa_sem_espaco_ganha_pontos_de_quebra():
    texto = "a" * 65
    resultado = _insert_break_hints(texto, _FONT, 300)
    assert _ZERO_WIDTH_SPACE in resultado
    assert resultado.replace(_ZERO_WIDTH_SPACE, "") == texto


def test_frase_normal_com_espacos_fica_inalterada():
    texto = "Isso é uma frase normal, com espaços e pontuação."
    assert _insert_break_hints(texto, _FONT, 300) == texto


def test_palavra_curta_nao_ganha_quebra():
    texto = "curta"
    assert _insert_break_hints(texto, _FONT, 300) == texto


def test_preserva_quebras_de_linha_reais():
    texto = "linha um\nlinha dois"
    assert _insert_break_hints(texto, _FONT, 300) == texto


def test_mistura_palavra_longa_e_texto_normal():
    texto = "olha isso: " + "b" * 50 + " e o resto normal"
    resultado = _insert_break_hints(texto, _FONT, 300)
    assert resultado.startswith("olha isso: ")
    assert resultado.endswith(" e o resto normal")
    assert _ZERO_WIDTH_SPACE in resultado


def test_cada_pedaco_cabe_de_verdade_na_largura_pedida():
    """Cada pedaço entre espaços de largura zero precisa caber fisicamente
    na largura disponível (medido pela fonte de verdade)."""
    texto = "x" * 400
    max_width = 300
    resultado = _insert_break_hints(texto, _FONT, max_width)
    metrics = QFontMetrics(_FONT)
    max_px_esperado = max_width - 54 - 4
    pedacos = resultado.split(_ZERO_WIDTH_SPACE)
    assert len(pedacos) > 1
    for pedaco in pedacos:
        assert metrics.horizontalAdvance(pedaco) <= max_px_esperado


def test_folga_nao_cresce_com_a_largura_do_balao():
    """Regressão: a margem de segurança era uma porcentagem (3%) da largura
    — em balões largos isso virava uma folga grande e visível. A folga real
    (limite da busca binária por caractere + margem fixa) não deve crescer
    conforme o balão fica mais largo."""
    metrics = QFontMetrics(_FONT)
    texto = "x" * 2000
    folgas = []
    for max_width in (300, 600, 1200):
        resultado = _insert_break_hints(texto, _FONT, max_width)
        maior_pedaco = max(
            metrics.horizontalAdvance(p) for p in resultado.split(_ZERO_WIDTH_SPACE)
        )
        largura_disponivel = max_width - 54  # só o chrome real, sem folga
        folgas.append(largura_disponivel - maior_pedaco)

    for folga in folgas:
        # limite generoso (não é porcentagem): até ~1 caractere de largura
        # (busca binária pode parar 1 char antes do limite) + margem fixa
        assert 0 <= folga <= 30, f"folga de {folga}px (deveria ser pequena e fixa)"
    # o ponto central da regressão: a folga não pode CRESCER com a largura
    # (a variação observada é só ruído de quantização da busca binária por
    # caractere — nada a ver com escalar proporcionalmente, que produziria
    # uma diferença bem maior, tipo 9px/18px/36px)
    assert max(folgas) - min(folgas) <= 20


def test_bolha_curta_abraca_o_conteudo():
    bubble = MessageBubble("oi", 500, is_user=True)
    # largura exata (min==max, calculada), bem menor que o teto de 500
    assert bubble.label.minimumWidth() == bubble.label.maximumWidth()
    assert bubble.label.maximumWidth() < 100


def test_bolha_com_palavra_gigante_sem_espaco_usa_largura_maxima_cheia():
    """Único caso que deve forçar largura máxima: uma "palavra" única maior
    que o balão inteiro, sem nenhum espaço pra quebrar naturalmente."""
    texto = "asd" * 200
    bubble = MessageBubble(texto, 400, is_user=True)
    assert bubble.label.minimumWidth() == 400
    assert bubble.label.maximumWidth() == 400


def test_bolha_com_frase_normal_longa_NAO_usa_o_teto_inteiro_sem_necessidade():
    """Regressão: uma resposta normal de IA (várias frases, com espaços de
    verdade) não deve ocupar o teto de largura inteiro se um valor menor já
    é suficiente pra quebrar no mesmo número de linhas."""
    texto = ("Oi, Matheus! Parece que sua mensagem ficou confusa. "
             "Sobre qual assunto ou tema você gostaria de estudar ou tirar dúvidas?")
    bubble = MessageBubble(texto, 1300, is_user=False)
    assert bubble.label.minimumWidth() == bubble.label.maximumWidth()
    assert bubble.label.maximumWidth() < 1300


def test_bolha_nao_espreme_texto_em_linhas_curtas_demais():
    """Bug real relatado: uma resposta curta de IA estava quebrando em
    várias linhas bem curtas em vez de usar uma largura razoável — o Qt,
    deixado decidir sozinho, às vezes escolhe uma largura menor do que o
    necessário. A largura calculada com mais espaço disponível deve
    resultar em MENOS linhas (altura menor), não ficar espremida à toa."""
    texto = ("Não entendi a sua mensagem, Matheus. Poderia reformular ou me "
              "dizer sobre qual assunto você gostaria de estudar?")
    altura_estreita = _fake_bubble_height(texto, 300)
    altura_larga = _fake_bubble_height(texto, 1300)
    assert altura_larga < altura_estreita


def _fake_bubble_height(texto, cap):
    largura = _ideal_bubble_width(texto, _FONT, cap)
    metrics = QFontMetrics(_FONT)
    rect = metrics.boundingRect(0, 0, largura - 54, 100000, Qt.TextWordWrap, texto)
    return rect.height()


def test_bolha_usuario_com_frase_normal_longa_tambem_calcula_largura_exata():
    texto = "Essa é uma frase bem normal, com bastante texto e espaços, " * 3
    bubble = MessageBubble(texto, 500, is_user=True)
    assert bubble.label.minimumWidth() == bubble.label.maximumWidth()


def test_set_max_width_recalcula():
    bubble = MessageBubble("oi", 500, is_user=True)
    largura_antes = bubble.label.maximumWidth()
    bubble.set_max_width(300)
    # "oi" continua curto — a largura exata não deveria mudar (o teto
    # mudou, mas o conteúdo continua cabendo com folga em ambos os casos)
    assert bubble.label.maximumWidth() == largura_antes
    assert bubble.label.minimumWidth() == bubble.label.maximumWidth()


def test_clicar_em_copiar_mostra_feedback_temporario():
    texto = "Aqui:\n\n```python\nprint(1)\n```"
    bubble = MessageBubble(texto, 500, is_user=False)
    assert "Copiar" in bubble.label.text() or "Copy" in bubble.label.text()

    bubble._on_link_activated("guia-copy:0")

    assert _app.clipboard().text() == "print(1)"
    assert "Copiado" in bubble.label.text() or "Copied" in bubble.label.text()
    assert bubble._copy_feedback_timer is not None


def test_feedback_de_copiar_volta_ao_texto_original_apos_o_timer():
    texto = "Aqui:\n\n```python\nprint(1)\n```"
    bubble = MessageBubble(texto, 500, is_user=False)
    bubble._on_link_activated("guia-copy:0")

    bubble._restore_copy_link_text()

    assert bubble.label.text() == bubble._rich_html
    assert "Copiado" not in bubble.label.text() and "Copied" not in bubble.label.text()


def test_href_invalido_nao_trava_nem_copia_nada():
    texto = "Aqui:\n\n```python\nprint(1)\n```"
    bubble = MessageBubble(texto, 500, is_user=False)
    _app.clipboard().setText("")

    bubble._on_link_activated("guia-copy:99")  # índice fora da lista
    bubble._on_link_activated("outro-link-qualquer")  # href sem relação

    assert _app.clipboard().text() == ""
