# API Contracts

本项目主要是服务端渲染 Web 应用，而不是 JSON API。以下契约描述 Flask 路由、输入、输出和副作用。

## Routes

| Method | Path | Function | Request | Response | Side Effects |
| --- | --- | --- | --- | --- | --- |
| GET | `/` | `index` | `page`, `keyword`, `work_type`, `min_rating`, `max_rating`, `start_year`, `end_year` query | `index.html` | 无 |
| GET | `/cover` | `cover_image` | `url` query，必须是 `doubanio.com` 图片 | image response 或 404 | 外部请求图片 |
| GET/POST | `/works/new` | `new_work` | POST form: work fields | GET 返回 `form.html`；POST 成功重定向 `/` | upsert SQLite |
| GET | `/works/<work_id>` | `work_detail` | path int | `detail.html` 或重定向 `/` | 无 |
| GET/POST | `/works/<work_id>/edit` | `edit_work` | POST form: work fields | GET 返回 `form.html`；POST 成功重定向 `/` | update SQLite |
| POST | `/works/<work_id>/refresh` | `refresh_work_detail` | path int | redirect detail/index | 外部请求豆瓣详情并更新 SQLite |
| POST | `/works/<work_id>/delete` | `remove_work` | path int | redirect `/` | delete SQLite |
| POST | `/works/bulk-delete` | `bulk_delete_works` | form `work_ids` list | redirect `/` | delete SQLite |
| GET/POST | `/crawl` | `crawl` | POST form: `keyword`, `work_type`, `start_year`, `end_year`, `douban_cookie` | `crawl.html` 或 redirect `/` | 外部请求豆瓣，upsert SQLite |
| POST | `/import` | `import_data` | multipart `file`, `.csv` | redirect `/` | 保存上传文件并导入 SQLite |
| GET | `/export` | `export_data` | none | CSV download | 写入 `exports/douban_export_*.csv` |
| GET | `/analysis` | `analysis_page` | none | `analysis.html` | 写入图表 PNG |
| GET/POST | `/compare` | `compare_page` | POST form `work_ids` list，最多取两个整数 | `compare.html` | 无 |
| GET | `/report` | `report_page` | none | HTML download | 写入图表 PNG 和 `reports/report_*.html` |

## Work Form Fields

| Field | Type | Required | Validation |
| --- | --- | --- | --- |
| `title` | string | yes | 非空 |
| `work_type` | string | no | 默认 `movie`；只允许 `movie` 或 `book` |
| `rating` | float | no | 0 到 10 |
| `rating_count` | int | no | 非负 |
| `creator` | string | no | trim |
| `year` | int | no | 1800 到 2100 |
| `cover_url` | string | no | 空或 http/https |
| `source_url` | string | no | 空或 http/https |
| `tags` | string | no | 逗号分隔文本 |
| `summary` | string | no | trim |

## Query Filters

`GET /` 支持以下过滤条件：

- `keyword`: 模糊匹配 `title` 或 `creator`
- `work_type`: 精确匹配
- `min_rating`, `max_rating`: 评分区间
- `start_year`, `end_year`: 年份区间
- `page`: 页码，非法时回退到 1 并显示错误 flash

## CSV Import Contract

- 上传路径：`POST /import`
- 文件类型：文件名必须以 `.csv` 结尾
- 编码：`utf-8-sig`
- 必需列：`title`, `work_type`
- 导入策略：先读取并规范化所有行；任意行校验失败则不写入数据库。
- 写入策略：逐条 upsert，返回新增和更新数量。

## CSV Export Contract

导出字段顺序：

```text
id,title,work_type,rating,rating_count,creator,year,cover_url,source_url,tags,summary,created_at,updated_at
```

响应为 `text/csv; charset=utf-8`，文件名格式为 `douban_export_YYYYMMDD_HHMMSS.csv`。

## Error Handling

- 表单校验错误通过 flash 展示并停留或重定向到相关页面。
- 不存在的作品详情/编辑/刷新会 flash `作品不存在。` 并重定向首页。
- 非豆瓣图片代理 URL、外部请求失败或非图片 Content-Type 返回 404。
- CSV 导入捕获 `ValueError`、`UnicodeDecodeError` 和 `csv.Error`。
