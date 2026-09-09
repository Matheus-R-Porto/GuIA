"""Quiz — banco de questões reais de vestibular (ENEM, UFRGS...), exibido
na UI como "Laboratório".

Diferente do tutor: aqui não é socrático, de propósito. O aluno escolhe uma
alternativa (as mesmas da prova original) e recebe feedback imediato —
certo/errado + explicação — sem conduzir por perguntas.

Fase 1 (2026-07-26): questões carregadas de um JSON estático
(`quiz/questoes.json`), curadas à mão a partir de provas reais baixadas
pelo usuário. Sem banco de dados aqui ainda — o volume é pequeno o
suficiente pra não justificar isso agora; se o banco de questões crescer
muito, migrar para SQLite (mesmo padrão do resto do app) é natural.
"""
import json
import random
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent / "questoes.json"
_IMAGES_DIR = Path(__file__).resolve().parent / "images"

_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        with open(_DATA_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def _as_set(valor):
    """Normaliza um filtro que pode chegar como valor único (string/int),
    coleção de valores (lista/set — seleção múltipla via caixas de marcação
    na tela) ou None (sem filtro nessa dimensão). Mantém compatibilidade
    total com o uso antigo (um valor só) e habilita o novo (vários)."""
    if valor is None:
        return None
    if isinstance(valor, (str, int)):
        return {valor}
    resultado = set(valor)
    return resultado or None


def _bate_conteudo(q: dict, conteudo) -> bool:
    """Confere o filtro de conteúdo contra uma questão. Aceita dois
    formatos: um valor único/coleção de valores (aplica GLOBALMENTE, pra
    qualquer matéria — uso antigo, ainda válido) ou um dict
    {matéria: valores} (aplica só à matéria correspondente — usado pela
    tela de filtros quando várias matérias estão marcadas ao mesmo tempo).

    Com o formato de dict, uma matéria marcada sem NENHUM conteúdo seu
    marcado fica sem restrição de conteúdo nenhuma (todas as questões
    daquela matéria valem) — só as matérias que aparecem no dict com pelo
    menos um valor ficam de fato restritas. Sem isso, marcar conteúdo
    específico de uma matéria excluiria silenciosamente TODAS as questões
    de outra matéria marcada mas sem conteúdo próprio selecionado."""
    if conteudo is None:
        return True
    if isinstance(conteudo, dict):
        conteudos_da_materia = _as_set(conteudo.get(q["materia"]))
        return not conteudos_da_materia or q["conteudo"] in conteudos_da_materia
    conteudos = _as_set(conteudo)
    return not conteudos or q["conteudo"] in conteudos


def _filtrar(questoes, materia=None, conteudo=None, vestibular=None, ano=None):
    materias = _as_set(materia)
    vestibulares = _as_set(vestibular)
    anos = _as_set(ano)
    if materias:
        questoes = [q for q in questoes if q["materia"] in materias]
    if vestibulares:
        questoes = [q for q in questoes if q["vestibular"] in vestibulares]
    if anos:
        questoes = [q for q in questoes if q["ano"] in anos]
    if conteudo is not None:
        questoes = [q for q in questoes if _bate_conteudo(q, conteudo)]
    return questoes


def image_path(filename: str) -> Path:
    """Caminho absoluto pra imagem de uma questão (figura recortada da
    prova original) — usado pela UI quando a questão tem q["imagem"]."""
    return _IMAGES_DIR / filename


def list_materias() -> list[str]:
    return sorted({q["materia"] for q in _load()})


def list_conteudos(materia=None) -> list[str]:
    questoes = _load()
    materias = _as_set(materia)
    if materias:
        questoes = [q for q in questoes if q["materia"] in materias]
    return sorted({q["conteudo"] for q in questoes})


def list_conteudos_agrupados(materias=None, vestibulares=None, anos=None) -> dict[str, list[str]]:
    """Como list_conteudos(), mas devolve os conteúdos AGRUPADOS por
    matéria (ex: {"Biologia": [...], "Física": [...]}), em vez de uma
    lista só misturada em ordem alfabética — usado pela tela de filtros
    quando várias matérias estão marcadas ao mesmo tempo, pra cada grupo
    de conteúdo ficar visualmente separado por matéria (pedido explícito:
    a ordem alfabética global não deve misturar conteúdo de matérias
    diferentes, ex. "Fisiologia" de Biologia caindo no meio do alfabeto
    entre dois conteúdos de Física)."""
    questoes = _load()
    materias_set = _as_set(materias)
    vestibulares_set = _as_set(vestibulares)
    anos_set = _as_set(anos)
    if materias_set:
        questoes = [q for q in questoes if q["materia"] in materias_set]
    if vestibulares_set:
        questoes = [q for q in questoes if q["vestibular"] in vestibulares_set]
    if anos_set:
        questoes = [q for q in questoes if q["ano"] in anos_set]

    agrupado: dict[str, set[str]] = {}
    for q in questoes:
        agrupado.setdefault(q["materia"], set()).add(q["conteudo"])
    return {materia: sorted(conteudos) for materia, conteudos in sorted(agrupado.items())}


def list_vestibulares() -> list[str]:
    return sorted({q["vestibular"] for q in _load()})


def list_anos(vestibular=None) -> list[int]:
    questoes = _load()
    vestibulares = _as_set(vestibular)
    if vestibulares:
        questoes = [q for q in questoes if q["vestibular"] in vestibulares]
    return sorted({q["ano"] for q in questoes})


def get_random_question(
    materia=None,
    conteudo=None,
    vestibular=None,
    ano=None,
    exclude_ids: set[str] | None = None,
) -> dict | None:
    """Sorteia uma questão que bate com os filtros informados (None = sem
    filtro nesse campo). materia/vestibular/ano aceitam um valor único, uma
    coleção de valores (seleção múltipla — caixas de marcação na tela) ou
    None. conteudo aceita, além disso, um dict {matéria: valores} pra
    restringir conteúdo só nas matérias que aparecem nele (ver
    _bate_conteudo). exclude_ids evita repetir questão já mostrada na
    mesma sessão, enquanto houver opção; se todas as que batem já foram
    mostradas, volta a sortear entre todas (não trava o usuário sem
    questão)."""
    questoes = _filtrar(_load(), materia, conteudo, vestibular, ano)
    if not questoes:
        return None

    exclude_ids = exclude_ids or set()
    restantes = [q for q in questoes if q["id"] not in exclude_ids]
    pool = restantes or questoes
    return random.choice(pool)


def count_questions(
    materia=None,
    conteudo=None,
    vestibular=None,
    ano=None,
) -> int:
    return len(_filtrar(_load(), materia, conteudo, vestibular, ano))
