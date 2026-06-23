# Data Models

## SQLite Schema

核心 schema 定义在 `src/douban_fatworm/database.py` 的 `SCHEMA` 常量中。

```sql
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
```

## Indexes and Uniqueness

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_works_source_url
ON works(source_url)
WHERE source_url IS NOT NULL AND source_url != '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_works_identity
ON works(title, work_type, IFNULL(year, 0), IFNULL(creator, ''));
```

去重规则：

1. 如果 `source_url` 非空，优先按来源链接查重。
2. 否则按 `title + work_type + year + creator` 查重。
3. `upsert_work` 命中重复时更新已有行并返回 `(id, False)`；新建时返回 `(id, True)`。

## Field Semantics

| Field | Type | Meaning | Validation |
| --- | --- | --- | --- |
| `id` | integer | 自增主键 | SQLite 自动生成 |
| `title` | text | 作品标题 | 必填 |
| `work_type` | text | `movie` 或 `book` | 非法值拒绝 |
| `rating` | real | 豆瓣评分 | 空或 0-10 |
| `rating_count` | integer | 评价人数 | 默认 0，不能为负 |
| `creator` | text | 电影导演或图书作者 | 可空 |
| `year` | integer | 上映/出版年份 | 空或 1800-2100 |
| `cover_url` | text | 封面图片 URL | 空或 http/https |
| `source_url` | text | 豆瓣或其他来源 URL | 空或 http/https |
| `tags` | text | 逗号分隔标签 | 可空 |
| `summary` | text | 简介 | 可空 |
| `created_at` | text | 创建时间 | SQLite 默认 |
| `updated_at` | text | 更新时间 | update 时刷新 |

## Query Result Model

`QueryResult` 是 dataclass：

| Field | Meaning |
| --- | --- |
| `rows` | 当前页 `sqlite3.Row` 列表 |
| `total` | 符合条件的总数 |
| `page` | 当前页 |
| `pages` | 总页数，至少为 1 |

## CSV Model

导入至少需要：

```csv
title,work_type
```

导出完整字段：

```csv
id,title,work_type,rating,rating_count,creator,year,cover_url,source_url,tags,summary,created_at,updated_at
```

CSV 导入使用 `utf-8-sig` 读取，导出使用 `utf-8-sig` 写入。

## Analysis Data Model

`analysis.rows_to_frame` 将 `sqlite3.Row` 或字典序列转为 pandas DataFrame。分析逻辑会将：

- `rating` 转为 numeric，用于均值、最高分、直方图和散点图。
- `rating_count` 转为 numeric，空值填 0。
- `year` 转为 numeric，用于年份覆盖和平均评分趋势。
- `tags` 按中文逗号或英文逗号拆分，用于 top tags 和词云。

## Generated File Models

| File Type | Path | Producer |
| --- | --- | --- |
| Uploaded CSV | `uploads/<secure_name>` | `routes.import_data` |
| Exported CSV | `exports/douban_export_*.csv` | `database.export_csv` |
| Chart PNG | `src/douban_fatworm/static/generated/*_<run_id>.png` | `analysis.generate_charts` |
| HTML Report | `reports/report_*.html` | `analysis.build_report` |
| SQLite DB | `instance/douban_fatworm.sqlite3` | `database.init_db` |
