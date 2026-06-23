from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from .analysis import build_report, compare, generate_charts, ranking, summarize
from .crawler import crawl_douban, fetch_subject_detail, merge_work_data
from .database import all_works, delete_work, delete_works, export_csv, get_work, import_csv, query_works, update_work, upsert_work


bp = Blueprint("main", __name__)

IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "https://movie.douban.com/",
}


@bp.get("/")
def index():
    page = max(optional_int(request.args.get("page"), default=1), 1)
    if has_invalid_numeric_filter(request.args):
        flash("部分数字筛选条件无效，已忽略。", "error")
    filters = {
        "keyword": request.args.get("keyword", ""),
        "work_type": request.args.get("work_type", ""),
        "min_rating": request.args.get("min_rating", ""),
        "max_rating": request.args.get("max_rating", ""),
        "start_year": request.args.get("start_year", ""),
        "end_year": request.args.get("end_year", ""),
    }
    result = query_works(current_app.config["DATABASE"], filters, page, current_app.config["ITEMS_PER_PAGE"])
    return render_template("index.html", result=result, filters=filters)


@bp.app_template_global()
def display_cover_url(cover_url: str) -> str:
    cover_url = str(cover_url or "")
    if is_doubanio_image_url(cover_url):
        return url_for("main.cover_image", url=cover_url)
    return cover_url


@bp.get("/cover")
def cover_image():
    cover_url = request.args.get("url", "")
    if not is_doubanio_image_url(cover_url):
        abort(404)
    try:
        response = requests.get(cover_url, headers=IMAGE_HEADERS, timeout=12)
        response.raise_for_status()
    except requests.RequestException:
        abort(404)
    content_type = response.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
    if not content_type.startswith("image/"):
        abort(404)
    proxied = Response(response.content, mimetype=content_type)
    proxied.headers["Cache-Control"] = "public, max-age=86400"
    return proxied


@bp.route("/works/new", methods=["GET", "POST"])
def new_work():
    if request.method == "POST":
        try:
            upsert_work(current_app.config["DATABASE"], request.form.to_dict())
            flash("作品已保存。", "success")
            return redirect(url_for("main.index"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("form.html", work=None)


@bp.get("/works/<int:work_id>")
def work_detail(work_id: int):
    work = get_work(current_app.config["DATABASE"], work_id)
    if not work:
        flash("作品不存在。", "error")
        return redirect(url_for("main.index"))
    return render_template("detail.html", work=work)


@bp.route("/works/<int:work_id>/edit", methods=["GET", "POST"])
def edit_work(work_id: int):
    work = get_work(current_app.config["DATABASE"], work_id)
    if not work:
        flash("作品不存在。", "error")
        return redirect(url_for("main.index"))
    if request.method == "POST":
        try:
            update_work(current_app.config["DATABASE"], work_id, request.form.to_dict())
            flash("作品已更新。", "success")
            return redirect(url_for("main.index"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("form.html", work=work)


@bp.post("/works/<int:work_id>/refresh")
def refresh_work_detail(work_id: int):
    work = get_work(current_app.config["DATABASE"], work_id)
    if not work:
        flash("作品不存在。", "error")
        return redirect(url_for("main.index"))
    if not work["source_url"]:
        flash("该作品没有来源链接，无法刷新详情。", "error")
        return redirect(url_for("main.work_detail", work_id=work_id))
    detail = fetch_subject_detail(work["source_url"], work["work_type"])
    if not detail:
        flash("未获取到新的详情信息。", "error")
        return redirect(url_for("main.work_detail", work_id=work_id))
    merged = merge_work_data(work_to_dict(work), detail)
    try:
        update_work(current_app.config["DATABASE"], work_id, merged)
        flash("作品详情已刷新。", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.work_detail", work_id=work_id))


@bp.post("/works/<int:work_id>/delete")
def remove_work(work_id: int):
    delete_work(current_app.config["DATABASE"], work_id)
    flash("作品已删除。", "success")
    return redirect(url_for("main.index"))


@bp.post("/works/bulk-delete")
def bulk_delete_works():
    work_ids = sorted({int(value) for value in request.form.getlist("work_ids") if value.isdigit()})
    if not work_ids:
        flash("请选择要删除的作品。", "error")
        return redirect(url_for("main.index"))
    deleted_count = delete_works(current_app.config["DATABASE"], work_ids)
    flash(f"已删除 {deleted_count} 个作品。", "success")
    return redirect(url_for("main.index"))


@bp.route("/crawl", methods=["GET", "POST"])
def crawl():
    if request.method == "POST":
        keyword = request.form.get("keyword", "")
        work_type = request.form.get("work_type", "movie")
        start_year = optional_int(request.form.get("start_year"))
        end_year = optional_int(request.form.get("end_year"))
        douban_cookie = request.form.get("douban_cookie", "") or current_app.config.get("DOUBAN_COOKIE", "")
        result = crawl_douban(keyword, work_type, start_year, end_year, douban_cookie)
        if result.error:
            flash(result.error, "error")
        created = updated = 0
        skipped = 0
        for item in result.items:
            try:
                _, is_created = upsert_work(current_app.config["DATABASE"], item)
                created += int(is_created)
                updated += int(not is_created)
            except ValueError:
                skipped += 1
        if result.items:
            flash(f"爬取完成：新增 {created} 条，更新 {updated} 条，跳过 {skipped} 条。", "success")
            return redirect(url_for("main.index"))
    return render_template("crawl.html")


@bp.route("/import", methods=["POST"])
def import_data():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("请选择 CSV 文件。", "error")
        return redirect(url_for("main.index"))
    if not file.filename.lower().endswith(".csv"):
        flash("只支持导入 CSV 文件。", "error")
        return redirect(url_for("main.index"))
    path = Path(current_app.config["UPLOAD_DIR"]) / secure_name(file.filename)
    file.save(path)
    try:
        stats = import_csv(current_app.config["DATABASE"], path)
        flash(f"导入完成：新增 {stats['created']} 条，更新 {stats['updated']} 条。", "success")
    except (ValueError, UnicodeDecodeError, csv.Error) as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.index"))


@bp.get("/export")
def export_data():
    path = Path(current_app.config["EXPORT_DIR"]) / f"douban_export_{datetime.now():%Y%m%d_%H%M%S}.csv"
    export_csv(current_app.config["DATABASE"], path)
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="text/csv; charset=utf-8")


@bp.get("/analysis")
def analysis_page():
    rows = all_works(current_app.config["DATABASE"])
    charts = generate_charts(rows, current_app.config["CHART_DIR"])
    chart_urls = {name: url_for("static", filename=f"generated/{Path(path).name}") for name, path in charts.items()}
    return render_template("analysis.html", summary=summarize(rows), charts=chart_urls, ranking=ranking(rows))


@bp.route("/compare", methods=["GET", "POST"])
def compare_page():
    rows = all_works(current_app.config["DATABASE"])
    selected = []
    if request.method == "POST":
        ids = [int(value) for value in request.form.getlist("work_ids") if value.isdigit()][:2]
        selected = compare([row for row in rows if row["id"] in ids])
        if len(selected) < 2:
            flash("请选择两部作品进行对比。", "error")
    return render_template("compare.html", works=rows, selected=selected)


@bp.get("/report")
def report_page():
    rows = all_works(current_app.config["DATABASE"])
    charts = generate_charts(rows, current_app.config["CHART_DIR"])
    path = Path(current_app.config["REPORT_DIR"]) / f"report_{datetime.now():%Y%m%d_%H%M%S}.html"
    build_report(rows, charts, path)
    flash("报告已生成。", "success")
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="text/html; charset=utf-8")


def optional_int(value: str | None, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def secure_name(filename: str) -> str:
    keep = [char for char in filename if char.isalnum() or char in {".", "_", "-"}]
    return "".join(keep) or "upload.csv"


def has_invalid_numeric_filter(args) -> bool:
    for key in ["page", "min_rating", "max_rating", "start_year", "end_year"]:
        value = args.get(key)
        if value in (None, ""):
            continue
        try:
            float(value) if "rating" in key else int(value)
        except ValueError:
            return True
    return False


def is_doubanio_image_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    hostname = parsed.hostname or ""
    return parsed.scheme in {"http", "https"} and (hostname == "doubanio.com" or hostname.endswith(".doubanio.com"))


def work_to_dict(work) -> dict:
    fields = ["title", "work_type", "rating", "rating_count", "creator", "year", "cover_url", "source_url", "tags", "summary"]
    return {field: work[field] for field in fields}
