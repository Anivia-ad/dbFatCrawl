from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


class Config:
    SECRET_KEY = os.environ.get("DOUBAN_FATWORM_SECRET_KEY", "dev-douban-fatworm")
    DOUBAN_COOKIE = os.environ.get("DOUBAN_COOKIE", "")
    DATABASE = BASE_DIR / "instance" / "douban_fatworm.sqlite3"
    UPLOAD_DIR = BASE_DIR / "uploads"
    EXPORT_DIR = BASE_DIR / "exports"
    REPORT_DIR = BASE_DIR / "reports"
    CHART_DIR = BASE_DIR / "src" / "douban_fatworm" / "static" / "generated"
    ITEMS_PER_PAGE = 12
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    @classmethod
    def ensure_directories(cls) -> None:
        for path in [cls.DATABASE.parent, cls.UPLOAD_DIR, cls.EXPORT_DIR, cls.REPORT_DIR, cls.CHART_DIR]:
            path.mkdir(parents=True, exist_ok=True)
