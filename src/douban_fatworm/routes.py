from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

from .analysis import build_report, compare, generate_charts, ranking, summarize
from .crawler import crawl_douban
from .database import all_works, delete_work, export_csv, get_work, import_csv, query_works, update_work, upsert_work


bp = Blueprint("main", __name__)


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


@bp.post("/works/<int:work_id>/delete")
def remove_work(work_id: int):
    delete_work(current_app.config["DATABASE"], work_id)
    flash("作品已删除。", "success")
    return redirect(url_for("main.index"))


@bp.route("/crawl", methods=["GET", "POST"])
def crawl():
    if request.method == "POST":
        keyword = request.form.get("keyword", "")
        work_type = request.form.get("work_type", "movie")
        start_year = optional_int(request.form.get("start_year"))
        end_year = optional_int(request.form.get("end_year"))
        result = crawl_douban(keyword, work_type, start_year, end_year)
        if result.error:
            flash(result.error, "error")
        created = updated = 0
        for item in result.items:
            _, is_created = upsert_work(current_app.config["DATABASE"], item)
            created += int(is_created)
            updated += int(not is_created)
        if result.items:
            flash(f"爬取完成：新增 {created} 条，更新 {updated} 条。", "success")
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
    except ValueError as exc:
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
        ids = [int(value) for value in request.form.getlist("work_ids")[:2]]
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
