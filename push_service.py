"""Whitelist-group scheduled push for overview / cloudmap / allweather."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
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


def split_cron_exprs(raw) -> List[str]:
    text = str(raw or "").replace("；", ";")
    out: List[str] = []
    for chunk in text.split(";"):
        for line in chunk.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def _beijing_now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def is_a_share_push_day(now: Optional[datetime] = None) -> bool:
    now = now or _beijing_now()
    if now.tzinfo is not None:
        now = now.astimezone(TZ).replace(tzinfo=None)
    try:
        from SayuStock.a_share_calendar import is_a_share_trading_day

        return bool(is_a_share_trading_day(now))
    except Exception as e:
        logger.warning("trading calendar unavailable, weekday fallback: %s", e)
        return now.weekday() < 5


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
        # 大盘概览 + 热力图同一 Cron：各渲染一次，再分发到所有群
        jobs: list[tuple[str, str, list[str]]] = [
            ("overview", "push_overview_cron", ["大盘概览", "大盘云图"]),
            ("allweather", "push_allweather_cron", ["全天候"]),
        ]
        extra_hm = str(config.get("push_cloudmap_cron") or "").strip()
        overview_cron = str(config.get("push_overview_cron") or "").strip()
        if extra_hm and extra_hm != overview_cron:
            jobs.append(("heatmap_extra", "push_cloudmap_cron", ["大盘云图"]))
        n = 0
        for jid, cron_key, cmds in jobs:
            exprs = split_cron_exprs(config.get(cron_key))
            for idx, cron in enumerate(exprs):
                try:
                    trigger = CronTrigger.from_crontab(cron, timezone=TZ)
                except Exception as e:
                    logger.error("bad cron %s=%r: %s", cron_key, cron, e)
                    continue

                async def _job(commands=list(cmds), gids=list(groups), name=jid):
                    await self._execute(commands, gids, name)

                job_id = f"sayustock_push_{jid}" if len(exprs) == 1 else f"sayustock_push_{jid}_{idx}"
                self._sched.add_job(
                    _job,
                    trigger,
                    id=job_id,
                    replace_existing=True,
                )
                n += 1
                logger.info("push job %s cmds=%s cron=%s groups=%s", job_id, cmds, cron, groups)

        if n:
            self._sched.start()
            self._started = True
            logger.info("push scheduler started jobs=%s", n)

    async def _execute(self, commands: List[str], groups: List[str], name: str) -> None:
        now = _beijing_now()
        if not is_a_share_push_day(now):
            logger.info(
                "push skip name=%s date=%s not A-share trading day",
                name,
                now.strftime("%Y-%m-%d"),
            )
            return
        logger.info("push fire name=%s cmds=%s groups=%s", name, commands, groups)
        payloads: List[Any] = []
        for command in commands:
            try:
                part = await self._run_command(command)
            except Exception as e:
                logger.exception("push run_command fail %s %s: %s", name, command, e)
                continue
            if not part:
                logger.warning("push %s cmd=%s empty", name, command)
                continue
            payloads.extend(part)
            logger.info("push rendered cmd=%s payloads=%s (once, reuse all groups)", command, len(part))
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
