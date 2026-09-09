"""Fluxograma GuIA — vertical, sem titulo, centralizado."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors
import math

OUT = r"C:\Users\theuz\PycharmProjects\GuIA\docs\fluxograma_guia.pdf"
PW, PH = landscape(A4)   # 841 x 595

DARK = colors.HexColor('#1e293b')
YF,YS,YT = colors.HexColor('#fef9c3'),colors.HexColor('#ca8a04'),colors.HexColor('#78350f')
RF,RS,RT = colors.HexColor('#fee2e2'),colors.HexColor('#dc2626'),colors.HexColor('#7f1d1d')
BF,BS,BT = colors.HexColor('#dbeafe'),colors.HexColor('#3b82f6'),colors.HexColor('#1e40af')
GF,GS,GT = colors.HexColor('#d1fae5'),colors.HexColor('#059669'),colors.HexColor('#065f46')
GRY = colors.HexColor('#6b7280')
ARR = colors.HexColor('#374151')

cv = rl_canvas.Canvas(OUT, pagesize=landscape(A4))
cv.setFillColor(colors.white)
cv.rect(0, 0, PW, PH, fill=1, stroke=0)

# ── Posições ──────────────────────────────────────────────────────
MX = 400    # coluna principal (centro horizontal)
RX = 630    # coluna direita (branches)
LX = 175    # coluna esquerda (retorno tracejado)

# Ys de cima para baixo
Y0 = 530   # Recebe mensagem
Y1 = 448   # Verifica mensagem?
Y2 = 360   # Aluno sabe algo?
Y3 = 272   # E exata/numerica?
Y4 = 185   # Resposta correta?
Y5 =  95   # Da uma dica

HW, HH = 82, 36   # losango meia-largura / meia-altura
BW, BH = 132, 32  # box largura / altura
OX, OY =  72, 22  # oval rx / ry

# ── Primitivos ────────────────────────────────────────────────────
def _tip(x2, y2, x1, y1, sz=6, c=ARR):
    a = math.atan2(y2 - y1, x2 - x1)
    cv.setFillColor(c); cv.setStrokeColor(c)
    p = cv.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - sz*math.cos(a - .4), y2 - sz*math.sin(a - .4))
    p.lineTo(x2 - sz*math.cos(a + .4), y2 - sz*math.sin(a + .4))
    p.close(); cv.drawPath(p, fill=1, stroke=0)

def solid(pts, lbl=None, lx=None, ly=None):
    cv.setStrokeColor(ARR); cv.setLineWidth(1.1); cv.setDash()
    p = cv.beginPath(); p.moveTo(*pts[0])
    for pt in pts[1:]: p.lineTo(*pt)
    cv.drawPath(p, fill=0, stroke=1)
    _tip(pts[-1][0], pts[-1][1], pts[-2][0], pts[-2][1])
    if lbl:
        cv.setFillColor(GRY); cv.setFont('Helvetica', 6.5)
        cv.drawCentredString(
            lx if lx is not None else (pts[0][0]+pts[1][0])/2,
            ly if ly is not None else (pts[0][1]+pts[1][1])/2 + 6, lbl)

def dash(pts, arrow=True, lbl=None, lx=None, ly=None):
    cv.setStrokeColor(GRY); cv.setLineWidth(1.0); cv.setDash(5, 3)
    p = cv.beginPath(); p.moveTo(*pts[0])
    for pt in pts[1:]: p.lineTo(*pt)
    cv.drawPath(p, fill=0, stroke=1); cv.setDash()
    if arrow:
        _tip(pts[-1][0], pts[-1][1], pts[-2][0], pts[-2][1], c=GRY)
    if lbl:
        cv.setFillColor(GRY); cv.setFont('Helvetica', 6.5)
        cv.drawCentredString(
            lx if lx is not None else (pts[0][0]+pts[1][0])/2,
            ly if ly is not None else (pts[0][1]+pts[1][1])/2 + 6, lbl)

def oval(cx, cy, t1, t2=None):
    cv.setFillColor(DARK)
    cv.ellipse(cx-OX, cy-OY, cx+OX, cy+OY, fill=1, stroke=0)
    cv.setFillColor(colors.white); cv.setFont('Helvetica-Bold', 9)
    if t2:
        cv.drawCentredString(cx, cy + 4, t1)
        cv.drawCentredString(cx, cy - 7, t2)
    else:
        cv.drawCentredString(cx, cy - 3, t1)

def diam(cx, cy, t1, t2, ff, fs, ft):
    cv.setFillColor(ff); cv.setStrokeColor(fs); cv.setLineWidth(1.4)
    p = cv.beginPath()
    p.moveTo(cx, cy+HH); p.lineTo(cx+HW, cy)
    p.lineTo(cx, cy-HH); p.lineTo(cx-HW, cy); p.close()
    cv.drawPath(p, fill=1, stroke=1)
    cv.setFillColor(ft); cv.setFont('Helvetica-Bold', 7.5)
    cv.drawCentredString(cx, cy + 5, t1)
    cv.drawCentredString(cx, cy - 6, t2)

def bx(cx, cy, w, h, t1, t2, ff, fs, ft):
    cv.setFillColor(ff); cv.setStrokeColor(fs); cv.setLineWidth(1.4)
    cv.roundRect(cx-w/2, cy-h/2, w, h, 5, fill=1, stroke=1)
    cv.setFillColor(ft); cv.setFont('Helvetica-Bold', 7.5)
    cv.drawCentredString(cx, cy + 5, t1)
    cv.drawCentredString(cx, cy - 6, t2)

def note(x, y, t, italic=False):
    cv.setFillColor(GRY)
    cv.setFont('Helvetica-Oblique' if italic else 'Helvetica', 6.5)
    cv.drawCentredString(x, y, t)

# ── SETAS (desenhadas antes dos nós) ──────────────────────────────

# -- Fluxo principal, descendo --
solid([(MX, Y0-OY),   (MX, Y1+HH)])
solid([(MX, Y1-HH),   (MX, Y2+HH)], 'OK',  lx=MX+14, ly=(Y1+Y2)/2+5)
solid([(MX, Y2-HH),   (MX, Y3+HH)], 'Sim', lx=MX+14, ly=(Y2+Y3)/2+5)
solid([(MX, Y3-HH),   (MX, Y4+HH)], 'Nao', lx=MX+14, ly=(Y3+Y4)/2+5)
solid([(MX, Y4-HH),   (MX, Y5+BH//2)], 'Nao', lx=MX+14, ly=(Y4+Y5)/2+5)

# -- Branches para a direita --
solid([(MX+HW, Y1), (RX-BW//2, Y1)], 'bloqueia', lx=(MX+HW+RX)/2-5, ly=Y1+8)
solid([(MX+HW, Y2), (RX-BW//2, Y2)], 'Nao',      lx=(MX+HW+RX)/2-5, ly=Y2+8)
solid([(MX+HW, Y3), (RX-BW//2, Y3)], 'Sim',      lx=(MX+HW+RX)/2-5, ly=Y3+8)
solid([(MX+HW, Y4), (RX-BW//2, Y4)], 'Sim',      lx=(MX+HW+RX)/2-5, ly=Y4+8)

# -- Retornos internos (tracejado):
# DIRECAO -> retorna ao nivel EXATA? pelo lado direito
dash([(RX, Y2-BH//2), (RX, Y3), (MX+HW+2, Y3)])

# FERRAMENTA -> retorna ao nivel CORRETA? pelo lado direito
dash([(RX, Y3-BH//2), (RX, Y4), (MX+HW+2, Y4)])

# -- Coluna de retorno ao inicio (lado esquerdo) --
# Ambos DICA e VALIDA se conectam aqui e o fluxo sobe de volta ao START
#   VALIDA: horizontal da esquerda do losango (MX-HW, Y4) ate a coluna (LX, Y4)
#   DICA:   horizontal da esquerda da caixa   (MX-BW/2, Y5) ate a coluna (LX, Y5)
#   Coluna: sobe de Y5 ate Y0 e retorna para START

dash([(MX-HW,    Y4), (LX, Y4)], arrow=False)   # VALIDA -> col esq
dash([(MX-BW//2, Y5), (LX, Y5)], arrow=False)   # DICA   -> col esq

# Coluna esquerda: de baixo (Y5) ate o topo, depois entra no START
dash([(LX, Y5), (LX, Y0), (MX-OX, Y0)], arrow=True)

# Rotulos na coluna esquerda
note(LX - 26, (Y0+Y4)//2 + 14, 'nova')
note(LX - 26, (Y0+Y4)//2 +  3, 'rodada')

# Rotulo no retorno de VALIDA
note((MX-HW+LX)//2, Y4 + 9, 'valida e continua')

# ── NÓS (desenhados por cima das setas) ───────────────────────────

oval(MX, Y0, 'Recebe', 'mensagem')

diam(MX, Y1, 'Verifica', 'mensagem?',        YF, YS, YT)
diam(MX, Y2, 'Aluno sabe', 'algo?',          YF, YS, YT)
diam(MX, Y3, 'E exata/', 'numerica?',        YF, YS, YT)
diam(MX, Y4, 'Resposta', 'correta?',         YF, YS, YT)

bx(RX, Y1, BW, BH, 'Bloqueia ou', 'encerra',       RF, RS, RT)
bx(RX, Y2, BW, BH, 'Da direcao', 'ao aluno',       BF, BS, BT)
bx(RX, Y3, BW, BH, 'Verifica com', 'ferramenta',   GF, GS, GT)
bx(RX, Y4, BW, BH, 'Valida e', 'continua',         BF, BS, BT)
bx(MX, Y5, BW, BH, 'Da uma dica', 'ao aluno',      BF, BS, BT)

cv.save()
print(f'PDF gerado: {OUT}')
