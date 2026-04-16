"""
LogiPulse — 信息采集器
从 RSS、网页、API 等多种源采集国际物流行业信息
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import feedparser
import httpx
import yaml
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}


def load_sources(config_path: str = "config/sources.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def fetch_url(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.text


async def collect_rss(client: httpx.AsyncClient, source: dict) -> list[dict]:
    """采集 RSS 源，返回最近 24 小时的条目"""
    rss_url = source.get("rss", source["url"])
    try:
        raw = await fetch_url(client, rss_url)
    except Exception as e:
        logger.warning(f"[RSS] Failed to fetch {source['name']}: {e}")
        return []

    feed = feedparser.parse(raw)
    cutoff = datetime.now() - timedelta(hours=48)
    items = []

    for entry in feed.entries[:20]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published = datetime(*entry.updated_parsed[:6])

        if published and published < cutoff:
            continue

        summary = ""
        if hasattr(entry, "summary"):
            soup = BeautifulSoup(entry.summary, "html.parser")
            summary = soup.get_text(strip=True)[:500]

        items.append({
            "source": source["name"],
            "category": source.get("category", "news"),
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": summary,
            "published": published.isoformat() if published else None,
            "language": source.get("language", "en"),
            "priority": source.get("priority", "medium"),
        })

    logger.info(f"[RSS] {source['name']}: {len(items)} items")
    return items


async def collect_web(client: httpx.AsyncClient, source: dict) -> list[dict]:
    """采集网页，提取标题和摘要"""
    try:
        html = await fetch_url(client, source["url"])
    except Exception as e:
        logger.warning(f"[WEB] Failed to fetch {source['name']}: {e}")
        return []

    soup = BeautifulSoup(html, "lxml")
    items = []

    # 通用提取策略: 查找文章链接
    selectors = [
        "article",
        ".post",
        ".news-item",
        ".article-item",
        ".blog-post",
        ".card",
        ".list-item",
        "li.item",
    ]

    articles = []
    for selector in selectors:
        articles = soup.select(selector)
        if articles:
            break

    if not articles:
        # Fallback: 提取所有 <a> 中包含关键词的链接
        articles = soup.find_all("a", href=True)
        articles = [
            a for a in articles
            if a.get_text(strip=True) and len(a.get_text(strip=True)) > 20
        ][:15]

    for article in articles[:10]:
        title = ""
        link = ""
        summary = ""

        if article.name == "a":
            title = article.get_text(strip=True)[:200]
            link = article.get("href", "")
        else:
            heading = article.find(["h1", "h2", "h3", "h4", "a"])
            if heading:
                title = heading.get_text(strip=True)[:200]
                if heading.name == "a":
                    link = heading.get("href", "")
                else:
                    a_tag = heading.find("a") or article.find("a")
                    if a_tag:
                        link = a_tag.get("href", "")

            desc = article.find(["p", ".summary", ".excerpt", ".description"])
            if desc:
                summary = desc.get_text(strip=True)[:500]

        if not title:
            continue

        # 补全相对 URL
        if link and not link.startswith("http"):
            from urllib.parse import urljoin
            link = urljoin(source["url"], link)

        items.append({
            "source": source["name"],
            "category": source.get("category", "news"),
            "title": title,
            "url": link or source["url"],
            "summary": summary,
            "published": None,
            "language": source.get("language", "en"),
            "priority": source.get("priority", "medium"),
        })

    logger.info(f"[WEB] {source['name']}: {len(items)} items")
    return items


async def collect_all(
    config_path: str = "config/sources.yaml",
    categories: list[str] | None = None,
    priority_filter: list[str] | None = None,
) -> list[dict]:
    """并发采集所有信息源"""
    sources_config = load_sources(config_path)
    priority_filter = priority_filter or ["critical", "high", "medium"]

    all_sources = []
    for category_name, sources in sources_config.items():
        if categories and category_name not in categories:
            continue
        for s in sources:
            s["category"] = category_name
            if s.get("priority", "medium") in priority_filter:
                all_sources.append(s)

    logger.info(f"Collecting from {len(all_sources)} sources...")

    async with httpx.AsyncClient() as client:
        tasks = []
        for source in all_sources:
            if source.get("type") == "rss":
                tasks.append(collect_rss(client, source))
            else:
                tasks.append(collect_web(client, source))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Collection error: {result}")

    logger.info(f"Total collected: {len(all_items)} items")
    return all_items


def save_raw(items: list[dict], output_dir: str = "data") -> Path:
    """保存原始采集数据为 YAML"""
    import json
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filepath = output_path / f"raw-{today}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(items)} items to {filepath}")
    return filepath
