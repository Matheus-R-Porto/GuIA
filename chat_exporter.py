import json
from datetime import datetime
from pathlib import Path

from config import CHAT_LOGS_DIR


def export_chat(history: list[dict], fmt: str = "txt", model_info: str = "") -> Path:
    CHAT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if fmt == "json":
        path = CHAT_LOGS_DIR / f"chat_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "exported_at": datetime.now().isoformat(),
                    "model_used": model_info,
                    "messages": history,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    else:
        path = CHAT_LOGS_DIR / f"chat_{timestamp}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Chat exportado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            if model_info:
                f.write(f"Modelo(s): {model_info}\n")
            f.write("=" * 60 + "\n\n")
            for msg in history:
                role = "Usuário" if msg["role"] == "user" else "GuIA"
                f.write(f"{role}: {msg['content']}\n\n")

    return path
