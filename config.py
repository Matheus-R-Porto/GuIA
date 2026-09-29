import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig", override=True)  # override=True: .env sempre tem prioridade sobre env do sistema

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"

# --- Semantic Scholar (Laboratório) ---
# Chave gratuita (Allen Institute for AI) tira o app do pool sem-chave
# compartilhado (congestionado, causa 429 fácil) e passa pro pool dedicado
# (1 req/s). Funciona sem chave também, só com limite mais apertado.
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# --- LM Studio ---
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen/qwen3-vl-4b")

# --- Chat ---
CHAT_LOGS_DIR = Path(__file__).resolve().parent / "chat_logs"
MAX_HISTORY_MESSAGES = 40
MAX_USER_CHARS = 2000
HARD_MAX_INPUT_CHARS = 2400

# --- UI ---
ENABLE_ATTACHMENTS = False
ENABLE_EXPLORE = False
# ENABLE_QUIZ = banco de questões de vestibular — tela "Laboratório"
ENABLE_QUIZ = True

# --- Modo coleta de dados (estudo comparativo) ---
STUDY_MODE = os.getenv("STUDY_MODE", "false").lower() == "true"
STUDY_TEMPERATURE = 0.0
STUDY_FAIL_LOUD = True
