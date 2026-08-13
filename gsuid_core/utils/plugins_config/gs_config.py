from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .models import GSC


class StringConfig:
    def __init__(self, name: str, path: Path | str, default: Dict[str, GSC]):
        self.name = name
        self.path = Path(path)
        self.default = default
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._data = {}
        for k, gsc in self.default.items():
            self._data[k] = gsc.default
            gsc.data = gsc.default
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        self._data[k] = v
                        if k in self.default:
                            self.default[k].data = v
            except Exception:
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_config(self, key: str) -> GSC:
        gsc = self.default.get(key)
        if gsc is None:
            g = GSC(key, key, self._data.get(key))
            g.data = self._data.get(key)
            return g
        gsc.data = self._data.get(key, gsc.default)
        return gsc

    def set_config(self, key: str, value: Any) -> None:
        self._data[key] = value
        if key in self.default:
            self.default[key].data = value
        self.save()
