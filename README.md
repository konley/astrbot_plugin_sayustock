# astrbot_plugin_sayustock

**早柚股票** — 将 [SayuStock](https://github.com/KimigaiiWuyi/SayuStock) 接入 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的插件。

> 大盘概览 · 云图 · 个股分时/K 线 · 自选 · 对比 · 分析 · 新闻订阅 · 白名单定时推送

---

## 致谢与版权（必读）

本插件**不是**从零重写的行情引擎，核心业务逻辑来自上游开源项目：

| 项目 | 作者 | 说明 |
|------|------|------|
| **[SayuStock](https://github.com/KimigaiiWuyi/SayuStock)** | [@KimigaiiWuyi](https://github.com/KimigaiiWuyi) | 股票/A 股机器人插件本体（云图、个股、自选、分析等） |
| **[gsuid_core](https://github.com/Genshin-bots/gsuid_core)** | Genshin-bots 社区 | 上游插件原运行时（早柚核心） |

**本仓库工作：**

- 提供 **AstrBot 加载入口**（`main.py`）
- 提供精简的 **`gsuid_core` 兼容层**，使 SayuStock 源码可在 AstrBot 内运行
- 增加 **T2I 帮助图**、**自定义别名**、**白名单群定时推送** 等 AstrBot 侧能力

请尊重原作者与社区：

1. 保留上游 **GPL-3.0** 许可与版权声明  
2. 二次分发 / 修改时继续开源，并注明来自 SayuStock  
3. Star 原仓库比 Star 本适配更有意义：  
   - https://github.com/KimigaiiWuyi/SayuStock  
   - https://github.com/Genshin-bots/gsuid_core  

上游说明（摘自 SayuStock）：*本项目仅供学习使用，请勿用于商业用途。行情数据仅供参考，不构成任何投资建议。*

---

## 功能一览

| 类别 | 命令示例 |
|------|----------|
| 帮助 | `股票帮助`（图文，中文 T2I） |
| 大盘 | `大盘概览` / `全天候`（可配别名如 `大盘`） |
| 云图 | `大盘云图` / `行业云图 半导体` / `概念云图 白酒`（可配别名如 `热力图`） |
| 个股 | `个股 茅台` · `个股 日k 600519` · `我的个股` |
| 对比 | `对比个股 A B` · `市盈率对比` · `市净率对比` · `股息率对比` |
| 自选 | `添加自选` · `删除自选` · `清空自选` · `我的自选` |
| 分析 | `技术分析` · `股票卡片` · `自动选股` · `组合体检` · `持仓分析` · `基金持仓` |
| 新闻 | `订阅雪球新闻` / `取消订阅雪球新闻`（群） |
| 定时 | WebUI 配置白名单群 + Cron（**群号仅写本机配置，不进仓库**） |

可选前缀：`a` / `股票`（如 `a大盘概览`）。

> 模拟盘 / Kronos Agent 等重度模块默认不加载（依赖上游 AI 运行时），主路径以 help 中列出的为准。

---

## 推荐定时推送（A 股）

| 内容 | 推荐 Cron（北京时间） | 说明 |
|------|----------------------|------|
| **大盘概览+热力图** | `1 9 * * 0-4;31 11 * * 0-4;1 15 * * 0-4` | A 股开市日 **09:01 / 11:31 / 15:01**（周末和节假日不推；0=周一） |
| **大盘云图** | `5 15 * * 0-4` | 仅额外加发时用。工作日 **15:05**（0=周一；非开市日仍跳过） |
| **全天候** | `0 8 * * 0-4` | 工作日 **08:00**（0=周一；非开市日跳过）；也可改 `0 21 * * 0-4` 看美盘 |

配置路径：**AstrBot WebUI → 插件 → 早柚股票**（或 `data/config/astrbot_plugin_sayustock_config.json`）：

```json
{
  "push_enable": true,
  "push_whitelist_groups": ["你的群号1", "你的群号2"],
  "push_overview_cron": "1 9 * * 0-4;31 11 * * 0-4;1 15 * * 0-4",
  "push_cloudmap_cron": "",
  "push_allweather_cron": ""
}
```

- 仅 **白名单群** 会收到推送  
- 群号属于**部署实例本地配置**，请勿写进公开仓库  

---

## 安装

1. 将本仓库放到 AstrBot 的 `data/plugins/astrbot_plugin_sayustock/`  
2. 安装依赖（使用 AstrBot 同一 Python 环境）：

```bash
pip install -r requirements.txt
python -m playwright install chromium   # 云图截图需要
```

3. 重启 AstrBot 或重载插件  
4. 在 WebUI 配置别名、推送白名单与 Cron  

### 依赖说明

见 `requirements.txt`。帮助图优先使用 [pillowmd](https://pypi.org/) + 本机 `astrbot_plugin_outputpro` 的中文字体样式（与 kkt 插件同类方案）。

---

## 配置项摘要

| 键 | 含义 |
|----|------|
| `market_aliases` / `cloudmap_aliases` | 大盘 / 云图自定义触发词 |
| `push_enable` | 定时推送总开关 |
| `push_whitelist_groups` | 推送白名单群 |
| `push_*_cron` | 各任务 Cron |
| `mapcloud_viewport` / `mapcloud_scale` | 云图清晰度 |
| `eastmoney_cookie` | 可选；接口限流时填写，**勿提交 git** |

---

## 架构

```
AstrBot 消息
  → main.py（别名 / 帮助 T2I / 白名单推送）
  → gsuid_core/ 兼容层
  → SayuStock/ 上游业务模块
```

---

## 开源协议

- 上游 SayuStock / gsuid 生态：**[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)**  
- 本适配层与之兼容，整体按 **GPL-3.0** 分发（见 `LICENSE`）  

使用本插件即表示你理解并同意遵守 GPL-3.0 对衍生作品的要求。

---

## 相关链接

- 上游插件：https://github.com/KimigaiiWuyi/SayuStock  
- 上游文档：https://docs.sayu-bot.com/  
- 上游赞助（作者爱发电）：https://afdian.com/a/KimigaiiWuyi  
- AstrBot：https://github.com/AstrBotDevs/AstrBot  

---

## 免责声明

本插件及所展示行情、图表、分析结论**仅供学习与技术交流**，不构成投资建议。股市有风险，决策请独立判断并自行承担后果。
