from __future__ import annotations

from typing import Any, Type


class PageSchema:
    def __init__(self, label: str = "", icon: str = "", **kwargs):
        self.label = label
        self.icon = icon


class GsAdminModel:
    pk_name = "id"
    page_schema = None
    model = None


class _Site:
    def register_admin(self, cls: Type) -> Type:
        return cls


site = _Site()
