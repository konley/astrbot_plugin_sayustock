from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

logger = logging.getLogger("SayuStock.aps")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _APS = True
except ImportError:
    AsyncIOScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore
    _APS = False


class _SchedulerProxy:
    def __init__(self):
        self._sched: Any = None
        self._pending: List[tuple] = []
        self._started = False

    def _ensure(self):
        if not _APS:
            return None
        if self._sched is None:
            self._sched = AsyncIOScheduler(timezone="Asia/Shanghai")
        return self._sched

    def scheduled_job(self, trigger: str = "cron", **trigger_args):
        def deco(func: Callable):
            self._pending.append((func, trigger, trigger_args))
            if self._started:
                self._add(func, trigger, trigger_args)
            return func

        return deco

    def _add(self, func, trigger, trigger_args):
        sch = self._ensure()
        if sch is None:
            logger.warning("apscheduler missing; skip job %s", getattr(func, "__name__", func))
            return
        try:
            if trigger == "cron":
                # APScheduler cron kwargs: hour, minute, day, ...
                sch.add_job(func, CronTrigger(**trigger_args, timezone="Asia/Shanghai"))
            else:
                sch.add_job(func, trigger, **trigger_args)
        except Exception as e:
            logger.error("add job fail %s: %s", func, e)

    def start(self):
        sch = self._ensure()
        if sch is None:
            return
        for item in self._pending:
            self._add(*item)
        if not self._started:
            try:
                sch.start()
                self._started = True
                logger.info("scheduler started jobs=%s", len(self._pending))
            except Exception as e:
                logger.error("scheduler start fail: %s", e)

    def shutdown(self):
        if self._sched is not None:
            try:
                self._sched.shutdown(wait=False)
            except Exception:
                pass
            self._sched = None
            self._started = False


scheduler = _SchedulerProxy()
