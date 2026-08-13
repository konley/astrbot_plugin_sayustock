from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from gsuid_core.data_store import get_res_path


class Subscribe:
    """Simple subscribe store (session-level)."""

    _lock = threading.Lock()

    def __init__(self, data: Dict[str, Any]):
        self.__dict__.update(data)

    @property
    def extra_message(self) -> Optional[str]:
        return self.__dict__.get("extra_message")

    @extra_message.setter
    def extra_message(self, v: Optional[str]) -> None:
        self.__dict__["extra_message"] = v

    @property
    def group_id(self) -> Optional[str]:
        return self.__dict__.get("group_id")

    async def send(self, message: Any) -> None:
        fn = self.__dict__.get("_send_fn")
        if fn:
            await fn(message)

    @classmethod
    def _file(cls) -> Path:
        p = get_res_path() / "SayuStock" / "db"
        p.mkdir(parents=True, exist_ok=True)
        return p / "Subscribe.json"

    @classmethod
    def _read(cls) -> List[Dict[str, Any]]:
        fp = cls._file()
        if not fp.exists():
            return []
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @classmethod
    def _write(cls, rows: List[Dict[str, Any]]) -> None:
        fp = cls._file()
        tmp = fp.with_suffix(".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(fp)

    @classmethod
    async def update_data_by_data(cls, query: Dict[str, Any], **kwargs) -> None:
        with cls._lock:
            rows = cls._read()
            for row in rows:
                if all(str(row.get(k)) == str(v) for k, v in query.items()):
                    row.update(kwargs)
            cls._write(rows)
