from __future__ import annotations

from douban_fatworm.crawler import parse_search_page


def test_parse_empty_search_page_returns_empty_list() -> None:
    assert parse_search_page("<html><body>empty</body></html>", "movie") == []
