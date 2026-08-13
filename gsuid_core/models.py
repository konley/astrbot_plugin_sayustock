from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Event:
    user_id: str = ""
    bot_id: str = "astrbot"
    group_id: Optional[str] = None
    text: str = ""
    at: Optional[str] = None
    message_type: str = "group"
    raw_text: str = ""
    sender: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)
