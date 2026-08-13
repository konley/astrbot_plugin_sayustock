from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, ClassVar

T_Bind = TypeVar("T_Bind", bound="Bind")
Type = type  # used as Type[T_Bind] in annotations


def _store_path() -> Path:
    from gsuid_core.data_store import get_res_path

    p = get_res_path() / "SayuStock" / "db"
    p.mkdir(parents=True, exist_ok=True)
    return p


class BaseIDModel:
    """Minimal stand-in; not a real SQLModel table."""

    pass


class Bind:
    """JSON-file backed bind store mimicking gsuid Bind API used by SsBind."""

    __tablename__: ClassVar[str] = "bind"
    _lock = threading.Lock()
    # subclass may set field defaults via class attrs; we ignore schema

    @classmethod
    def _file(cls) -> Path:
        return _store_path() / f"{cls.__name__}.json"

    @classmethod
    def _read_all(cls) -> List[Dict[str, Any]]:
        fp = cls._file()
        if not fp.exists():
            return []
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @classmethod
    def _write_all(cls, rows: List[Dict[str, Any]]) -> None:
        fp = cls._file()
        tmp = fp.with_suffix(".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(fp)

    @classmethod
    def get_gameid_name(cls, game_name: Optional[str] = None) -> str:
        return "uid"

    @classmethod
    async def get_uid_list_by_game(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        game_name: Optional[str] = None,
    ) -> Optional[str]:
        with cls._lock:
            for row in cls._read_all():
                if str(row.get("user_id")) == str(user_id) and str(row.get("bot_id")) == str(
                    bot_id
                ):
                    uid = row.get("uid") or ""
                    return uid if uid else None
        return None

    @classmethod
    async def insert_uid(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        uid: str,
        group_id: Optional[str] = None,
        is_digit: bool = False,
        game_name: Optional[str] = None,
        **kwargs,
    ) -> int:
        with cls._lock:
            rows = cls._read_all()
            found = None
            for row in rows:
                if str(row.get("user_id")) == str(user_id) and str(row.get("bot_id")) == str(
                    bot_id
                ):
                    found = row
                    break
            if found is None:
                found = {
                    "user_id": str(user_id),
                    "bot_id": str(bot_id),
                    "uid": str(uid),
                    "group_id": group_id,
                    "push": "off",
                }
                rows.append(found)
            else:
                cur = found.get("uid") or ""
                parts = [p for p in str(cur).split("_") if p]
                if str(uid) not in parts:
                    parts.append(str(uid))
                found["uid"] = "_".join(parts)
                if group_id:
                    found["group_id"] = group_id
            cls._write_all(rows)
        return 0

    @classmethod
    async def update_data(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        **kwargs,
    ) -> None:
        with cls._lock:
            rows = cls._read_all()
            for row in rows:
                if str(row.get("user_id")) == str(user_id) and str(row.get("bot_id")) == str(
                    bot_id
                ):
                    row.update(kwargs)
                    break
            else:
                row = {"user_id": str(user_id), "bot_id": str(bot_id)}
                row.update(kwargs)
                rows.append(row)
            cls._write_all(rows)

    @classmethod
    async def delete_row(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        **kwargs,
    ) -> None:
        with cls._lock:
            rows = [
                r
                for r in cls._read_all()
                if not (
                    str(r.get("user_id")) == str(user_id)
                    and str(r.get("bot_id")) == str(bot_id)
                )
            ]
            cls._write_all(rows)

    @classmethod
    async def get_all_data(cls: Type[T_Bind]) -> List[Dict[str, Any]]:
        with cls._lock:
            return list(cls._read_all())

    @classmethod
    async def delete_uid(
        cls: Type[T_Bind],
        user_id: str,
        bot_id: str,
        uid: str,
        game_name: Optional[str] = None,
    ) -> int:
        # default impl; SsBind overrides
        result = await cls.get_uid_list_by_game(user_id, bot_id, game_name)
        if result is None:
            return -1
        parts = [p for p in str(result).split("_") if p]
        if uid not in parts:
            return -1
        parts.remove(uid)
        if not parts:
            await cls.delete_row(user_id=user_id, bot_id=bot_id)
        else:
            await cls.update_data(user_id, bot_id, uid="_".join(parts))
        return 0
