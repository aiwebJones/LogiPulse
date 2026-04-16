#!/usr/bin/env python3
"""
LogiPulse — 国际物流每日情报系统
主入口：采集 → 分析 → 生成日报

Usage:
    python run.py                  # 运行完整流程 (采集+分析+生成)
    python run.py --collect-only   # 仅采集数据
    python run.py --from-cache     # 从缓存数据生成报告 (不重新采集)
    python run.py --dry-run        # 仅采集，使用示例分析结果生成报告 (不调用AI)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# 确保项目根目录在 path 中
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.collector import collect_all, save_raw
from src.analyzer import analyze_items
from src.reporter import save_reports

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("logipulse")


DEMO_ANALYSIS = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "layer1_input": {
        "headline": "中东航线运力收缩，亚欧价格重估开始",
        "supply_signals": [
            {
                "signal": "A4E呼吁欧盟采取临时措施应对中东冲突，多家航司调整中东绕飞路线，有效运力下降约8%",
                "source": "Air Cargo News",
                "url": "https://www.aircargonews.net",
                "severity": "high",
            },
            {
                "signal": "法兰克福机场3月货量逆势增长0.4%至185,500吨，preighters重新投入中东运营",
                "source": "Air Cargo News",
                "url": "https://www.aircargonews.net",
                "severity": "medium",
            },
            {
                "signal": "National Airlines接收首架777F货机，中美远程运力将增加",
                "source": "Air Cargo News",
                "url": "https://www.aircargonews.net",
                "severity": "medium",
            },
        ],
        "demand_signals": [
            {
                "signal": "跨境电商旺季备货需求提前释放，Temu/SHEIN包裹量周环比增长15%",
                "source": "FreightWaves",
                "url": "https://www.freightwaves.com",
                "severity": "high",
            },
            {
                "signal": "Dachser警告地缘政治推动中德海空运费率大幅上涨，客户开始锁舱",
                "source": "The Loadstar",
                "url": "https://theloadstar.com",
                "severity": "high",
            },
        ],
        "rule_signals": [
            {
                "signal": "美国CBP关税退税门户4月20日上线，约1270亿美元退税待处理",
                "source": "US CBP",
                "url": "https://www.cbp.gov/newsroom",
                "severity": "high",
                "deadline": "2026-04-20",
            },
            {
                "signal": "美国CBP更新锂电池空运安检要求，旧版UN38.3报告5月1日后不再接受",
                "source": "US CBP",
                "url": "https://www.cbp.gov",
                "severity": "high",
                "deadline": "2026-05-01",
            },
            {
                "signal": "EU CBAM 首个证书价格发布，碳边境调节机制进入实质运行",
                "source": "EU DG TAXUD",
                "url": "https://taxation-customs.ec.europa.eu",
                "severity": "medium",
                "deadline": "2026-04-30",
            },
        ],
    },
    "layer2_explain": {
        "core_logic": (
            "今天的核心逻辑链：中东冲突持续 → 航司绕飞增加燃油成本+飞行时间 → "
            "亚欧有效运力下降约8% → 稀缺性上升 → 运价进入重估周期。"
            "同时，电商旺季备货提前释放需求，供需两端同时收紧。"
            "关键判断：这不是短期波动，是结构性的运力收缩。"
            "客户会问「为什么涨」——你的回答不是「因为旺季」，"
            "而是「因为能飞的路线在减少，确定性在变贵」。"
        ),
        "certainty_index": "volatile",
        "causal_chains": [
            {
                "cause": "中东地缘冲突升级",
                "effect": "航司绕飞增加2-3小时航程，部分中东中转航线暂停",
                "implication": "亚欧直飞舱位稀缺，溢价空间扩大¥3-5/kg",
            },
            {
                "cause": "电商备货需求提前释放",
                "effect": "Temu/SHEIN包裹量激增，占据大量腹舱运力",
                "implication": "普货被电商挤占舱位，大件客户需提前2周预订",
            },
            {
                "cause": "美国关税退税门户即将上线",
                "effect": "进口商现金流改善，可能增加补货采购",
                "implication": "中美线5月可能出现一波补货需求，提前锁价有利",
            },
        ],
    },
    "layer3_translate": {
        "by_route": [
            {
                "route": "PVG-FRA（上海→法兰克福）",
                "status": "hot",
                "rate_direction": "up",
                "detail": "中东绕飞叠加电商备货，本周涨¥1.5-2/kg，预计持续到5月中旬",
                "forwarder_talk": "张总，欧洲线这周又涨了，不是我们在涨价——是中东那边绕飞导致能飞的路线在减少。建议您这批货这周确认，下周可能还要调。",
            },
            {
                "route": "PVG-LAX（上海→洛杉矶）",
                "status": "stable",
                "rate_direction": "stable",
                "detail": "暂时平稳，但National Airlines新增777F运力尚未消化，关注5月GRI",
                "forwarder_talk": "王总，美线目前还算稳定，但5月有GRI预期。如果有5月的货，建议这两周先把价格锁了。",
            },
            {
                "route": "PVG-DXB（上海→迪拜）",
                "status": "volatile",
                "rate_direction": "up",
                "detail": "中东局势导致部分航司暂停或减频，运力紧张，涨幅约4-6%",
                "forwarder_talk": "李总，中东线现在很不稳定，不是价格问题——是能不能走的问题。我帮你盯着舱位，有了第一时间通知你。",
            },
        ],
        "by_product": [
            {
                "product": "超大件/项目货",
                "impact": "中东绕飞导致全货机舱位更紧，超大件排期拉长，建议提前3周预订",
                "opportunity_or_risk": "opportunity",
            },
            {
                "product": "危险品(DG)",
                "impact": "锂电池新规5月1日生效，DG客户需紧急更新UN38.3报告",
                "opportunity_or_risk": "risk",
            },
            {
                "product": "电商小包",
                "impact": "Temu/SHEIN备货挤占腹舱，电商渠道价格竞争白热化",
                "opportunity_or_risk": "neutral",
            },
            {
                "product": "返修件/RMA",
                "impact": "美国关税退税门户上线后，返修件流程可能简化，关注政策细节",
                "opportunity_or_risk": "opportunity",
            },
        ],
        "by_customer": [
            {
                "customer_type": "欧洲线大客户（汽车零部件/机械）",
                "behavior_prediction": "会主动询价，因为他们的德国客户在催货",
                "your_move": "主动打电话报价，强调\"现在锁舱比下周便宜\"",
            },
            {
                "customer_type": "中东线客户",
                "behavior_prediction": "会犹豫要不要发，因为不确定性太高",
                "your_move": "提供替代方案（如转经IST中转），把\"不确定\"变成\"有方案\"",
            },
            {
                "customer_type": "DG/锂电池客户",
                "behavior_prediction": "大多数还没注意到5月新规",
                "your_move": "今天就发一条提醒消息，建立\"专业可靠\"的认知",
            },
        ],
    },
    "layer4_action": {
        "money_moves": [
            {
                "opportunity": "亚欧线锁舱套利：本周订5月上旬的FRA舱位，预计下周GRI后可多赚¥2-3/kg",
                "why_now": "航司5月GRI通知已出，本周是最后窗口",
                "expected_margin": "较当前报价多¥2-3/kg利润空间",
            },
            {
                "opportunity": "DG客户服务升级：主动帮锂电池客户对接UN38.3报告更新，绑定长期合作",
                "why_now": "5月1日deadline临近，同行还没反应过来",
                "expected_margin": "服务溢价 + 客户粘性，长期价值远超单票利润",
            },
            {
                "opportunity": "中东线替代路径方案：为DXB客户设计IST/DOH中转方案，在\"别人说走不了\"的时候你说\"我有办法\"",
                "why_now": "中东局势不会短期缓解，替代方案需求持续存在",
                "expected_margin": "复杂路径溢价约15-20%",
            },
        ],
        "pricing_strategy": {
            "conservative": "亚欧线按当前市场价+¥1/kg报，强调\"本周价格，下周不保\"",
            "standard": "按当前市场价+¥2/kg报，含下周GRI预期，提供\"本周确认锁价\"优惠",
            "aggressive": "按下周GRI后价格直接报，客户如果嫌贵就说\"这是下周的价格，我今天可以帮你锁住\"",
            "rationale": "市场在涨价通道中，报价策略的核心是制造紧迫感——不是让客户觉得便宜，是让客户觉得\"现在不定就更贵\"",
        },
        "call_list": [
            {
                "who": "欧洲线前10大客户",
                "why": "运价上涨+GRI预期，他们需要提前锁舱",
                "talking_point": "张总，下周欧洲线有一波GRI，我帮你先把舱位锁了，价格按今天的算。",
            },
            {
                "who": "所有DG/锂电池客户",
                "why": "5月1日美国新规deadline，大多数人还不知道",
                "talking_point": "王总，提醒一下，5月1日开始美线锂电池需要新版UN38.3报告，旧版不认了。需要我帮你对接检测机构吗？",
            },
            {
                "who": "中东线有询价未成交的客户",
                "why": "局势波动=价格在变，之前嫌贵的客户现在可能接受了",
                "talking_point": "李总，中东线最近运力很紧，但我这边有一个IST中转的方案可以走，您看要不要先锁一个舱位？",
            },
        ],
        "team_brief": (
            "今天早会三个重点：第一，欧洲线在涨，下周有GRI，今天所有欧洲线报价都加一句"
            "「本周价格，下周不保」，制造紧迫感。第二，美国锂电池新规5月1日生效，"
            "今天下午所有DG客户发一条提醒消息，模板我发群里。第三，中东线不要说「走不了」，"
            "要说「我有替代方案」。客户要的不是最便宜的价格，是确定性——"
            "谁能给他确定性，他就跟谁走。"
        ),
    },
    "fuel_snapshot": {
        "summary": "航空煤油价格本周小幅回落1.2%，布伦特原油$82-84/桶区间震荡，中东局势仍是最大变量。",
        "impact_on_fsc": "本月FSC标准不变，但5月可能因中东风险溢价上调。建议报价时预留FSC调整空间。",
    },
    "quote_of_the_day": {
        "text": "客户不是在买运费，是在买「不出事」。谁能给他确定性，他就跟谁走。",
        "context": "这个市场，不是价格决定成交，是确定性决定成交。",
    },
}


async def main():
    parser = argparse.ArgumentParser(description="LogiPulse — 国际物流每日情报系统")
    parser.add_argument("--collect-only", action="store_true", help="仅采集数据，不分析")
    parser.add_argument("--from-cache", action="store_true", help="从缓存数据生成报告")
    parser.add_argument("--dry-run", action="store_true", help="使用示例数据生成报告（不调用AI）")
    parser.add_argument("--output", default="reports", help="输出目录")
    parser.add_argument("--config", default="config/sources.yaml", help="源配置文件路径")
    args = parser.parse_args()

    os.chdir(ROOT)
    output_dir = args.output

    if args.dry_run:
        logger.info("=== DRY RUN: 使用示例数据生成报告 ===")
        zh_path, en_path = save_reports(DEMO_ANALYSIS, output_dir)
        logger.info(f"中文日报: {zh_path}")
        logger.info(f"英文日报: {en_path}")
        print(f"\n✅ 日报已生成（示例数据）:")
        print(f"   中文: {zh_path}")
        print(f"   英文: {en_path}")
        return

    # Step 1: 采集
    if args.from_cache:
        today = datetime.now().strftime("%Y-%m-%d")
        cache_path = Path("data") / f"raw-{today}.json"
        if not cache_path.exists():
            logger.error(f"Cache not found: {cache_path}")
            sys.exit(1)
        with open(cache_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        logger.info(f"Loaded {len(items)} items from cache")
    else:
        logger.info("=== Step 1/3: 采集信息源 ===")
        items = await collect_all(config_path=args.config)
        save_raw(items)

    if args.collect_only:
        print(f"\n✅ 采集完成: {len(items)} 条信息")
        return

    # Step 2: AI 分析
    logger.info("=== Step 2/3: AI 分析 ===")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set, using demo analysis")
        analysis = DEMO_ANALYSIS
    else:
        analysis = analyze_items(items)

    # Step 3: 生成报告
    logger.info("=== Step 3/3: 生成日报 ===")
    zh_path, en_path = save_reports(analysis, output_dir)

    print(f"\n✅ LogiPulse 日报已生成:")
    print(f"   中文: {zh_path}")
    print(f"   英文: {en_path}")
    print(f"   信息源: {len(items)} 条")


if __name__ == "__main__":
    asyncio.run(main())
