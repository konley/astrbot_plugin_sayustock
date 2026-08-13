from __future__ import annotations

from typing import Any, List, Optional


class GSC:
    def __init__(self, title: str = "", desc: str = "", default: Any = None, options: Optional[List] = None):
        self.title = title
        self.desc = desc
        self.default = default
        self.options = options or []
        self.data = default


class GsIntConfig(GSC):
    def __init__(self, title: str, desc: str, default: int = 0, options: Optional[List] = None):
        super().__init__(title, desc, default, options)


class GsStrConfig(GSC):
    def __init__(self, title: str, desc: str, default: str = "", options: Optional[List] = None):
        super().__init__(title, desc, default, options)


class GsBoolConfig(GSC):
    def __init__(self, title: str, desc: str, default: bool = False, options: Optional[List] = None):
        super().__init__(title, desc, default, options)


class GsListConfig(GSC):
    def __init__(self, title: str, desc: str, default: Optional[List] = None, options: Optional[List] = None):
        super().__init__(title, desc, default or [], options)
