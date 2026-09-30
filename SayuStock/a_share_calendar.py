"""A-share session calendar. No package side effects."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

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


def is_a_share_trading_day(dt: Optional[datetime] = None) -> bool:
    d = dt or datetime.now()
    if d.weekday() >= 5:
        return False
    return d.strftime("%Y-%m-%d") not in A_SHARE_HOLIDAYS
