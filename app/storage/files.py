import json
import uuid
from pathlib import Path

from fastapi import UploadFile

BASE_DIR = Path("storage")
UPLOADS_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
DEMO_DIR = BASE_DIR / "demo"

for folder in (UPLOADS_DIR, RESULTS_DIR, DEMO_DIR):
    folder.mkdir(parents=True, exist_ok=True)


async def save_upload_file(file: UploadFile) -> tuple[str, int]:
    ext = Path(file.filename or "file.bin").suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    target = UPLOADS_DIR / filename

    content = await file.read()
    target.write_bytes(content)
    return str(target), len(content)


def save_json_report(data: dict) -> tuple[str, int]:
    filename = f"{uuid.uuid4().hex}.json"
    target = RESULTS_DIR / filename
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    target.write_bytes(raw)
    return str(target), len(raw)

