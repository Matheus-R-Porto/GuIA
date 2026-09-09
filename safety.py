import re
import unicodedata

# safety.py — rede determinística contra pedidos inequívocos de má-fé OU de dano.
# NÃO é a defesa principal: a defesa real é o modelo (system prompt), que entende
# intenção e cobre o dual-use (estudar um tema sensível é OK; pedir dano não é).
# Aqui só pegamos casos claros: má-fé educacional, conteúdo nocivo (violência,
# drogas, crimes, sexual/menores) e automutilação (com resposta acolhedora).

# --- Normalização agressiva (anti-ofuscação) ---

# Homóglifos cirílicos/gregos comuns -> Latim. O português não usa esses
# alfabetos, então o folding não afeta texto legítimo, mas derruba o ataque
# de "letras parecidas" (ex: 'іgnore' com 'i' cirílico).
_HOMOGLYPHS = {
    # Cirílico minúsculo
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "к": "k", "м": "m", "н": "h", "т": "t",
    "в": "b", "д": "d", "л": "l", "г": "r", "и": "u", "п": "n", "ԁ": "d",
    "һ": "h",
    # Grego minúsculo
    "α": "a", "ο": "o", "ε": "e", "ρ": "p", "ν": "v", "τ": "t", "ι": "i",
    "κ": "k", "χ": "x", "γ": "y", "η": "n", "μ": "u", "ϲ": "c", "υ": "u",
}
_HOMOGLYPH_MAP = {ord(k): v for k, v in _HOMOGLYPHS.items()}

# Leet -> letras. Atenção: roda só sobre a cópia normalizada usada para o
# filtro; o texto original enviado ao modelo nunca é alterado.
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g", "@": "a", "$": "s",
    "!": "i", "|": "i",
})


def _normalize(text: str) -> str:
    # 1. minúsculas + decomposição compatível (NFKD pega fullwidth, superscritos…)
    base = unicodedata.normalize("NFKD", text.strip().lower())
    # 2. remove acentos (Mn) e caracteres invisíveis/formatação (Cf: zero-width,
    #    soft hyphen, etc.) — usados para "quebrar" palavras no meio
    limpo = "".join(
        ch for ch in base if unicodedata.category(ch) not in ("Mn", "Cf")
    )
    # 3. folding de homóglifos cirílico/grego -> latim
    sem_homoglifo = limpo.translate(_HOMOGLYPH_MAP)
    # 4. leet -> letras
    sem_leet = sem_homoglifo.translate(_LEET_MAP)
    # 5. colapsa espaços em branco antes de juntar letras isoladas
    espacos = re.sub(r"\s+", " ", sem_leet)
    # 6. junta letras isoladas por espaço OU pontuação — cobre o copy-paste clássico:
    #    "i g n o r e", "i.g.n.o.r.e", "i-g-n-o-r-e", "i_g_n_o_r_e" -> "ignore"
    #    (exige 3+ letras isoladas para não colapsar fragmentos legítimos como "e a")
    return re.sub(
        r"(?:[a-z0-9][ ._*\-]+){2,}[a-z0-9]\b",
        lambda m: re.sub(r"[ ._*\-]", "", m.group(0)),
        espacos,
    )


# Prefixo compartilhado pelos padrões de dano real que começam com "como
# <verbo>": cobre não só "como fazer X" mas a paráfrase igualmente comum
# "como eu faço/posso/consigo para fazer X" (bypass real encontrado em
# revisão externa — o "como" + verbo direto não cobria essa forma).
_HOW_PREFIX = r"\bcomo\s+(?:(?:eu\s+)?(?:faco|faço|posso|consigo|devo)\s+(?:pra|para)\s+)?"

_SELF_HARM_PATTERNS = {
    r"\bcomo\b.{0,20}\b(me|se)\s+(matar|suicidar|cortar|enforcar|envenenar|machucar)\b",
    _HOW_PREFIX + r"(cometer|cometo|fazer)\s+(um\s+)?suicidio\b",
    r"\b(quero|vou|penso\s+em|pensando\s+em|estou\s+pensando\s+em)\s+(me\s+)?(matar|suicidar)\b",
    r"\b(tirar|acabar\s+com|por\s+fim|dar\s+fim)\s+.{0,8}\b(minha|propria)\s+vida\b",
    r"\bnao\s+(quero|aguento)\s+mais\s+viver\b",
    r"\bmetodos?\s+(de|para)\s+(suicidio|me\s+matar)\b",
    r"\bme\s+suicidar\b",
    r"\bquero\s+morrer\b",
    r"\b(sumir|desaparecer)\s+(de\s+vez|pra\s+sempre|para\s+sempre|do\s+mundo)\b",
}   # resposta acolhedora + CVV 188
_HARM_PATTERNS = {
    # Violência / armas / explosivos
    _HOW_PREFIX + r"(fazer|faco|faz|construir|montar|fabricar|produzir|criar)\b.{0,25}\b(bomba|explosivo|coquetel\s+molotov|arma\s+de\s+fogo)\b",
    _HOW_PREFIX + r"(matar|assassinar|envenenar|esfaquear|agredir|espancar|sequestrar|torturar)\s+(alguem|uma\s+pessoa|pessoas|meu\s+|minha\s+|o\s+meu\b|a\s+minha\b)",
    # Drogas (síntese / obtenção / tráfico)
    _HOW_PREFIX + r"(fazer|sintetizar|produzir|fabricar|cultivar|plantar|cozinhar)\b.{0,20}\b(droga|drogas|cocaina|maconha|metanfetamina|crack|lsd|ecstasy|heroina)\b",
    _HOW_PREFIX + r"(comprar|conseguir|vender|traficar)\b.{0,15}\b(droga|drogas|cocaina|maconha|crack|lsd|ecstasy|heroina)\b",
    # Crimes / fraude / invasão
    _HOW_PREFIX + r"(invadir|hackear|hackiar|haquear)\b.{0,25}\b(conta|celular|computador|sistema|wi-?fi|rede|instagram|whatsapp|facebook|e-?mail|senha)\b",
    _HOW_PREFIX + r"(roubar|furtar|clonar)\b.{0,15}\b(cartao|cartoes|senha|conta|contas|dados|dinheiro|carro)\b",
    _HOW_PREFIX + r"(fazer|cometer|aplicar|dar)\s+(uma\s+|um\s+)?(fraude|golpe|estelionato)\b",
    _HOW_PREFIX + r"falsificar\b.{0,15}\b(documento|assinatura|diploma|carteira|identidade|nota\s+fiscal)\b",
}        # violência, drogas, crimes
_ADULT_PATTERNS = {
    r"\bconteudo\s*[\+\s]*(18|i8|ib)\b",
    r"\bcena\s+(adulta|erotica|sexual|picante|safada)\b",
    r"\bhistoria\s+erotica\b",
    r"\bfinja\s+(ser|que\s+e)\s+(minha?\s*)?(namorad[ao]|parceiro[a]?|amant[ae])\b",
    r"\baja\s+como\s+(minha?\s*)?(namorad[ao]|parceiro[a]?|amant[ae])\b",
    r"\bseja\s+meu\s+(namorad[ao]|amigo\s+virtual)\b",
    r"\bfala[r]?\s+(coisas?\s+)?(safad[ao]s?|eroticas?|sujas?)\b",
    r"\bme\s+seduz\b",
    r"\broleplay\s+(sexual|adulto|erotico)\b",
    # Proteção infantil: produção de conteúdo sexual envolvendo menores.
    # Exige verbo de produção para não bloquear "educação sexual para adolescentes".
    r"\b(escrev[ae]|conte|descrev[ae]|faca|crie|gere)\b.{0,30}\b(sexo|sexual|erotic[ao]|pornografic[ao]|nudes?|pelad[ao]s?)\b.{0,25}\b(crianca|criancas|menor|menores|adolescente|infantil)\b",
}       # conteúdo +18
_OTHER_PATTERNS = (r"\bignore\b(?:\s+\w+){0,3}\s+(regras|instrucoes|diretrizes|anteriores|acima|instructions|prompts?)\b",
    r"\bdesconsidere\b(?:\s+\w+){0,3}\s+(regras|instrucoes|diretrizes|anteriores|acima)\b",
    r"\besquec[ae]\b.{0,20}\b(regras|instrucoes|diretrizes)\b",
    r"\bdeveloper\s+mode\b",
    r"\bmodo\s+(desenvolvedor|dev|deus|livre|irrestrito)\b",
    r"\bjailbreak\b",
    r"\bsem\s+(restricoes|filtros|regras|censura|moderacao|limitacoes)\b",
    r"\bvoce\s+agora\s+e\s+(um\s+)?(gpt|chatgpt|ia\s+sem|assistente\s+sem|modelo\s+sem|sistema\s+sem)\b",
    r"\bfinja\s+que\s+voce\s+(nao\s+tem|e\s+outro|e\s+um\s+modelo)\b",
    r"\baja\s+como\s+(se\s+voce\s+(nao|fosse)|um\s+(modelo|sistema|gpt|chatgpt|ia)\s+sem)\b",
    r"\bdesative\s+o\s+modo\b",
    r"\bsystem\s+prompt\b",
    r"\bprompt\s+de\s+sistema\b",
    r"\b(seu|teu)\s+(system\s+)?prompt\b",
    r"\bmostre\s+(suas\s+)?instrucoes\b",
    # extração de prompt: verbo + possessivo ("traduza/repita suas instruções/regras")
    r"\b(mostre|traduza|repita|revele|imprima|liste|exiba|copie)\s+(suas?|seu)\s+(instrucoes|regras|prompt|diretrizes|configuracoes)\b",
    r"\bdo\s+anything\s+now\b",
    # Pedido explícito de resposta
    r"\bme\s+(manda|passa|da|diga|fala|mostra|entrega|envia)\s+(so\s+)?a\s+resposta\b",
    r"\bso\s+a\s+resposta\b",
    r"\bresposta\s+pronta\b",
    r"\bpronto\s+para\s+copiar\b",
    # Gabarito: só má-fé explícita (pedir/exigir), não menção legítima
    r"\b(me\s+)?(da|passa|manda|diga|envia|entrega|mostra)\s+(o\s+|os\s+)?gabaritos?\b",
    r"\bqual\s+(e\s+|eh\s+)?(o\s+)?gabaritos?\b",
    r"\bgabaritos?\s+(completo|pronto|da\s+prova|das\s+questoes)\b",
    r"\bresolva\s+tudo\b",
    r"\bresponda\s+tudo\b",
    r"\bresponda\s+todas\s+as\s+questoes\b",
    # Inglês (preguiçoso / inequívoco)
    r"\b(give|tell)\s+me\s+the\s+answer\b",
    r"\bdo\s+my\s+homework\b",
    r"\bwrite\s+my\s+(essay|homework|paper)\b",
    # Automação acadêmica explícita
    r"\bescrev[ae]\s+(minha|a)\s+redacao\b",
    r"\bme\s+escrev[ae]\s+(uma|a)\s+redacao\b",
    r"\bescrev[ae]\s+uma\s+redacao\b",
    r"\bescrev[ae]\s+(um|uma|o|a|meu|minha)\s+(texto|dissertacao|ensaio|resumo|relatorio|trabalho)\b",
    r"\b(faca|faz)\s+(meu|o)\s+trabalho\b",
    r"\bburlar\s+(o\s+)?detector\b",
    r"\bpassar\s+no\s+detector\b",
    r"\bhumanizar\b.*\bdetector\b",)       # jailbreak, cola, automação

_BLOCKED_RESPONSE = (
    "Não consigo fazer isso. "
    "Estou aqui para te ajudar a aprender, não para substituir seu esforço. "
    "Se tiver uma dúvida específica, pode me perguntar."
)

_BLOCKED_RESPONSE_18 = (
    "Não consigo fazer isso. "
    "Sou um tutor educacional e só atendo dúvidas de estudo."
)

_BLOCKED_RESPONSE_HARM = (
    "Não posso ajudar com isso. Não forneço informações que possam causar dano a "
    "você ou a outras pessoas. Se for um tema de estudo, posso te ajudar a "
    "entendê-lo de forma segura."
)

_BLOCKED_RESPONSE_SELF_HARM = (
    "Sinto muito que você esteja passando por isso — e que bom que você falou. "
    "Eu não sou capaz de te ajudar com isso sozinho, mas há pessoas prontas para te "
    "ouvir agora, com carinho e sem julgamento. Ligue para o CVV no 188 (gratuito, "
    "24 horas) ou acesse cvv.org.br. Você não está sozinho."
)

_GROUPS = (
    (_SELF_HARM_PATTERNS, _BLOCKED_RESPONSE_SELF_HARM),
    (_HARM_PATTERNS, _BLOCKED_RESPONSE_HARM),
    (_ADULT_PATTERNS, _BLOCKED_RESPONSE_18),
    (_OTHER_PATTERNS, _BLOCKED_RESPONSE),
)


def _find_block(text: str, mode: str) -> tuple[str | None, str | None]:
    t = _normalize(text)        #anti-ofuscação
    for patterns, response in _GROUPS:
        if mode == "professor" and patterns is _OTHER_PATTERNS:
            continue
        for p in patterns:
            if re.search(p, t):
                return response, p  # bloqueia com resposta adequada + padrão que disparou
    return None, None               # segue para o tutor


def check_safety(text: str, mode: str = "aluno") -> str | None:
    """mode="professor" pula só o grupo de má-fé educacional (_OTHER_PATTERNS
    — "gabarito", "resolva tudo", jailbreak): esses padrões existem para
    proteger o ALUNO de colar, e bloqueariam pedidos legítimos de um
    professor (ex: "monta um gabarito completo dessa prova"). Os grupos de
    dano real (automutilação, violência/drogas/crimes, conteúdo adulto)
    continuam ativos para qualquer um, independente do modo."""
    response, _ = _find_block(text, mode)
    return response


def check_safety_verbose(text: str, mode: str = "aluno") -> tuple[str | None, str | None]:
    """Igual a check_safety, mas também devolve o padrão de regex que disparou
    o bloqueio (ou None se não bloqueou) — usado para registrar o motivo em
    SafetyBlock, dado bruto para a pesquisa do TCC."""
    return _find_block(text, mode)
