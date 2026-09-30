"""A-share session calendar.

Weekends never open. Statutory days off come from the public holiday API
(refreshed daily). Years not published yet fall back to the builtin list.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("sayustock.calendar")
_TZ = timezone(timedelta(hours=8))
_TTL = timedelta(hours=24)
_warned: set[str] = set()

# Weekends are excluded by weekday(). Dates below are SSE closures
# (上证公告〔2025〕45号 for 2026). No 2026 weekend makeup sessions.
A_SHARE_HOLIDAYS = {
    "2025-01-01",
    "2025-01-28",
    "2025-01-29",
    "2025-01-30",
    "2025-01-31",
    "2025-02-03",
    "2025-02-04",
    "2025-02-05",
    "2025-02-06",
    "2025-02-07",
    "2025-04-04",
    "2025-04-05",
    "2025-04-06",
    "2025-05-01",
    "2025-05-02",
    "2025-05-05",
    "2025-05-31",
    "2025-06-02",
    "2025-10-01",
    "2025-10-02",
    "2025-10-03",
    "2025-10-06",
    "2025-10-07",
    "2025-10-08",
    "2026-01-01",
    "2026-01-02",
    "2026-02-16",
    "2026-02-17",
    "2026-02-18",
    "2026-02-19",
    "2026-02-20",
    "2026-02-23",
    "2026-04-06",
    "2026-05-01",
    "2026-05-04",
    "2026-05-05",
    "2026-06-19",
    "2026-09-25",
    "2026-10-01",
    "2026-10-02",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
}


def _cache_file() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "plugins" and (parent.parent / "plugin_data").is_dir():
            folder = parent.parent / "plugin_data" / "astrbot_plugin_sayustock"
            folder.mkdir(parents=True, exist_ok=True)
            return folder / "a_share_calendar_cache.json"
    folder = here.parents[1] / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "a_share_calendar_cache.json"


def _read_cache() -> dict:
    path = _cache_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("calendar cache read fail: %s", e)
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(data: dict) -> None:
    path = _cache_file()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _fresh(cache: dict) -> bool:
    raw = str(cache.get("fetched_at") or "")
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_TZ)
    return datetime.now(_TZ) - ts < _TTL


def _get_json(url: str):
    req = Request(url, headers={"User-Agent": "astrbot-sayustock"})
    try:
        with urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(body)
    except HTTPError as e:
        if e.code == 404:
            return 404, None
        logger.warning("calendar http %s %s", e.code, url)
        return None, None
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        logger.warning("calendar fetch fail %s: %s", url, e)
        return None, None


def _fetch_year(year: int) -> Optional[dict]:
    status, data = _get_json(f"https://api.jiejiariapi.com/v1/holidays/{year}")
    if status == 404:
        return {"published": False, "off": [], "source": "jiejiari"}
    if status == 200 and isinstance(data, dict):
        if not data:
            return {"published": False, "off": [], "source": "jiejiari"}
        off = sorted(
            key for key, row in data.items()
            if isinstance(row, dict) and row.get("isOffDay") is True
        )
        return {"published": bool(off), "off": off, "source": "jiejiari"}

    status, data = _get_json(f"https://timor.tech/api/holiday/year/{year}")
    if status == 200 and isinstance(data, dict):
        holiday = data.get("holiday") or {}
        if not isinstance(holiday, dict) or not holiday:
            return {"published": False, "off": [], "source": "timor"}
        off = sorted(
            row["date"]
            for row in holiday.values()
            if isinstance(row, dict) and row.get("holiday") is True and row.get("date")
        )
        return {"published": bool(off), "off": off, "source": "timor"}
    return None


def ensure_calendar(year: int) -> None:
    years = [int(year), int(year) + 1]
    cache = _read_cache()
    have = cache.get("years") if isinstance(cache.get("years"), dict) else {}
    if _fresh(cache) and all(str(y) in have for y in years):
        return
    merged = dict(have)
    changed = False
    for y in years:
        info = _fetch_year(y)
        if info is None:
            logger.warning("calendar year %s unchanged, fetch failed", y)
            continue
        merged[str(y)] = info
        changed = True
        logger.info(
            "calendar year=%s published=%s off=%s source=%s",
            y,
            info["published"],
            len(info["off"]),
            info["source"],
        )
    if changed:
        _write_cache({"fetched_at": datetime.now(_TZ).isoformat(), "years": merged})


def is_a_share_trading_day(dt: Optional[datetime] = None) -> bool:
    d = dt or datetime.now()
    if d.tzinfo is not None:
        d = d.astimezone(_TZ).replace(tzinfo=None)
    if d.weekday() >= 5:
        return False
    key = d.strftime("%Y-%m-%d")
    year = str(d.year)
    info = (_read_cache().get("years") or {}).get(year)
    if isinstance(info, dict) and info.get("published"):
        return key not in set(info.get("off") or [])
    if year not in _warned:
        _warned.add(year)
        logger.info("calendar %s unpublished, use builtin holidays", year)
    return key not in A_SHARE_HOLIDAYS
