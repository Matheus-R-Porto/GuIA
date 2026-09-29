import sources
from i18n import t


def test_repeated_requests_use_original_answer():
    history = [dict(role='user', content='Como o sono afeta a memória?'),
               dict(role='assistant', content='O sono contribui para consolidar memórias.'),
               dict(role='user', content=t('sources_request')),
               dict(role='assistant', content='Fontes encontradas')]
    assert sources.latest_exchange(history) == (
        'Como o sono afeta a memória?', 'O sono contribui para consolidar memórias.')
    assert sources.latest_exchange([]) is None


def test_links_only_come_from_search(monkeypatch):
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': [
        dict(title='Sleep and memory', authors='A. Author', year=2020,
             url='https://example.org/paper'),
        dict(title='Invalid', url='javascript:alert(1)'),
    ]})
    response = sources.find_sources('question', 'answer', lambda *a: 'sleep memory')
    assert '[Sleep and memory](https://example.org/paper)' in response
    assert 'javascript:' not in response
    assert t('sources_caveat') in response


def test_no_claim_does_not_search(monkeypatch):
    def unexpected(*a, **kw):
        raise AssertionError('Search should not run')
    monkeypatch.setattr(sources, 'search_articles', unexpected)
    assert sources.find_sources('Oi', 'Olá', lambda *a: 'NONE') == t('sources_no_claim')


def test_search_failures_are_not_confirmation(monkeypatch):
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: None)
    assert sources.find_sources('q', 'a', lambda *a: 'sleep memory') == t('sources_unavailable')
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': []})
    assert sources.find_sources('q', 'a', lambda *a: 'sleep memory') == t('sources_not_found')


def test_metadata_cannot_inject_a_link(monkeypatch):
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': [
        dict(title='[Fake](https://invented.invalid)', authors='<b>Author</b>', year=2020,
             url='https://example.org/paper')
    ]})
    response = sources.find_sources('q', 'a', lambda *a: 'sleep memory')
    assert '[Fake](https://invented.invalid)' not in response
    assert '<b>' not in response


def test_button_preserves_draft_and_busy_state():
    from PySide6.QtWidgets import QApplication
    from ui.widgets import ChatInputPanel, SidebarWidget
    app = QApplication.instance() or QApplication([])
    panel = ChatInputPanel()
    assert not panel.sources_btn.isEnabled()
    panel.input_field.setPlainText('rascunho que deve ficar')
    panel.set_sources_available(True)
    clicked = []
    panel.sourcesRequested.connect(lambda: clicked.append(True))
    panel.sources_btn.click()
    assert clicked == [True]
    assert panel.get_text() == 'rascunho que deve ficar'
    panel.set_busy(True)
    assert not panel.sources_btn.isEnabled()
    panel.set_busy(False)
    assert panel.sources_btn.isEnabled()
    sidebar = SidebarWidget()
    assert not hasattr(sidebar, 'library_btn')


def test_http_links_open_and_local_links_do_not(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QDesktopServices
    from ui.widgets import MessageBubble
    app = QApplication.instance() or QApplication([])
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url.toString()))
    bubble = MessageBubble('fonte', 600, is_user=False)
    bubble._on_link_activated('https://example.org/paper')
    bubble._on_link_activated('file:///C:/private.txt')
    assert opened == ['https://example.org/paper']


def test_sources_persist_and_target_survives_reload(monkeypatch, tmp_path):
    import db.session as session
    import app_controller
    import db

    class Provider:
        def chat(self, messages, system_prompt, max_tokens=800):
            return 'sleep memory' if max_tokens == 100 else 'O sono consolida memórias.'

    monkeypatch.setattr(session, '_engine', None)
    monkeypatch.setattr(session, '_SessionLocal', None)
    monkeypatch.setattr(session, '_DATA_DIR', tmp_path)
    monkeypatch.setattr(session, '_DB_URL', f'sqlite:///{tmp_path / "test.db"}')
    monkeypatch.setattr(app_controller.AppController, '_build_providers', lambda self: [Provider()])
    monkeypatch.setattr(sources, 'search_articles', lambda *a, **kw: {'articles': [
        dict(title='Sleep study', authors='Author', year=2021, url='https://example.org/study')]})
    controller = app_controller.AppController()
    user = controller.create_profile('Teste', 'senha-teste')
    controller.set_active_user(user['id'])
    assert not controller.can_request_sources()
    controller.ask('Como o sono afeta a memória?')
    original = sources.latest_exchange(controller._engine.get_history())
    result = controller.request_sources()
    conversation_id = controller.current_conversation_id
    saved = db.get_conversation_messages(conversation_id)
    assert saved[-1]['content'] == result
    assert len(saved) == 4
    controller._engine.clear_history()
    controller.load_conversation(conversation_id)
    assert sources.latest_exchange(controller._engine.get_history()) == original
    controller.request_sources()
    assert len(db.get_conversation_messages(conversation_id)) == 6
    session._engine.dispose()
