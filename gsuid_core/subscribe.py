from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from gsuid_core.data_store import get_res_path
from gsuid_core.models import Event
from gsuid_core.utils.database.models import Subscribe as SubRow


class _SubItem(SubRow):
    pass


class gs_subscribe:
    _lock = threading.Lock()
    _push_fn: Optional[Callable] = None

    @classmethod
    def set_push_fn(cls, fn: Callable) -> None:
        cls._push_fn = fn

    @classmethod
    def _file(cls) -> Path:
        p = get_res_path() / "SayuStock" / "db"
        p.mkdir(parents=True, exist_ok=True)
        return p / "gs_subscribe.json"

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
    async def add_subscribe(
        cls,
        scope: str,
        task_name: str,
        ev: Event,
        extra_message: str = "",
        **kwargs,
    ) -> None:
        with cls._lock:
            rows = cls._read()
            key = {
                "task": task_name,
                "user_id": str(ev.user_id),
                "group_id": str(ev.group_id or ""),
                "bot_id": str(ev.bot_id),
            }
            for row in rows:
                if all(str(row.get(k)) == str(v) for k, v in key.items()):
                    row["extra_message"] = str(extra_message)
                    cls._write(rows)
                    return
            row = dict(key)
            row["extra_message"] = str(extra_message)
            row["scope"] = scope
            rows.append(row)
            cls._write(rows)

    @classmethod
    async def delete_subscribe(cls, scope: str, task_name: str, ev: Event, **kwargs) -> None:
        with cls._lock:
            rows = cls._read()
            uid = str(ev.user_id)
            gid = str(ev.group_id or "")
            rows = [
                r
                for r in rows
                if not (
                    r.get("task") == task_name
                    and str(r.get("user_id")) == uid
                    and str(r.get("group_id") or "") == gid
                )
            ]
            cls._write(rows)

    @classmethod
    async def get_subscribe(cls, task_name: str) -> List[_SubItem]:
        with cls._lock:
            rows = [r for r in cls._read() if r.get("task") == task_name]
        items: List[_SubItem] = []
        for r in rows:
            data = dict(r)
            if cls._push_fn:
                # bind push
                async def _send(msg, _r=r):
                    await cls._push_fn(_r, msg)  # type: ignore

                data["_send_fn"] = _send
            items.append(_SubItem(data))
        return items
