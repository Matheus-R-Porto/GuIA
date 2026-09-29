from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication

from quiz_chat import make_context, introduction
from ui.widgets.quiz_widget import QuizWidget
from i18n import t


@pytest.fixture
def question():
    return {'id': 'revisao-1', 'vestibular': 'Teste', 'ano': 2026,
            'materia': 'Matemática', 'conteudo': 'Álgebra', 'detalhe': 'Soma',
            'enunciado': 'Quanto é 2 + 2?', 'alternativas': {'A': '4', 'B': '5'},
            'resposta_correta': 'A', 'explicacao': 'Somar duas unidades a duas resulta em quatro.'}


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('selected', ['A', 'B'])
def test_button_only_after_answer_and_carries_snapshot(app, monkeypatch, question, selected):
    import quiz
    monkeypatch.setattr(quiz, 'get_random_question', lambda **kw: deepcopy(question))
    widget = QuizWidget()
    emitted = []
    widget.chatAboutQuestionRequested.connect(lambda q, s: emitted.append((q, s)))
    widget._load_next_question()
    assert widget.discuss_btn.isHidden()
    widget._on_discuss_clicked()
    assert not emitted
    widget._on_alternative_clicked(selected)
    assert not widget.discuss_btn.isHidden()
    assert widget._current_question['id'] == question['id']
    widget.discuss_btn.click()
    assert emitted == [(question, selected)]
    emitted[0][0]['alternativas']['A'] = 'mudou'
    assert widget._current_question['alternativas']['A'] == '4'


def test_back_navigation_restores_selected_answer(app, monkeypatch, question):
    import quiz
    second = {**question, 'id': 'revisao-2'}
    questions = iter([question, second])
    monkeypatch.setattr(quiz, 'get_random_question', lambda **kw: next(questions))
    widget = QuizWidget()
    widget._load_next_question()
    widget._on_alternative_clicked('B')
    widget._on_next_clicked()
    assert widget.discuss_btn.isHidden()
    widget._on_previous_clicked()
    assert not widget.discuss_btn.isHidden()
    assert widget._selected_answer == 'B'
    emitted = []
    widget.chatAboutQuestionRequested.connect(lambda q, s: emitted.append((q['id'], s)))
    widget.discuss_btn.click()
    assert emitted == [('revisao-1', 'B')]


@pytest.fixture
def controller(monkeypatch, tmp_path):
    import db.session as session
    from app_controller import AppController

    class Provider:
        calls = []
        def chat(self, messages, system_prompt, max_tokens=800):
            self.calls.append((deepcopy(messages), system_prompt))
            return 'Vamos examinar a soma.'

    provider = Provider()
    monkeypatch.setattr(session, '_engine', None)
    monkeypatch.setattr(session, '_SessionLocal', None)
    monkeypatch.setattr(session, '_DATA_DIR', tmp_path)
    monkeypatch.setattr(session, '_DB_URL', f'sqlite:///{tmp_path / "quiz.db"}')
    monkeypatch.setattr(AppController, '_build_providers', lambda self: [provider])
    monkeypatch.setattr(AppController, '_auto_export', lambda self: None)
    controller = AppController()
    user = controller.create_profile('Aluno', 'senha-teste')
    controller.set_active_user(user['id'])
    yield controller, provider
    session._engine.dispose()


def test_context_saved_before_first_question_and_restored(controller, question):
    import db
    from app_controller import AppController
    controller, provider = controller
    conversation_id = controller.start_quiz_chat(question, 'B')
    assert not provider.calls  # student chooses what to ask; no automatic paid call
    saved = db.get_conversation_messages(conversation_id)
    assert len(saved) == 1 and saved[0]['role'] == 'assistant'
    assert '2 + 2' in saved[0]['content'] and 'B' in saved[0]['content']
    question['enunciado'] = 'Questão alterada posteriormente'
    # A fresh controller simulates reopening the app.
    restored = AppController()
    restored.set_active_user(controller.user_id)
    restored.load_conversation(conversation_id)
    assert restored.current_mode == 'quiz'
    assert restored.current_quiz['question']['enunciado'] == 'Quanto é 2 + 2?'
    restored.ask('Por que minha resposta está errada?')
    prompt = provider.calls[-1][1]
    assert 'Quanto é 2 + 2?' in prompt
    assert '"selected": "B"' in prompt
    assert 'Matemática' in prompt and 'Somar duas unidades' in prompt
    assert 'nunca entregue a resposta pronta' not in prompt


def test_new_chat_and_switching_conversations_clear_context(controller, question):
    controller, provider = controller
    controller.ask('Explique fotossíntese')
    normal_id = controller.current_conversation_id
    quiz_id = controller.start_quiz_chat(question, 'A')
    controller.load_conversation(normal_id)
    assert controller.current_quiz is None and controller.current_mode == 'aluno'
    controller.ask('Pode detalhar?')
    assert 'Quanto é 2 + 2?' not in provider.calls[-1][1]
    controller.load_conversation(quiz_id)
    controller.new_chat()
    assert controller.current_quiz is None and controller.current_mode == 'aluno'
    assert controller.current_conversation_id is None


def test_window_opens_new_chat_without_advancing_quiz(app, controller, monkeypatch, question):
    import quiz
    from ui.windows.guia_window import GuiAWindow
    controller, provider = controller
    monkeypatch.setattr(quiz, 'get_random_question', lambda **kw: deepcopy(question))
    window = GuiAWindow(controller)
    window.open_quiz()
    window.quiz_widget._load_next_question()
    window.quiz_widget._on_alternative_clicked('B')
    window.quiz_widget.discuss_btn.click()
    app.processEvents()
    assert not window._quiz_open
    assert window.first_message_sent
    assert not window.chat_area.isHidden()
    assert not window.scroll.isHidden()
    assert window.input_panel.get_text() == ''
    assert not window.input_panel.input_field.isReadOnly()
    assert controller.current_quiz['selected'] == 'B'
    assert window.messages_layout.count() == 2  # intro + stretch
    assert not provider.calls
    window.open_quiz()
    assert window.quiz_widget._current_question['id'] == question['id']
    assert window.quiz_widget._selected_answer == 'B'
    window.close()


def test_migration_preserves_existing_conversations():
    from sqlalchemy import create_engine, text, inspect
    from db.session import _migrate_missing_columns
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE conversations (id INTEGER PRIMARY KEY, title TEXT)'))
        conn.execute(text("INSERT INTO conversations VALUES (1, 'Antiga')"))
    _migrate_missing_columns(engine)
    _migrate_missing_columns(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT title, quiz_context FROM conversations')).one() == ('Antiga', '')
    engine.dispose()


def test_image_question_does_not_claim_visual_access(question):
    question['imagem'] = 'figura.png'
    intro = introduction(make_context(question, 'A'))
    assert t('quiz_chat_image') in intro


def test_invalid_answer_rejected(question):
    with pytest.raises(ValueError):
        make_context(question, 'Z')
