"""模拟盘交易日判断工具。

- :func:`is_a_share_trading_day`  判定今天是否是 A 股交易日（拉 1.000001 上证分时）
- :func:`is_trading_time`  判定当前是否在 9:30-11:30 / 13:00-15:00 交易时段
- :func:`next_decision_time`  返回下一个合理决策时间（用于日志和休眠）

缓存：trading_calendar.json 在 data/ 目录，每天 0 点刷新一次即可。
"""

import json
from typing import Tuple, Optional
from datetime import time, datetime, timedelta

from gsuid_core.logger import logger

from ..a_share_calendar import is_a_share_trading_day
from ..utils.resource_path import DATA_PATH

_CALENDAR_CACHE_PATH = DATA_PATH / "papertrade_trading_calendar.json"
_CACHE_TTL_HOURS = 6  # 6 小时内的判断走缓存


def _load_cache() -> dict:
    """读取缓存的交易日历；过期或不存在返回空 dict。"""
    if not _CALENDAR_CACHE_PATH.exists():
        return {}
    try:
        mtime = datetime.fromtimestamp(_CALENDAR_CACHE_PATH.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=_CACHE_TTL_HOURS):
            return {}
        with _CALENDAR_CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"[SayuStock][PaperTrade] 读取交易日历缓存失败: {e}")
        return {}


def _save_cache(cache: dict) -> None:
    """写入缓存（带过期时间戳）"""
    try:
        _CALENDAR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _CALENDAR_CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"[SayuStock][PaperTrade] 写交易日历缓存失败: {e}")


def is_trading_time(dt: Optional[datetime] = None) -> bool:
    """判定当前是否在 A 股交易时段内。

    A 股交易时段：
    - 上午 9:30 - 11:30（含 9:30 集合竞价）
    - 下午 13:00 - 15:00
    """
    d = dt or datetime.now()
    t = d.time()
    morning = time(9, 30) <= t <= time(11, 30)
    afternoon = time(13, 0) <= t <= time(15, 0)
    return morning or afternoon


def should_run_papertrade(dt: Optional[datetime] = None) -> bool:
    """综合判断：是否应该跑一次 模拟盘决策。

    条件：是 A 股交易日 **且** 在交易时段内。
    """
    return is_a_share_trading_day(dt) and is_trading_time(dt)


def next_decision_time(dt: Optional[datetime] = None) -> datetime:
    """返回下一个合理的决策触发时间（用于日志 / 重试 / 心跳规划）。

    规则：
    - 当前是交易日 + 交易时段内 → 当前时间（立即）
    - 当前是交易日 + 午休（11:30~13:00）→ 13:00
    - 当前是交易日 + 收盘后（>=15:00）→ 次日 9:30
    - 当前是非交易日 → 下一个交易日 9:30
    """
    now = dt or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if not is_a_share_trading_day(now):
        # 找下一个交易日
        for offset in range(1, 15):
            candidate = today + timedelta(days=offset)
            if is_a_share_trading_day(candidate):
                return candidate.replace(hour=9, minute=30)
        return now + timedelta(hours=24)  # fallback

    t = now.time()
    if time(9, 30) <= t <= time(11, 30):
        return now
    if time(11, 30) < t < time(13, 0):
        return now.replace(hour=13, minute=0, second=0, microsecond=0)
    if t >= time(15, 0):
        return (today + timedelta(days=1)).replace(hour=9, minute=30)
    # 9:30 之前
    return now.replace(hour=9, minute=30, second=0, microsecond=0)


def trading_day_summary(dt: Optional[datetime] = None) -> Tuple[bool, bool, str]:
    """汇总当前状态：(is_trading_day, is_trading_time, human_desc)"""
    now = dt or datetime.now()
    td = is_a_share_trading_day(now)
    tt = is_trading_time(now)
    if not td:
        return td, tt, f"{now.strftime('%Y-%m-%d %A')} 非交易日"
    if not tt:
        if now.time() < time(9, 30):
            return td, tt, f"{now.strftime('%Y-%m-%d %A')} 开盘前（9:30 开）"
        if time(11, 30) < now.time() < time(13, 0):
            return td, tt, "午间休市（13:00 复盘）"
        return td, tt, f"{now.strftime('%Y-%m-%d %A')} 已收盘"
    return td, tt, f"{now.strftime('%Y-%m-%d %A')} 交易时段"
