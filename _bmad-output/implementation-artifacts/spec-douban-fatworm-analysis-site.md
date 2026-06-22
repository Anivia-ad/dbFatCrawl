---
title: '豆瓣肥虫数据分析网站'
type: 'feature'
created: '2026-06-22'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** 当前项目目录没有可运行的 Python 应用，需要按课程要求实现一个豆瓣数据分析网站，覆盖爬取、存储、检索、可视化、导入导出和报告生成。项目还必须使用 uv 管理环境，并保持源码、配置、响应和日志为 UTF-8。

**Approach:** 新建一个 Flask + SQLite + pandas 的单体 Web 应用，提供作品数据管理、豆瓣关键字/年份范围爬取、去重入库、搜索筛选、统计图表、词云、排行榜、对比分析、CSV 导入导出和 Markdown/HTML 报告导出。爬虫默认采用 requests + BeautifulSoup 的保守抓取实现，并允许手工新增/修改数据，避免网络不可用时应用不可演示。

## Boundaries & Constraints

**Always:** 使用 uv 项目结构和 `pyproject.toml` 管理依赖；所有源码和配置保存为 UTF-8 without BOM + CRLF；Web 响应声明 UTF-8；SQLite 数据保存在本地；导入和爬取写入时按豆瓣链接、标题、年份、作者/导演组合去重；UI 必须支持响应式布局；图表生成和导出功能必须在无外网数据时可通过示例/手动数据演示。

**Ask First:** 若需要真实登录豆瓣、绕过反爬、使用代理池、验证码处理、接入第三方付费 API、改成大型前后端分离架构，必须先询问用户。

**Never:** 不实现登录豆瓣、验证码绕过、账号自动化、分布式爬虫或任何规避站点访问控制的行为；不把爬取结果写到项目外目录；不引入非必要的重型框架；不依赖在线 CDN 才能打开页面。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 爬取电影 | 关键字、年份起止、类型为 movie | 请求豆瓣搜索页，解析标题、评分、评价人数、导演/作者、年份、封面、链接并去重保存 | 网络失败或解析为空时返回错误提示，不破坏已有数据 |
| 手工新增 | 表单提交标题、类型、年份、评分等 | 数据写入 SQLite，列表页立即可见 | 必填缺失或评分/年份非法时展示字段错误 |
| 搜索筛选 | 标题/作者、评分区间、年份区间、类型 | 分页展示匹配结果，保留筛选条件 | 无结果时显示空态而非异常 |
| 分析图表 | 数据库有 0 条或多条数据 | 生成评分分布、年份均分趋势、评价人数评分散点、标签词云、排行榜 | 无数据时显示可读提示，不生成破损图片 |
| 导入导出 | 上传 CSV 或点击导出 | CSV 导入去重，导出当前数据库数据 | CSV 列缺失时提示所需列 |
| 报告导出 | 点击报告导出 | 生成包含核心指标、图表和排行榜的 HTML 报告 | 数据不足时仍生成带空态说明的报告 |

</frozen-after-approval>

## Code Map

- `pyproject.toml` -- uv 项目元数据、依赖和脚本入口。
- `README.md` -- 运行、爬取、导入导出和报告生成说明。
- `.gitignore` -- 忽略虚拟环境、缓存、数据库和生成的图表/报告。
- `src/douban_fatworm/__init__.py` -- Flask 应用工厂和 UTF-8 响应配置。
- `src/douban_fatworm/config.py` -- 数据库、上传、导出和图表目录配置。
- `src/douban_fatworm/database.py` -- SQLite 连接、建表、CRUD、去重、CSV 导入导出。
- `src/douban_fatworm/crawler.py` -- requests + BeautifulSoup 豆瓣搜索解析和容错。
- `src/douban_fatworm/analysis.py` -- pandas 统计、matplotlib 图表、wordcloud 词云、报告生成。
- `src/douban_fatworm/routes.py` -- 页面路由、表单处理、文件下载、爬取触发。
- `src/douban_fatworm/templates/*.html` -- 基础布局、列表、表单、分析、对比、报告页面。
- `src/douban_fatworm/static/css/app.css` -- 响应式页面样式。
- `tests/test_database.py` -- 数据层去重、筛选和 CSV 导入测试。
- `tests/test_analysis.py` -- 空数据和统计输出测试。

## Tasks & Acceptance

**Execution:**
- [x] `pyproject.toml` -- 创建 uv 项目配置和依赖 -- 确保环境可复现。
- [x] `src/douban_fatworm/config.py`, `database.py` -- 实现 SQLite schema、CRUD、筛选、去重、CSV 导入导出 -- 支撑全部数据功能。
- [x] `src/douban_fatworm/crawler.py` -- 实现保守豆瓣搜索爬取与解析 -- 满足课程爬虫模块要求。
- [x] `src/douban_fatworm/analysis.py` -- 实现统计、图表、词云、排行榜、对比和报告 -- 满足分析和可视化要求。
- [x] `src/douban_fatworm/__init__.py`, `routes.py` -- 实现 Flask 应用工厂和全部 Web 路由 -- 连接前端、数据、爬虫和分析。
- [x] `src/douban_fatworm/templates/*.html`, `static/css/app.css` -- 构建响应式中文界面 -- 让数据分页展示、搜索筛选、分析报告可操作。
- [x] `tests/*.py`, `README.md`, `.gitignore` -- 添加核心测试和使用文档 -- 便于验收和运行。
- [x] 全项目文本文件 -- 统一 UTF-8 without BOM + CRLF -- 满足项目 AGENTS 规则。

**Acceptance Criteria:**
- Given 全新 checkout, when 执行 `uv sync` 后 `uv run flask --app douban_fatworm run`, then 网站可启动并自动初始化本地 SQLite 数据库。
- Given 用户手动新增或导入 CSV 数据, when 打开首页并使用标题/作者、评分、年份、类型筛选, then 列表按条件分页展示并支持编辑删除。
- Given 用户输入关键字和年份范围触发爬取, when 豆瓣可访问且返回结果, then 解析出的作品去重保存；when 网络不可用, then 页面显示失败原因且数据库不损坏。
- Given 数据库已有多条数据, when 打开分析页, then 能看到评分分布、年份均分趋势、评价人数评分散点、词云、排行榜和核心指标。
- Given 两个作品被选择对比, when 提交对比表单, then 页面展示评分、评价人数、年份、标签等字段差异。
- Given 点击导出 CSV 或生成报告, when 操作完成, then 下载文件或报告页面可访问，内容使用 UTF-8 中文。
- Given 运行 `uv run pytest`, when 测试完成, then 数据库和分析核心用例通过。

## Spec Change Log

## Design Notes

应用采用单体 Flask 是为了让课程验收可以用一个命令启动，且不需要 Node/CDN。爬虫只做公开搜索页解析和明确的异常提示；核心演示能力依赖本地数据管理和 CSV 导入，不把真实网络爬取作为唯一成功路径。

## Verification

**Commands:**
- `uv sync` -- expected: 依赖安装成功。
- `uv run pytest` -- expected: 测试全部通过。
- `uv run flask --app douban_fatworm run` -- expected: 开发服务器启动，访问首页无异常。

## Suggested Review Order

**应用入口与路由**

- 应用工厂初始化数据库并声明 UTF-8 响应。
  [`__init__.py:9`](../../../src/douban_fatworm/__init__.py#L9)

- 页面路由连接筛选、爬取、导入导出、分析和报告。
  [`routes.py:16`](../../../src/douban_fatworm/routes.py#L16)

**数据与爬取**

- SQLite schema、去重键和本地持久化集中在数据层。
  [`database.py:11`](../../../src/douban_fatworm/database.py#L11)

- 豆瓣公开搜索爬取保持保守请求和失败提示。
  [`crawler.py:31`](../../../src/douban_fatworm/crawler.py#L31)

**分析与报告**

- pandas 统计、图表、词云和排行榜统一生成。
  [`analysis.py:24`](../../../src/douban_fatworm/analysis.py#L24)

- HTML 报告转义用户数据并内嵌图表。
  [`analysis.py:91`](../../../src/douban_fatworm/analysis.py#L91)

**前端页面**

- 首页提供分页筛选、导入导出和作品卡片。
  [`index.html:1`](../../../src/douban_fatworm/templates/index.html#L1)

- 响应式样式覆盖导航、筛选、卡片、图表和移动端。
  [`app.css:1`](../../../src/douban_fatworm/static/css/app.css#L1)

**验证与运行**

- uv 依赖和 pytest 配置定义在项目清单。
  [`pyproject.toml:1`](../../../pyproject.toml#L1)

- 测试覆盖数据库、分析、路由和爬虫基础边界。
  [`test_routes.py:1`](../../../tests/test_routes.py#L1)
