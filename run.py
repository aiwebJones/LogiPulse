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
    "market_pulse": {
        "summary": (
            "今日全球空运市场整体偏强运行。亚欧航线运价继续小幅上涨，"
            "主要受益于跨境电商旺季备货需求拉动。北美航线保持稳定，"
            "但部分航司已开始释放五月GRI信号。中东转运枢纽吞吐量持续增长，"
            "迪拜和多哈货站处理量同比上升12%。需关注红海局势对亚欧海运转空运的溢出效应。"
        ),
        "sentiment": "bullish",
        "key_signals": [
            {
                "signal": "亚欧空运运价周环比上涨 3-5%",
                "source": "TAC Index",
                "impact": "货代可适当锁定舱位，避免GRI后被动提价",
                "url": "https://www.tacindex.com",
            },
            {
                "signal": "IATA 3月全球货运需求同比增长 8.2%",
                "source": "IATA",
                "impact": "行业景气度持续，利好空运货量增长",
                "url": "https://www.iata.org",
            },
            {
                "signal": "Flexport 宣布推出 AI 自动报价系统",
                "source": "FreightWaves",
                "impact": "数字化竞争加剧，传统货代需加速工具建设",
                "url": "https://www.freightwaves.com",
            },
        ],
    },
    "rate_trends": {
        "summary": "空运运价整体呈现分化走势：亚欧偏强，跨太平洋稳定，区域内航线竞争加剧。",
        "highlights": [
            {
                "route": "上海→法兰克福 (PVG-FRA)",
                "direction": "up",
                "detail": "普货 ¥32-35/kg，周涨 ¥1.5，电商旺季效应",
                "source": "TAC Index",
            },
            {
                "route": "上海→洛杉矶 (PVG-LAX)",
                "direction": "stable",
                "detail": "普货 ¥28-31/kg，持平，关注5月GRI",
                "source": "WorldACD",
            },
            {
                "route": "香港→迪拜 (HKG-DXB)",
                "direction": "up",
                "detail": "中东转运需求旺盛，涨幅约 4%",
                "source": "Clive Data",
            },
        ],
    },
    "fuel_update": {
        "summary": "航空煤油价格本周小幅回落 1.2%，布伦特原油在 $82-84/桶区间震荡。",
        "highlights": [
            "新加坡航煤现货价 $96.5/桶，周跌 $1.2",
            "IATA 燃油附加费标准本月不变，下月可能下调",
            "中东地缘风险仍是油价最大不确定性因素",
        ],
    },
    "top_stories": [
        {
            "title_zh": "IATA：3月全球航空货运需求同比增长8.2%，连续第5个月正增长",
            "title_en": "IATA: Global Air Cargo Demand Up 8.2% YoY in March, 5th Consecutive Month of Growth",
            "summary_zh": (
                "IATA最新数据显示，3月全球航空货运需求（以CTK计）同比增长8.2%，"
                "超出市场预期。亚太地区贡献最大增量，其中中国出口需求尤为强劲。"
                "对货代而言，需求持续增长意味着旺季可能提前，建议提前锁定核心航线舱位。"
            ),
            "summary_en": (
                "IATA's latest data shows global air cargo demand (CTK) grew 8.2% YoY in March, "
                "exceeding market expectations. Asia-Pacific contributed the largest increment, "
                "with Chinese export demand particularly strong. For forwarders, sustained growth "
                "suggests peak season may arrive early — consider securing core route capacity now."
            ),
            "source": "IATA",
            "url": "https://www.iata.org/en/iata-repository/publications/economic-reports/",
            "category": "market_data",
            "importance": "high",
        },
        {
            "title_zh": "Flexport 推出 AI 自动报价系统，可在30秒内完成全球空运报价",
            "title_en": "Flexport Launches AI Auto-Quoting System — Global Air Freight Quotes in 30 Seconds",
            "summary_zh": (
                "数字化货代巨头 Flexport 宣布推出基于大模型的自动报价系统，"
                "集成了全球200+航司实时运价数据。该系统可在30秒内生成包含多方案对比的报价单。"
                "这一举措将进一步压缩传统货代的报价时间优势，"
                "国内货代需加速自身数字化工具建设以应对竞争。"
            ),
            "summary_en": (
                "Digital freight giant Flexport unveiled an LLM-powered auto-quoting system "
                "integrating real-time rates from 200+ carriers globally. The system generates "
                "multi-option quotes in 30 seconds. This move further compresses the quoting "
                "advantage of traditional forwarders — domestic forwarders must accelerate "
                "their digital tool development to stay competitive."
            ),
            "source": "FreightWaves",
            "url": "https://www.freightwaves.com",
            "category": "tech_innovation",
            "importance": "high",
        },
        {
            "title_zh": "中国海关总署：4月1日起调整部分商品进出口关税",
            "title_en": "China Customs: Import/Export Tariff Adjustments Effective April 1",
            "summary_zh": (
                "海关总署发布公告，自4月1日起对部分机电产品、化工原料的进出口关税进行调整。"
                "其中新能源汽车零部件出口退税率提高至16%，锂电池相关产品也有调整。"
                "这些变化将直接影响相关品类的空运出口量，"
                "货代应提前通知相关客户并调整操作流程。"
            ),
            "summary_en": (
                "China's General Administration of Customs announced tariff adjustments "
                "for certain mechanical, electrical, and chemical products effective April 1. "
                "NEV components export tax rebate increased to 16%, with lithium battery "
                "products also adjusted. These changes will directly impact air cargo "
                "volumes for related categories."
            ),
            "source": "中国海关总署",
            "url": "http://www.customs.gov.cn/",
            "category": "regulatory",
            "importance": "high",
        },
    ],
    "regulatory_alerts": [
        {
            "title": "EU CBAM 碳边境调节机制过渡期报告截止日提醒",
            "detail": "2026年Q1报告截止日为4月30日，涉及钢铁、铝、水泥等品类出口欧盟的碳排放申报。货代需提醒相关客户准备申报材料。",
            "region": "欧盟",
            "urgency": "upcoming",
        },
        {
            "title": "美国 CBP 更新锂电池空运安检要求",
            "detail": "自5月1日起，所有含锂电池货物空运入境美国需附带新版UN38.3测试报告，旧版将不再接受。",
            "region": "美国",
            "urgency": "upcoming",
        },
    ],
    "tech_innovation": [
        {
            "title": "cargo.one 新增东南亚5家航司运价对接",
            "detail": "新增 Bangkok Airways Cargo、Vietnam Airlines Cargo 等5家东南亚航司实时运价，覆盖曼谷、河内、胡志明等枢纽。",
            "source": "cargo.one",
        },
        {
            "title": "CargoAi 推出 AI 预测工具，准确率达 92%",
            "detail": "基于历史数据和市场信号预测未来7天运价走势，目前覆盖亚欧、跨太平洋主要航线。",
            "source": "CargoAi",
        },
    ],
    "action_items": [
        "亚欧航线运价上行，建议本周锁定5月前两周的核心舱位",
        "关注美国锂电池新规（5月1日生效），提前通知DG客户更新UN38.3报告",
        "IATA货量数据持续向好，可适当加大市场开拓力度，特别是电商和新能源品类",
        "学习 Flexport 的AI报价模式，思考自身报价流程的数字化升级路径",
    ],
    "quote_of_the_day": {
        "text": "在物流行业，信息差正在快速消失。未来赢的不是报价最低的人，是响应最快、判断最准的人。",
        "source": "Jones · LogiPulse",
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
