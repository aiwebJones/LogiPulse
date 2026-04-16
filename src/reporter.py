"""
LogiPulse — 报告生成器 v2
四层情报系统：输入层 → 解释层 → 转换层 → 行动层
"""

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Template

logger = logging.getLogger(__name__)

# ============================================================
# 中文模板 — 四层情报结构
# ============================================================
ZH_TEMPLATE = Template("""# LogiPulse 国际物流情报日报

> **{{ date }}** · 上海时间 {{ time }} 更新
> 信号源 {{ source_count }}+ · 这不是新闻，是你今天的作战地图

---

## Layer 1 · 世界发生了什么

{% if analysis.layer1_input %}
### {{ analysis.layer1_input.headline }}

{% if analysis.layer1_input.supply_signals %}
#### 供给变化（运力端）
{% for s in analysis.layer1_input.supply_signals %}
- {% if s.severity == 'high' %}🔴{% elif s.severity == 'medium' %}🟡{% else %}⚪{% endif %} {{ s.signal }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer1_input.demand_signals %}
#### 需求变化（货量端）
{% for s in analysis.layer1_input.demand_signals %}
- {% if s.severity == 'high' %}🔴{% elif s.severity == 'medium' %}🟡{% else %}⚪{% endif %} {{ s.signal }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer1_input.rule_signals %}
#### 规则变化（政策/合规）
{% for s in analysis.layer1_input.rule_signals %}
- {% if s.severity == 'high' %}🚨{% elif s.severity == 'medium' %}⚠️{% else %}👀{% endif %} {{ s.signal }}{% if s.deadline %} **[{{ s.deadline }}]**{% endif %}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}
{% endif %}

---

## Layer 2 · 为什么会这样

{% if analysis.layer2_explain %}
> **确定性指数**: {% if analysis.layer2_explain.certainty_index == 'certain' %}🟢 确定{% elif analysis.layer2_explain.certainty_index == 'volatile' %}🔴 剧烈波动{% else %}🟡 不确定{% endif %}

{{ analysis.layer2_explain.core_logic }}

{% if analysis.layer2_explain.causal_chains %}
**因果链拆解：**
{% for c in analysis.layer2_explain.causal_chains %}
{{ loop.index }}. **{{ c.cause }}** → {{ c.effect }} → *{{ c.implication }}*
{% endfor %}
{% endif %}
{% endif %}

---

## Layer 3 · 对你意味着什么

{% if analysis.layer3_translate %}
{% if analysis.layer3_translate.by_route %}
### 按航线

| 航线 | 状态 | 运价 | 分析 |
|------|------|------|------|
{% for r in analysis.layer3_translate.by_route %}
| **{{ r.route }}** | {% if r.status == 'hot' %}🔥 热{% elif r.status == 'cold' %}❄️ 冷{% elif r.status == 'volatile' %}⚡ 波动{% else %}➡️ 稳{% endif %} | {% if r.rate_direction == 'up' %}📈{% elif r.rate_direction == 'down' %}📉{% else %}➡️{% endif %} | {{ r.detail }} |
{% endfor %}

{% for r in analysis.layer3_translate.by_route %}
{% if r.forwarder_talk %}
> **{{ r.route }} 对客话术**：「{{ r.forwarder_talk }}」
{% endif %}
{% endfor %}
{% endif %}

{% if analysis.layer3_translate.by_product %}
### 按货物类型

{% for p in analysis.layer3_translate.by_product %}
- {% if p.opportunity_or_risk == 'opportunity' %}💰{% elif p.opportunity_or_risk == 'risk' %}⚠️{% else %}➡️{% endif %} **{{ p.product }}**：{{ p.impact }}
{% endfor %}
{% endif %}

{% if analysis.layer3_translate.by_customer %}
### 按客户类型

{% for c in analysis.layer3_translate.by_customer %}
- **{{ c.customer_type }}**
  预判：{{ c.behavior_prediction }}
  你的动作：**{{ c.your_move }}**

{% endfor %}
{% endif %}
{% endif %}

---

## Layer 4 · 今天怎么赚钱

{% if analysis.layer4_action %}
{% if analysis.layer4_action.money_moves %}
### 💰 商机

{% for m in analysis.layer4_action.money_moves %}
**{{ loop.index }}. {{ m.opportunity }}**
为什么是今天：{{ m.why_now }}
{% if m.expected_margin %}预估空间：{{ m.expected_margin }}{% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer4_action.pricing_strategy %}
### 📊 今日报价策略

| 档位 | 策略 |
|------|------|
| 🟢 保守 | {{ analysis.layer4_action.pricing_strategy.conservative }} |
| 🟡 标准 | {{ analysis.layer4_action.pricing_strategy.standard }} |
| 🔴 激进 | {{ analysis.layer4_action.pricing_strategy.aggressive }} |

> {{ analysis.layer4_action.pricing_strategy.rationale }}
{% endif %}

{% if analysis.layer4_action.call_list %}
### 📞 今天该打的电话

{% for c in analysis.layer4_action.call_list %}
{{ loop.index }}. **{{ c.who }}** — {{ c.why }}
   话术：「{{ c.talking_point }}」

{% endfor %}
{% endif %}

{% if analysis.layer4_action.team_brief %}
### 🎯 销售早会一段话

> {{ analysis.layer4_action.team_brief }}
{% endif %}
{% endif %}

---

## 燃油快照

{% if analysis.fuel_snapshot and analysis.fuel_snapshot.summary %}
{{ analysis.fuel_snapshot.summary }}

{% if analysis.fuel_snapshot.impact_on_fsc %}FSC影响：{{ analysis.fuel_snapshot.impact_on_fsc }}{% endif %}
{% else %}
*今日暂无燃油重大变动*
{% endif %}

---

{% if analysis.quote_of_the_day and analysis.quote_of_the_day.text %}
> 💬 **{{ analysis.quote_of_the_day.text }}**
{% if analysis.quote_of_the_day.context %}> {{ analysis.quote_of_the_day.context }}{% endif %}
{% endif %}

---

*LogiPulse by Jones · 不是新闻，是作战地图*
*这个市场，不是价格决定成交，是确定性决定成交。*
""")

# ============================================================
# 英文模板 — 四层情报结构
# ============================================================
EN_TEMPLATE = Template("""# LogiPulse — International Logistics Intelligence

> **{{ date }}** · Updated {{ time }} Shanghai Time
> {{ source_count }}+ sources · This is not news — it's your battle map

---

## Layer 1 · What Happened

{% if analysis.layer1_input %}
### {{ analysis.layer1_input.headline }}

{% if analysis.layer1_input.supply_signals %}
#### Supply Signals
{% for s in analysis.layer1_input.supply_signals %}
- {% if s.severity == 'high' %}🔴{% elif s.severity == 'medium' %}🟡{% else %}⚪{% endif %} {{ s.signal }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer1_input.demand_signals %}
#### Demand Signals
{% for s in analysis.layer1_input.demand_signals %}
- {% if s.severity == 'high' %}🔴{% elif s.severity == 'medium' %}🟡{% else %}⚪{% endif %} {{ s.signal }}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer1_input.rule_signals %}
#### Regulatory Signals
{% for s in analysis.layer1_input.rule_signals %}
- {% if s.severity == 'high' %}🚨{% elif s.severity == 'medium' %}⚠️{% else %}👀{% endif %} {{ s.signal }}{% if s.deadline %} **[{{ s.deadline }}]**{% endif %}{% if s.source %} *({{ s.source }})*{% endif %}{% if s.url %} [→]({{ s.url }}){% endif %}

{% endfor %}
{% endif %}
{% endif %}

---

## Layer 2 · Why It Matters

{% if analysis.layer2_explain %}
> **Certainty Index**: {% if analysis.layer2_explain.certainty_index == 'certain' %}🟢 Certain{% elif analysis.layer2_explain.certainty_index == 'volatile' %}🔴 Volatile{% else %}🟡 Uncertain{% endif %}

{{ analysis.layer2_explain.core_logic }}

{% if analysis.layer2_explain.causal_chains %}
**Causal Chains:**
{% for c in analysis.layer2_explain.causal_chains %}
{{ loop.index }}. **{{ c.cause }}** → {{ c.effect }} → *{{ c.implication }}*
{% endfor %}
{% endif %}
{% endif %}

---

## Layer 3 · What It Means For You

{% if analysis.layer3_translate %}
{% if analysis.layer3_translate.by_route %}
### By Route

| Route | Status | Rate | Analysis |
|-------|--------|------|----------|
{% for r in analysis.layer3_translate.by_route %}
| **{{ r.route }}** | {% if r.status == 'hot' %}🔥 Hot{% elif r.status == 'cold' %}❄️ Cold{% elif r.status == 'volatile' %}⚡ Volatile{% else %}➡️ Stable{% endif %} | {% if r.rate_direction == 'up' %}📈{% elif r.rate_direction == 'down' %}📉{% else %}➡️{% endif %} | {{ r.detail }} |
{% endfor %}
{% endif %}

{% if analysis.layer3_translate.by_product %}
### By Cargo Type

{% for p in analysis.layer3_translate.by_product %}
- {% if p.opportunity_or_risk == 'opportunity' %}💰{% elif p.opportunity_or_risk == 'risk' %}⚠️{% else %}➡️{% endif %} **{{ p.product }}**: {{ p.impact }}
{% endfor %}
{% endif %}

{% if analysis.layer3_translate.by_customer %}
### By Customer Type

{% for c in analysis.layer3_translate.by_customer %}
- **{{ c.customer_type }}**
  Prediction: {{ c.behavior_prediction }}
  Your move: **{{ c.your_move }}**

{% endfor %}
{% endif %}
{% endif %}

---

## Layer 4 · How to Make Money Today

{% if analysis.layer4_action %}
{% if analysis.layer4_action.money_moves %}
### Opportunities

{% for m in analysis.layer4_action.money_moves %}
**{{ loop.index }}. {{ m.opportunity }}**
Why today: {{ m.why_now }}
{% if m.expected_margin %}Expected margin: {{ m.expected_margin }}{% endif %}

{% endfor %}
{% endif %}

{% if analysis.layer4_action.pricing_strategy %}
### Pricing Strategy

| Tier | Strategy |
|------|----------|
| 🟢 Conservative | {{ analysis.layer4_action.pricing_strategy.conservative }} |
| 🟡 Standard | {{ analysis.layer4_action.pricing_strategy.standard }} |
| 🔴 Aggressive | {{ analysis.layer4_action.pricing_strategy.aggressive }} |

> {{ analysis.layer4_action.pricing_strategy.rationale }}
{% endif %}

{% if analysis.layer4_action.team_brief %}
### Team Brief

> {{ analysis.layer4_action.team_brief }}
{% endif %}
{% endif %}

---

{% if analysis.quote_of_the_day and analysis.quote_of_the_day.text %}
> 💬 **{{ analysis.quote_of_the_day.text }}**
{% if analysis.quote_of_the_day.context %}> {{ analysis.quote_of_the_day.context }}{% endif %}
{% endif %}

---

*LogiPulse by Jones · Not news — battle maps.*
*In this market, certainty closes deals, not price.*
""")


def render_zh(analysis: dict, source_count: int = 120) -> str:
    now = datetime.now()
    return ZH_TEMPLATE.render(
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
        source_count=source_count,
        analysis=analysis,
    )


def render_en(analysis: dict, source_count: int = 120) -> str:
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
    source_count: int = 120,
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
