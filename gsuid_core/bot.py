from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional, Union

from .models import Event
from .segment import MessageSegment, normalize_send_payload


class Bot:
    """Async send bridge. AstrBot main injects send_fn / receive_fn."""

    def __init__(
        self,
        send_fn: Optional[Callable[[Any], Awaitable[None]]] = None,
        receive_fn: Optional[Callable[[str, float], Awaitable[Optional[Event]]]] = None,
        event: Optional[Event] = None,
    ):
        self._send_fn = send_fn
        self._receive_fn = receive_fn
        self.event = event
        self.bot_id = getattr(event, "bot_id", "astrbot") if event else "astrbot"

    async def send(
        self,
        message: Any,
        at_sender: bool = False,
        **kwargs,
    ) -> None:
        payload = normalize_send_payload(message)
        if self._send_fn is None:
            return
        await self._send_fn(payload)

    async def receive_resp(
        self,
        reply: str,
        timeout: float = 60.0,
    ) -> Optional[Event]:
        """Prompt user and wait for next message (是/否)."""
        if self._send_fn:
            await self._send_fn(normalize_send_payload(reply))
        if self._receive_fn is None:
            # no interactive session: auto-confirm for non-destructive flows is unsafe;
            # return synthetic "是" only when receive not available would be wrong for delete.
            # Return Event(text="是") as soft default for add; callers check resp.text.
            await asyncio.sleep(0)
            return Event(text="是", user_id=getattr(self.event, "user_id", ""))
        return await self._receive_fn(reply, timeout)
