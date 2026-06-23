# 豆瓣肥虫数据分析网站 - Project Overview

**Date:** 2026-06-23T12:00:41+08:00
**Type:** Python Web Application
**Architecture:** Flask 单体应用

## Executive Summary

本项目面向课程设计场景，提供一个完整的数据采集、维护、分析和报告生成 Web 应用。用户可以通过豆瓣公开搜索页抓取电影或图书条目，也可以手工录入或通过 CSV 导入数据；应用会把作品写入本地 SQLite 数据库，并提供筛选、分页、详情查看、批量删除、作品对比、图表分析和 HTML 报告导出。

## Project Classification

- **Repository Type:** 单体仓库
- **Project Type:** Web 应用，兼具数据分析与爬虫能力
- **Primary Language:** Python
- **Architecture Pattern:** Flask application factory + Blueprint routes + 函数式服务模块 + SQLite 数据访问层

## Technology Stack Summary

| Category | Technology | Version / Source | Purpose |
| --- | --- | --- | --- |
| Language | Python | `>=3.11` | 应用、爬虫、分析和测试 |
| Web Framework | Flask | `>=3.0.3` | HTTP 路由、模板渲染、文件下载、flash 消息 |
| Database | SQLite | Python stdlib `sqlite3` | 本地持久化作品数据 |
| Crawling | requests, BeautifulSoup4 | `requests>=2.32.3`, `beautifulsoup4>=4.12.3` | 访问公开页面并解析 HTML/JSON |
| Data Analysis | pandas | `>=2.2.3` | DataFrame 汇总、排行和分组 |
| Visualization | matplotlib, wordcloud | `matplotlib>=3.9.2`, `wordcloud>=1.9.3` | 图表、词云和报告图片 |
| Testing | pytest | `>=8.3.3` | 单元测试和 Flask test client 测试 |
| Package Manager | uv | `uv.lock`, `[tool.uv]` | 依赖同步、运行和测试 |

## Key Features

- 豆瓣电影/图书公开搜索爬取，支持关键字、类型和年份范围。
- 详情补全策略包括桌面详情页、移动端 Rexxar API、电影 `subject_abstract` JSON。
- 作品数据新增、编辑、删除、批量删除和详情刷新。
- 关键词、类型、评分范围、年份范围筛选和分页展示。
- CSV 导入、CSV 导出，导入前整体校验，导出包含 UTF-8 BOM 以兼容 Excel。
- 评分分布、年份趋势、评价人数散点图、标签词云、排行榜和 HTML 分析报告。
- 豆瓣图片代理，避免页面直接加载受 Referer 限制的 `doubanio.com` 图片。

## Architecture Highlights

- `create_app` 负责配置加载、目录创建、数据库初始化、蓝图注册和 UTF-8 文本响应头。
- `routes.py` 是 Web 层入口，负责请求参数、文件上传下载、flash 消息和模板渲染。
- `database.py` 封装 schema、校验、去重、CRUD、查询和 CSV 导入导出。
- `crawler.py` 封装外部 HTTP 请求、HTML/JSON 解析、详情补全和年份过滤。
- `analysis.py` 将数据库行转换为 DataFrame，生成汇总指标、排行、图表和 HTML 报告。
- Jinja 模板和 CSS 位于 `src/douban_fatworm/templates` 与 `src/douban_fatworm/static/css`。

## Development Overview

### Prerequisites

- Python 3.11+
- uv
- 可选：能访问豆瓣公开页面的网络环境；如果网络不可用，可使用手工新增或 CSV 导入。

### Key Commands

- **Install:** `uv sync --extra dev`
- **Dev:** `uv run flask --app douban_fatworm run`
- **Test:** `uv run pytest`
- **UTF-8 Console:** `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

## Repository Structure

核心代码在 `src/douban_fatworm`，测试在 `tests`，AI/项目文档在 `docs`，运行时文件默认写入 `instance`、`uploads`、`exports`、`reports` 和 `src/douban_fatworm/static/generated`。

## Documentation Map

- [index.md](./index.md) - 主入口
- [architecture.md](./architecture.md) - 技术架构
- [source-tree-analysis.md](./source-tree-analysis.md) - 源码树
- [component-inventory.md](./component-inventory.md) - 模块和页面清单
- [development-guide.md](./development-guide.md) - 开发指南
- [api-contracts.md](./api-contracts.md) - 路由契约
- [data-models.md](./data-models.md) - 数据模型
