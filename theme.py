"""Temas da interface.

Fonte única de estilo: style.qss (tema claro). O tema escuro é derivado dele
trocando cada cor pela equivalente escura — assim não há dois arquivos .qss
para manter em paralelo. Cores compartilhadas por vários elementos viram a
mesma cor escura, o que é aceitável.
"""
import re
from pathlib import Path

_STYLE_PATH = Path(__file__).resolve().parent / "style.qss"

# Cor de ênfase padrão (azul) — usada em dois formatos no style.qss: hex
# exato ("#1565C0", logo/enviar/toggle/texto de botão de menu) e rgba com o
# mesmo RGB ("rgba(21, 101, 192, alpha)", usado nas caixas de alternativa da
# Biblioteca, cards do Laboratório, bordas de foco, etc. — de propósito fora
# do _DARK_MAP, pra ficarem legíveis nos dois temas sem precisar de uma
# variante escura própria). Trocar a cor de ênfase substitui as duas formas.
_DEFAULT_ACCENT_HEX = "#1565C0"
_DEFAULT_ACCENT_RGB = (21, 101, 192)

_DARK_MAP = {
    "#E3F2FD": "#0F1720",  # fundo principal
    "#BBDEFB": "#15212E",  # sidebar
    "#FFFFFF": "#1B2733",  # superfícies (input, balão da IA)
    "#ADD4F2": "#2E5A86",  # balão do usuário
    "#90CAF9": "#2A3B4D",  # bordas / hover estrutural
    "#A9D0F5": "#243446",  # hover do toggle
    "#1565C0": "#5AA2E8",  # acento (logo, enviar, toggle)
    "#0D47A1": "#BBD6F2",  # texto dos botões de menu
    "#37474F": "#E6EDF3",  # título de boas-vindas
    "#546E7A": "#8A9AA8",  # texto suave (rodapé)
    "#6788AB": "#5E7790",  # seta de scroll
    "#2F6FA8": "#7FB0E0",  # seta de scroll (borda ativa)
    "#1F5E97": "#9CC6EE",  # seta de scroll (hover)
    "#B7D7F2": "#324456",  # borda do input
    "#1B2B3A": "#E6EDF3",  # texto do input
    "#B7D8F6": "#2F5070",  # seleção de texto
    "#4B9BDE": "#3E5B74",  # barra de rolagem
    "#2F8ED9": "#5A82A6",  # barra de rolagem (hover)
    "#4E9AD9": "#5AA2E8",  # botão anexar
    "#E3F0FB": "#243446",  # hover anexar (fundo)
    "#C7DDF2": "#324456",  # hover anexar (borda)
    "#D7E7F6": "#243446",  # hover enviar (fundo)
    "#C5DCF1": "#2C3F52",  # enviar pressionado (fundo)
    "#A9C8E6": "#324456",  # enviar pressionado (borda)
    "#90A4AE": "#5E6B75",  # texto desabilitado
    "#7B8A97": "#8A9AA8",  # contador de caracteres
    "#D08A00": "#E0A030",  # aviso
    "#D84C4C": "#E66A6A",  # erro
    "#7FB6E2": "#3A6A98",  # borda do balão do usuário
    "#C3D4E6": "#324456",  # borda do balão da IA
    "#111111": "#E6EDF3",  # texto principal / balão do usuário
    "#1A1A1A": "#E6EDF3",  # texto do balão da IA
    "#64B5F6": "#3E5F82",  # conversa selecionada (fundo)
    "#0D2E5C": "#E6EDF3",  # conversa selecionada (texto)
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _lighten(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(c + (255 - c) * factor) for c in rgb)


def stylesheet(theme: str = "light", accent: str | None = None) -> str:
    qss = _STYLE_PATH.read_text(encoding="utf-8")
    if theme == "dark":
        for light, dark in _DARK_MAP.items():
            qss = qss.replace(light, dark)

    accent = (accent or _DEFAULT_ACCENT_HEX).upper()
    if accent != _DEFAULT_ACCENT_HEX:
        accent_rgb = _hex_to_rgb(accent)
        # A forma hex (logo/enviar/toggle) já foi trocada pela variante
        # escura do azul padrão acima (se theme=="dark") ou continua
        # #1565C0 (se "light") — nos dois casos, é ela que está no texto
        # agora e precisa virar a cor customizada. No escuro, clareamos um
        # pouco pra manter o mesmo contraste que o azul padrão tinha lá.
        hex_alvo = _rgb_to_hex(_lighten(accent_rgb, 0.3) if theme == "dark" else accent_rgb)
        hex_atual = _DARK_MAP[_DEFAULT_ACCENT_HEX] if theme == "dark" else _DEFAULT_ACCENT_HEX
        qss = qss.replace(hex_atual, hex_alvo)

        # A forma rgba(21, 101, 192, alpha) nunca passa pelo _DARK_MAP (de
        # propósito — ver comentário acima), então o RGB original continua
        # intacto em qualquer tema; troca direta pelo RGB da cor escolhida.
        r, g, b = _DEFAULT_ACCENT_RGB
        padrao_rgba = re.compile(rf"rgba\({r},\s*{g},\s*{b},")
        qss = padrao_rgba.sub(f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]},", qss)

    return qss
