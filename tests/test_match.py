from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SAYUSTOCK_DATA"] = str(ROOT / "data")

from gsuid_core.data_store import set_res_base

set_res_base(ROOT / "data")

import SayuStock  # noqa: E402
from gsuid_core.sv import match_message, iter_handlers  # noqa: E402


def test_handlers_registered():
    assert len(iter_handlers()) >= 20


def test_match_core_commands():
    cases = {
        "股票帮助": "send_stock_help_img",
        "大盘概览": "send_stock_info",
        "全天候": "send_future_stock",
        "大盘云图": "send_cloudmap_img",
        "行业云图 半导体": "send_typemap_img",
        "概念云图 白酒": "send_gn_img",
        "个股 茅台": "send_stock_img",
        "个股 日k 600519": "send_stock_img",
        "对比个股 A B": "send_compare_img",
        "添加自选 600519": "bind_uid",
        "我的自选": "send_my_stock",
        "技术分析 茅台": "send_technical_analysis",
        "股票卡片 600519": "send_stock_card",
        "自动选股 市值50-200": "send_auto_screener",
        "订阅雪球新闻": "send_add_subscribe_info",
        "市盈率对比 600519": "send_stock_PE_info",
        "a大盘概览": "send_stock_info",
        "股票个股 茅台": "send_stock_img",
    }
    for text, fn in cases.items():
        m = match_message(text)
        assert m is not None, text
        assert m[1].func.__name__ == fn, (text, m[1].func.__name__)
