from __future__ import annotations

from pathlib import Path

import pytest

from douban_fatworm.database import all_works, delete_works, export_csv, import_csv, init_db, query_works, update_work, upsert_work


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    init_db(path)
    return path


def test_upsert_deduplicates_by_source_url(db_path: Path) -> None:
    first_id, created = upsert_work(
        db_path,
        {
            "title": "测试电影",
            "work_type": "movie",
            "rating": "8.8",
            "rating_count": "100",
            "creator": "测试导演",
            "year": "2020",
            "source_url": "https://example.test/movie/1",
        },
    )
    second_id, second_created = upsert_work(
        db_path,
        {
            "title": "测试电影",
            "work_type": "movie",
            "rating": "9.0",
            "rating_count": "120",
            "creator": "测试导演",
            "year": "2020",
            "source_url": "https://example.test/movie/1",
        },
    )

    result = query_works(db_path, {}, 1, 10)

    assert created is True
    assert first_id == second_id
    assert second_created is False
    assert result.total == 1
    assert result.rows[0]["rating"] == 9.0


def test_query_filters_by_keyword_rating_and_year(db_path: Path) -> None:
    upsert_work(db_path, {"title": "高分科幻", "work_type": "movie", "rating": 9.1, "creator": "甲", "year": 2019})
    upsert_work(db_path, {"title": "普通小说", "work_type": "book", "rating": 7.0, "creator": "乙", "year": 2022})

    result = query_works(db_path, {"keyword": "科幻", "min_rating": 8, "start_year": 2018, "end_year": 2020}, 1, 10)

    assert result.total == 1
    assert result.rows[0]["title"] == "高分科幻"


def test_invalid_filters_are_ignored(db_path: Path) -> None:
    upsert_work(db_path, {"title": "可见作品", "work_type": "movie", "rating": 8.0, "year": 2020})

    result = query_works(db_path, {"min_rating": "bad", "start_year": "bad"}, 1, 10)

    assert result.total == 1


def test_update_duplicate_raises_value_error(db_path: Path) -> None:
    first_id, _ = upsert_work(db_path, {"title": "作品一", "work_type": "movie", "creator": "甲", "year": 2020})
    upsert_work(db_path, {"title": "作品二", "work_type": "movie", "creator": "乙", "year": 2021})

    with pytest.raises(ValueError, match="重复"):
        update_work(db_path, first_id, {"title": "作品二", "work_type": "movie", "creator": "乙", "year": 2021})


def test_delete_works_removes_selected_rows(db_path: Path) -> None:
    first_id, _ = upsert_work(db_path, {"title": "作品一", "work_type": "movie"})
    second_id, _ = upsert_work(db_path, {"title": "作品二", "work_type": "movie"})
    third_id, _ = upsert_work(db_path, {"title": "作品三", "work_type": "movie"})

    deleted = delete_works(db_path, [first_id, third_id])
    remaining_ids = {row["id"] for row in all_works(db_path)}

    assert deleted == 2
    assert remaining_ids == {second_id}


def test_rejects_unsafe_source_url(db_path: Path) -> None:
    with pytest.raises(ValueError, match="来源链接"):
        upsert_work(db_path, {"title": "危险链接", "work_type": "movie", "source_url": "javascript:alert(1)"})


def test_csv_import_validates_before_writing(db_path: Path, tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("title,work_type,rating\n有效作品,movie,8.0\n坏作品,movie,not-a-number\n", encoding="utf-8")

    with pytest.raises(ValueError):
        import_csv(db_path, csv_path)

    assert all_works(db_path) == []


def test_csv_import_and_export(db_path: Path, tmp_path: Path) -> None:
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("title,work_type,rating,creator,year\n测试图书,book,8.2,作者,2021\n", encoding="utf-8")

    stats = import_csv(db_path, csv_path)
    export_path = export_csv(db_path, tmp_path / "output.csv")

    assert stats == {"created": 1, "updated": 0}
    assert export_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "测试图书" in export_path.read_text(encoding="utf-8")
