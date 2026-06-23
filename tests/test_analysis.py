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
    assert all("_" in Path(path).stem for path in charts.values())


def test_summary_without_ratings_uses_zero(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    upsert_work(db_path, {"title": "未评分", "work_type": "book"})

    assert summarize(all_works(db_path))["avg_rating"] == 0


def test_ranking_moves_polluted_creator_to_summary(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    polluted_summary = "一场谋杀案使银行家安迪蒙冤入狱，谋杀妻子及其情人的指控将囚禁他终生。"
    upsert_work(db_path, {"title": "污染数据", "work_type": "movie", "rating": 9.7, "creator": polluted_summary})

    item = ranking(all_works(db_path))[0]

    assert item["creator"] == ""
    assert item["summary"] == polluted_summary


def test_report_escapes_user_data_and_embeds_images(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    upsert_work(db_path, {"title": "<script>alert(1)</script>", "work_type": "movie", "rating": 8, "year": 2020, "tags": "测试", "summary": "<b>简介</b>"})
    rows = all_works(db_path)
    charts = generate_charts(rows, tmp_path / "charts")
    report = build_report(rows, charts, tmp_path / "report.html")
    html = report.read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<th>简介</th>" in html
    assert "&lt;b&gt;简介&lt;/b&gt;" in html
    assert "data:image/png;base64" in html
