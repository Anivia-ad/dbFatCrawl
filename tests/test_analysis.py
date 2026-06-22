from __future__ import annotations

from pathlib import Path

from douban_fatworm.analysis import build_report, generate_charts, ranking, summarize
from douban_fatworm.database import all_works, init_db, upsert_work


def test_empty_analysis_is_safe(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    rows = all_works(db_path)

    assert summarize(rows)["total"] == 0
    assert ranking(rows) == []
    assert generate_charts(rows, tmp_path / "charts") == {}


def test_analysis_generates_summary_ranking_and_charts(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    upsert_work(db_path, {"title": "作品一", "work_type": "movie", "rating": 9.2, "rating_count": 300, "year": 2020, "tags": "剧情,经典"})
    upsert_work(db_path, {"title": "作品二", "work_type": "movie", "rating": 8.1, "rating_count": 100, "year": 2021, "tags": "剧情,科幻"})

    rows = all_works(db_path)
    charts = generate_charts(rows, tmp_path / "charts")

    assert summarize(rows)["avg_rating"] == 8.65
    assert ranking(rows)[0]["title"] == "作品一"
    assert {"rating_hist", "rating_count_scatter", "year_trend", "wordcloud"}.issubset(charts)


def test_summary_without_ratings_uses_zero(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    upsert_work(db_path, {"title": "未评分", "work_type": "book"})

    assert summarize(all_works(db_path))["avg_rating"] == 0


def test_report_escapes_user_data_and_embeds_images(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    upsert_work(db_path, {"title": "<script>alert(1)</script>", "work_type": "movie", "rating": 8, "year": 2020, "tags": "测试"})
    rows = all_works(db_path)
    charts = generate_charts(rows, tmp_path / "charts")
    report = build_report(rows, charts, tmp_path / "report.html")
    html = report.read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "data:image/png;base64" in html
