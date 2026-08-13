from __future__ import annotations

from typing import Any


async def run_capability_agent(*a, **k) -> Any:
    return {"ok": False, "message": "AI capability agent not available in AstrBot shim"}
