"""Help card: kkt-style markdown → pillowmd (no tables / raw ---)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from astrbot.api import logger

PLUGIN = "astrbot_plugin_sayustock"

# pillowmd 对 GFM 表格、部分 --- 分隔支持不稳定，按 kkt 用标题+列表+粗体
HELP_MARKDOWN = """# 早柚股票 · 命令帮助

基于 SayuStock。群内直接发命令（可加 `/`）。
下面 **粗体** 是主指令。

## 一、大盘

- **大盘概览** — 主要指数 + 涨跌分布图
- **全天候** — 全球股市 / 商品 / 汇率等

别名可在插件配置「大盘别名」修改（默认：大盘、盘面、今日大盘）。

## 二、云图

- **大盘云图** — A 股行业涨跌云图
- **行业云图** 半导体 — 指定行业（示例）
- **概念云图** 白酒 — 指定概念（示例）

别名可在配置「云图别名」修改（默认：云图、热力图、A股云图）。

## 三、个股

- **个股** 茅台 — 分时图（默认）
- **个股** 日k 600519 — 日 K（亦支持 周k / 月k / 季k / 年k）
- **我的个股** — 自选前 5 只分时

## 四、对比

- **对比个股** A B — 多股涨跌幅对比（可加「年初至今」等）
- **市盈率对比** A B — PE 历史对比
- **市净率对比** A B — PB 历史对比
- **股息率对比** A B — 股息率对比

## 五、自选

- **添加自选** 茅台 600519 — 可多个，需回复「是」确认
- **删除自选** 600519
- **清空自选** — 清空当前账号
- **我的自选** — 自选行情一览图

## 六、分析

- **技术分析** 茅台 — 技术面评分
- **股票卡片** 600519 — 一页纸摘要
- **自动选股** 市值50-200 PE小于30 — 条件筛选
- **组合体检** — 自选行业集中度
- **持仓分析** — 自选 / 文本持仓分析
- **基金持仓** 510300 — 基金重仓分布

## 七、新闻

- **订阅雪球新闻** — 群内订阅财经快讯（仅群聊）
- **取消订阅雪球新闻** — 取消

## 八、其它

- **股票帮助** — 本说明
- 可选前缀：`a` / `股票`（如 `a大盘概览`）
- 定时推送：WebUI → 插件配置 → 白名单群与 Cron

数据仅供参考，不构成投资建议。
"""

HELP_PLAIN = """早柚股票 · 命令帮助
粗体位=主指令。可加 / 前缀。

【大盘】
大盘概览 — 指数+涨跌分布
全天候 — 全球/商品/汇率
（别名默认：大盘、盘面、今日大盘）

【云图】
大盘云图
行业云图 半导体
概念云图 白酒
（别名默认：云图、热力图、A股云图）

【个股】
个股 茅台
个股 日k 600519
我的个股

【对比】
对比个股 A B
市盈率/市净率/股息率对比 A B

【自选】
添加自选 / 删除自选 / 清空自选 / 我的自选

【分析】
技术分析 / 股票卡片 / 自动选股
组合体检 / 持仓分析 / 基金持仓

【新闻】
订阅雪球新闻（群）/ 取消订阅雪球新闻

【其它】
股票帮助
可选前缀 a / 股票
定时推送见插件配置

数据仅供参考，不构成投资建议。
"""


def _resolve_pillowmd_style_dirs() -> list[Path]:
    candidates: list[Path] = []
    env = str(os.getenv("SAYUSTOCK_PILLOWMD_STYLE_DIR", "") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())

    roots = [
        Path("/opt/astrbot/data"),
        Path("/AstrBot/data"),
    ]
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path

        roots.insert(0, Path(get_astrbot_data_path()))
    except Exception:
        pass
    try:
        # plugin file → data/plugins/xxx → data
        roots.append(Path(__file__).resolve().parent.parent.parent)
    except Exception:
        pass

    for root in roots:
        candidates.append(root / "plugins" / "astrbot_plugin_outputpro" / "t2i_style")
        candidates.append(root / "addons" / "plugins" / "astrbot_plugin_outputpro" / "t2i_style")

    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            key = str(path.resolve()) if path.exists() else str(path)
        except Exception:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_dir() and (path / "setting.yml").is_file():
            out.append(path)
    return out


async def render_help_t2i(cache_dir: Path, markdown_text: str = HELP_MARKDOWN) -> Optional[str]:
    """pillowmd(outputpro 样式) → AstrBot html_renderer 回退。"""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    try:
        import pillowmd  # type: ignore
    except Exception as exc:
        logger.debug("[%s] pillowmd missing: %s", PLUGIN, exc)
        pillowmd = None  # type: ignore

    if pillowmd is not None:
        for style_dir in _resolve_pillowmd_style_dirs():
            try:
                style = pillowmd.LoadMarkdownStyles(style_dir)
                rendered = await style.AioRender(
                    text=markdown_text,
                    useImageUrl=False,
                    autoPage=True,
                )
                saved = rendered.Save(cache_dir)
                path = Path(str(saved))
                if path.is_file() and path.stat().st_size > 1024:
                    logger.info(
                        "[%s] help pillowmd ok style=%s size=%d",
                        PLUGIN,
                        style_dir,
                        path.stat().st_size,
                    )
                    return str(path.resolve())
            except Exception as exc:
                logger.warning("[%s] pillowmd fail style=%s: %s", PLUGIN, style_dir, exc)

    try:
        from astrbot.api import html_renderer
    except Exception as exc:
        logger.debug("[%s] html_renderer unavailable: %s", PLUGIN, exc)
        return None

    for use_network in (False, True):
        try:
            path = await html_renderer.render_t2i(
                markdown_text,
                use_network=use_network,
                return_url=False,
                template_name="base",
            )
            if path and Path(str(path)).is_file():
                logger.info("[%s] help t2i ok network=%s", PLUGIN, use_network)
                return str(path)
        except Exception as exc:
            logger.warning("[%s] help t2i fail network=%s: %s", PLUGIN, use_network, exc)
    return None
