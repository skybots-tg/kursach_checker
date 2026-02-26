from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models_domain import File


BASE_STORAGE_DIR = Path("storage")


class FileStorage:
    """
    Простое файловое хранилище на локальном диске.

    В проде можно заменить на S3 и т.п., не меняя интерфейс.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        BASE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    async def save_bytes(
        self,
        content: bytes,
        original_name: str,
        mime: str,
    ) -> File:
        file_id = uuid.uuid4().hex
        ext = Path(original_name).suffix or ""
        rel_path = Path(file_id[0:2]) / f"{file_id}{ext}"
        abs_path = BASE_STORAGE_DIR / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        with abs_path.open("wb") as f:
            f.write(content)

        file = File(
            storage_path=str(rel_path),
            original_name=original_name,
            mime=mime,
            size=len(content),
        )
        self.session.add(file)
        await self.session.flush()
        return file

    async def save_json(
        self,
        data: dict[str, Any],
        original_name: str = "report.json",
    ) -> File:
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return await self.save_bytes(content, original_name=original_name, mime="application/json")

    def open_file(self, file: File) -> bytes:
        abs_path = BASE_STORAGE_DIR / file.storage_path
        with abs_path.open("rb") as f:
            return f.read()





