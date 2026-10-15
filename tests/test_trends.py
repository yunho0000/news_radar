"""구글 트렌드 수집 모듈 테스트 (이슈 #3).

실제 구글 트렌드·DB를 부르지 않고, tests/samples/ 의 저장된 샘플 응답과
가짜 저장 함수로 확인한다.
"""

from datetime import datetime
from pathlib import Path

import pytest

from collector import __main__ as runner
from collector.sources import trends
from collector.store import MENTION_FIELDS, save_mentions

SAMPLES = Path(__file__).parent / "samples"
SOURCE = {
    "id": "google_trends",
    "module": "trends",
    "enabled": True,
    "url": "https://trends.google.com/trending/rss?geo=KR",
    "timeout_seconds": 20,
}
NOW = datetime.fromisoformat("2026-10-15T09:00:00+09:00")
AT = "2026-10-15T09:00:00+09:00"


def sample_fetch(name):
    def fetch(url, timeout):
        return (SAMPLES / name).read_bytes()

    return fetch


def row(keyword, headline=None, link=None, outlet=None):
    return {
        "source": "google_trends",
        "keyword": keyword,
        "headline": headline,
        "link": link,
        "outlet": outlet,
        "category": None,
        "collected_at": AT,
    }


EXPECTED = [
    row("가상가수 컴백"),
    row("가상가수 컴백", "가상가수, 2년 만에 '새 앨범'으로 컴백", "https://news.example.com/a/1", "가상일보"),
    row("가상가수 컴백", "가상가수 컴백 쇼케이스 현장", "https://news.example.com/a/2", "가상스포츠"),
    row("가상FC 역전승"),
    row("가상FC 역전승", "가상FC, 후반 추가시간 역전승", "https://news.example.com/b/1", "가상스포츠"),
    row("가상드라마 결말"),
]


# --- 수집: 샘플 응답 → 공통 형식 ---------------------------------------------

def test_collect_sample_response():
    rows = trends.collect(SOURCE, now=NOW, fetch=sample_fetch("google_trends_kr.xml"))
    assert rows == EXPECTED


def test_rows_follow_common_format():
    rows = trends.collect(SOURCE, now=NOW, fetch=sample_fetch("google_trends_kr.xml"))
    for r in rows:
        assert tuple(r) == MENTION_FIELDS  # 공통 형식의 칸만, 같은 순서로
        datetime.fromisoformat(r["collected_at"])  # 시간대 포함 ISO 8601
        assert r["collected_at"].endswith("+09:00")


def test_no_images_or_body_saved():
    rows = trends.collect(SOURCE, now=NOW, fetch=sample_fetch("google_trends_kr.xml"))
    for r in rows:
        for value in r.values():
            assert not (isinstance(value, str) and value.endswith(".jpg"))


def test_uses_url_and_timeout_from_config():
    calls = []

    def fetch(url, timeout):
        calls.append((url, timeout))
        return (SAMPLES / "google_trends_kr.xml").read_bytes()

    trends.collect({**SOURCE, "url": "https://example.com/rss", "timeout_seconds": 5}, now=NOW, fetch=fetch)
    assert calls == [("https://example.com/rss", 5)]


# --- 실패해도 멈추지 않음 ------------------------------------------------------

def test_network_failure_returns_empty_list():
    def fetch(url, timeout):
        raise ConnectionError("네트워크 끊김")

    assert trends.collect(SOURCE, now=NOW, fetch=fetch) == []


def test_broken_response_returns_empty_list():
    assert trends.collect(SOURCE, now=NOW, fetch=sample_fetch("google_trends_broken.xml")) == []


def test_missing_url_returns_empty_list():
    assert trends.collect({"id": "google_trends"}, now=NOW, fetch=sample_fetch("google_trends_kr.xml")) == []


def test_one_source_failure_does_not_stop_others(monkeypatch):
    original = trends.collect
    monkeypatch.setattr(
        trends, "collect", lambda source: original(source, now=NOW, fetch=sample_fetch("google_trends_kr.xml"))
    )
    saved = []
    sources = [
        {"id": "broken", "module": "does_not_exist", "enabled": True},
        SOURCE,
        {"id": "off", "module": "trends", "enabled": False},
    ]
    summary = runner.run(sources, save=lambda rows: saved.extend(rows) or len(rows))
    assert summary == {
        "broken": {"collected": 0, "saved": 0},
        "google_trends": {"collected": 6, "saved": 6},
    }
    assert saved == EXPECTED


# --- 저장: mentions 표로 보내는 내용 (실제 DB는 부르지 않음) --------------------

class FakeResponse:
    def __init__(self, status=201):
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


def test_save_sends_rows_to_mentions_and_ignores_duplicates():
    sent = {}

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent.update(kwargs)
        return FakeResponse()

    count = save_mentions(EXPECTED, url="https://demo.supabase.co/", key="test-key", post=fake_post)

    assert count == 6
    assert sent["url"] == "https://demo.supabase.co/rest/v1/mentions"
    assert sent["params"] == {"on_conflict": "source,link"}
    assert "resolution=ignore-duplicates" in sent["headers"]["Prefer"]
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["json"] == EXPECTED
    links = [r["link"] for r in sent["json"] if r["link"]]
    assert len(links) == len(set(links))  # 같은 기사 링크는 한 번만


def test_save_without_env_does_not_raise(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    def must_not_post(*args, **kwargs):
        pytest.fail("접속 정보가 없으면 DB를 부르면 안 된다")

    assert save_mentions(EXPECTED, post=must_not_post) == 0


def test_save_http_error_does_not_raise():
    assert save_mentions(EXPECTED, url="https://demo.supabase.co", key="k", post=lambda *a, **k: FakeResponse(500)) == 0


def test_save_empty_list_does_nothing():
    assert save_mentions([], url="https://demo.supabase.co", key="k", post=lambda *a, **k: pytest.fail()) == 0
