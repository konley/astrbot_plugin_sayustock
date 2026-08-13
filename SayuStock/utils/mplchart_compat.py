"""mplchart 新旧版本兼容层。

旧版（如 0.0.37）与新版（如 0.0.46+）有多处 API 差异：

- ``Price``：旧版在 ``mplchart.primitives`` 中；新版已移除，改用 ``LinePlot``。
- ``Chart(bgcolor=..., color_scheme=...)``：新版已弃用/忽略，须走 ``style=``。
- ``chart.add_legends()`` / ``chart.main_axes()``：新版迁到 ``chart.canvas``。

业务代码统一从本模块导入 ``Chart`` / ``Price`` 等符号。
"""

from __future__ import annotations

import inspect
import warnings
from typing import Any, Mapping, cast

from mplchart import primitives as _mpl_primitives
from mplchart.chart import Chart as _MplChart
from mplchart.indicators import SMA, Indicator
from mplchart.primitives import (
    Pane,
    HLine,
    Volume,
    BarPlot,
    LinePlot,
    Candlesticks,
)

_NativePrice = cast("type[LinePlot] | None", getattr(_mpl_primitives, "Price", None))

__all__ = [
    "BarPlot",
    "Candlesticks",
    "Chart",
    "HLine",
    "Indicator",
    "LinePlot",
    "Pane",
    "Price",
    "SMA",
    "Volume",
]


class _PriceCompat(LinePlot):
    """新版 mplchart 无 Price 时的兼容实现。"""

    def __init__(
        self,
        item: str = "close",
        *,
        width: float = 1.0,
        alpha: float = 1.0,
        color: str | None = None,
    ) -> None:
        super().__init__(item, width=width, alpha=alpha, color=color, label=str(item))


Price: type[LinePlot] = _NativePrice if _NativePrice is not None else _PriceCompat

_CHART_INIT_PARAMS = inspect.signature(_MplChart.__init__).parameters
_SUPPORTS_STYLE = "style" in _CHART_INIT_PARAMS
_SUPPORTS_BGCOLOR = "bgcolor" in _CHART_INIT_PARAMS
_SUPPORTS_COLOR_SCHEME = "color_scheme" in _CHART_INIT_PARAMS


def _build_dark_style(
    bgcolor: str | None,
    color_scheme: Any,
) -> dict[str, Any]:
    """Map legacy bgcolor/color_scheme → mplchart style spec (dark CN A-share look)."""
    bg = bgcolor or "#050505"
    scheme: dict[str, Any] = {}
    if isinstance(color_scheme, Mapping):
        scheme = dict(color_scheme)
    elif color_scheme:
        try:
            scheme = dict(color_scheme)
        except Exception:
            scheme = {}

    up = scheme.get("colorup") or scheme.get("up") or "#e74c3c"
    down = scheme.get("colordn") or scheme.get("down") or "#00b050"
    text = scheme.get("text") or "#f5f5f5"
    grid = scheme.get("grid") or "#555555"
    bg = scheme.get("bgcolor") or bg

    settings: dict[str, Any] = {
        "yaxis.right": True,
        "candle.up.color": up,
        "candle.down.color": down,
        "candle.alpha": 0.95,
        "ohlc.up.color": up,
        "ohlc.down.color": down,
        "volume.up.color": up,
        "volume.down.color": down,
        "volume.alpha": 0.45,
    }
    # optional boll band fill keys from scheme (label -> color)
    for key, val in scheme.items():
        if isinstance(key, str) and key.startswith("BOLL") and isinstance(val, str):
            # not a standard setting; keep for potential future alias use
            settings[f"overlay.{key}.color"] = val

    return {
        "stylesheet": "dark_background",
        "rc": {
            "axes.grid": True,
            "axes.facecolor": bg,
            "figure.facecolor": bg,
            "savefig.facecolor": bg,
            "axes.edgecolor": "#888888",
            "axes.labelcolor": text,
            "xtick.color": text,
            "ytick.color": text,
            "text.color": text,
            "grid.color": grid,
            "grid.alpha": 0.55,
            "legend.facecolor": bg,
            "legend.edgecolor": "#444444",
            "legend.labelcolor": text,
        },
        "settings": settings,
    }


class Chart(_MplChart):
    """兼容包装：屏蔽新旧 Chart 构造参数与辅助方法差异。"""

    def __init__(
        self,
        prices: Any = None,
        *,
        title: Any = None,
        max_bars: Any = None,
        start: Any = None,
        end: Any = None,
        figure: Any = None,
        figsize: Any = None,
        bgcolor: Any = None,
        holidays: Any = None,
        normalize: bool = False,
        raw_dates: bool = False,
        style: Any = None,
        color_scheme: Any = (),
        **extra: Any,
    ) -> None:
        # 新版：color_scheme 被忽略 → 合成 style，保证深色底 + 红涨绿跌
        if _SUPPORTS_STYLE and style is None and (
            bgcolor is not None or color_scheme not in (None, (), {})
        ):
            style = _build_dark_style(bgcolor, color_scheme)

        init_kwargs: dict[str, Any] = {
            "title": title,
            "max_bars": max_bars,
            "start": start,
            "end": end,
            "figure": figure,
            "figsize": figsize,
            "normalize": normalize,
            "raw_dates": raw_dates,
            "style": style,
            "holidays": holidays,
            **extra,
        }
        if _SUPPORTS_BGCOLOR and bgcolor is not None:
            init_kwargs["bgcolor"] = bgcolor
        if _SUPPORTS_COLOR_SCHEME:
            init_kwargs["color_scheme"] = color_scheme

        filtered = {
            key: value
            for key, value in init_kwargs.items()
            if key in _CHART_INIT_PARAMS and value is not None
        }
        for flag in ("normalize", "raw_dates"):
            if flag in _CHART_INIT_PARAMS:
                filtered[flag] = init_kwargs.get(flag, False)

        # 抑制新版对 color_scheme 的弃用警告（我们已转 style）
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            super().__init__(prices, **filtered)

        # 双保险：部分版本 style 未完全落到 figure
        if bgcolor or (isinstance(color_scheme, Mapping) and color_scheme.get("bgcolor")):
            bg = bgcolor or color_scheme.get("bgcolor")  # type: ignore[union-attr]
            try:
                self.figure.set_facecolor(bg)
                for ax in self.figure.axes:
                    ax.set_facecolor(bg)
            except Exception:
                pass

    def add_legends(self) -> Any:
        method = getattr(_MplChart, "add_legends", None)
        if callable(method):
            return method(self)
        return self.canvas.add_legends()

    def main_axes(self) -> Any:
        method = getattr(_MplChart, "main_axes", None)
        if callable(method):
            return method(self)
        return self.canvas.main_axes()
