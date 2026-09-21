import json
import re
from pathlib import Path

MESSAGES = json.loads((Path(__file__).parent / "assets" / "messages.json").read_text())
REVERSE = {value: key for key, value in MESSAGES.items()}
STATUS = {
    "draft": ("Ready to start", "Готов к запуску"),
    "queued": ("Queued", "В очереди"),
    "running": ("Searching", "Идёт поиск"),
    "paused": ("Paused", "На паузе"),
    "completed": ("Completed", "Завершён"),
    "read": ("Read", "Прочитан"),
    "unavailable": ("Unavailable", "Недоступен"),
    "done": ("Done", "Выполнен"),
    "failed": ("Failed", "Ошибка"),
    "pending": ("Pending", "В очереди"),
    "superseded": ("Superseded", "Заменён новыми критериями"),
}


def translate(value, language="en"):
    text = str(value)
    if text in STATUS:
        return STATUS[text][int(language == "ru")]
    if language == "ru":
        return REVERSE.get(text, text)
    if text in MESSAGES:
        return MESSAGES[text]
    for pattern, replacement in [
        (r"^Источник недоступен: HTTP (\d+)$", r"Source unavailable: HTTP \1"),
        (
            r"^Не удалось проверить robots.txt \(HTTP (\d+)\); источник пропущен$",
            r"Could not check robots.txt (HTTP \1); source skipped",
        ),
    ]:
        if re.search(pattern, text):
            return re.sub(pattern, replacement, text)
    return text
