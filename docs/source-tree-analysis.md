# Source Tree Analysis

## Annotated Tree

```text
Project/
├── pyproject.toml                         # 项目元数据、依赖、pytest 配置、uv 配置
├── uv.lock                                # uv 锁文件
├── README.md                              # 运行、功能、测试和爬虫说明
├── docs/
│   ├── index.md                           # AI 项目文档主入口
│   ├── architecture.md                    # 架构文档
│   ├── api-contracts.md                   # Flask 路由契约
│   ├── data-models.md                     # SQLite 和 CSV 数据模型
│   ├── component-inventory.md             # 模块、模板、样式清单
│   ├── development-guide.md               # 开发指南
│   ├── project-overview.md                # 项目概览
│   ├── source-tree-analysis.md            # 本文件
│   ├── course_design_report.md            # 已有课程设计报告
│   └── report_20260622_184855.html        # 已有 HTML 分析报告
├── src/
│   └── douban_fatworm/
│       ├── __init__.py                    # Flask app factory，入口模块
│       ├── config.py                      # 配置和运行目录
│       ├── database.py                    # SQLite schema、CRUD、CSV
│       ├── routes.py                      # Flask Blueprint 和全部 HTTP 路由
│       ├── crawler.py                     # 豆瓣搜索、详情抓取和字段解析
│       ├── analysis.py                    # 汇总、排行、图表、HTML 报告
│       ├── templates/
│       │   ├── base.html                  # 站点布局和导航
│       │   ├── index.html                 # 数据列表、筛选、导入导出、批量删除
│       │   ├── form.html                  # 新增/编辑作品表单
│       │   ├── detail.html                # 作品详情和详情刷新
│       │   ├── crawl.html                 # 爬取表单
│       │   ├── analysis.html              # 分析指标、图表、排行榜
│       │   └── compare.html               # 两部作品对比
│       └── static/
│           ├── css/app.css                # 全站样式
│           └── generated/                 # 运行时生成图表 PNG
├── tests/
│   ├── test_routes.py                     # Flask 页面、表单、代理、报告等路由测试
│   ├── test_database.py                   # SQLite、校验、CSV、去重测试
│   ├── test_crawler.py                    # HTML/JSON 解析和详情补全测试
│   └── test_analysis.py                   # 汇总、图表、报告转义测试
├── instance/                              # 运行时 SQLite 数据库，默认 gitignore
├── uploads/                               # 上传 CSV 临时目录
├── exports/                               # 导出 CSV 目录
└── reports/                               # 导出 HTML 报告目录
```

## Critical Folders

| Path | Purpose | Notes |
| --- | --- | --- |
| `src/douban_fatworm` | 应用核心代码 | 所有生产代码都在此包内 |
| `src/douban_fatworm/templates` | Jinja 页面模板 | 与 `routes.py` 的 render_template 一一对应 |
| `src/douban_fatworm/static/css` | 静态样式 | 没有前端构建链 |
| `tests` | 自动测试 | 使用 pytest、tmp_path、monkeypatch 和 Flask test client |
| `docs` | 项目知识库 | BMAD 文档输出位置 |
| `instance`, `uploads`, `exports`, `reports` | 运行时目录 | 由 `Config.ensure_directories` 创建 |

## Entry Points

- 应用入口：`douban_fatworm:create_app`
- Flask CLI：`uv run flask --app douban_fatworm run`
- 主蓝图：`routes.bp`
- 数据库初始化：`database.init_db`
- 测试入口：`uv run pytest`

## Organization Pattern

项目没有多包、多服务或前后端分离结构。业务边界通过 Python 模块划分：Web 请求、数据访问、爬虫解析、分析输出各自独立，模板只负责展示。新增功能时应优先沿用这个模块边界，而不是把业务逻辑写入模板。
