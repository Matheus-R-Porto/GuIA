import json
from pathlib import Path

import quiz

_QUESTOES_PATH = Path(__file__).resolve().parent.parent / "quiz" / "questoes.json"


def test_lista_materias_nao_vazia():
    assert "Matemática" in quiz.list_materias()


def test_lista_vestibulares_nao_vazia():
    assert "UFRGS" in quiz.list_vestibulares()


def test_lista_conteudos_filtra_por_materia():
    conteudos = quiz.list_conteudos("Matemática")
    assert len(conteudos) > 0
    assert quiz.list_conteudos("Matéria inexistente") == []


def test_lista_anos_filtra_por_vestibular():
    assert 2023 in quiz.list_anos("UFRGS")
    assert quiz.list_anos("Vestibular inexistente") == []


def test_count_questions_sem_filtro_conta_tudo():
    assert quiz.count_questions() >= 6


def test_count_questions_com_filtro_zero_quando_nao_ha_match():
    assert quiz.count_questions(vestibular="UFRGS", ano=1999) == 0


def test_get_random_question_respeita_filtro():
    q = quiz.get_random_question(materia="Matemática")
    assert q is not None
    assert q["materia"] == "Matemática"


def test_get_random_question_none_quando_sem_match():
    assert quiz.get_random_question(vestibular="Inexistente") is None


def test_get_random_question_respeita_filtro_de_conteudo():
    conteudo = quiz.list_conteudos("Matemática")[0]
    q = quiz.get_random_question(materia="Matemática", conteudo=conteudo)
    assert q is not None
    assert q["conteudo"] == conteudo


def test_get_random_question_todas_tem_campos_obrigatorios():
    for _ in range(20):
        q = quiz.get_random_question()
        for campo in ("id", "vestibular", "ano", "materia", "conteudo", "detalhe",
                      "enunciado", "alternativas", "resposta_correta", "explicacao"):
            assert campo in q, f"campo '{campo}' ausente em {q.get('id')}"
        assert q["resposta_correta"] in q["alternativas"]


def test_get_random_question_exclude_ids_evita_repetir_enquanto_possivel():
    todos_ids = set()
    for _ in range(50):
        q = quiz.get_random_question(materia="Matemática", exclude_ids=todos_ids)
        todos_ids.add(q["id"])
    # com exclude_ids acumulando, deveria ter percorrido mais de uma questão distinta
    assert len(todos_ids) > 1


def test_image_path_aponta_para_pasta_images():
    caminho = quiz.image_path("exemplo.png")
    assert caminho.parent.name == "images"
    assert caminho.name == "exemplo.png"


def test_todas_as_questoes_com_imagem_tem_arquivo_correspondente():
    """Regressão: uma questão referenciando um arquivo de imagem que não
    existe de verdade quebraria a tela silenciosamente (QPixmap nulo, sem
    erro nenhum) — melhor pegar isso na suíte do que só ao testar na UI."""
    questoes = json.loads(_QUESTOES_PATH.read_text(encoding="utf-8"))
    sem_arquivo = [
        q["id"] for q in questoes
        if q.get("imagem") and not quiz.image_path(q["imagem"]).is_file()
    ]
    assert sem_arquivo == []


# --- seleção múltipla (caixas de marcação na tela de filtros) ---

def test_count_questions_aceita_varias_materias():
    total_separado = quiz.count_questions(materia="Física") + quiz.count_questions(materia="Química")
    total_junto = quiz.count_questions(materia={"Física", "Química"})
    assert total_junto == total_separado


def test_get_random_question_aceita_varias_materias():
    for _ in range(20):
        q = quiz.get_random_question(materia=["Física", "Química"])
        assert q["materia"] in ("Física", "Química")


def test_count_questions_aceita_varios_vestibulares():
    # só existe UFRGS por enquanto, mas a lista de 1 item já confere que o
    # parâmetro aceita coleção sem quebrar (e bate com o valor único).
    assert quiz.count_questions(vestibular=["UFRGS"]) == quiz.count_questions(vestibular="UFRGS")


def test_conteudo_como_dict_restringe_so_a_materia_correspondente():
    """Regressão: ao marcar Física + Biologia na tela, com conteúdo
    restringido só pra Física (Biologia sem nenhum conteúdo próprio
    marcado), Biologia precisa continuar SEM restrição de conteúdo —
    marcar conteúdo de uma matéria não pode excluir silenciosamente outra
    matéria marcada que não teve conteúdo nenhum selecionado."""
    conteudo_fisica = quiz.list_conteudos("Física")[0]
    filtro_dict = {"Física": {conteudo_fisica}}

    total_com_dict = quiz.count_questions(materia={"Física", "Biologia"}, conteudo=filtro_dict)
    esperado = (
        quiz.count_questions(materia="Física", conteudo=conteudo_fisica)
        + quiz.count_questions(materia="Biologia")
    )
    assert total_com_dict == esperado


def test_conteudo_dict_com_materia_sem_entrada_fica_irrestrita():
    q = quiz.get_random_question(materia="Biologia", conteudo={"Física": {"Mecânica"}})
    assert q is not None
    assert q["materia"] == "Biologia"


def test_list_conteudos_agrupados_agrupa_por_materia():
    agrupado = quiz.list_conteudos_agrupados(materias=["Física", "Biologia"])
    assert set(agrupado.keys()) == {"Física", "Biologia"}
    assert agrupado["Física"] == quiz.list_conteudos("Física")
    assert agrupado["Biologia"] == quiz.list_conteudos("Biologia")


def test_list_conteudos_agrupados_sem_filtro_inclui_todas_as_materias():
    agrupado = quiz.list_conteudos_agrupados()
    assert set(agrupado.keys()) == set(quiz.list_materias())
