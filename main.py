"""AstrBot entry: SayuStock + help T2I + alias + whitelist push."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, StarTools, register
import astrbot.api.message_components as Comp

PLUGIN = "astrbot_plugin_sayustock"
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# package-relative first (AstrBot loads as data.plugins....), flat fallback for tests
try:
    from .help_card import HELP_MARKDOWN, HELP_PLAIN, render_help_t2i
    from .push_service import PushService, parse_csv_aliases, parse_list
except ImportError:
    from help_card import HELP_MARKDOWN, HELP_PLAIN, render_help_t2i
    from push_service import PushService, parse_csv_aliases, parse_list

HELP_TRIGGERS = {
    "股票帮助",
    "sayustock帮助",
    "sayustock",
    "早柚股票",
    "早柚帮助",
    "股票指令",
}


def _setup_paths(data_dir: Path) -> None:
    from gsuid_core.data_store import set_res_base

    set_res_base(data_dir)
    (data_dir / "SayuStock" / "data").mkdir(parents=True, exist_ok=True)
    (data_dir / "SayuStock" / "db").mkdir(parents=True, exist_ok=True)
    (data_dir / "tmp").mkdir(parents=True, exist_ok=True)
    (data_dir / "help_t2i").mkdir(parents=True, exist_ok=True)


def _cfg(config, key, default=None):
    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(key, default)
    return config.get(key, default) if hasattr(config, "get") else default


@register(
    "astrbot_plugin_sayustock",
    "konley",
    "早柚股票 SayuStock 完整移植（gsuid_core 兼容层）",
    "1.1.0",
    "https://github.com/KimigaiiWuyi/SayuStock",
)
class SayuStockPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self._data_dir: Optional[Path] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._loaded = False
        self._load_error: Optional[str] = None
        self._push: Optional[PushService] = None
        self._market_aliases: List[str] = []
        self._cloudmap_aliases: List[str] = []
        self._allweather_aliases: List[str] = []

    async def initialize(self) -> None:
        try:
            try:
                base = Path(str(StarTools.get_data_dir(PLUGIN)))
            except Exception:
                base = _ROOT / "data"
            base.mkdir(parents=True, exist_ok=True)
            self._data_dir = base
            _setup_paths(base)
            os.environ["SAYUSTOCK_DATA"] = str(base)

            from gsuid_core.subscribe import gs_subscribe

            gs_subscribe.set_push_fn(self._push_subscribe)

            import SayuStock  # noqa: F401

            from gsuid_core.aps import scheduler
            from gsuid_core.sv import iter_handlers

            self._apply_config()
            self._reload_aliases()

            scheduler.start()
            self._setup_push()
            self._loaded = True
            logger.info(
                "[%s] loaded handlers=%s push=%s data=%s",
                PLUGIN,
                len(iter_handlers()),
                bool(self._push and self._push._started),
                base,
            )
        except Exception as e:
            self._load_error = str(e)
            logger.exception("[%s] initialize failed: %s", PLUGIN, e)

    def _reload_aliases(self) -> None:
        self._market_aliases = parse_csv_aliases(
            _cfg(self.config, "market_aliases", "大盘,盘面,今日大盘"),
            "大盘,盘面,今日大盘",
        )
        self._cloudmap_aliases = parse_csv_aliases(
            _cfg(self.config, "cloudmap_aliases", "云图,热力图,A股云图"),
            "云图,热力图,A股云图",
        )
        self._allweather_aliases = parse_csv_aliases(
            _cfg(self.config, "allweather_aliases", ""),
            "",
        )
        logger.info(
            "[%s] aliases market=%s cloudmap=%s allweather=%s",
            PLUGIN,
            self._market_aliases,
            self._cloudmap_aliases,
            self._allweather_aliases,
        )

    def _apply_config(self) -> None:
        try:
            from SayuStock.stock_config.stock_config import STOCK_CONFIG

            for key in (
                "mapcloud_viewport",
                "mapcloud_scale",
                "mapcloud_refresh_minutes",
                "stock_cache_retention_days",
                "eastmoney_cookie",
            ):
                val = _cfg(self.config, key, None)
                if val is not None and val != "":
                    STOCK_CONFIG.set_config(key, val)
        except Exception as e:
            logger.warning("[%s] apply config skip: %s", PLUGIN, e)

    def _setup_push(self) -> None:
        if self._push:
            self._push.shutdown()
        self._push = PushService(
            run_command=self._run_command_payloads,
            send_to_group=self._send_payload_to_group,
        )
        cfg = self.config if isinstance(self.config, dict) else dict(self.config or {})
        self._push.setup(cfg)

    async def terminate(self) -> None:
        if self._push:
            self._push.shutdown()
            self._push = None
        try:
            from gsuid_core.aps import scheduler

            scheduler.shutdown()
        except Exception:
            pass
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        logger.info("[%s] terminate", PLUGIN)

    # ── platform send ─────────────────────────────

    async def _push_subscribe(self, row: dict, message: Any) -> None:
        gid = str(row.get("group_id") or "").strip()
        if not gid:
            return
        # news subscribe also respects whitelist if configured
        wl = parse_list(
            _cfg(self.config, "push_whitelist_groups", [])
            or _cfg(self.config, "push_groups", [])
        )
        if wl and gid not in wl:
            logger.info("[%s] news skip non-whitelist gid=%s", PLUGIN, gid)
            return
        await self._send_payload_to_group(gid, message)

    def _resolve_platform(self) -> str:
        configured = str(_cfg(self.config, "push_platform", "") or "").strip()
        pm = getattr(self.context, "platform_manager", None)
        insts = getattr(pm, "platform_insts", None) if pm else None
        if not insts:
            return configured or "aiocqhttp"
        if configured:
            for inst in insts:
                try:
                    if inst.meta().id == configured:
                        return configured
                except Exception:
                    pass
        for inst in insts:
            try:
                if "aiocqhttp" in type(inst).__name__.lower():
                    return inst.meta().id
            except Exception:
                pass
        try:
            return insts[0].meta().id
        except Exception:
            return configured or "aiocqhttp"

    async def _send_payload_to_group(self, gid: str, payload: Any) -> None:
        platform = self._resolve_platform()
        session = f"{platform}:GroupMessage:{gid}"
        try:
            chain = await self._payload_to_chain(payload)
            await self.context.send_message(session, chain)
            logger.info("[%s] send -> %s", PLUGIN, session)
        except Exception as e:
            logger.error("[%s] send fail %s: %s", PLUGIN, session, e)
            raise

    async def _run_command_payloads(self, command: str) -> List[Any]:
        """Run a SayuStock command headlessly; return bot.send payloads."""
        from gsuid_core.sv import match_message
        from gsuid_core.models import Event as GsEvent
        from gsuid_core.bot import Bot

        matched = match_message(command)
        if matched is None:
            # try alias expand
            expanded = self._expand_aliases(command)
            matched = match_message(expanded)
        if matched is None:
            logger.warning("[%s] push cmd not matched: %s", PLUGIN, command)
            return []
        _sv, handler, remain = matched
        collected: List[Any] = []

        async def send_fn(payload: Any):
            collected.append(payload)

        bot = Bot(
            send_fn=send_fn,
            event=GsEvent(
                user_id="system",
                bot_id="astrbot",
                group_id=None,
                text=remain,
                raw_text=command,
            ),
        )
        ret = handler.func(bot, bot.event)
        if asyncio.iscoroutine(ret):
            ret = await ret
        if isinstance(ret, (str, bytes, list)) and ret is not None:
            await bot.send(ret)
        return collected

    # ── alias ─────────────────────────────────────

    def _strip(self, text: str) -> str:
        t = (text or "").strip()
        if t.startswith(("/", "#")):
            t = t.lstrip("/#").strip()
        # optional force prefixes
        for p in ("股票", "a"):
            if t.startswith(p) and len(t) > len(p):
                rest = t[len(p) :].lstrip()
                if rest:
                    t = rest
                    break
        return t

    def _expand_aliases(self, text: str) -> str:
        """Map custom aliases → canonical SayuStock commands."""
        t = self._strip(text)
        if not t:
            return text

        # help
        if t.lower() in {x.lower() for x in HELP_TRIGGERS} or t in HELP_TRIGGERS:
            return "股票帮助"

        # fullmatch aliases for 大盘概览
        for a in self._market_aliases:
            if t == a or t.lower() == a.lower():
                return "大盘概览"

        # fullmatch / prefix aliases for 大盘云图
        for a in self._cloudmap_aliases:
            if t == a or t.lower() == a.lower():
                return "大盘云图"
            if t.startswith(a + " ") or t.startswith(a + "\n"):
                return "大盘云图 " + t[len(a) :].strip()
            # CJK no-space: 云图医药
            if t.startswith(a) and len(t) > len(a) and a not in ("大盘",):
                # avoid eating 大盘概览 etc.
                rest = t[len(a) :].strip()
                if rest and rest not in ("概览", "概况", "云图"):
                    return "大盘云图 " + rest

        for a in self._allweather_aliases:
            if t == a or t.lower() == a.lower():
                return "全天候"

        return t

    def _is_help(self, text: str) -> bool:
        t = self._strip(text)
        # intercept upstream help triggers too
        if t in ("股票帮助", "SayuStock帮助") or t.lower() in HELP_TRIGGERS:
            return True
        if t.lower() in {x.lower() for x in HELP_TRIGGERS}:
            return True
        return False

    # ── image / chain ─────────────────────────────

    def _session_key(self, event: AstrMessageEvent) -> str:
        try:
            gid = event.get_group_id() or ""
        except Exception:
            gid = ""
        return f"{gid}:{event.get_sender_id()}"

    def _group_id(self, event: AstrMessageEvent) -> Optional[str]:
        try:
            gid = event.get_group_id()
            return str(gid) if gid else None
        except Exception:
            return None

    async def _materialize_image(self, data: Any) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, str) and os.path.exists(data):
            return data
        raw: Optional[bytes] = None
        if isinstance(data, (bytes, bytearray)):
            raw = bytes(data)
        if raw is None:
            return None
        assert self._data_dir is not None
        path = self._data_dir / "tmp" / f"ss_{int(time.time() * 1000)}_{os.getpid()}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return str(path)

    async def _comps_from_payload(self, payload: Any) -> List[Any]:
        from gsuid_core.segment import normalize_send_payload

        comps: List[Any] = []
        for seg in normalize_send_payload(payload):
            if seg.type == "text":
                comps.append(Comp.Plain(str(seg.data or "")))
            elif seg.type == "image":
                path = await self._materialize_image(seg.data)
                if path:
                    comps.append(Comp.Image(file=path))
                else:
                    comps.append(Comp.Plain("[图片生成失败]"))
        return comps

    async def _payload_to_chain(self, payload: Any) -> MessageChain:
        comps = await self._comps_from_payload(payload)
        try:
            return MessageChain(comps)
        except Exception:
            texts = []
            for c in comps:
                t = getattr(c, "text", None)
                if t:
                    texts.append(str(t))
            return MessageChain().message("\n".join(texts) if texts else "")

    async def _send_help(self, event: AstrMessageEvent):
        assert self._data_dir is not None
        cache = self._data_dir / "help_t2i"
        path = await render_help_t2i(cache, HELP_MARKDOWN)
        if path:
            try:
                yield event.chain_result([Comp.Image(file=path)])
                return
            except Exception as e:
                logger.warning("[%s] help image send fail: %s", PLUGIN, e)
        yield event.plain_result(HELP_PLAIN)

    # ── message router ────────────────────────────

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        text = (event.message_str or "").strip()
        if not text:
            return

        sk = self._session_key(event)
        if sk in self._pending:
            fut = self._pending.get(sk)
            if fut and not fut.done():
                from gsuid_core.models import Event as GsEvent

                if text in ("是", "否", "yes", "no", "Y", "N", "y", "n") or len(text) <= 10:
                    event.stop_event()
                    fut.set_result(
                        GsEvent(
                            user_id=str(event.get_sender_id()),
                            text=text,
                            group_id=self._group_id(event),
                        )
                    )
                    return

        if not self._loaded:
            if self._is_help(text):
                event.stop_event()
                yield event.plain_result(
                    f"SayuStock 未加载：{self._load_error or 'unknown'}"
                )
            return

        # custom help (T2I) — bypass upstream mojibake help
        if self._is_help(text):
            event.stop_event()
            async for r in self._send_help(event):
                yield r
            return

        from gsuid_core.sv import match_message
        from gsuid_core.models import Event as GsEvent
        from gsuid_core.bot import Bot

        expanded = self._expand_aliases(text)
        matched = match_message(expanded)
        if matched is None and expanded != text:
            matched = match_message(text)
        if matched is None:
            return

        sv, handler, remain = matched
        # block upstream help handler if somehow matched
        if getattr(handler.func, "__name__", "") == "send_stock_help_img":
            event.stop_event()
            async for r in self._send_help(event):
                yield r
            return

        if getattr(sv, "area", "ALL") == "GROUP" and not self._group_id(event):
            return

        event.stop_event()
        logger.info(
            "[%s] sv=%s fn=%s remain=%r raw=%r sender=%s",
            PLUGIN,
            sv.name,
            getattr(handler.func, "__name__", "?"),
            remain[:50],
            text[:50],
            event.get_sender_id(),
        )

        gs_ev = GsEvent(
            user_id=str(event.get_sender_id()),
            bot_id="astrbot",
            group_id=self._group_id(event),
            text=remain,
            raw_text=text,
            message_type="group" if self._group_id(event) else "private",
        )

        collected: List[Any] = []
        interactive = {"on": False}

        async def send_fn(payload: Any):
            if interactive["on"]:
                try:
                    uo = event.unified_msg_origin
                    await self.context.send_message(
                        uo, await self._payload_to_chain(payload)
                    )
                except Exception as e:
                    logger.warning("[%s] interactive send: %s", PLUGIN, e)
                    collected.append(payload)
            else:
                collected.append(payload)

        async def receive_fn(prompt: str, timeout: float = 60.0):
            interactive["on"] = True
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            self._pending[sk] = fut
            try:
                return await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                return GsEvent(text="否", user_id=gs_ev.user_id)
            finally:
                self._pending.pop(sk, None)
                interactive["on"] = False

        bot = Bot(send_fn=send_fn, receive_fn=receive_fn, event=gs_ev)

        try:
            ret = handler.func(bot, gs_ev)
            if asyncio.iscoroutine(ret):
                ret = await ret
            if isinstance(ret, (str, bytes, list)) and ret is not None:
                await bot.send(ret)
        except Exception as e:
            logger.exception("[%s] handler error: %s", PLUGIN, e)
            yield event.plain_result(f"[SayuStock] 执行失败：{e}")
            return

        for payload in collected:
            comps = await self._comps_from_payload(payload)
            if comps:
                yield event.chain_result(comps)
