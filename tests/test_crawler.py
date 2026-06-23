from __future__ import annotations

from douban_fatworm.crawler import (
    fetch_mobile_subject_detail,
    fetch_subject_abstract_detail,
    filter_by_year,
    normalize_source_url,
    parse_creator,
    parse_mobile_subject_payload,
    parse_search_page,
    parse_subject_id,
    parse_subject_page,
)


class FakeJsonResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict):
        self.payload = payload
        self.headers = {}
        self.requested_url = ""

    def get(self, url: str, **kwargs):
        self.requested_url = url
        return FakeJsonResponse(self.payload)


def test_parse_empty_search_page_returns_empty_list() -> None:
    assert parse_search_page("<html><body>empty</body></html>", "movie") == []


def test_parse_search_page_normalizes_source_and_lazy_cover() -> None:
    html = """
    <div class="result">
      <div class="pic"><img data-original="//img.example.test/poster.jpg"></div>
      <div class="content">
        <div class="title">
          <a href="https://www.douban.com/link2/?url=https%3A%2F%2Fmovie.douban.com%2Fsubject%2F1889243%2F">星际穿越</a>
        </div>
        <p>导演: 克里斯托弗·诺兰 / 2014 / 剧情 科幻</p>
        <span class="rating_nums">9.4</span>
        <span>2195613 人评价</span>
      </div>
    </div>
    """

    item = parse_search_page(html, "movie")[0]

    assert item["source_url"] == "https://movie.douban.com/subject/1889243/"
    assert item["cover_url"] == "https://img.example.test/poster.jpg"


def test_year_filter_excludes_items_without_year_when_filter_is_set() -> None:
    items = [{"title": "未知年份", "year": None}, {"title": "命中", "year": 2020}]

    assert filter_by_year(items, 2019, 2021) == [{"title": "命中", "year": 2020}]


def test_parse_creator_does_not_treat_summary_as_creator() -> None:
    summary = "一场谋杀案使银行家安迪蒙冤入狱，谋杀妻子及其情人的指控将囚禁他终生。"

    assert parse_creator(summary, "movie") == ""


def test_parse_creator_extracts_labeled_creator() -> None:
    assert parse_creator("导演: 弗兰克·德拉邦特 / 主演: 蒂姆·罗宾斯 / 1994", "movie") == "弗兰克·德拉邦特"


def test_parse_subject_page_uses_detail_positions() -> None:
    html = """
    <html>
      <body>
        <h1><span property="v:itemreviewed">夏目友人帐 第三季</span><span class="year">(2011)</span></h1>
        <div id="mainpic"><img data-original="https://img.example.test/poster.jpg"></div>
        <div id="info">
          导演: 大森贵弘 / 植田秀仁 / 高桥秀弥 / 园田雅裕 / 松田清 / 更多...
          编剧: 绿川幸 / 村井贞之
          主演: 神谷浩史 / 井上和彦
          类型: 剧情 / 动画 / 奇幻
          首播: 2011-07-04(日本)
          集数: 13
        </div>
        <strong class="rating_num">9.6</strong>
        <span property="v:votes">105657</span>
        <div class="tags-body"><a>夏目友人帐</a><a>治愈</a></div>
        <div id="link-report-intra">
          <span property="v:summary">高中生夏目本来可以拥有平凡的高中生活...</span>
          <span class="all">高中生夏目本来可以拥有平凡的高中生活，但是，他却能看到妖怪。</span>
        </div>
      </body>
    </html>
    """

    item = parse_subject_page(html, "movie", "https://movie.douban.com/subject/5967223/")

    assert item["title"] == "夏目友人帐 第三季"
    assert item["creator"] == "大森贵弘 / 植田秀仁 / 高桥秀弥 / 园田雅裕 / 松田清"
    assert item["year"] == 2011
    assert item["rating"] == 9.6
    assert item["rating_count"] == 105657
    assert item["summary"] == "高中生夏目本来可以拥有平凡的高中生活，但是，他却能看到妖怪。"
    assert item["cover_url"] == "https://img.example.test/poster.jpg"
    assert item["source_url"] == "https://movie.douban.com/subject/5967223/"
    assert item["tags"] == "夏目友人帐, 治愈"


def test_normalize_source_url_unwraps_douban_link2_for_fetching() -> None:
    url = "https://www.douban.com/link2/?url=https%3A%2F%2Fmovie.douban.com%2Fsubject%2F5967223%2F"

    assert normalize_source_url(url) == "https://movie.douban.com/subject/5967223/"


def test_parse_subject_id_from_douban_subject_url() -> None:
    url = "https://www.douban.com/link2/?url=https%3A%2F%2Fmovie.douban.com%2Fsubject%2F5967223%2F"

    assert parse_subject_id(url) == "5967223"


def test_parse_mobile_subject_payload_uses_intro_and_large_cover() -> None:
    item = parse_mobile_subject_payload(
        {
            "title": "星际穿越",
            "pic": {
                "large": "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg",
                "normal": "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p2614988097.jpg",
            },
            "intro": "近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝。",
            "rating": {"value": 9.4, "count": 2195613},
            "directors": [{"name": "克里斯托弗·诺兰"}],
            "year": "2014",
            "genres": ["剧情", "科幻", "冒险"],
        },
        "movie",
        "https://movie.douban.com/subject/1889243/",
    )

    assert item["cover_url"] == "https://img3.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg"
    assert item["summary"] == "近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝。"
    assert item["rating"] == 9.4
    assert item["rating_count"] == 2195613
    assert item["creator"] == "克里斯托弗·诺兰"
    assert item["year"] == 2014
    assert item["tags"] == "剧情, 科幻, 冒险"


def test_fetch_mobile_subject_detail_uses_rexxar_api() -> None:
    session = FakeSession(
        {
            "title": "星际穿越",
            "pic": {"large": "https://img.example.test/current.jpg"},
            "intro": "完整简介",
            "rating": {"value": 9.4, "count": 2195613},
            "directors": [{"name": "克里斯托弗·诺兰"}],
            "year": "2014",
        }
    )

    item = fetch_mobile_subject_detail("https://movie.douban.com/subject/1889243/", "movie", session)

    assert session.requested_url == "https://m.douban.com/rexxar/api/v2/movie/1889243?ck=&for_mobile=1"
    assert item["cover_url"] == "https://img.example.test/current.jpg"
    assert item["summary"] == "完整简介"


def test_fetch_subject_abstract_detail_uses_directors() -> None:
    session = FakeSession(
        {
            "r": 0,
            "subject": {
                "directors": ["大森贵弘", "植田秀仁", "高桥秀弥", "园田雅裕", "松田清", "久木晃嗣"],
                "release_year": "2011",
                "rate": "9.6",
                "types": ["剧情", "动画", "奇幻"],
            },
        }
    )

    item = fetch_subject_abstract_detail("https://movie.douban.com/subject/5967223/", "movie", session)

    assert session.requested_url == "https://movie.douban.com/j/subject_abstract?subject_id=5967223"
    assert item["creator"] == "大森贵弘 / 植田秀仁 / 高桥秀弥 / 园田雅裕 / 松田清 / 久木晃嗣"
    assert item["year"] == 2011
    assert item["rating"] == 9.6
    assert item["tags"] == "剧情, 动画, 奇幻"
