from __future__ import annotations

from pathlib import Path
from io import BytesIO

from douban_fatworm import create_app
from douban_fatworm.config import Config
from douban_fatworm.crawler import CrawlResult
from douban_fatworm.database import all_works, get_work, upsert_work


class TestConfig(Config):
    TESTING = True


class FakeImageResponse:
    status_code = 200
    headers = {"Content-Type": "image/jpeg"}
    content = b"fake-image"

    def raise_for_status(self) -> None:
        return None


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
        {
            "title": "测试作品",
            "work_type": "movie",
            "rating": 8.5,
            "rating_count": 10,
            "creator": "导演",
            "year": 2020,
            "tags": "剧情",
            "summary": "页面简介",
        },
    )

    client = app.test_client()

    for path in ["/", "/analysis", "/compare", "/crawl"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html; charset=utf-8" in response.headers["Content-Type"]

    analysis_response = client.get("/analysis")
    assert "简介" in analysis_response.text
    assert "页面简介" in analysis_response.text


def test_invalid_query_params_do_not_500(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/?page=bad&min_rating=bad&start_year=bad")

    assert response.status_code == 200


def test_work_detail_page_renders_from_card_entry(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    work_id, _ = upsert_work(
        app.config["DATABASE"],
        {
            "title": "详情作品",
            "work_type": "book",
            "rating": 9.1,
            "rating_count": 88,
            "creator": "作者",
            "year": 2024,
            "source_url": "https://example.com/work",
            "tags": "小说, 推理",
            "summary": "详情页简介",
        },
    )
    client = app.test_client()

    index_response = client.get("/")
    detail_response = client.get(f"/works/{work_id}")

    assert index_response.status_code == 200
    assert f"/works/{work_id}" in index_response.text
    assert "详情" in index_response.text
    assert detail_response.status_code == 200
    assert "详情作品" in detail_response.text
    assert "详情页简介" in detail_response.text
    assert "https://example.com/work" in detail_response.text


def test_missing_work_detail_redirects_to_index(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/works/999", follow_redirects=True)

    assert response.status_code == 200
    assert "作品不存在" in response.text


def test_refresh_work_detail_updates_existing_work(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    work_id, _ = upsert_work(
        app.config["DATABASE"],
        {
            "title": "星际穿越",
            "work_type": "movie",
            "rating": 9.4,
            "rating_count": 100,
            "creator": "克里斯托弗·诺兰",
            "year": 2014,
            "cover_url": "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.jpg",
            "source_url": "https://movie.douban.com/subject/1889243/",
            "tags": "剧情, 科幻",
            "summary": "近未来的地球黄沙遍野...",
        },
    )

    def fake_fetch_detail(source_url, work_type):
        assert source_url == "https://movie.douban.com/subject/1889243/"
        assert work_type == "movie"
        return {
            "cover_url": "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg",
            "summary": "近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝。",
            "rating_count": 2195613,
        }

    monkeypatch.setattr("douban_fatworm.routes.fetch_subject_detail", fake_fetch_detail)
    client = app.test_client()

    response = client.post(f"/works/{work_id}/refresh", follow_redirects=True)
    work = get_work(app.config["DATABASE"], work_id)

    assert response.status_code == 200
    assert "作品详情已刷新" in response.text
    assert work is not None
    assert work["cover_url"] == "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg"
    assert work["summary"] == "近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝。"
    assert work["rating_count"] == 2195613


def test_compare_ignores_non_integer_ids(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/compare", data={"work_ids": ["abc"]})

    assert response.status_code == 200


def test_bulk_delete_removes_selected_works(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    first_id, _ = upsert_work(app.config["DATABASE"], {"title": "作品一", "work_type": "movie"})
    second_id, _ = upsert_work(app.config["DATABASE"], {"title": "作品二", "work_type": "movie"})
    third_id, _ = upsert_work(app.config["DATABASE"], {"title": "作品三", "work_type": "movie"})
    client = app.test_client()

    response = client.post("/works/bulk-delete", data={"work_ids": [str(first_id), str(third_id)]}, follow_redirects=True)
    remaining_ids = {row["id"] for row in all_works(app.config["DATABASE"])}

    assert response.status_code == 200
    assert remaining_ids == {second_id}


def test_bulk_delete_requires_selection(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/works/bulk-delete", data={"work_ids": ["abc"]}, follow_redirects=True)

    assert response.status_code == 200
    assert "请选择要删除的作品" in response.text


def test_import_non_utf8_csv_does_not_500(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()
    data = {
        "file": (BytesIO(b"\xff\xfe\x00\x00"), "bad.csv"),
    }

    response = client.post("/import", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200


def test_crawl_passes_optional_cookie(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    captured = {}

    def fake_crawl(keyword, work_type, start_year, end_year, douban_cookie):
        captured["douban_cookie"] = douban_cookie
        return CrawlResult([])

    monkeypatch.setattr("douban_fatworm.routes.crawl_douban", fake_crawl)
    client = app.test_client()

    response = client.post("/crawl", data={"keyword": "夏目", "work_type": "movie", "douban_cookie": "bid=test;"})

    assert response.status_code == 200
    assert captured["douban_cookie"] == "bid=test;"


def test_cover_image_proxies_doubanio_images(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["referer"] = headers["Referer"]
        captured["timeout"] = timeout
        return FakeImageResponse()

    monkeypatch.setattr("douban_fatworm.routes.requests.get", fake_get)
    client = app.test_client()

    response = client.get("/cover?url=https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg")

    assert response.status_code == 200
    assert response.data == b"fake-image"
    assert response.content_type == "image/jpeg"
    assert captured["url"] == "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg"
    assert captured["referer"] == "https://movie.douban.com/"
    assert captured["timeout"] == 12


def test_cover_image_rejects_non_doubanio_urls(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/cover?url=https://example.com/poster.jpg")

    assert response.status_code == 404
