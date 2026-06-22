from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


DOUBAN_SEARCH_URL = "https://www.douban.com/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


@dataclass
class CrawlResult:
    items: list[dict]
    error: str = ""


def crawl_douban(keyword: str, work_type: str = "movie", start_year: int | None = None, end_year: int | None = None) -> CrawlResult:
    keyword = keyword.strip()
    if not keyword:
        return CrawlResult([], "关键字不能为空")
    if work_type not in {"movie", "book"}:
        return CrawlResult([], "类型必须是 movie 或 book")

    params = {"q": keyword, "cat": "1002" if work_type == "movie" else "1001"}
    url = f"{DOUBAN_SEARCH_URL}?q={quote_plus(params['q'])}&cat={params['cat']}"
    response = None
    for attempt in range(2):
        try:
            if attempt:
                time.sleep(1.5)
            response = requests.get(url, headers=HEADERS, timeout=12)
            if response.status_code in {403, 429}:
                return CrawlResult([], f"豆瓣限制了本次请求（HTTP {response.status_code}），请降低频率或稍后再试")
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == 1:
                return CrawlResult([], f"请求豆瓣失败：{exc}")
    if response is None:
        return CrawlResult([], "请求豆瓣失败：未获得响应")

    items = parse_search_page(response.text, work_type)
    filtered = filter_by_year(items, start_year, end_year)
    if not filtered:
        return CrawlResult([], "未解析到符合条件的数据，可能是页面结构变化或结果为空")
    return CrawlResult(filtered)


def parse_search_page(html: str, work_type: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for result in soup.select(".result"):
        title_link = result.select_one(".title a")
        if not title_link:
            continue
        title = compact_text(title_link.get_text(" ", strip=True))
        source_url = title_link.get("href", "")
        info = compact_text(result.select_one(".content p").get_text(" ", strip=True) if result.select_one(".content p") else "")
        rating_el = result.select_one(".rating_nums")
        rating = safe_float(rating_el.get_text(strip=True)) if rating_el else None
        rating_count = parse_rating_count(result.get_text(" ", strip=True))
        year = parse_year(info)
        creator = parse_creator(info, work_type)
        cover = result.select_one(".pic img")
        tags = ", ".join(extract_tags(info, title))
        results.append(
            {
                "title": title,
                "work_type": work_type,
                "rating": rating,
                "rating_count": rating_count,
                "creator": creator,
                "year": year,
                "cover_url": cover.get("src", "") if cover else "",
                "source_url": source_url,
                "tags": tags,
                "summary": info,
            }
        )
    return results


def filter_by_year(items: Iterable[dict], start_year: int | None, end_year: int | None) -> list[dict]:
    filtered = []
    for item in items:
        year = item.get("year")
        if start_year and year and year < start_year:
            continue
        if end_year and year and year > end_year:
            continue
        filtered.append(item)
    return filtered


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_rating_count(text: str) -> int:
    match = re.search(r"(\d+)\s*人评价", text)
    return int(match.group(1)) if match else 0


def parse_year(text: str) -> int | None:
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return int(match.group(1)) if match else None


def parse_creator(text: str, work_type: str) -> str:
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"[/|]", text) if part.strip()]
    if work_type == "movie":
        for part in parts:
            if "导演" in part:
                return part.replace("导演:", "").replace("导演：", "").strip()
    return parts[0] if parts else ""


def extract_tags(info: str, title: str) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,}", f"{title} {info}")
    stop_words = {"电影", "图书", "导演", "作者", "主演", "出版社", "豆瓣"}
    return [word for word in words[:12] if word not in stop_words]
