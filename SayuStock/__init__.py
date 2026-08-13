"""SayuStock package bootstrap for AstrBot (gsuid_core shim).

Loads main help.json feature modules. Heavy experimental modules
(papertrade / agent / kronos AI) load best-effort and never block core.
"""
from __future__ import annotations

from gsuid_core.logger import logger
from gsuid_core.sv import Plugins

# Core feature modules (help.json mainline)
from . import stock_help  # noqa: F401
from . import stock_info  # noqa: F401
from . import stock_cloudmap  # noqa: F401
from . import stock_stockinfo  # noqa: F401
from . import stock_user  # noqa: F401
from . import stock_news  # noqa: F401
from . import stock_sina  # noqa: F401
from . import stock_analysis  # noqa: F401
from . import stock_status  # noqa: F401

# Optional / heavy
for _mod in (
    "stock_holdings_analysis",
    "stock_ai",
    "stock_ai_func",
    "stock_papertrade",
    "stock_agent",
):
    try:
        __import__(f"{__name__}.{_mod}", fromlist=["*"])
    except Exception as e:
        logger.warning(f"[SayuStock] optional module {_mod} not loaded: {e}")

Plugins(
    name="SayuStock",
    force_prefix=["a", "股票"],
    allow_empty_prefix=True,
)
