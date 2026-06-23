# Component Inventory

## Python Modules

| Component | Type | Responsibility | Reuse Notes |
| --- | --- | --- | --- |
| `create_app` | Application factory | 创建 Flask 应用、加载配置、初始化 DB、注册蓝图、设置 UTF-8 响应头 | 测试通过传入自定义 Config 复用 |
| `Config` | Configuration class | 集中管理密钥、Cookie、数据库、上传、导出、报告、图表目录 | 新环境变量应在此集中声明 |
| `database.py` | Data access module | schema、连接、输入校验、upsert、查询、CSV | 新增字段要同步 schema、normalize、CSV、模板 |
| `crawler.py` | Crawling/parser module | 搜索页解析、详情页补全、移动 API 和摘要 API 补全 | 外部请求相关逻辑集中在此，便于 monkeypatch |
| `analysis.py` | Analysis module | DataFrame 汇总、图表、词云、HTML 报告 | 图表路径和字体策略在此维护 |
| `routes.py` | Web controller module | 全部 Flask 路由、参数解析、文件 IO、flash 和模板调用 | 保持路由薄，复杂逻辑下沉到服务模块 |

## Flask Routes as Components

| Route Function | Page / Action | Template / Output |
| --- | --- | --- |
| `index` | 作品列表、筛选、分页 | `index.html` |
| `new_work` | 新增作品 | `form.html` |
| `work_detail` | 作品详情 | `detail.html` |
| `edit_work` | 编辑作品 | `form.html` |
| `refresh_work_detail` | 根据来源链接刷新详情 | redirect |
| `remove_work`, `bulk_delete_works` | 单条/批量删除 | redirect |
| `crawl` | 豆瓣公开搜索爬取 | `crawl.html` |
| `import_data`, `export_data` | CSV 导入/导出 | redirect / CSV download |
| `analysis_page` | 数据分析页面 | `analysis.html` |
| `compare_page` | 两部作品对比 | `compare.html` |
| `report_page` | 生成并下载 HTML 报告 | HTML download |
| `cover_image` | 豆瓣图片代理 | image response |

## Jinja Templates

| Template | Category | Purpose |
| --- | --- | --- |
| `base.html` | Layout | 文档类型、UTF-8 meta、导航、flash 消息、CSS 引用 |
| `index.html` | Data management | 筛选表单、导入导出、卡片网格、分页、批量删除 |
| `form.html` | Form | 新增/编辑作品，字段与 `works` 表基本一致 |
| `detail.html` | Detail | 作品详情、来源链接、刷新详情、编辑/删除 |
| `crawl.html` | Crawler | 关键字、类型、年份范围、临时 Cookie 输入 |
| `analysis.html` | Analysis | 汇总指标、图表展示、排行榜 |
| `compare.html` | Compare | 多选两项作品并按字段对比 |

## UI and Styling Components

| CSS Component | Purpose |
| --- | --- |
| `.topbar`, `.brand`, `.nav` | 顶部导航 |
| `.toolbar` | 页面标题和主要操作 |
| `.filters` | 列表筛选网格 |
| `.import-export` | CSV 导入导出区域 |
| `.grid`, `.card`, `.cover`, `.score` | 作品卡片列表 |
| `.bulk-actions` | 批量删除操作条 |
| `.detail-panel`, `.detail-fields`, `.summary-box` | 详情页布局 |
| `.panel`, `.metrics`, `.charts` | 分析/表单/对比页面区块 |
| `@media (max-width: 820px)` | 移动端布局收敛 |

## Generated Artifacts

| Artifact | Producer | Consumer |
| --- | --- | --- |
| `static/generated/*.png` | `analysis.generate_charts` | `analysis.html`, `build_report` |
| `reports/report_*.html` | `routes.report_page` + `analysis.build_report` | Browser download |
| `exports/douban_export_*.csv` | `database.export_csv` | Browser download |
| `uploads/*.csv` | `routes.import_data` | `database.import_csv` |

## Extension Guidance

- 新增页面：在 `routes.py` 添加路由，在 `templates` 添加 Jinja 模板，并在 `base.html` 中按需加入导航。
- 新增数据字段：同时更新 SQLite schema、`normalize_work`、CSV fieldnames、表单、详情页、列表页和测试。
- 新增分析图表：在 `analysis.generate_charts` 注册生成函数，在 `analysis.html` 中可自动展示 `charts` 字典项。
