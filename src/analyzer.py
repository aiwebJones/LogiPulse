"""
LogiPulse — AI 分析引擎
使用 Claude 对采集到的物流行业信息进行分析、归类、提炼
"""

import json
import logging
import os
from datetime import datetime

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """你是一位资深国际空运物流行业分析师，同时精通中英文。你的任务是从今天采集到的行业信息中，提炼出一份高质量的每日行业简报。

## 你的读者画像
- 中国国际空运货代从业者（主要）
- 外贸企业物流负责人
- 供应链管理者
- 需要快速了解行业动态的决策者

## 分析要求

请从以下原始数据中，按照下面的结构输出分析结果。**只输出 JSON**，不要输出其他内容。

### 输出 JSON 结构

```json
{
  "date": "YYYY-MM-DD",
  "market_pulse": {
    "summary": "一段话概括今日市场整体态势（中文，100-150字）",
    "sentiment": "bullish/neutral/bearish",
    "key_signals": [
      {
        "signal": "信号描述",
        "source": "信息来源",
        "impact": "对货代的影响",
        "url": "原文链接"
      }
    ]
  },
  "rate_trends": {
    "summary": "运价走势概述（如有数据）",
    "highlights": [
      {
        "route": "航线/区域",
        "direction": "up/down/stable",
        "detail": "具体描述",
        "source": "来源"
      }
    ]
  },
  "fuel_update": {
    "summary": "燃油价格动态概述",
    "highlights": ["要点1", "要点2"]
  },
  "top_stories": [
    {
      "title_zh": "中文标题",
      "title_en": "English Title",
      "summary_zh": "中文摘要（100-200字，突出对货代的影响）",
      "summary_en": "English summary (80-150 words, focus on freight forwarder impact)",
      "source": "来源名",
      "url": "链接",
      "category": "分类标签",
      "importance": "high/medium/low"
    }
  ],
  "regulatory_alerts": [
    {
      "title": "政策/监管动态标题",
      "detail": "具体内容和影响分析",
      "region": "影响区域",
      "urgency": "immediate/upcoming/watch"
    }
  ],
  "tech_innovation": [
    {
      "title": "技术/平台/工具动态",
      "detail": "对行业的影响",
      "source": "来源"
    }
  ],
  "action_items": [
    "基于今日信息，货代从业者应该关注/行动的具体建议1",
    "建议2",
    "建议3"
  ],
  "quote_of_the_day": {
    "text": "今日最值得记住的一句话/观点",
    "source": "出处"
  }
}
```

## 分析原则

1. **实用优先**：每条信息都要回答"这对中国货代意味着什么？"
2. **信号思维**：识别趋势变化的早期信号，而非重复已知事实
3. **运价敏感**：任何可能影响空运运价的信息都需要高亮
4. **风险预警**：政策变化、航线调整、燃油波动等风险需要及时提醒
5. **去重提炼**：多个源报道同一事件时，合并为一条，标注多个来源
6. **top_stories 控制在 5-8 条**，quality over quantity
7. **如果某个板块今日没有相关信息，该字段留空数组即可**

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
    """使用 Claude 分析采集到的信息"""
    client = create_client()

    # 压缩数据: 只传关键字段
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

    # 如果数据太长，截断
    if len(data_text) > 80000:
        data_text = data_text[:80000] + "\n... (truncated)"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": ANALYSIS_PROMPT + data_text,
            }
        ],
    )

    response_text = message.content[0].text

    # 提取 JSON
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
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": TRANSLATE_PROMPT + zh_markdown,
            }
        ],
    )

    return message.content[0].text
