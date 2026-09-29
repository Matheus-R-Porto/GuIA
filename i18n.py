"""Tradução da interface (PT/EN/ES).

Cobre só o "chrome" fixo da UI (botões, rótulos, títulos, mensagens de
status) — as respostas da IA no chat NÃO passam por aqui, elas seguem o
idioma configurado em "response_language" (user_config), que é
independente do idioma da interface (esse aqui é "ui_language").

Trocar o idioma da interface exige reiniciar o app: os textos são lidos uma
vez na construção de cada tela, não há retradução em tempo real (decisão de
escopo — refazer o texto de toda tela já aberta dinamicamente não compensa
pro tamanho deste projeto; a tela de configurações avisa isso ao usuário).
"""
import user_config

_STRINGS = {
    'sources_query_failed': {'pt': 'Não consegui preparar a busca a partir da resposta da IA. Tente novamente; a informação ainda não foi verificada.', 'en': 'I could not prepare a search from the AI answer. Try again; the information remains unverified.', 'es': 'No pude preparar una búsqueda a partir de la respuesta de la IA. Inténtalo de nuevo; la información sigue sin verificar.'},
    'sources_provider': {'pt': 'Base consultada: {provider}', 'en': 'Source database: {provider}', 'es': 'Base consultada: {provider}'},
    'sources_status_rate_limited': {'pt': 'limite de consultas atingido', 'en': 'request limit reached', 'es': 'límite de consultas alcanzado'},
    'sources_status_timeout': {'pt': 'demorou demais para responder', 'en': 'response timed out', 'es': 'tardó demasiado en responder'},
    'sources_status_network_error': {'pt': 'falha de conexão', 'en': 'connection failure', 'es': 'fallo de conexión'},
    'sources_status_http_error': {'pt': 'serviço recusou a consulta', 'en': 'service rejected the request', 'es': 'el servicio rechazó la consulta'},
    'sources_status_invalid_response': {'pt': 'resposta do serviço inválida', 'en': 'invalid service response', 'es': 'respuesta del servicio no válida'},
    'sources_status_empty': {'pt': 'nenhum artigo encontrado', 'en': 'no papers found', 'es': 'no se encontraron artículos'},
    'quiz_discuss_button': {'pt': 'Conversar sobre esta questão', 'en': 'Discuss this question', 'es': 'Conversar sobre esta pregunta'},
    'quiz_chat_title': {'pt': 'Simulado — {subject} — {id}', 'en': 'Practice — {subject} — {id}', 'es': 'Simulacro — {subject} — {id}'},
    'quiz_chat_intro': {'pt': '**Vamos conversar sobre esta questão.**\n\n{context}\n\nQual parte você quer entender melhor ou aprofundar?', 'en': '**Let’s discuss this question.**\n\n{context}\n\nWhat would you like to understand better or explore further?', 'es': '**Conversemos sobre esta pregunta.**\n\n{context}\n\n¿Qué parte quieres entender mejor o profundizar?'},
    'quiz_chat_subject': {'pt': 'Matéria', 'en': 'Subject', 'es': 'Materia'},
    'quiz_chat_topic': {'pt': 'Conteúdo', 'en': 'Topic', 'es': 'Tema'},
    'quiz_chat_question': {'pt': 'Enunciado', 'en': 'Question', 'es': 'Enunciado'},
    'quiz_chat_selected': {'pt': 'Sua resposta', 'en': 'Your answer', 'es': 'Tu respuesta'},
    'quiz_chat_key': {'pt': 'Gabarito do Simulado', 'en': 'Practice answer key', 'es': 'Respuesta del simulacro'},
    'quiz_chat_correct': {'pt': 'Você acertou.', 'en': 'You answered correctly.', 'es': 'Acertaste.'},
    'quiz_chat_incorrect': {'pt': 'Sua resposta foi diferente do gabarito.', 'en': 'Your answer differed from the answer key.', 'es': 'Tu respuesta fue diferente de la respuesta correcta.'},
    'quiz_chat_explanation': {'pt': 'Explicação do Simulado', 'en': 'Practice explanation', 'es': 'Explicación del simulacro'},
    'quiz_chat_image': {'pt': 'Esta questão contém imagens que a IA não recebe. Se sua dúvida depender delas, descreva a figura ou a alternativa no chat.', 'en': 'This question contains images that the AI does not receive. If your question depends on them, describe the figure or option in the chat.', 'es': 'Esta pregunta contiene imágenes que la IA no recibe. Si tu duda depende de ellas, describe la figura o la opción en el chat.'},
    'quiz_chat_image_option': {'pt': 'Alternativa em imagem', 'en': 'Image option', 'es': 'Opción en imagen'},
    'sources_button': {'pt': 'Pedir fontes', 'en': 'Request sources', 'es': 'Pedir fuentes'},
    'sources_tooltip': {'pt': 'Buscar artigos relacionados à última resposta da IA.', 'en': 'Find papers related to the latest AI answer.', 'es': 'Buscar artículos relacionados con la última respuesta de la IA.'},
    'sources_request': {'pt': 'Quero fontes para conferir sua última resposta.', 'en': 'I want sources to check your last answer.', 'es': 'Quiero fuentes para comprobar tu última respuesta.'},
    'sources_loading': {'pt': 'Buscando fontes…', 'en': 'Searching for sources…', 'es': 'Buscando fuentes…'},
    'sources_no_answer': {'pt': 'Receba uma resposta da IA antes de pedir fontes.', 'en': 'Get an AI answer before requesting sources.', 'es': 'Recibe una respuesta de la IA antes de pedir fuentes.'},
    'sources_no_claim': {'pt': 'Não identifiquei uma afirmação factual para pesquisar nessa resposta. Peça uma explicação sobre o assunto e tente novamente.', 'en': 'I could not identify a factual claim to search for in that answer. Ask for an explanation of the topic and try again.', 'es': 'No identifiqué una afirmación factual para buscar en esa respuesta. Pide una explicación del tema e inténtalo de nuevo.'},
    'sources_unavailable': {'pt': 'Não consegui consultar as fontes agora. Tente novamente em instantes; a resposta anterior continua sem verificação.', 'en': 'I could not look up sources right now. Try again shortly; the previous answer remains unverified.', 'es': 'No pude consultar las fuentes ahora. Inténtalo de nuevo; la respuesta anterior sigue sin verificar.'},
    'sources_not_found': {'pt': 'Não obtive artigos com links para essa resposta. Isso pode ocorrer por falta de resultados ou falha na busca. Não foi possível confirmar a informação.', 'en': 'I did not obtain papers with links for this answer. There may be no results or the search may have failed. The information could not be confirmed.', 'es': 'No obtuve artículos con enlaces para esta respuesta. Puede que no haya resultados o que la búsqueda haya fallado. No se pudo confirmar la información.'},
    'sources_heading': {'pt': '**Fontes para conferir a resposta**', 'en': '**Sources to check the answer**', 'es': '**Fuentes para comprobar la respuesta**'},
    'sources_caveat': {'pt': 'Estes artigos foram encontrados em uma base bibliográfica após sua solicitação; não são necessariamente as fontes usadas pela IA. São referências relacionadas ao tema, não uma confirmação da resposta. Abra os links e confira se os estudos realmente sustentam a afirmação.', 'en': 'These papers were found in a bibliographic database after your request; they are not necessarily the sources used by the AI. They are related references, not confirmation of the answer. Open the links and check whether the studies actually support the claim.', 'es': 'Estos artículos se encontraron en una base bibliográfica después de tu solicitud; no son necesariamente las fuentes usadas por la IA. Son referencias relacionadas, no una confirmación de la respuesta. Abre los enlaces y comprueba si los estudios respaldan la afirmación.'},
    'sources_query': {'pt': 'Busca utilizada: {query}', 'en': 'Search query: {query}', 'es': 'Búsqueda utilizada: {query}'},
    # --- guia_window.py ---
    "app_window_title": {
        "pt": "GuIA - Tutor Socrático", "en": "GuIA - Socratic Tutor", "es": "GuIA - Tutor Socrático",
    },
    "welcome_default": {
        "pt": "Como GuIA pode te ajudar hoje?", "en": "How can GuIA help you today?",
        "es": "¿Cómo puede ayudarte GuIA hoy?",
    },
    "welcome_article_template": {
        "pt": 'Vamos conversar sobre "{title}"?', "en": 'Shall we talk about "{title}"?',
        "es": '¿Conversamos sobre "{title}"?',
    },
    "delete_conversation_title": {
        "pt": "Excluir conversa", "en": "Delete conversation", "es": "Eliminar conversación",
    },
    "delete_conversation_body": {
        "pt": "Tem certeza que deseja excluir esta conversa? Essa ação não pode ser desfeita.",
        "en": "Are you sure you want to delete this conversation? This action cannot be undone.",
        "es": "¿Seguro que quieres eliminar esta conversación? Esta acción no se puede deshacer.",
    },
    "coming_soon_title": {"pt": "Em breve", "en": "Coming soon", "es": "Próximamente"},
    "coming_soon_projects_body": {
        "pt": "O agrupamento de conversas em projetos ainda não está disponível — chega em uma atualização futura.",
        "en": "Grouping conversations into projects isn't available yet — coming in a future update.",
        "es": "Agrupar conversaciones en proyectos todavía no está disponible — llega en una futura actualización.",
    },
    "message_too_long_title": {
        "pt": "Mensagem muito longa", "en": "Message too long", "es": "Mensaje demasiado largo",
    },
    "message_too_long_body": {
        "pt": "A mensagem excede o limite em {exceeded} caracteres.",
        "en": "The message exceeds the limit by {exceeded} characters.",
        "es": "El mensaje supera el límite en {exceeded} caracteres.",
    },
    "thinking_label": {
        "pt": "GuIA está pensando", "en": "GuIA is thinking", "es": "GuIA está pensando",
    },

    # --- settings_dialog.py ---
    "settings_title": {"pt": "Configurações", "en": "Settings", "es": "Configuración"},
    "settings_name_question": {
        "pt": "Como você quer que o GuIA te chame?", "en": "What would you like GuIA to call you?",
        "es": "¿Cómo quieres que GuIA te llame?",
    },
    "settings_name_placeholder": {
        "pt": "Ex: Matheus (deixe em branco para nenhum)", "en": "E.g.: Matheus (leave blank for none)",
        "es": "Ej: Matheus (deja en blanco para ninguno)",
    },
    "role_aluno": {"pt": "Aluno", "en": "Student", "es": "Estudiante"},
    "settings_level_label": {"pt": "Nível de ensino", "en": "Education level", "es": "Nivel educativo"},
    "option_auto": {"pt": "Automático", "en": "Automatic", "es": "Automático"},
    "level_fundamental": {"pt": "Fundamental", "en": "Elementary", "es": "Primaria"},
    "level_medio": {"pt": "Médio", "en": "High School", "es": "Secundaria"},
    "level_superior": {"pt": "Superior", "en": "College", "es": "Universidad"},
    "settings_response_lang_label": {
        "pt": "Idioma das respostas", "en": "Response language", "es": "Idioma de las respuestas",
    },
    "settings_font_label": {"pt": "Tamanho da fonte", "en": "Font size", "es": "Tamaño de fuente"},
    "font_small": {"pt": "Pequena", "en": "Small", "es": "Pequeña"},
    "font_medium": {"pt": "Média", "en": "Medium", "es": "Mediana"},
    "font_large": {"pt": "Grande", "en": "Large", "es": "Grande"},
    "settings_theme_label": {"pt": "Tema", "en": "Theme", "es": "Tema"},
    "theme_light": {"pt": "Claro", "en": "Light", "es": "Claro"},
    "theme_dark": {"pt": "Escuro", "en": "Dark", "es": "Oscuro"},
    "settings_accent_label": {"pt": "Cor de ênfase", "en": "Accent color", "es": "Color de énfasis"},
    "settings_accent_dialog_title": {
        "pt": "Escolher cor de ênfase", "en": "Choose accent color", "es": "Elegir color de énfasis",
    },
    "settings_ui_language_label": {
        "pt": "Idioma da interface", "en": "Interface language", "es": "Idioma de la interfaz",
    },
    "settings_ui_language_restart_note": {
        "pt": "Reinicie o GuIA para o novo idioma da interface valer.",
        "en": "Restart GuIA for the new interface language to take effect.",
        "es": "Reinicia GuIA para que el nuevo idioma de la interfaz tenga efecto.",
    },
    "settings_api_label": {
        "pt": "IA / Chave de API (opcional — em branco usa o modelo local grátis)",
        "en": "AI / API key (optional — leave blank to use the free local model)",
        "es": "IA / Clave de API (opcional — déjala en blanco para usar el modelo local gratis)",
    },
    "provider_local": {"pt": "Local (grátis)", "en": "Local (free)", "es": "Local (gratis)"},
    "provider_custom": {"pt": "Personalizado", "en": "Custom", "es": "Personalizado"},
    "settings_base_url_placeholder": {
        "pt": "URL base (ex: https://api.groq.com/openai/v1)",
        "en": "Base URL (e.g.: https://api.groq.com/openai/v1)",
        "es": "URL base (ej: https://api.groq.com/openai/v1)",
    },
    "settings_api_key_placeholder": {"pt": "Chave de API", "en": "API key", "es": "Clave de API"},
    "settings_model_placeholder": {
        "pt": "Modelo (ex: openai/gpt-oss-120b)", "en": "Model (e.g.: openai/gpt-oss-120b)",
        "es": "Modelo (ej: openai/gpt-oss-120b)",
    },
    "switch_profile_btn": {"pt": "Trocar perfil", "en": "Switch profile", "es": "Cambiar perfil"},
    "cancel_btn": {"pt": "Cancelar", "en": "Cancel", "es": "Cancelar"},
    "save_btn": {"pt": "Salvar", "en": "Save", "es": "Guardar"},

    # --- login_dialog.py ---
    "login_window_title": {"pt": "Entrar no GuIA", "en": "Log in to GuIA", "es": "Iniciar sesión en GuIA"},
    "login_who_question": {"pt": "Quem está usando o GuIA?", "en": "Who's using GuIA?", "es": "¿Quién está usando GuIA?"},
    "login_create_profile_btn": {"pt": "+ Criar perfil", "en": "+ Create profile", "es": "+ Crear perfil"},
    "login_enter_btn": {"pt": "Entrar", "en": "Log in", "es": "Entrar"},
    "login_new_profile_label": {"pt": "Criar novo perfil", "en": "Create new profile", "es": "Crear nuevo perfil"},
    "login_name_placeholder": {"pt": "Seu nome", "en": "Your name", "es": "Tu nombre"},
    "login_password_placeholder": {"pt": "Senha", "en": "Password", "es": "Contraseña"},
    "login_confirm_password_placeholder": {
        "pt": "Confirmar senha", "en": "Confirm password", "es": "Confirmar contraseña",
    },
    "back_btn": {"pt": "Voltar", "en": "Back", "es": "Volver"},
    "login_create_profile_confirm_btn": {"pt": "Criar perfil", "en": "Create profile", "es": "Crear perfil"},
    "login_error_no_name": {"pt": "Digite um nome.", "en": "Enter a name.", "es": "Escribe un nombre."},
    "login_error_no_password": {"pt": "Digite uma senha.", "en": "Enter a password.", "es": "Escribe una contraseña."},
    "login_error_password_mismatch": {
        "pt": "As senhas não coincidem.", "en": "Passwords don't match.", "es": "Las contraseñas no coinciden.",
    },
    "login_error_wrong_password": {
        "pt": "Senha incorreta.", "en": "Incorrect password.", "es": "Contraseña incorrecta.",
    },
    "login_password_of_template": {
        "pt": "Senha de {name}", "en": "Password for {name}", "es": "Contraseña de {name}",
    },

    # --- sidebar_widget.py ---
    "sidebar_new_chat": {"pt": "Novo Chat", "en": "New Chat", "es": "Nuevo Chat"},
    "sidebar_menu_simulado": {"pt": "Simulado", "en": "Simulation", "es": "Simulado"},
    "sidebar_menu_explorar": {"pt": "Explorar", "en": "Explore", "es": "Explorar"},
    "sidebar_menu_biblioteca": {"pt": "Biblioteca", "en": "Library", "es": "Biblioteca"},
    "context_rename": {"pt": "Renomear", "en": "Rename", "es": "Renombrar"},
    "context_move_to_project": {"pt": "Mover para projeto", "en": "Move to project", "es": "Mover a proyecto"},
    "context_delete": {"pt": "Excluir", "en": "Delete", "es": "Eliminar"},

    # --- chat_input_widget.py ---
    "chat_input_placeholder": {
        "pt": "Pergunte alguma coisa para GuIA", "en": "Ask GuIA something", "es": "Pregúntale algo a GuIA",
    },
    "chars_remaining_template": {
        "pt": "Restam {n} caracteres", "en": "{n} characters left", "es": "Quedan {n} caracteres",
    },
    "chars_hard_limit_tooltip": {
        "pt": "Limite técnico de {n} caracteres atingido.",
        "en": "Technical limit of {n} characters reached.",
        "es": "Se alcanzó el límite técnico de {n} caracteres.",
    },

    # --- library_widget.py (tela "Laboratório", banco de questões) ---
    "library_back_to_filters_tooltip": {
        "pt": "Voltar aos filtros", "en": "Back to filters", "es": "Volver a los filtros",
    },
    "library_next_question_tooltip": {
        "pt": "Próxima questão", "en": "Next question", "es": "Siguiente pregunta",
    },
    "library_previous_question_tooltip": {
        "pt": "Questão anterior", "en": "Previous question", "es": "Pregunta anterior",
    },
    "library_choose_filters_label": {
        "pt": "Marque o que quiser praticar (deixe em branco pra incluir tudo):",
        "en": "Check what you want to practice (leave blank to include everything):",
        "es": "Marca lo que quieras practicar (deja en blanco para incluir todo):",
    },
    "library_subject_label": {"pt": "Matérias", "en": "Subjects", "es": "Materias"},
    "library_select_all": {"pt": "Selecionar todas", "en": "Select all", "es": "Seleccionar todas"},
    "library_confirm_subjects_btn": {
        "pt": "Confirmar matérias", "en": "Confirm subjects", "es": "Confirmar materias",
    },
    "library_content_label": {"pt": "Conteúdo", "en": "Content", "es": "Contenido"},
    "library_content_hint_sem_materia": {
        "pt": "Marque ao menos uma matéria à esquerda pra habilitar o filtro de conteúdo.",
        "en": "Check at least one subject on the left to enable the content filter.",
        "es": "Marca al menos una materia a la izquierda para habilitar el filtro de contenido.",
    },
    "library_content_hint_nao_confirmado": {
        "pt": "Clique em \"Confirmar matérias\" pra escolher o conteúdo específico.",
        "en": "Click \"Confirm subjects\" to choose specific content.",
        "es": "Haz clic en \"Confirmar materias\" para elegir contenido específico.",
    },
    "library_exam_label": {"pt": "Vestibulares", "en": "Exams", "es": "Exámenes de acceso"},
    "library_year_label": {"pt": "Ano", "en": "Year", "es": "Año"},
    "library_start_btn": {"pt": "Começar", "en": "Start", "es": "Empezar"},
    "option_all": {"pt": "Todos", "en": "All", "es": "Todos"},
    "library_no_questions_status": {
        "pt": "Não há questões para essa combinação de filtros ainda.",
        "en": "There are no questions for this filter combination yet.",
        "es": "Todavía no hay preguntas para esta combinación de filtros.",
    },
    "library_no_more_questions_status": {
        "pt": "Não há mais questões para essa combinação de filtros.",
        "en": "There are no more questions for this filter combination.",
        "es": "No hay más preguntas para esta combinación de filtros.",
    },
    "library_correct_feedback_template": {
        "pt": "A alternativa está correta, porque {explicacao}",
        "en": "This option is correct, because {explicacao}",
        "es": "Esta opción es correcta, porque {explicacao}",
    },
    "library_incorrect_feedback_template": {
        "pt": "A alternativa está errada. A correta é a {correta}), porque {explicacao}",
        "en": "This option is wrong. The correct one is {correta}), because {explicacao}",
        "es": "Esta opción es incorrecta. La correcta es la {correta}), porque {explicacao}",
    },

    # --- lab_widget.py (tela "Biblioteca", busca de artigos) ---
    "lang_filter_any": {"pt": "Qualquer idioma", "en": "Any language", "es": "Cualquier idioma"},
    "lang_filter_pt": {"pt": "Português", "en": "Portuguese", "es": "Portugués"},
    "lang_filter_en": {"pt": "Inglês", "en": "English", "es": "Inglés"},
    "lang_filter_es": {"pt": "Espanhol", "en": "Spanish", "es": "Español"},
    "lab_no_abstract_fallback": {
        "pt": "Sem resumo disponível.", "en": "No abstract available.", "es": "Resumen no disponible.",
    },
    "lab_open_site_btn": {"pt": "Abrir no site", "en": "Open on site", "es": "Abrir en el sitio"},
    "lab_chat_about_btn": {
        "pt": "Conversar no chat", "en": "Discuss in chat", "es": "Conversar en el chat",
    },
    "lab_subtitle": {
        "pt": "Busque artigos científicos por palavra-chave", "en": "Search scientific articles by keyword",
        "es": "Busca artículos científicos por palabra clave",
    },
    "lab_search_placeholder": {
        "pt": "Ex: fotossíntese, revolução francesa, aprendizagem baseada em projetos...",
        "en": "E.g.: photosynthesis, French Revolution, project-based learning...",
        "es": "Ej: fotosíntesis, revolución francesa, aprendizaje basado en proyectos...",
    },
    "lab_search_btn": {"pt": "Buscar", "en": "Search", "es": "Buscar"},
    "lab_year_label": {"pt": "Ano:", "en": "Year:", "es": "Año:"},
    "lab_year_until": {"pt": "até", "en": "to", "es": "hasta"},
    "lab_language_label": {"pt": "Idioma:", "en": "Language:", "es": "Idioma:"},
    "lab_searching_status": {"pt": "Buscando…", "en": "Searching…", "es": "Buscando…"},
    "lab_rate_limited_status": {
        "pt": "A busca demorou demais ou a API gratuita está com limite de uso no momento. Espera um pouco e tenta de novo.",
        "en": "The search took too long, or the free API is temporarily rate-limited. Wait a bit and try again.",
        "es": "La búsqueda demoró demasiado o la API gratuita está con límite de uso ahora. Espera un poco e inténtalo de nuevo.",
    },
    "lab_no_results_status": {
        "pt": "Nenhum artigo encontrado — tenta outra palavra-chave ou filtros mais amplos.",
        "en": "No articles found — try another keyword or broader filters.",
        "es": "No se encontraron artículos — prueba otra palabra clave o filtros más amplios.",
    },
    "lab_results_with_lang_filter_template": {
        "pt": "Mostrando {shown} artigo(s) no idioma escolhido (de {total} encontrados no total — filtro de idioma é aproximado).",
        "en": "Showing {shown} article(s) in the chosen language (out of {total} found in total — language filter is approximate).",
        "es": "Mostrando {shown} artículo(s) en el idioma elegido (de {total} encontrados en total — el filtro de idioma es aproximado).",
    },
    "lab_results_count_template": {
        "pt": "{total} artigo(s) encontrado(s).", "en": "{total} article(s) found.",
        "es": "{total} artículo(s) encontrado(s).",
    },

    # --- code_highlighter.py (botão de copiar do bloco de código) ---
    "code_copy_link": {"pt": "⧉ Copiar", "en": "⧉ Copy", "es": "⧉ Copiar"},
    "code_copied_label": {"pt": "✓ Copiado", "en": "✓ Copied", "es": "✓ Copiado"},

    # --- quiz_widget.py (reportar problema numa questão) ---
    "quiz_report_button": {
        "pt": "🐛 Reportar problema", "en": "🐛 Report a problem", "es": "🐛 Reportar un problema",
    },
    "quiz_back_to_filters_btn": {
        "pt": "‹ Filtros", "en": "‹ Filters", "es": "‹ Filtros",
    },
    "quiz_report_email_subject": {
        "pt": "[GuIA] Problema na questão {id}",
        "en": "[GuIA] Problem with question {id}",
        "es": "[GuIA] Problema con la pregunta {id}",
    },
    "quiz_report_email_body": {
        "pt": "Descreva aqui o problema que você encontrou nesta questão:\n\n\n\n"
              "---\nID: {id}\n{vestibular} {ano} — {materia} — {conteudo}: {detalhe}\n"
              "Resposta marcada como correta: {resposta_correta}\n\nEnunciado:\n{enunciado}",
        "en": "Describe the problem you found with this question here:\n\n\n\n"
              "---\nID: {id}\n{vestibular} {ano} — {materia} — {conteudo}: {detalhe}\n"
              "Answer marked as correct: {resposta_correta}\n\nQuestion text:\n{enunciado}",
        "es": "Describe aquí el problema que encontraste en esta pregunta:\n\n\n\n"
              "---\nID: {id}\n{vestibular} {ano} — {materia} — {conteudo}: {detalhe}\n"
              "Respuesta marcada como correcta: {resposta_correta}\n\nEnunciado:\n{enunciado}",
    },

    # --- report_bug_dialog.py (fallback quando mailto: não abre nada) ---
    "report_dialog_title": {"pt": "Reportar problema", "en": "Report a problem", "es": "Reportar un problema"},
    "report_dialog_instructions": {
        "pt": "Tentei abrir seu aplicativo de email — se não abriu (comum se você usa só o "
              "Gmail pelo navegador, sem programa de email instalado), copie o texto abaixo "
              "e cole num email para:\n{email}",
        "en": "I tried opening your email app — if it didn't open (common if you only use "
              "Gmail through the browser, without an installed email program), copy the text "
              "below and paste it into an email to:\n{email}",
        "es": "Intenté abrir tu aplicación de correo — si no se abrió (común si usas solo "
              "Gmail por el navegador, sin programa de correo instalado), copia el texto de "
              "abajo y pégalo en un correo para:\n{email}",
    },
    "report_dialog_copy_btn": {"pt": "Copiar texto", "en": "Copy text", "es": "Copiar texto"},
    "report_dialog_copied_label": {"pt": "✓ Copiado!", "en": "✓ Copied!", "es": "✓ Copiado!"},
    "close_btn": {"pt": "Fechar", "en": "Close", "es": "Cerrar"},
}


def t(key: str, **kwargs) -> str:
    """Traduz `key` pro idioma de interface configurado (user_config
    "ui_language", padrão "pt"). Se `key` não existir no catálogo, devolve a
    própria chave (visível/óbvio de detectar em teste manual, nunca quebra a
    UI). `kwargs` preenche placeholders `{nome}` do template, se houver."""
    lang = user_config.get("ui_language", "pt")
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    texto = entry.get(lang) or entry.get("pt", key)
    return texto.format(**kwargs) if kwargs else texto
