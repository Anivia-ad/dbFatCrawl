from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup


DOUBAN_SEARCH_URL = "https://www.douban.com/search"
DOUBAN_MOBILE_API_URL = "https://m.douban.com/rexxar/api/v2"
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


def crawl_douban(
    keyword: str,
    work_type: str = "movie",
    start_year: int | None = None,
    end_year: int | None = None,
    douban_cookie: str = "",
) -> CrawlResult:
    keyword = keyword.strip()
    if not keyword:
        return CrawlResult([], "关键字不能为空")
    if work_type not in {"movie", "book"}:
        return CrawlResult([], "类型必须是 movie 或 book")

    session = requests.Session()
    session.headers.update(HEADERS)
    if douban_cookie.strip():
        session.headers.update({"Cookie": douban_cookie.strip()})
    params = {"q": keyword, "cat": "1002" if work_type == "movie" else "1001"}
    url = f"{DOUBAN_SEARCH_URL}?q={quote_plus(params['q'])}&cat={params['cat']}"
    response = None
    for attempt in range(2):
        try:
            if attempt:
                time.sleep(1.5)
            response = session.get(url, timeout=12)
            if response.status_code in {403, 429}:
                return CrawlResult([], f"豆瓣限制了本次请求（HTTP {response.status_code}），请降低频率或稍后再试")
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == 1:
                return CrawlResult([], f"请求豆瓣失败：{exc}")
    if response is None:
        return CrawlResult([], "请求豆瓣失败：未获得响应")

    items = enrich_with_subject_pages(parse_search_page(response.text, work_type), work_type, session)
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
        source_url = normalize_source_url(title_link.get("href", ""))
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
                "cover_url": extract_image_url(cover),
                "source_url": source_url,
                "tags": tags,
                "summary": info,
            }
        )
    return results


def enrich_with_subject_pages(items: list[dict], work_type: str, session: requests.Session | None = None) -> list[dict]:
    enriched: list[dict] = []
    session = session or requests.Session()
    session.headers.update(HEADERS)
    for item in items:
        source_url = item.get("source_url") or ""
        detail = fetch_subject_detail(source_url, work_type, session) if source_url else {}
        enriched.append(merge_work_data(item, detail))
    return enriched


def merge_work_data(base: dict, *details: dict) -> dict:
    merged = dict(base)
    for detail in details:
        for key, value in detail.items():
            if should_use_detail_value(key, merged.get(key), value):
                merged[key] = normalize_source_url(value) if key == "source_url" else value
    return merged


def should_apply_detail_value(key: str, value) -> bool:
    if value in (None, ""):
        return False
    return not (key == "rating_count" and value == 0)


def should_use_detail_value(key: str, current, value) -> bool:
    if not should_apply_detail_value(key, value):
        return False
    if key == "summary":
        current_text = clean_summary_text(str(current or ""))
        value_text = clean_summary_text(str(value))
        return not current_text or is_truncated_text(current_text) or len(value_text) > len(current_text)
    if key == "source_url":
        return normalize_source_url(str(value)) != str(current or "")
    if key == "cover_url":
        return not current or is_obsolete_cover_url(str(current))
    return True


def is_truncated_text(value: str) -> bool:
    return value.endswith(("...", "…")) or "展开全部" in value


def is_obsolete_cover_url(value: str) -> bool:
    return bool(re.search(r"/p\d+\.jpg$", value)) and "s_ratio_poster" in value


def fetch_subject_detail(url: str, work_type: str, session: requests.Session | None = None) -> dict:
    session = session or requests.Session()
    session.headers.update(HEADERS)
    detail_url = normalize_source_url(url)
    detail: dict = {}
    try:
        response = session.get(detail_url, headers={**HEADERS, "Referer": DOUBAN_SEARCH_URL}, timeout=12)
        if response.status_code not in {403, 429}:
            response.raise_for_status()
            detail = parse_subject_page(response.text, work_type, detail_url)
    except requests.RequestException:
        detail = {}
    mobile_detail = fetch_mobile_subject_detail(detail_url, work_type, session)
    abstract_detail = fetch_subject_abstract_detail(detail_url, work_type, session)
    return merge_work_data(detail, mobile_detail, abstract_detail)


def fetch_mobile_subject_detail(url: str, work_type: str, session: requests.Session | None = None) -> dict:
    subject_id = parse_subject_id(url)
    if not subject_id:
        return {}
    resource = "movie" if work_type == "movie" else "book"
    session = session or requests.Session()
    session.headers.update(HEADERS)
    api_url = f"{DOUBAN_MOBILE_API_URL}/{resource}/{subject_id}?ck=&for_mobile=1"
    try:
        response = session.get(
            api_url,
            headers={**HEADERS, "Referer": f"https://m.douban.com/{resource}/subject/{subject_id}/"},
            timeout=12,
        )
        if response.status_code in {403, 429}:
            return {}
        response.raise_for_status()
        payload = response.json()
    except (ValueError, requests.RequestException):
        return {}
    return parse_mobile_subject_payload(payload, work_type, normalize_source_url(url))


def parse_mobile_subject_payload(payload: dict, work_type: str, source_url: str) -> dict:
    if not isinstance(payload, dict):
        return {}
    rating_payload = payload.get("rating") if isinstance(payload.get("rating"), dict) else {}
    return {
        "title": compact_text(str(payload.get("title") or "")),
        "work_type": work_type,
        "rating": safe_float(str(rating_payload.get("value") or "")),
        "rating_count": parse_count(str(rating_payload.get("count") or "")),
        "creator": parse_mobile_creator(payload, work_type),
        "year": parse_year(str(payload.get("year") or payload.get("pubdate") or payload.get("card_subtitle") or "")),
        "cover_url": parse_mobile_cover(payload),
        "source_url": source_url,
        "tags": parse_mobile_tags(payload),
        "summary": clean_summary_text(str(payload.get("intro") or payload.get("summary") or payload.get("description") or "")),
    }


def parse_mobile_cover(payload: dict) -> str:
    pic = payload.get("pic")
    if isinstance(pic, dict):
        for key in ["large", "normal", "small", "url"]:
            url = normalize_image_url(str(pic.get(key) or ""))
            if url:
                return url
    if isinstance(pic, str):
        return normalize_image_url(pic)
    return ""


def parse_mobile_creator(payload: dict, work_type: str) -> str:
    fields = ["directors"] if work_type == "movie" else ["author", "authors"]
    for field in fields:
        people = parse_people(payload.get(field))
        if people:
            return " / ".join(people)
    return ""


def parse_people(value) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name") or item.get("title")
        else:
            name = item
        name = compact_text(str(name or ""))
        if name:
            names.append(name)
    return names


def parse_mobile_tags(payload: dict) -> str:
    tags = payload.get("tags") or payload.get("genres") or []
    if not isinstance(tags, list):
        return ""
    values: list[str] = []
    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name") or tag.get("title")
        else:
            name = tag
        name = compact_text(str(name or ""))
        if name:
            values.append(name)
    return ", ".join(values)


def fetch_subject_abstract_detail(url: str, work_type: str, session: requests.Session | None = None) -> dict:
    if work_type != "movie":
        return {}
    subject_id = parse_subject_id(url)
    if not subject_id:
        return {}
    session = session or requests.Session()
    session.headers.update(HEADERS)
    try:
        response = session.get(f"https://movie.douban.com/j/subject_abstract?subject_id={subject_id}", timeout=12)
        if response.status_code in {403, 429}:
            return {}
        response.raise_for_status()
        payload = response.json()
    except (ValueError, requests.RequestException):
        return {}
    subject = payload.get("subject") if isinstance(payload, dict) else None
    if not isinstance(subject, dict):
        return {}
    directors = [str(name).strip() for name in subject.get("directors") or [] if str(name).strip()]
    types = [str(name).strip() for name in subject.get("types") or [] if str(name).strip()]
    return {
        "creator": " / ".join(directors),
        "year": parse_year(str(subject.get("release_year") or "")),
        "rating": safe_float(str(subject.get("rate") or "")),
        "tags": ", ".join(types),
    }


def parse_subject_page(html: str, work_type: str, source_url: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    info = compact_text(soup.select_one("#info").get_text(" ", strip=True) if soup.select_one("#info") else "")
    title = parse_subject_title(soup)
    rating_el = soup.select_one("strong.rating_num, .rating_num")
    votes_el = soup.select_one("[property='v:votes'], .rating_people span")
    cover = soup.select_one("#mainpic img, .nbg img")
    summary = parse_subject_summary(soup)
    tags = parse_subject_tags(soup)
    return {
        "title": title,
        "work_type": work_type,
        "rating": safe_float(rating_el.get_text(strip=True)) if rating_el else None,
        "rating_count": parse_count(votes_el.get_text(" ", strip=True)) if votes_el else parse_rating_count(soup.get_text(" ", strip=True)),
        "creator": parse_creator(info, work_type),
        "year": parse_subject_year(soup, info),
        "cover_url": extract_image_url(cover),
        "source_url": source_url,
        "tags": tags or ", ".join(extract_tags(info, title)),
        "summary": summary,
    }


def parse_subject_title(soup: BeautifulSoup) -> str:
    title_el = soup.select_one("h1 span[property='v:itemreviewed'], h1 span")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    return compact_text(re.sub(r"\s*\(\d{4}\)\s*$", "", title))


def parse_subject_summary(soup: BeautifulSoup) -> str:
    selectors = [
        "#link-report span.all",
        "#link-report-intra span.all",
        ".related-info span.all",
        "#link-report [property='v:summary']",
        "#link-report-intra [property='v:summary']",
        ".related-info [property='v:summary']",
        "#link-report .intro",
        "#link-report-intra",
        "#link-report",
    ]
    for selector in selectors:
        summary_el = soup.select_one(selector)
        summary = clean_summary_text(summary_el.get_text(" ", strip=True) if summary_el else "")
        if summary:
            return summary
    return ""


def parse_subject_tags(soup: BeautifulSoup) -> str:
    tags = [compact_text(tag.get_text(" ", strip=True)) for tag in soup.select(".tags-body a")]
    return ", ".join(tag for tag in tags if tag)


def filter_by_year(items: Iterable[dict], start_year: int | None, end_year: int | None) -> list[dict]:
    filtered = []
    for item in items:
        year = item.get("year")
        if (start_year or end_year) and year is None:
            continue
        if start_year and year and year < start_year:
            continue
        if end_year and year and year > end_year:
            continue
        filtered.append(item)
    return filtered


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_summary_text(value: str) -> str:
    value = compact_text(value)
    value = re.sub(r"\s*[（(]?展开全部[）)]?\s*", "", value)
    value = re.sub(r"\s*©豆瓣\s*$", "", value)
    return value.strip()


def extract_image_url(image) -> str:
    if not image:
        return ""
    for attr in ["data-original", "data-src", "src"]:
        url = normalize_image_url(str(image.get(attr) or ""))
        if url:
            return url
    srcset = str(image.get("srcset") or "")
    if srcset:
        last_candidate = srcset.split(",")[-1].strip().split(" ")[0]
        return normalize_image_url(last_candidate)
    return ""


def normalize_image_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    return url


def safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_rating_count(text: str) -> int:
    match = re.search(r"(\d+)\s*人评价", text)
    return int(match.group(1)) if match else 0


def parse_count(text: str) -> int:
    match = re.search(r"\d+", text.replace(",", ""))
    return int(match.group(0)) if match else 0


def parse_year(text: str) -> int | None:
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return int(match.group(1)) if match else None


def parse_subject_year(soup: BeautifulSoup, info: str) -> int | None:
    year_el = soup.select_one("h1 .year")
    if year_el:
        year = parse_year(year_el.get_text(" ", strip=True))
        if year:
            return year
    for label in ["上映日期", "首播", "出版年", "发行日期"]:
        value = parse_labeled_field(info, label)
        year = parse_year(value)
        if year:
            return year
    return parse_year(info)


def parse_creator(text: str, work_type: str) -> str:
    if not text:
        return ""
    label = "导演" if work_type == "movie" else "作者"
    creator = parse_labeled_field(text, label)
    if creator:
        return cleanup_creator(creator)
    parts = [part.strip() for part in re.split(r"[/|]", text) if part.strip()]
    if work_type == "movie":
        for part in parts:
            if "导演" in part:
                return part.replace("导演:", "").replace("导演：", "").strip()
    if work_type == "book":
        for part in parts:
            if "作者" in part:
                return part.replace("作者:", "").replace("作者：", "").strip()
    return ""


def parse_labeled_field(text: str, label: str) -> str:
    labels = [
        "导演",
        "编剧",
        "主演",
        "作者",
        "出版社",
        "出品方",
        "副标题",
        "原作名",
        "译者",
        "出版年",
        "页数",
        "定价",
        "装帧",
        "丛书",
        "ISBN",
        "类型",
        "制片国家/地区",
        "语言",
        "首播",
        "上映日期",
        "片长",
        "季数",
        "集数",
        "单集片长",
        "又名",
        "IMDb",
    ]
    other_labels = [name for name in labels if name != label]
    pattern = rf"{re.escape(label)}[:：]\s*(.*?)(?=\s+(?:{'|'.join(map(re.escape, other_labels))})[:：]|$)"
    match = re.search(pattern, text)
    return compact_text(match.group(1)) if match else ""


def cleanup_creator(value: str) -> str:
    value = re.sub(r"\s*/\s*更多\.\.\..*$", "", value)
    value = re.sub(r"\s*更多\.\.\..*$", "", value)
    return compact_text(value).strip(" /|")


def normalize_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("douban.com") and parsed.path == "/link2/":
        target = parse_qs(parsed.query).get("url", [""])[0]
        return target or url
    return url


def parse_subject_id(url: str) -> str:
    match = re.search(r"/subject/(\d+)/?", normalize_source_url(url))
    return match.group(1) if match else ""


def extract_tags(info: str, title: str) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,}", f"{title} {info}")
    stop_words = {"电影", "图书", "导演", "作者", "主演", "出版社", "豆瓣"}
    return [word for word in words[:12] if word not in stop_words]
