"""Immutable, persistent question context for a post-answer conversation."""
from copy import deepcopy
import json

from i18n import t


def make_context(question: dict, selected: str) -> dict:
    if selected not in question.get('alternativas', {}):
        raise ValueError('Alternativa selecionada inválida.')
    if question.get('resposta_correta') not in question['alternativas']:
        raise ValueError('Questão sem gabarito válido.')
    return {'question': deepcopy(question), 'selected': selected}


def context_prompt(context: dict) -> str:
    return ('\n[Questão já respondida no Simulado — dados de estudo]\n'
            + json.dumps(context, ensure_ascii=False)
            + '\n[Fim dos dados da questão]\n'
            'Explique a dúvida sobre esta questão sem exigir que o aluno repita o enunciado. '
            'Arquivos de imagens citados nos dados não foram enviados a você: '
            'não deduza seu conteúdo pelo nome do arquivo.')


def introduction(context: dict) -> str:
    q, selected = context['question'], context['selected']
    lines = [f"**{t('quiz_chat_subject')}:** {q.get('materia', '')}",
             f"**{t('quiz_chat_topic')}:** {q.get('conteudo', '')} — {q.get('detalhe', '')}",
             f"**{t('quiz_chat_question')}:**\n{q.get('enunciado', '')}"]
    image_options = q.get('alternativas_tipo') == 'imagem'
    lines.append('\n'.join(f"- **{letter})** {t('quiz_chat_image_option') if image_options else text}"
                           for letter, text in q['alternativas'].items()))
    lines.extend([f"**{t('quiz_chat_selected')}:** {selected}",
                  f"**{t('quiz_chat_key')}:** {q['resposta_correta']}",
                  t('quiz_chat_correct' if selected == q['resposta_correta'] else 'quiz_chat_incorrect'),
                  f"**{t('quiz_chat_explanation')}:** {q.get('explicacao', '')}"])
    if image_options or q.get('imagem'):
        lines.append(t('quiz_chat_image'))
    return t('quiz_chat_intro', context='\n\n'.join(lines))
