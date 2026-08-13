"""Whitelist-group scheduled push for overview / cloudmap / allweather."""
from __future__ import annotations

import asyncio
import logging
from datetime import timezone, timedelta
from typing import Any, Awaitable, Callable, List, Optional

logger = logging.getLogger("sayustock.push")

TZ = timezone(timedelta(hours=8))

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _APS = True
except ImportError:
    _APS = False
    AsyncIOScheduler = None  # type: ignore


def parse_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).replace(",", "\n").replace("，", "\n")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def parse_csv_aliases(raw, default: str = "") -> List[str]:
    text = (raw if raw is not None else default) or default
    return [x.strip() for x in str(text).replace("，", ",").split(",") if x.strip()]


class PushService:
    def __init__(
        self,
        *,
        run_command: Callable[[str], Awaitable[List[Any]]],
        send_to_group: Callable[[str, Any], Awaitable[None]],
    ):
        self._run_command = run_command
        self._send_to_group = send_to_group
        self._sched = None
        self._started = False

    def setup(self, config: dict) -> None:
        self.shutdown()
        if not _APS:
            logger.error("apscheduler not installed")
            return
        if not _cfg_bool(config, "push_enable", False):
            logger.info("push_enable=false, skip scheduler")
            return
        groups = parse_list(config.get("push_whitelist_groups") or config.get("push_groups"))
        if not groups:
            logger.warning("push enabled but whitelist empty")
            return

        self._sched = AsyncIOScheduler(timezone=TZ)
        jobs = [
            ("overview", "push_overview_cron", "大盘概览"),
            ("cloudmap", "push_cloudmap_cron", "大盘云图"),
            ("allweather", "push_allweather_cron", "全天候"),
        ]
        n = 0
        for jid, cron_key, cmd in jobs:
            cron = str(config.get(cron_key) or "").strip()
            if not cron:
                continue
            try:
                trigger = CronTrigger.from_crontab(cron, timezone=TZ)
            except Exception as e:
                logger.error("bad cron %s=%r: %s", cron_key, cron, e)
                continue

            async def _job(command=cmd, gids=list(groups), name=jid):
                await self._execute(command, gids, name)

            self._sched.add_job(
                _job,
                trigger,
                id=f"sayustock_push_{jid}",
                replace_existing=True,
            )
            n += 1
            logger.info("push job %s cron=%s groups=%s", jid, cron, groups)

        if n:
            self._sched.start()
            self._started = True
            logger.info("push scheduler started jobs=%s", n)

    async def _execute(self, command: str, groups: List[str], name: str) -> None:
        logger.info("push fire name=%s cmd=%s", name, command)
        try:
            payloads = await self._run_command(command)
        except Exception as e:
            logger.exception("push run_command fail %s: %s", name, e)
            return
        if not payloads:
            logger.warning("push %s empty result", name)
            return
        for gid in groups:
            for payload in payloads:
                try:
                    await self._send_to_group(gid, payload)
                    await asyncio.sleep(0.4)
                except Exception as e:
                    logger.error("push send gid=%s: %s", gid, e)

    def shutdown(self) -> None:
        if self._sched is not None:
            try:
                self._sched.shutdown(wait=False)
            except Exception:
                pass
            self._sched = None
            self._started = False


def _cfg_bool(config: dict, key: str, default: bool = False) -> bool:
    v = config.get(key, default) if isinstance(config, dict) else default
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)
