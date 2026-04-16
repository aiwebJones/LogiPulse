"""
LogiPulse — 报告生成器
将 AI 分析结果渲染为 Markdown 日报
"""

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Template

logger = logging.getLogger(__name__)

ZH_TEMPLATE = Template("""# LogiPulse 国际物流日报

> **{{ date }}** · 上海时间 {{ time }} 更新
> 信号源：{{ source_count }}+ · 覆盖航空货运、海运、供应链全链路

---

## 📊 市场脉搏

{{ analysis.market_pulse.summary }}

**市场情绪**: {% if analysis.market_pulse.sentiment == 'bullish' %}🟢 偏多{% elif analysis.market_pulse.sentiment == 'bearish' %}🔴 偏空{% else %}🟡 中性{% endif %}

{% if analysis.market_pulse.key_signals %}
### 关键信号
{% for s in analysis.market_pulse.key_signals %}
- **{{ s.signal }}** — {{ s.impact }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

---

## ✈️ 运价动态

{% if analysis.rate_trends and analysis.rate_trends.summary %}
{{ analysis.rate_trends.summary }}

{% if analysis.rate_trends.highlights %}
| 航线/区域 | 走势 | 详情 | 来源 |
|-----------|------|------|------|
{% for h in analysis.rate_trends.highlights %}
| {{ h.route }} | {% if h.direction == 'up' %}📈 上涨{% elif h.direction == 'down' %}📉 下跌{% else %}➡️ 持平{% endif %} | {{ h.detail }} | {{ h.source }} |
{% endfor %}
{% endif %}
{% else %}
*今日暂无显著运价变动信息*
{% endif %}

---

## ⛽ 燃油动态

{% if analysis.fuel_update and analysis.fuel_update.summary %}
{{ analysis.fuel_update.summary }}

{% if analysis.fuel_update.highlights %}
{% for h in analysis.fuel_update.highlights %}
- {{ h }}
{% endfor %}
{% endif %}
{% else %}
*今日暂无燃油价格重大变动*
{% endif %}

---

## 📰 今日要闻

{% if analysis.top_stories %}
{% for story in analysis.top_stories %}
### {{ loop.index }}. {{ story.title_zh }}

{{ story.summary_zh }}

{% if story.source %}> 来源：{{ story.source }}{% endif %}{% if story.url %} [原文→]({{ story.url }}){% endif %}

{% if story.importance == 'high' %}⚡ **重要程度：高**{% endif %}

{% endfor %}
{% else %}
*今日暂无重大要闻*
{% endif %}

---

## 🏛️ 政策监管

{% if analysis.regulatory_alerts %}
{% for alert in analysis.regulatory_alerts %}
- {% if alert.urgency == 'immediate' %}🚨{% elif alert.urgency == 'upcoming' %}⚠️{% else %}👀{% endif %} **{{ alert.title }}** ({{ alert.region }})
  {{ alert.detail }}

{% endfor %}
{% else %}
*今日暂无政策监管动态*
{% endif %}

---

## 🔧 技术与创新

{% if analysis.tech_innovation %}
{% for tech in analysis.tech_innovation %}
- **{{ tech.title }}** — {{ tech.detail }}{% if tech.source %} *({{ tech.source }})*{% endif %}

{% endfor %}
{% else %}
*今日暂无技术创新动态*
{% endif %}

---

## 🎯 今日行动建议

{% if analysis.action_items %}
{% for item in analysis.action_items %}
{{ loop.index }}. {{ item }}
{% endfor %}
{% else %}
*保持关注市场动态，做好常规运营*
{% endif %}

---

{% if analysis.quote_of_the_day and analysis.quote_of_the_day.text %}
> 💬 **{{ analysis.quote_of_the_day.text }}**
> — {{ analysis.quote_of_the_day.source }}
{% endif %}

---

*LogiPulse 由 Jones 出品 · AI 驱动的国际物流情报系统*
*数据来源覆盖 IATA、TAC Index、FreightWaves、Air Cargo News 等 {{ source_count }}+ 信息源*
""")

EN_TEMPLATE = Template("""# LogiPulse — International Logistics Daily Briefing

> **{{ date }}** · Updated {{ time }} Shanghai Time
> Sources: {{ source_count }}+ · Covering air cargo, ocean freight & supply chain

---

## Market Pulse

{{ analysis.market_pulse.summary }}

**Sentiment**: {% if analysis.market_pulse.sentiment == 'bullish' %}🟢 Bullish{% elif analysis.market_pulse.sentiment == 'bearish' %}🔴 Bearish{% else %}🟡 Neutral{% endif %}

{% if analysis.market_pulse.key_signals %}
### Key Signals
{% for s in analysis.market_pulse.key_signals %}
- **{{ s.signal }}** — {{ s.impact }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

---

## Rate Trends

{% if analysis.rate_trends and analysis.rate_trends.summary %}
{{ analysis.rate_trends.summary }}

{% if analysis.rate_trends.highlights %}
| Route/Region | Trend | Details | Source |
|-------------|-------|---------|--------|
{% for h in analysis.rate_trends.highlights %}
| {{ h.route }} | {% if h.direction == 'up' %}📈 Up{% elif h.direction == 'down' %}📉 Down{% else %}➡️ Stable{% endif %} | {{ h.detail }} | {{ h.source }} |
{% endfor %}
{% endif %}
{% else %}
*No significant rate changes reported today*
{% endif %}

---

## Fuel Update

{% if analysis.fuel_update and analysis.fuel_update.summary %}
{{ analysis.fuel_update.summary }}

{% if analysis.fuel_update.highlights %}
{% for h in analysis.fuel_update.highlights %}
- {{ h }}
{% endfor %}
{% endif %}
{% else %}
*No major fuel price changes today*
{% endif %}

---

## Top Stories

{% if analysis.top_stories %}
{% for story in analysis.top_stories %}
### {{ loop.index }}. {{ story.title_en }}

{{ story.summary_en }}

{% if story.source %}> Source: {{ story.source }}{% endif %}{% if story.url %} [Read more→]({{ story.url }}){% endif %}

{% if story.importance == 'high' %}⚡ **Importance: High**{% endif %}

{% endfor %}
{% else %}
*No major stories today*
{% endif %}

---

## Regulatory Alerts

{% if analysis.regulatory_alerts %}
{% for alert in analysis.regulatory_alerts %}
- {% if alert.urgency == 'immediate' %}🚨{% elif alert.urgency == 'upcoming' %}⚠️{% else %}👀{% endif %} **{{ alert.title }}** ({{ alert.region }})
  {{ alert.detail }}

{% endfor %}
{% else %}
*No regulatory updates today*
{% endif %}

---

## Tech & Innovation

{% if analysis.tech_innovation %}
{% for tech in analysis.tech_innovation %}
- **{{ tech.title }}** — {{ tech.detail }}{% if tech.source %} *({{ tech.source }})*{% endif %}

{% endfor %}
{% else %}
*No tech updates today*
{% endif %}

---

## Action Items

{% if analysis.action_items %}
{% for item in analysis.action_items %}
{{ loop.index }}. {{ item }}
{% endfor %}
{% else %}
*Stay informed and maintain regular operations*
{% endif %}

---

{% if analysis.quote_of_the_day and analysis.quote_of_the_day.text %}
> 💬 **{{ analysis.quote_of_the_day.text }}**
> — {{ analysis.quote_of_the_day.source }}
{% endif %}

---

*LogiPulse by Jones · AI-Powered International Logistics Intelligence*
*Sourced from {{ source_count }}+ feeds including IATA, TAC Index, FreightWaves, Air Cargo News*
""")


def render_zh(analysis: dict, source_count: int = 70) -> str:
    now = datetime.now()
    return ZH_TEMPLATE.render(
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
        source_count=source_count,
        analysis=analysis,
    )


def render_en(analysis: dict, source_count: int = 70) -> str:
    now = datetime.now()
    return EN_TEMPLATE.render(
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
        source_count=source_count,
        analysis=analysis,
    )


def save_reports(
    analysis: dict,
    output_dir: str = "reports",
    source_count: int = 70,
) -> tuple[Path, Path]:
    """生成并保存中英文日报"""
    today = datetime.now().strftime("%Y-%m-%d")
    year = datetime.now().strftime("%Y")

    zh_dir = Path(output_dir) / "zh" / year
    en_dir = Path(output_dir) / "en" / year
    zh_dir.mkdir(parents=True, exist_ok=True)
    en_dir.mkdir(parents=True, exist_ok=True)

    zh_path = zh_dir / f"{today}.md"
    en_path = en_dir / f"{today}.md"

    zh_content = render_zh(analysis, source_count)
    en_content = render_en(analysis, source_count)

    zh_path.write_text(zh_content, encoding="utf-8")
    en_path.write_text(en_content, encoding="utf-8")

    logger.info(f"Reports saved: {zh_path}, {en_path}")
    return zh_path, en_path
