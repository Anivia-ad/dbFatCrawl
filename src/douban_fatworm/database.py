from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    work_type TEXT NOT NULL CHECK (work_type IN ('movie', 'book')),
    rating REAL,
    rating_count INTEGER DEFAULT 0,
    creator TEXT,
    year INTEGER,
    cover_url TEXT,
    source_url TEXT,
    tags TEXT,
    summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_works_source_url
ON works(source_url)
WHERE source_url IS NOT NULL AND source_url != '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_works_identity
ON works(title, work_type, IFNULL(year, 0), IFNULL(creator, ''));
"""


@dataclass
class QueryResult:
    rows: list[sqlite3.Row]
    total: int
    page: int
    pages: int


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def normalize_work(data: dict[str, Any]) -> dict[str, Any]:
    def text(name: str) -> str:
        return str(data.get(name) or "").strip()

    def optional_int(name: str) -> int | None:
        value = data.get(name)
        if value in (None, ""):
            return None
        return int(value)

    def optional_float(name: str) -> float | None:
        value = data.get(name)
        if value in (None, ""):
            return None
        return float(value)

    title = text("title")
    work_type = text("work_type") or "movie"
    if not title:
        raise ValueError("标题不能为空")
    if work_type not in {"movie", "book"}:
        raise ValueError("类型必须是 movie 或 book")

    rating = optional_float("rating")
    if rating is not None and not 0 <= rating <= 10:
        raise ValueError("评分必须在 0 到 10 之间")

    year = optional_int("year")
    if year is not None and not 1800 <= year <= 2100:
        raise ValueError("年份不合理")

    rating_count = optional_int("rating_count") or 0
    if rating_count < 0:
        raise ValueError("评价人数不能为负数")

    cover_url = validate_url(text("cover_url"), "封面链接")
    source_url = validate_url(text("source_url"), "来源链接")

    return {
        "title": title,
        "work_type": work_type,
        "rating": rating,
        "rating_count": rating_count,
        "creator": text("creator"),
        "year": year,
        "cover_url": cover_url,
        "source_url": source_url,
        "tags": text("tags"),
        "summary": text("summary"),
    }


def upsert_work(db_path: str | Path, data: dict[str, Any]) -> tuple[int, bool]:
    work = normalize_work(data)
    with connect(db_path) as conn:
        return upsert_normalized(conn, work)


def find_duplicate(conn: sqlite3.Connection, work: dict[str, Any]) -> sqlite3.Row | None:
    if work.get("source_url"):
        row = conn.execute("SELECT * FROM works WHERE source_url = ?", (work["source_url"],)).fetchone()
        if row:
            return row
    return conn.execute(
        """
        SELECT * FROM works
        WHERE title = ? AND work_type = ? AND IFNULL(year, 0) = IFNULL(?, 0)
          AND IFNULL(creator, '') = IFNULL(?, '')
        """,
        (work["title"], work["work_type"], work.get("year"), work.get("creator")),
    ).fetchone()


def update_work(db_path: str | Path, work_id: int, data: dict[str, Any]) -> None:
    work = normalize_work(data)
    with connect(db_path) as conn:
        update_normalized(conn, work_id, work)


def upsert_normalized(conn: sqlite3.Connection, work: dict[str, Any]) -> tuple[int, bool]:
    existing = find_duplicate(conn, work)
    if existing:
        update_normalized(conn, int(existing["id"]), work)
        return int(existing["id"]), False
    cursor = conn.execute(
        """
        INSERT INTO works
        (title, work_type, rating, rating_count, creator, year, cover_url, source_url, tags, summary)
        VALUES (:title, :work_type, :rating, :rating_count, :creator, :year, :cover_url, :source_url, :tags, :summary)
        """,
        work,
    )
    return int(cursor.lastrowid), True


def update_normalized(conn: sqlite3.Connection, work_id: int, work: dict[str, Any]) -> None:
    payload = {**work, "id": work_id}
    try:
        conn.execute(
            """
            UPDATE works
            SET title = :title, work_type = :work_type, rating = :rating, rating_count = :rating_count,
                creator = :creator, year = :year, cover_url = :cover_url, source_url = :source_url,
                tags = :tags, summary = :summary, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """,
            payload,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("该作品与已有数据重复") from exc


def delete_work(db_path: str | Path, work_id: int) -> None:
    delete_works(db_path, [work_id])


def delete_works(db_path: str | Path, work_ids: Iterable[int]) -> int:
    ids = sorted({int(work_id) for work_id in work_ids})
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    with connect(db_path) as conn:
        cursor = conn.execute(f"DELETE FROM works WHERE id IN ({placeholders})", ids)
        return int(cursor.rowcount)


def get_work(db_path: str | Path, work_id: int) -> sqlite3.Row | None:
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()


def query_works(db_path: str | Path, filters: dict[str, Any], page: int = 1, per_page: int = 12) -> QueryResult:
    clauses: list[str] = []
    params: list[Any] = []

    keyword = str(filters.get("keyword") or "").strip()
    if keyword:
        clauses.append("(title LIKE ? OR creator LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    work_type = str(filters.get("work_type") or "").strip()
    if work_type:
        clauses.append("work_type = ?")
        params.append(work_type)

    for field, operator in [("min_rating", ">="), ("max_rating", "<=")]:
        value = safe_float(filters.get(field))
        if value is not None:
            clauses.append(f"rating {operator} ?")
            params.append(value)

    for field, operator in [("start_year", ">="), ("end_year", "<=")]:
        value = safe_int(filters.get(field))
        if value is not None:
            clauses.append(f"year {operator} ?")
            params.append(value)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = max(page - 1, 0) * per_page
    with connect(db_path) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM works {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM works {where_sql}
            ORDER BY COALESCE(rating, -1) DESC, rating_count DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, per_page, offset],
        ).fetchall()
    pages = max((total + per_page - 1) // per_page, 1)
    return QueryResult(rows=rows, total=total, page=page, pages=pages)


def all_works(db_path: str | Path) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM works ORDER BY id DESC").fetchall()


def import_csv(db_path: str | Path, csv_path: str | Path) -> dict[str, int]:
    required = {"title", "work_type"}
    created = updated = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV 至少需要 title 和 work_type 列")
        works = [normalize_work(row) for row in reader]

    with connect(db_path) as conn:
        for work in works:
            _, is_created = upsert_normalized(conn, work)
            if is_created:
                created += 1
            else:
                updated += 1
    return {"created": created, "updated": updated}


def export_csv(db_path: str | Path, output_path: str | Path) -> Path:
    rows = all_works(db_path)
    fieldnames = [
        "id",
        "title",
        "work_type",
        "rating",
        "rating_count",
        "creator",
        "year",
        "cover_url",
        "source_url",
        "tags",
        "summary",
        "created_at",
        "updated_at",
    ]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})
    return output


def safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_url(value: str, field_name: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{field_name}只支持 http 或 https 链接")
    return value
