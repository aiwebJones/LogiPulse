# LogiPulse — AI 驱动的国际物流每日情报系统

> 设计为每天 8:00 采集全球物流信息源，AI 分析后生成中文报告及英文栏目版。

## 它能做什么

- **自动采集** 全球头部货代、IATA、运价指数、行业新闻、航司动态等 70+ 信息源
- **AI 分析** 使用 Claude 提炼市场脉搏、运价趋势、政策预警、行动建议
- **日报生成** 输出中文及英文栏目版 Markdown；英文版分析正文目前仍为中文
- **GitHub 自动发布** 通过 GitHub Actions 每日定时运行，报告自动入库

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 3. 试运行（使用示例数据，不调用 AI）
python run.py --dry-run

# 4. 完整运行
python run.py
```

## 命令参数

| 命令 | 说明 |
|------|------|
| `python run.py` | 完整流程：采集 → AI分析 → 生成日报 |
| `python run.py --dry-run` | 使用示例数据生成报告（不采集、不调用AI） |
| `python run.py --collect-only` | 仅采集数据，保存到 `data/` |
| `python run.py --from-cache` | 从今日缓存数据生成报告（不重新采集） |

## 信息源覆盖

| 类别 | 数量 | 代表源 |
|------|------|--------|
| 全球头部货代 | 10 | DHL, K+N, DSV, DB Schenker, Sinotrans |
| 行业协会 | 6 | IATA, FIATA, TIACA, ICAO, WTO |
| 数字化平台 | 8 | cargo.one, WebCargo, Freightos, Flexport |
| 运价指数 | 7 | TAC Index, Baltic Air Freight, FBX, WorldACD |
| 航空燃油 | 4 | IATA Fuel Monitor, S&P Platts, EIA |
| 行业新闻 | 14 | Air Cargo News, The Loadstar, FreightWaves |
| 播客 | 5 | Air Cargo Podcast, FreightCasts |
| 航空公司货运 | 9 | Lufthansa, Emirates, Qatar, Turkish, Cathay |
| 社交社区 | 4 | Reddit, LinkedIn, 货代圈 |
| 政策监管 | 5 | 中国海关, US CBP, EU TAXUD, CAAC |

**合计 70+ 信息源**

## 日报结构

每日生成的报告包含以下板块：

1. **市场脉搏** — 当日市场总览 + 多空情绪判断
2. **运价动态** — 主要航线运价走势（表格形式）
3. **燃油动态** — 航空煤油价格变化
4. **今日要闻** — 5-8 条精选重大新闻（中英双语摘要）
5. **政策监管** — 海关、航空、贸易政策变化预警
6. **技术创新** — 行业数字化工具、平台动态
7. **今日行动建议** — 货代从业者具体行动指引
8. **每日金句** — 值得记住的行业洞察

## 项目结构

```
LogiPulse/
├── run.py                    # 主入口
├── config/
│   └── sources.yaml          # 信息源配置（70+ 源）
├── src/
│   ├── collector.py          # 信息采集器（RSS/Web并发）
│   ├── analyzer.py           # AI 分析引擎（Claude）
│   └── reporter.py           # 报告生成器（Jinja2模板）
├── reports/
│   ├── zh/2026/              # 中文日报
│   └── en/2026/              # 英文日报
├── .github/workflows/
│   └── daily-briefing.yml    # GitHub Actions 定时任务
└── .env.example              # 环境变量模板
```

## GitHub Actions 自动化

工作流启用后，日报在每天北京时间 8:00 自动生成并提交到仓库。
手动 Run workflow 默认 `publish=false`：生成本次日报并上传 `daily-briefing-<run_id>`
附件，保留7天，不提交报告。确认需要发布时，显式选择 `publish=true`；这会重新
采集和生成，需核对新一轮结果。手动预览也会调用AI并消耗账户额度。

需要在仓库 Settings → Secrets 中添加：
- `ANTHROPIC_API_KEY` — Claude API 密钥

可选仓库变量 `ANTHROPIC_MODEL` 用于选择账号可用的模型，默认
`claude-sonnet-5-5`。原先硬编码的 `claude-sonnet-4-20250514` 已在
2026-08-15 的运行中返回 404；实际可用性须以当前账号运行结果为准。

未配置密钥或没有近48小时内有明确发布时间的资料时，正式运行会失败退出，不生成示例日报。
`--dry-run` 默认写入 `demo-reports/`，内容带显式示例标记，不会混入
工作流提交的 `reports/`。来源计数表示本次通过日期筛选并提交分析的不同来源数量，
报告更新时间使用上海时区。

当前英文模板仅翻译栏目标题，分析正文仍沿用中文；完整英文翻译尚未接入
主流程。没有发布日期、超过48小时或未来日期的条目不参与日报分析；只有更新时间
也不能证明是新文章。原始资料仍保存在 `data/`，`--collect-only` 不受分析筛选影响。
网页采集目前不提取发布日期，因此网页条目仅留作原始资料，不进入当日日报。
近期发布也可能回顾旧事，正式对外引用前仍需核对原文事件时间、运价和政策。
恢复定时任务前，先手动预览并核对结果；如果 Actions
显示 `disabled_inactivity`，还需要在 GitHub 重新启用该工作流。

运行离线回归检查（不调用付费模型）：

```bash
python -m unittest discover -s tests
```

---

*LogiPulse by Jones · 让信息差成为你的护城河*
