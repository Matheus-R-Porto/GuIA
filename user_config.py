"""Preferências do usuário, persistidas em JSON.

Diferente do .env (segredos de desenvolvimento, ex: chave de API), este arquivo
guarda as escolhas do usuário final — tratamento, tema, etc. Fica em
%APPDATA%/GuIA/config.json (Windows) ou ~/GuIA/config.json.
"""
import json
import os
import sys
from pathlib import Path

_CONFIG_DIR = Path(os.getenv("APPDATA") or Path.home()) / "GuIA"
_CONFIG_PATH = _CONFIG_DIR / "config.json"

# Chaves conhecidas e seus padrões. Crescer aqui conforme novas configs entram.
_DEFAULTS = {
    "user_name": "",           # como o GuIA se refere ao usuário ("" = sem nome)
    "education_level": "",     # "" (auto) | "fundamental" | "medio" | "superior"
    "response_language": "auto",  # "auto" | "pt" | "en" | "es"
    "ui_language": "pt",       # "pt" | "en" | "es" — idioma dos textos da interface (não da IA)
    "font_size": "medium",     # "small" | "medium" | "large"
    "theme": "light",          # "light" ou "dark"
    "accent_color": "#1565C0",  # cor de ênfase (logo, botões, destaques)
    # Chave de API do usuário (opcional). Com os três preenchidos, usa a nuvem
    # como principal; vazio = usa o modelo local grátis (LM Studio).
    "api_base_url": "",     # ex: https://api.groq.com/openai/v1
    "api_key": "",          # chave do usuário (guardada em texto por ora)
    "api_model": "",        # ex: openai/gpt-oss-120b
}


def _load() -> dict:
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**_DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return dict(_DEFAULTS)


_cache = _load()


def get(key: str, default=None):
    if default is None:
        default = _DEFAULTS.get(key)
    return _cache.get(key, default)


def set(key: str, value):
    _cache[key] = value


# Tamanho de fonte (pt) do texto do chat (balões + campo de digitação), por
# nível escolhido em configurações. Ponto único usado pela UI toda.
FONT_SIZES = {"small": 12, "medium": 14, "large": 17}


def chat_font_size() -> int:
    return FONT_SIZES.get(get("font_size", "medium"), FONT_SIZES["medium"])


def save():
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(
            json.dumps(_cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[GuIA] Não foi possível salvar as configurações: {e}", file=sys.stderr)
