from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, List, Union


@dataclass
class MessageSegment:
    type: str
    data: Any = None

    @staticmethod
    def text(s: str) -> "MessageSegment":
        return MessageSegment("text", str(s))

    @staticmethod
    def image(img: Any) -> "MessageSegment":
        return MessageSegment("image", img)

    @staticmethod
    def at(uid: str) -> "MessageSegment":
        return MessageSegment("at", str(uid))


def normalize_send_payload(message: Any) -> List[MessageSegment]:
    """Normalize bot.send args into a list of MessageSegment."""
    if message is None:
        return [MessageSegment.text("")]
    if isinstance(message, MessageSegment):
        return [message]
    if isinstance(message, (list, tuple)):
        out: List[MessageSegment] = []
        for m in message:
            out.extend(normalize_send_payload(m))
        return out or [MessageSegment.text("")]
    if isinstance(message, (bytes, bytearray)):
        return [MessageSegment.image(bytes(message))]
    if isinstance(message, Path):
        return [MessageSegment.image(str(message))]
    if isinstance(message, BytesIO):
        return [MessageSegment.image(message.getvalue())]
    # PIL Image
    if hasattr(message, "save") and message.__class__.__name__ == "Image":
        buf = BytesIO()
        message.save(buf, format="PNG")
        return [MessageSegment.image(buf.getvalue())]
    if isinstance(message, str):
        # file path to image?
        p = Path(message)
        if p.exists() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            return [MessageSegment.image(str(p))]
        return [MessageSegment.text(message)]
    return [MessageSegment.text(str(message))]
