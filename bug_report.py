"""Report de problema por email — sem credencial nenhuma guardada no app.

O app vai virar um .exe distribuído pros alunos; qualquer senha ou chave de
API embutida no código seria extraível do executável (risco real: alguém
usaria pra mandar spam em nome do Matheus, ou estourar limite de uma API
paga). A alternativa segura, que não depende de nenhum segredo: tentar abrir
o cliente de email PADRÃO do usuário (mailto:) já preenchido — a pessoa que
está reportando revisa e aperta "enviar" ela mesma, o app nunca manda nada
sozinho.

Só que `mailto:` não é garantido: muita gente usa Gmail só pelo navegador,
sem programa de email nenhum configurado como padrão no Windows — nesse
caso o `mailto:` não tem pra onde ir, e o SO só abre o navegador padrão sem
fazer nada útil (confirmado testando de verdade: abriu o Opera GX e parou
por aí). Por isso `REPORT_EMAIL` é exposto aqui também, pra UI sempre
oferecer um jeito confiável de qualquer forma (copiar o texto pronto e
colar manualmente) — ver ui/dialogs/report_bug_dialog.py.
"""
import urllib.parse
import webbrowser

REPORT_EMAIL = "Matheusporto.sg030@academico.ifsul.edu.br"


def open_report_email(subject: str, body: str) -> None:
    """Tentativa best-effort de abrir o cliente de email padrão já
    preenchido. Pode não fazer nada visível (sem cliente de email
    configurado) — por isso nunca é o único caminho oferecido ao usuário."""
    params = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    webbrowser.open(f"mailto:{REPORT_EMAIL}?{params}")


def format_report_text(subject: str, body: str) -> str:
    """Texto pronto pra copiar e colar manualmente num email — o caminho
    garantido de funcionar, independente de o usuário ter ou não um
    cliente de email associado ao mailto: no sistema."""
    return f"Para: {REPORT_EMAIL}\nAssunto: {subject}\n\n{body}"
