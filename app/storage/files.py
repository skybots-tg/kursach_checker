import json
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

BASE_DIR = Path(__file__).resolve().parents[2] / "storage"
UPLOADS_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
DEMO_DIR = BASE_DIR / "demo"

for folder in (UPLOADS_DIR, RESULTS_DIR, DEMO_DIR):
    folder.mkdir(parents=True, exist_ok=True)


async def save_upload_file(file: UploadFile, *, max_bytes: int = 20 * 1024 * 1024) -> tuple[str, int]:
    ext = Path(file.filename or "file.bin").suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    target = UPLOADS_DIR / filename

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Файл превышает лимит {max_bytes // (1024*1024)} МБ")
    target.write_bytes(content)
    return str(target), len(content)


def save_raw_file(data: bytes, ext: str) -> tuple[str, int]:
    """Save raw bytes to uploads directory. Returns (path, size)."""
    filename = f"{uuid.uuid4().hex}{ext}"
    target = UPLOADS_DIR / filename
    target.write_bytes(data)
    return str(target), len(data)


def save_json_report(data: dict) -> tuple[str, int]:
    filename = f"{uuid.uuid4().hex}.json"
    target = RESULTS_DIR / filename
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    target.write_bytes(raw)
    return str(target), len(raw)


def fixed_output_download_name(input_original_name: str | None, *, max_len: int = 240) -> str:
    """Имя файла для выдачи исправленного DOCX: базовое имя загрузки + «_исправлено» + .docx."""
    raw = (input_original_name or "").strip() or "document"
    stem = Path(Path(raw).name).stem or "document"
    for ch in '<>:"/\\|?*\x00':
        stem = stem.replace(ch, "_")
    stem = stem.strip() or "document"
    tag = "_исправлено"
    ext = ".docx"
    name = f"{stem}{tag}{ext}"
    if len(name) > max_len:
        budget = max(1, max_len - len(tag) - len(ext))
        name = f"{stem[:budget]}{tag}{ext}"
    return name


