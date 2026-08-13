from __future__ import annotations

import logging

_log = logging.getLogger("SayuStock")


class _Logger:
    def debug(self, msg, *a, **k):
        _log.debug(str(msg), *a, **k)

    def info(self, msg, *a, **k):
        _log.info(str(msg), *a, **k)

    def warning(self, msg, *a, **k):
        _log.warning(str(msg), *a, **k)

    def error(self, msg, *a, **k):
        _log.error(str(msg), *a, **k)

    def exception(self, msg, *a, **k):
        _log.exception(str(msg), *a, **k)

    def success(self, msg, *a, **k):
        _log.info(str(msg), *a, **k)


logger = _Logger()
