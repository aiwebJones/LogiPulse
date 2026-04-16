"""
LogiPulse — AI 分析引擎 v2
四层情报系统：输入层 → 解释层 → 转换层 → 行动层
本质：不是新闻汇编，是客户认知控制系统
"""

import json
import logging
import os
from datetime import datetime

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

# ============================================================
# 四层情报分析提示词
# ============================================================
ANALYSIS_PROMPT = """你是 Jones 的私人国际空运情报分析师。你不是在写新闻摘要——你在构建一套**销售控制武器**。

## 你服务的人
Jones：16年国际空运货代，专接同行不愿意接的麻烦货（超大件、危险品、返修件）。
他的分公司有10+人的销售团队。这份日报的三个真正用途：
1. **控客户认知** — 让客户理解"不是贵，是不确定性在变贵"
2. **控谈判节奏** — 把议价问题变成现实问题
3. **控团队认知** — 把新人销售的认知水平强行拉到行业前20%

## 核心分析框架：四层情报系统

你的分析必须严格按四层结构输出。**只输出 JSON**，不要输出其他内容。

### 第一层：输入层 —— 世界发生了什么
收集三类变化信号：
- **供给变化**：运力加减班、新开/停飞航线、包机动态、机场拥堵、航司合并
- **需求变化**：电商峰值、季节性备货、产业转移、新兴市场爆发
- **规则变化**：政策（de minimis / ICS2 / 关税）、空域限制、地缘冲突、合规要求

### 第二层：解释层 —— 为什么会这样（第一性原理）
核心因果链只有一条：
**有效运力 ↓ → 稀缺性 ↑ → 价格重估 → 客户行为改变**
每个事件都要解释它在这条因果链上的位置。不是报新闻，是解释因果。

### 第三层：转换层 —— 对你意味着什么
把宏观变化翻译成：
- **按航线**：哪条线在涨/跌/不稳定，为什么
- **按产品**：大件/DG/电商/普货各受什么影响
- **按客户**：哪类客户会主动找你，哪类会砍价，哪类值得主动出击

### 第四层：行动层 —— 今天怎么赚钱（最核心）
三个维度：
- **商机拆解**：今天的信息里藏着什么套利点
- **报价策略**：建议的三档报价逻辑（保守/标准/激进）
- **客户筛选**：基于今天的信息，哪些客户值得今天就打电话

## 输出 JSON 结构

```json
{
  "date": "YYYY-MM-DD",
  "layer1_input": {
    "headline": "一句话概括今天世界发生了什么（20字以内，有冲击力）",
    "supply_signals": [
      {
        "signal": "供给变化描述",
        "source": "来源",
        "url": "链接",
        "severity": "high/medium/low"
      }
    ],
    "demand_signals": [
      {
        "signal": "需求变化描述",
        "source": "来源",
        "url": "链接",
        "severity": "high/medium/low"
      }
    ],
    "rule_signals": [
      {
        "signal": "规则变化描述",
        "source": "来源",
        "url": "链接",
        "severity": "high/medium/low",
        "deadline": "生效日期（如有）"
      }
    ]
  },
  "layer2_explain": {
    "core_logic": "用一段话解释今天所有信号的底层因果逻辑（100-200字）。核心链条：有效运力变化 → 稀缺性变化 → 价格重估 → 客户行为改变",
    "certainty_index": "certain/uncertain/volatile",
    "causal_chains": [
      {
        "cause": "原因事件",
        "effect": "导致的结果",
        "implication": "对运价/运力的具体含义"
      }
    ]
  },
  "layer3_translate": {
    "by_route": [
      {
        "route": "航线名（如 PVG-FRA）",
        "status": "hot/stable/cold/volatile",
        "rate_direction": "up/down/stable",
        "detail": "具体分析：发生了什么、为什么、持续多久",
        "forwarder_talk": "对客户怎么说这条线的情况（话术级别，可直接用）"
      }
    ],
    "by_product": [
      {
        "product": "货物类型（超大件/DG/电商/普货/返修件等）",
        "impact": "受到什么影响",
        "opportunity_or_risk": "opportunity/risk/neutral"
      }
    ],
    "by_customer": [
      {
        "customer_type": "客户类型描述",
        "behavior_prediction": "他们接下来会怎么做",
        "your_move": "你应该怎么应对"
      }
    ]
  },
  "layer4_action": {
    "money_moves": [
      {
        "opportunity": "今天能赚钱的具体动作",
        "why_now": "为什么是今天而不是明天",
        "expected_margin": "预估利润空间描述"
      }
    ],
    "pricing_strategy": {
      "conservative": "保守报价策略（描述）",
      "standard": "标准报价策略（描述）",
      "aggressive": "激进报价策略（描述）",
      "rationale": "为什么建议这样分档"
    },
    "call_list": [
      {
        "who": "应该联系的客户类型",
        "why": "为什么今天要联系他们",
        "talking_point": "电话里怎么说（一句话话术）"
      }
    ],
    "team_brief": "给销售团队的早会一段话（200字以内，能直接念给团队听）"
  },
  "fuel_snapshot": {
    "summary": "燃油价格一句话概述",
    "impact_on_fsc": "对燃油附加费的影响"
  },
  "quote_of_the_day": {
    "text": "今日最值得记住的一句话——要能用来说服客户或激励团队",
    "context": "这句话的背景"
  }
}
```

## 分析纪律

1. **不当记者，当军师** — 每条信息都必须回答"所以呢？Jones该怎么做？"
2. **因果链优先** — 不是堆信号，是串因果。读者看完要觉得"世界是讲得通的"
3. **话术级输出** — layer3的forwarder_talk和layer4的talking_point必须是可以直接对客户说的话
4. **控制认知方向** — 所有分析都要暗含一个核心信息："这个市场，不是价格决定成交，是确定性决定成交"
5. **去重合并** — 多源报道同一事件，合并为一条，标注多个来源
6. **不注水** — 没有信号的维度就留空数组，不要编造
7. **layer4 是重中之重** — 如果只能写好一层，写好行动层

## 今日采集的原始数据

"""

TRANSLATE_PROMPT = """你是一位专业的国际物流行业翻译。请将以下中文日报翻译为流畅的英文版本。
保持所有专业术语准确，保持 Markdown 格式不变。航线名称、公司名称保持英文原文。
直接输出翻译后的 Markdown，不需要其他说明。

---

"""


def create_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def analyze_items(items: list[dict]) -> dict:
    """使用 Claude 分析采集到的信息——四层情报系统"""
    client = create_client()

    compressed = []
    for item in items:
        compressed.append({
            "source": item.get("source", ""),
            "title": item.get("title", ""),
            "summary": item.get("summary", "")[:300],
            "url": item.get("url", ""),
            "category": item.get("category", ""),
            "priority": item.get("priority", ""),
        })

    data_text = json.dumps(compressed, ensure_ascii=False, indent=1)

    if len(data_text) > 80000:
        data_text = data_text[:80000] + "\n... (truncated)"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=12000,
        messages=[
            {
                "role": "user",
                "content": ANALYSIS_PROMPT + data_text,
            }
        ],
    )

    response_text = message.content[0].text

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    return json.loads(response_text.strip())


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
def translate_report(zh_markdown: str) -> str:
    """将中文报告翻译为英文"""
    client = create_client()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=12000,
        messages=[
            {
                "role": "user",
                "content": TRANSLATE_PROMPT + zh_markdown,
            }
        ],
    )

    return message.content[0].text
