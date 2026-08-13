from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Global registry filled at import time
_SV_REGISTRY: List["SV"] = []
_PLUGIN_PREFIXES: Dict[str, List[str]] = {}


def get_plugin_available_prefix(name: str) -> str:
    prefs = _PLUGIN_PREFIXES.get(name) or []
    return prefs[0] if prefs else ""


def Plugins(name: str = "", force_prefix: Optional[List[str]] = None, allow_empty_prefix: bool = True, **kwargs):
    _PLUGIN_PREFIXES[name] = list(force_prefix or [])
    return None


@dataclass
class _Handler:
    kind: str  # fullmatch | command | prefix | regex
    triggers: Tuple[str, ...]
    func: Callable
    block: bool = False
    priority: int = 5
    to_ai: str = ""
    pattern: Optional[re.Pattern] = None


class SV:
    def __init__(
        self,
        name: str = "",
        priority: int = 5,
        pm: int = 3,
        area: str = "ALL",
        **kwargs,
    ):
        self.name = name
        self.priority = priority
        self.pm = pm
        self.area = area  # GROUP / ALL
        self.handlers: List[_Handler] = []
        _SV_REGISTRY.append(self)

    def _reg(self, kind: str, triggers, func, block=False, priority=None, to_ai="", **kw):
        if isinstance(triggers, str):
            triggers = (triggers,)
        h = _Handler(
            kind=kind,
            triggers=tuple(triggers),
            func=func,
            block=block,
            priority=priority if priority is not None else self.priority,
            to_ai=to_ai or "",
            pattern=kw.get("pattern"),
        )
        self.handlers.append(h)
        return func

    def on_fullmatch(self, triggers, block=False, to_ai="", **kw):
        def deco(func):
            return self._reg("fullmatch", triggers, func, block=block, to_ai=to_ai, **kw)

        return deco

    def on_command(self, triggers, block=False, to_ai="", priority=None, **kw):
        def deco(func):
            return self._reg(
                "command", triggers, func, block=block, priority=priority, to_ai=to_ai, **kw
            )

        return deco

    def on_prefix(self, triggers, block=False, to_ai="", **kw):
        def deco(func):
            return self._reg("prefix", triggers, func, block=block, to_ai=to_ai, **kw)

        return deco

    def on_regex(self, pattern, block=False, to_ai="", **kw):
        def deco(func):
            return self._reg(
                "regex",
                (),
                func,
                block=block,
                to_ai=to_ai,
                pattern=re.compile(pattern) if isinstance(pattern, str) else pattern,
                **kw,
            )

        return deco


def iter_handlers() -> List[Tuple[SV, _Handler]]:
    items: List[Tuple[SV, _Handler]] = []
    for sv in _SV_REGISTRY:
        for h in sv.handlers:
            items.append((sv, h))
    items.sort(key=lambda x: x[1].priority)
    return items


def match_message(text: str) -> Optional[Tuple[SV, _Handler, str]]:
    """Return (sv, handler, remaining_text) or None.

    Supports optional prefixes: a / 股票 (force_prefix from Plugins).
    """
    raw = (text or "").strip()
    if not raw:
        return None
    # strip slash
    if raw.startswith(("/", "#")):
        raw = raw.lstrip("/#").strip()

    candidates = [raw]
    # force prefixes from any plugin registration
    prefs: List[str] = []
    for v in _PLUGIN_PREFIXES.values():
        prefs.extend(v)
    if not prefs:
        prefs = ["a", "股票"]
    for p in prefs:
        if raw.startswith(p):
            rest = raw[len(p) :].lstrip()
            if rest:
                candidates.append(rest)

    best = None
    best_score = -1
    for cand in candidates:
        for sv, h in iter_handlers():
            hit, remain, score = _try_match(h, cand)
            if hit and score > best_score:
                best = (sv, h, remain)
                best_score = score
    return best


def _try_match(h: _Handler, text: str) -> Tuple[bool, str, int]:
    t = text
    tl = t.lower()
    if h.kind == "fullmatch":
        for trig in h.triggers:
            if t == trig or tl == trig.lower():
                return True, "", 1000 + len(trig)
        return False, t, -1
    if h.kind == "command":
        # command: trigger as full prefix word
        for trig in h.triggers:
            if t == trig or tl == trig.lower():
                return True, "", 800 + len(trig)
            if t.startswith(trig + " ") or t.startswith(trig + "\n"):
                return True, t[len(trig) :].strip(), 800 + len(trig)
            # also allow no space for CJK
            if t.startswith(trig) and len(t) > len(trig):
                return True, t[len(trig) :].strip(), 700 + len(trig)
        return False, t, -1
    if h.kind == "prefix":
        for trig in h.triggers:
            if t.startswith(trig):
                return True, t[len(trig) :].strip(), 600 + len(trig)
        return False, t, -1
    if h.kind == "regex" and h.pattern:
        m = h.pattern.search(t)
        if m:
            return True, t, 500
        return False, t, -1
    return False, t, -1
