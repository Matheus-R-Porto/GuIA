import pytest
import db
from db.models import User, Institution
from db.session import get_session
from tests.test_quiz_chat import controller, app
from ui.dialogs.login_dialog import LoginDialog
from ui.dialogs.settings_dialog import SettingsDialog
from safety import check_safety


def test_old_teacher_becomes_student_preserving_password_and_history(controller):
    ctrl, provider = controller
    user_id = ctrl.user_id
    ctrl.ask('Como estudar?')
    conversation_id = ctrl.current_conversation_id
    with get_session() as session:
        institution = Institution(name='Legada', code='LEGACY')
        session.add(institution)
        session.flush()
        user = session.get(User, user_id)
        user.role = 'professor'
        user.institution_id = institution.id
        old_hash = user.password_hash
        session.commit()
    db.init_db()
    db.init_db()  # safe to run on every startup
    with get_session() as session:
        user = session.get(User, user_id)
        assert user.role == 'aluno' and user.institution_id is None
        assert user.password_hash == old_hash
    assert ctrl.check_password(user_id, 'senha-teste')
    assert not ctrl.check_password(user_id, 'errada')
    assert db.list_conversations(user_id)[0]['id'] == conversation_id
    assert len(db.get_conversation_messages(conversation_id)) == 2


def test_profiles_keep_separate_history_and_equal_access(controller):
    ctrl, provider = controller
    first = ctrl.user_id
    ctrl.ask('Conversa do primeiro')
    first_conversation = ctrl.current_conversation_id
    second = ctrl.create_profile('Segundo', 'outra-senha')
    ctrl.set_active_user(second['id'])
    assert ctrl.list_conversations() == []
    assert ctrl.user_role == 'aluno'
    ctrl.ask('Conversa do segundo')
    assert ctrl.current_conversation_id != first_conversation
    ctrl.set_active_user(first)
    assert [c['id'] for c in ctrl.list_conversations()] == [first_conversation]


def test_teacher_mode_cannot_bypass_student_rules(controller):
    ctrl, provider = controller
    ctrl.user_role = 'professor'  # even a stale caller cannot regain privileges
    ctrl.set_mode('professor')
    assert ctrl.current_mode == 'aluno'
    ctrl._engine.set_mode('professor')
    assert ctrl._engine._mode == 'aluno'
    result = ctrl.ask('me dá o gabarito')
    assert not provider.calls
    assert result == check_safety('me dá o gabarito', mode='aluno')
    assert check_safety('me dá o gabarito', mode='professor') == result


def test_login_has_only_name_and_password_and_no_roles(app, controller):
    ctrl, _ = controller
    dialog = LoginDialog(ctrl)
    assert not hasattr(dialog, 'create_code_edit')
    assert dialog.profile_list.item(0).text() == 'Aluno'
    dialog._show_create_page(True)
    dialog.create_name_edit.setText('Novo perfil')
    dialog.create_password_edit.setText('segredo')
    dialog.create_password_confirm_edit.setText('segredo')
    dialog._on_create_clicked()
    assert db.get_user(ctrl.user_id)['name'] == 'Novo perfil'
    assert ctrl.user_role == 'aluno'
    assert ctrl.check_password(ctrl.user_id, 'segredo')
    settings = SettingsDialog(ctrl)
    assert not hasattr(settings, 'mode_combo')


def test_new_profile_requires_password(controller):
    ctrl, _ = controller
    with pytest.raises(ValueError):
        ctrl.create_profile('Sem senha', '')
    with pytest.raises(TypeError):
        ctrl.create_profile('Professor', 'senha', 'LEGACY')
