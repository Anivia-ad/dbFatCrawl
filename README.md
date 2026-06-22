# 豆瓣肥虫数据分析网站

这是一个使用 Flask、SQLite、pandas、matplotlib、wordcloud 和 BeautifulSoup 实现的课程项目。项目使用 uv 管理环境，支持豆瓣电影/图书数据爬取、手工维护、CSV 导入导出、搜索筛选、可视化分析、作品对比和 HTML 报告生成。

## 运行

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
uv sync --extra dev
uv run flask --app douban_fatworm run
```

打开 `http://127.0.0.1:5000` 即可访问。首次启动会自动创建本地 SQLite 数据库。

## 主要功能

- 按关键字、年份范围和类型爬取豆瓣公开搜索结果。
- 手工新增、编辑、删除电影或图书数据。
- 按标题、作者/导演、类型、评分区间和年份区间筛选，并分页展示。
- 数据去重、CSV 导入和 CSV 导出。
- 评分分布直方图、年份平均评分趋势、评价人数与评分散点图、标签词云和排行榜。
- 两部作品对比。
- 生成 HTML 分析报告。

## 测试

```powershell
uv run pytest
```

## 说明

爬虫只访问公开搜索页，不包含登录、验证码处理、代理池或任何规避访问控制的逻辑。请低频、少量、学习用途运行，并遵守目标网站的 robots、服务条款和版权要求。若网络不可用，可以通过手工新增或 CSV 导入数据完成演示。

CSV 文件请保存为 UTF-8。Windows PowerShell 如需显示中文输出，建议先执行：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

图表中文字体会优先使用 Windows 的微软雅黑或黑体；如果运行环境没有中文字体，图表仍会生成，但中文可能无法正常显示。
