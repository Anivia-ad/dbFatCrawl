# Development Guide

## Prerequisites

- Python 3.11+
- uv
- Windows PowerShell 建议使用 UTF-8 输出：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## Install

```powershell
uv sync --extra dev
```

## Run Locally

```powershell
uv run flask --app douban_fatworm run
```

默认访问地址为 `http://127.0.0.1:5000`。首次启动会创建 `instance/douban_fatworm.sqlite3` 和其他运行目录。

## Test

```powershell
uv run pytest
```

测试配置在 `pyproject.toml` 中：

- `testpaths = ["tests"]`
- `pythonpath = ["src"]`

## Configuration

| Environment Variable | Purpose |
| --- | --- |
| `DOUBAN_FATWORM_SECRET_KEY` | Flask secret key，默认开发值为 `dev-douban-fatworm` |
| `DOUBAN_COOKIE` | 可选豆瓣 Cookie；爬取详情被安全校验拦截时可作为默认 Cookie |

运行目录由 `Config.ensure_directories` 创建：

- `instance/`
- `uploads/`
- `exports/`
- `reports/`
- `src/douban_fatworm/static/generated/`

## Common Tasks

### Add a Work Field

1. 修改 `database.SCHEMA` 中的 `works` 表。
2. 更新 `normalize_work` 的字段读取、类型转换和校验。
3. 更新 `upsert_normalized`、`update_normalized` 和 `export_csv` 字段列表。
4. 更新 `form.html`、`detail.html`、`index.html` 和必要的分析逻辑。
5. 添加数据库、路由和 CSV 测试。

### Add a New Analysis Chart

1. 在 `analysis.py` 添加 `save_*` 函数。
2. 在 `generate_charts` 中按数据条件加入 `charts["name"] = save_*(...)`。
3. 如 HTML 报告需要特殊展示，调整 `build_report`。
4. 添加测试断言图表键存在、文件生成。

### Add a Route

1. 在 `routes.py` 的 `bp` 上添加 GET/POST 路由。
2. 输入解析保持在路由层，业务逻辑优先放入 `database.py`、`crawler.py` 或 `analysis.py`。
3. 添加模板或下载响应。
4. 使用 Flask test client 添加成功路径和错误路径测试。

## Data and File Encoding

- 项目要求源文件 UTF-8 without BOM + CRLF。
- Web 响应文本由 `create_app` 的 `after_request` 设置 `charset=utf-8`。
- CSV 导入使用 `utf-8-sig` 读取，兼容 BOM。
- CSV 导出使用 `utf-8-sig` 写入，方便 Windows Excel 打开。
- HTML 报告使用 UTF-8 meta 和 `encoding="utf-8"` 写入。

## Deployment Notes

当前仓库未发现 Dockerfile、CI/CD、云部署或进程管理配置。默认形态适合本地课程演示。如果要部署到公网，至少需要补充：

- 生产 WSGI 服务器，如 waitress、gunicorn 或 uWSGI。
- 非开发默认的 `SECRET_KEY`。
- CSRF 防护和更严格的上传策略。
- 持久化数据库备份策略。
- 爬虫请求频率限制和明确的合规说明。

## Test Coverage Map

| Test File | Coverage |
| --- | --- |
| `test_database.py` | 去重、筛选、非法输入、批量删除、CSV 导入导出 |
| `test_crawler.py` | 搜索页解析、详情页解析、移动 API、摘要 API、年份过滤 |
| `test_analysis.py` | 空数据、汇总、排行、图表、报告转义 |
| `test_routes.py` | 页面渲染、详情刷新、导入错误、Cookie 透传、图片代理 |
