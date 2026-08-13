from __future__ import annotations

from typing import Any, Callable


def ai_tools(*a, **k) -> Callable:
    def deco(fn):
        return fn

    return deco


def ai_entity(*a, **k) -> Callable:
    def deco(fn):
        return fn

    return deco


def ai_alias(*a, **k) -> Callable:
    def deco(fn):
        return fn

    return deco
