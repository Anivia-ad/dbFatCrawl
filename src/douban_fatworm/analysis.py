from __future__ import annotations

from collections import Counter
from base64 import b64encode
from html import escape
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from wordcloud import WordCloud


def rows_to_frame(rows: Iterable) -> pd.DataFrame:
    records = [dict(row) for row in rows]
    return pd.DataFrame.from_records(records)


def summarize(rows: Iterable) -> dict:
    df = rows_to_frame(rows)
    if df.empty:
        return {
            "total": 0,
            "avg_rating": 0,
            "max_rating": None,
            "top_count": None,
            "years": 0,
            "top_tags": [],
        }
    numeric_rating = pd.to_numeric(df["rating"], errors="coerce")
    years = pd.to_numeric(df["year"], errors="coerce").dropna()
    tags = collect_tags(df.get("tags", pd.Series(dtype=str)).fillna("").tolist())
    avg_rating = float(numeric_rating.mean(skipna=True)) if numeric_rating.notna().any() else 0
    return {
        "total": int(len(df)),
        "avg_rating": round(avg_rating, 2),
        "max_rating": row_to_dict(df.loc[numeric_rating.idxmax()]) if numeric_rating.notna().any() else None,
        "top_count": row_to_dict(df.sort_values("rating_count", ascending=False).iloc[0]) if "rating_count" in df else None,
        "years": int(years.nunique()),
        "top_tags": tags.most_common(10),
    }


def generate_charts(rows: Iterable, chart_dir: str | Path) -> dict[str, str]:
    configure_matplotlib_font()
    df = rows_to_frame(rows)
    output_dir = Path(chart_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex[:8]
    charts: dict[str, str] = {}
    if df.empty:
        return charts

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").fillna(0)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    valid_rating = df.dropna(subset=["rating"])
    if not valid_rating.empty:
        charts["rating_hist"] = save_rating_hist(valid_rating, output_dir, run_id)
        charts["rating_count_scatter"] = save_rating_count_scatter(valid_rating, output_dir, run_id)

    by_year = valid_rating.dropna(subset=["year"])
    if not by_year.empty:
        charts["year_trend"] = save_year_trend(by_year, output_dir, run_id)

    tag_text = " ".join(tag for tag, count in collect_tags(df.get("tags", pd.Series(dtype=str)).fillna("").tolist()).items() for _ in range(count))
    if tag_text.strip():
        charts["wordcloud"] = save_wordcloud(tag_text, output_dir, run_id)

    return charts


def ranking(rows: Iterable, limit: int = 10) -> list[dict]:
    df = rows_to_frame(rows)
    if df.empty:
        return []
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce").fillna(0)
    ranked = df.sort_values(["rating", "rating_count"], ascending=[False, False]).head(limit)
    return [normalize_ranking_item(row_to_dict(row)) for _, row in ranked.iterrows()]


def compare(rows: Iterable) -> list[dict]:
    return [row_to_dict(row) for row in rows]


def build_report(rows: Iterable, charts: dict[str, str], output_path: str | Path) -> Path:
    summary = summarize(rows)
    ranks = ranking(rows, 10)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    chart_html = "\n".join(report_image_tag(name, path) for name, path in charts.items())
    rank_html = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('title', '') or ''))}</td>"
        f"<td>{escape(str(item.get('creator', '') or ''))}</td>"
        f"<td>{escape(str(item.get('summary', '') or ''))}</td>"
        f"<td>{escape(str(item.get('year') or ''))}</td>"
        f"<td>{escape(str(item.get('rating') or ''))}</td>"
        f"<td>{escape(str(item.get('rating_count') or 0))}</td>"
        "</tr>"
        for item in ranks
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>豆瓣肥虫数据分析报告</title>
  <style>
    body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 32px; color: #1f2937; }}
    img {{ max-width: 720px; display: block; margin: 20px 0; border: 1px solid #d1d5db; }}
    table {{ border-collapse: collapse; table-layout: fixed; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    td:nth-child(3) {{ word-break: break-word; }}
  </style>
</head>
<body>
  <h1>豆瓣肥虫数据分析报告</h1>
  <p>数据总量：{summary['total']}，平均评分：{summary['avg_rating']}，覆盖年份数：{summary['years']}</p>
  <h2>可视化图表</h2>
  {chart_html or '<p>暂无足够数据生成图表。</p>'}
  <h2>排行榜</h2>
  <table>
    <thead><tr><th>标题</th><th>作者/导演</th><th>简介</th><th>年份</th><th>评分</th><th>评价人数</th></tr></thead>
    <tbody>{rank_html or '<tr><td colspan="6">暂无数据</td></tr>'}</tbody>
  </table>
</body>
</html>
"""
    output.write_text(html, encoding="utf-8")
    return output


def save_rating_hist(df: pd.DataFrame, output_dir: Path, run_id: str) -> str:
    path = output_dir / f"rating_hist_{run_id}.png"
    plt.figure(figsize=(8, 4.5))
    plt.hist(df["rating"], bins=10, color="#2563eb", edgecolor="white")
    plt.title("评分分布")
    plt.xlabel("评分")
    plt.ylabel("作品数量")
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return str(path)


def save_year_trend(df: pd.DataFrame, output_dir: Path, run_id: str) -> str:
    path = output_dir / f"year_trend_{run_id}.png"
    trend = df.groupby("year")["rating"].mean().sort_index()
    plt.figure(figsize=(8, 4.5))
    plt.plot(trend.index.astype(int), trend.values, marker="o", color="#059669")
    plt.title("年份与平均评分趋势")
    plt.xlabel("年份")
    plt.ylabel("平均评分")
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return str(path)


def save_rating_count_scatter(df: pd.DataFrame, output_dir: Path, run_id: str) -> str:
    path = output_dir / f"rating_count_scatter_{run_id}.png"
    plt.figure(figsize=(8, 4.5))
    plt.scatter(df["rating_count"], df["rating"], alpha=0.72, color="#dc2626")
    plt.title("评价人数与评分")
    plt.xlabel("评价人数")
    plt.ylabel("评分")
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return str(path)


def save_wordcloud(text: str, output_dir: Path, run_id: str) -> str:
    path = output_dir / f"tags_wordcloud_{run_id}.png"
    font_path = find_chinese_font()
    cloud = WordCloud(width=900, height=480, background_color="white", font_path=font_path).generate(text)
    cloud.to_file(path)
    return str(path)


def collect_tags(values: Iterable[str]) -> Counter:
    counter: Counter = Counter()
    for value in values:
        for tag in str(value or "").replace("，", ",").split(","):
            tag = tag.strip()
            if tag:
                counter[tag] += 1
    return counter


def row_to_dict(row) -> dict:
    if hasattr(row, "to_dict"):
        data = row.to_dict()
    else:
        data = dict(row)
    return {key: (None if pd.isna(value) else value) for key, value in data.items()}


def normalize_ranking_item(item: dict) -> dict:
    creator = str(item.get("creator") or "").strip()
    summary = str(item.get("summary") or "").strip()
    if creator and not summary and looks_like_summary(creator):
        item["summary"] = creator
        item["creator"] = ""
    elif creator and summary == creator and looks_like_summary(creator):
        item["creator"] = ""
    return item


def looks_like_summary(value: str) -> bool:
    return len(value) >= 40 or any(mark in value for mark in ("。", "，", "...", "…"))


def find_chinese_font() -> str | None:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def configure_matplotlib_font() -> None:
    font_path = find_chinese_font()
    if font_path:
        font_manager.fontManager.addfont(font_path)
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.sans-serif"] = [font_name, *plt.rcParams.get("font.sans-serif", [])]
    plt.rcParams["axes.unicode_minus"] = False


def report_image_tag(name: str, path: str) -> str:
    image_path = Path(path)
    if not image_path.exists():
        return ""
    data = b64encode(image_path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}" alt="{escape(name)}">'
