from __future__ import annotations

from pathlib import Path

from douban_fatworm import create_app
from douban_fatworm.config import Config
from douban_fatworm.database import upsert_work


class TestConfig(Config):
    TESTING = True


def make_app(tmp_path: Path):
    class LocalConfig(TestConfig):
        DATABASE = tmp_path / "app.sqlite3"
        UPLOAD_DIR = tmp_path / "uploads"
        EXPORT_DIR = tmp_path / "exports"
        REPORT_DIR = tmp_path / "reports"
        CHART_DIR = tmp_path / "charts"

    return create_app(LocalConfig)


def test_index_analysis_and_compare_pages_render(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    upsert_work(
        app.config["DATABASE"],
        {"title": "测试作品", "work_type": "movie", "rating": 8.5, "rating_count": 10, "creator": "导演", "year": 2020, "tags": "剧情"},
    )

    client = app.test_client()

    for path in ["/", "/analysis", "/compare", "/crawl"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html; charset=utf-8" in response.headers["Content-Type"]


def test_invalid_query_params_do_not_500(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/?page=bad&min_rating=bad&start_year=bad")

    assert response.status_code == 200
