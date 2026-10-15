"""뉴스 RSS 수집 모듈 테스트 (이슈 #4).

실제 인터넷 대신 tests/samples/rss/ 의 샘플 RSS 를 쓴다.
"""

import json
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from collector.sources import rss

SAMPLES = Path(__file__).parent / "samples" / "rss"
NOW = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)

ENT_URL = "https://feeds.example/entertainment.xml"
SPORTS_URL = "https://feeds.example/sports.xml"
BROKEN_URL = "https://feeds.example/broken.xml"
DOWN_URL = "https://feeds.example/down.xml"

FEED_FILES = {
    ENT_URL: "google_news_entertainment.xml",
    SPORTS_URL: "yna_sports.xml",
    BROKEN_URL: "broken.xml",
}

COMMON_KEYS = {"source", "keyword", "headline", "link", "outlet", "category", "collected_at"}


def fake_fetch(url):
    if url not in FEED_FILES:
        raise urllib.error.URLError("연결 실패 (테스트용)")
    return (SAMPLES / FEED_FILES[url]).read_bytes()


def write_config(tmp_path, ent_feeds, sports_feeds, *, enabled=True, sports_enabled=True):
    def feeds_yaml(feeds):
        lines = []
        for f in feeds:
            lines.append(f'      - name: "{f["name"]}"')
            lines.append(f'        url: "{f["url"]}"')
            if f.get("outlet"):
                lines.append(f'        outlet: {f["outlet"]}')
        return "\n".join(lines) if lines else "      []"

    (tmp_path / "sources.yaml").write_text(
        "sources:\n"
        "  - id: google_trends\n    module: trends\n    enabled: true\n"
        f"  - id: news_rss\n    module: rss\n    enabled: {str(enabled).lower()}\n",
        encoding="utf-8",
    )
    (tmp_path / "categories.yaml").write_text(
        "categories:\n"
        "  - id: entertainment\n    enabled: true\n    rss:\n" + feeds_yaml(ent_feeds) + "\n"
        f"  - id: sports\n    enabled: {str(sports_enabled).lower()}\n    rss:\n" + feeds_yaml(sports_feeds) + "\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def config_dir(tmp_path):
    return write_config(
        tmp_path,
        [{"name": "샘플 연예", "url": ENT_URL}],
        [{"name": "샘플 스포츠", "url": SPORTS_URL, "outlet": "가상통신"}],
    )


# --- 결과 모양 ---------------------------------------------------------------

def test_collect_returns_common_format(config_dir):
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)

    assert rows, "샘플에서 기사가 나와야 한다"
    for row in rows:
        assert set(row) == COMMON_KEYS
        assert row["source"] == "news_rss"  # sources.yaml 의 id 를 읽어 씀
        assert row["keyword"] is None
        assert row["collected_at"] == "2026-10-15T00:00:00+00:00"


def test_headline_link_outlet_category(config_dir):
    rows = {r["link"]: r for r in rss.collect(config_dir, fetcher=fake_fetch, now=NOW)}

    # 구글 뉴스형: 언론사는 <source> 에서, 제목 끝 ' - 언론사' 는 뗀다
    first = rows["https://news.google.com/rss/articles/SAMPLE-ENT-001?oc=5"]
    assert first["headline"] == "가상그룹 A, 정규 2집으로 컴백 확정"
    assert first["outlet"] == "가상일보"
    assert first["category"] == "entertainment"

    # HTML 특수문자는 원래 글자로
    second = rows["https://news.google.com/rss/articles/SAMPLE-ENT-002?oc=5"]
    assert second["headline"] == '배우 홍길동 & 김영희, 새 드라마 "첫방" 시청률 1위'
    assert second["outlet"] == "샘플스포츠"

    # 구글 뉴스가 붙인 마지막 ' - 언론사' 만 떼고, 원래 제목의 ' - ' 는 남긴다
    third = rows["https://news.google.com/rss/articles/SAMPLE-ENT-003?oc=5"]
    assert third["headline"] == "원래 제목에 붙은 꼬리 - 가상비즈"
    assert third["outlet"] == "Gasang Biz"

    # 언론사 한 곳 피드: <source> 가 없으면 설정의 outlet, 공백·줄바꿈 정리
    sports = rows["https://news.example.com/view/SPORTS-001"]
    assert sports["headline"] == "'만년 꼴찌' 가상FC, 개막 4연승 질주"
    assert sports["outlet"] == "가상통신"
    assert sports["category"] == "sports"
    assert rows["https://news.example.com/view/SPORTS-002"]["headline"] == "가상 선수, 시즌 30호 홈런"


def test_item_without_link_is_skipped(config_dir):
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)
    assert all("링크가 없는" not in r["headline"] for r in rows)


# --- 본문·이미지 저장 안 함 --------------------------------------------------

def test_no_body_or_image_is_stored(config_dir):
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)
    dumped = json.dumps(rows, ensure_ascii=False)

    assert "저장하면 안 됩니다" not in dumped   # description, content:encoded
    assert "본문" not in dumped
    assert ".jpg" not in dumped                 # media:content, enclosure


# --- 중복 방지 ---------------------------------------------------------------

def test_same_link_in_two_feeds_is_kept_once(config_dir):
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)
    links = [r["link"] for r in rows]

    assert len(links) == len(set(links))
    both = [r for r in rows if r["link"].endswith("SAMPLE-BOTH-001?oc=5")]
    assert len(both) == 1
    assert both[0]["category"] == "entertainment"  # 먼저 읽은 피드 기준


def test_save_asks_db_to_ignore_existing_links():
    calls = []

    def poster(url, body, headers):
        calls.append((url, json.loads(body), headers))
        return b"[]"

    rows = [{"source": "news_rss", "link": "https://a", "headline": "h"}]
    rss.save(rows, supabase_url="https://x.supabase.co/", supabase_key="test-key", poster=poster)

    url, body, headers = calls[0]
    assert url == "https://x.supabase.co/rest/v1/mentions?on_conflict=source,link"
    assert "resolution=ignore-duplicates" in headers["Prefer"]
    assert body == rows


def test_second_run_saves_nothing_new(config_dir):
    """DB 처럼 (source, link) 중복을 무시하는 가짜 저장소로 두 번 수집해 본다."""
    stored = {}

    def poster(url, body, headers):
        inserted = []
        for row in json.loads(body):
            key = (row["source"], row["link"])
            if key not in stored:
                stored[key] = row
                inserted.append(row)
        return json.dumps(inserted).encode()

    kwargs = dict(supabase_url="https://x.supabase.co", supabase_key="k", poster=poster)
    first = rss.save(rss.collect(config_dir, fetcher=fake_fetch, now=NOW), **kwargs)
    second = rss.save(rss.collect(config_dir, fetcher=fake_fetch, now=NOW), **kwargs)

    assert first == 6
    assert second == 0
    assert len(stored) == 6


# --- 실패 격리 ---------------------------------------------------------------

def test_broken_or_unreachable_feed_does_not_stop_others(tmp_path):
    config_dir = write_config(
        tmp_path,
        [{"name": "깨진 피드", "url": BROKEN_URL}, {"name": "샘플 연예", "url": ENT_URL}],
        [{"name": "접속 안 됨", "url": DOWN_URL}, {"name": "샘플 스포츠", "url": SPORTS_URL}],
    )
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)

    assert {r["category"] for r in rows} == {"entertainment", "sports"}
    assert len(rows) == 6


def test_missing_config_returns_empty_list(tmp_path):
    assert rss.collect(tmp_path / "없는폴더", fetcher=fake_fetch, now=NOW) == []


def test_save_failure_returns_zero():
    def poster(url, body, headers):
        raise urllib.error.URLError("DB 연결 실패 (테스트용)")

    rows = [{"source": "news_rss", "link": "https://a"}]
    assert rss.save(rows, supabase_url="https://x", supabase_key="k", poster=poster) == 0


def test_save_without_env_returns_zero(monkeypatch):
    monkeypatch.delenv(rss.ENV_SUPABASE_URL, raising=False)
    monkeypatch.delenv(rss.ENV_SUPABASE_KEY, raising=False)
    assert rss.save([{"source": "news_rss", "link": "https://a"}]) == 0


# --- 설정을 따름 -------------------------------------------------------------

def test_disabled_source_collects_nothing(tmp_path):
    config_dir = write_config(tmp_path, [{"name": "샘플 연예", "url": ENT_URL}], [], enabled=False)
    assert rss.collect(config_dir, fetcher=fake_fetch, now=NOW) == []


def test_disabled_category_is_skipped(tmp_path):
    config_dir = write_config(
        tmp_path,
        [{"name": "샘플 연예", "url": ENT_URL}],
        [{"name": "샘플 스포츠", "url": SPORTS_URL}],
        sports_enabled=False,
    )
    rows = rss.collect(config_dir, fetcher=fake_fetch, now=NOW)
    assert {r["category"] for r in rows} == {"entertainment"}


def test_real_config_lists_feeds_for_each_category():
    """레포의 실제 config 를 읽을 수 있고, 켜진 카테고리마다 피드가 있다."""
    settings = rss.load_settings()
    categories = yaml.safe_load((rss.CONFIG_DIR / "categories.yaml").read_text(encoding="utf-8"))
    enabled = {c["id"] for c in categories["categories"] if c.get("enabled", True)}

    assert settings["source_id"] == "news_rss"
    assert {f["category"] for f in settings["feeds"]} == enabled
