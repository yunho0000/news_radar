"""구글 트렌드 한국 급상승 검색어 수집 모듈. (이슈 #3, docs/PLAN.md 4장)

config/sources.yaml 의 google_trends 항목에 적힌 주소(RSS)를 읽어
공통 수집 모듈 형식(docs/DATA.md 4장)의 목록으로 돌려준다.

급상승 검색어 1개마다 아래 줄을 만든다.
- 검색어 줄 1개: keyword 만 있고 link 는 비움.
  link 가 비어 있으면 중복 제한이 없으므로, 수집할 때마다 "이번 회차에도 급상승 중"이 기록된다.
- 관련 기사 줄 여러 개: keyword + 기사 제목·링크·언론사.
  같은 기사 링크는 DB에서 한 번만 저장된다.

기사 본문·이미지(ht:picture 등)는 읽지도 저장하지도 않는다.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger(__name__)

# 구글 트렌드 RSS 의 ht: 태그 이름공간
HT = "{https://trends.google.com/trending/rss}"
KST = timezone(timedelta(hours=9))
DEFAULT_TIMEOUT_SECONDS = 20


def _text(element, tag):
    """태그 안의 글자를 앞뒤 공백 없이 꺼낸다. 없거나 비어 있으면 None."""
    found = element.find(tag)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _row(source_id, keyword, headline, link, outlet, collected_at):
    return {
        "source": source_id,
        "keyword": keyword,
        "headline": headline,
        "link": link,
        "outlet": outlet,
        "category": None,  # 카테고리 판별은 규칙 필터(#5)에서 한다
        "collected_at": collected_at,
    }


def parse(xml_text, source_id, collected_at):
    """RSS 글자를 공통 형식 목록으로 바꾼다. 형식이 깨져 있으면 예외를 낸다."""
    root = ET.fromstring(xml_text)
    rows = []
    seen_links = set()
    for item in root.iter("item"):
        keyword = _text(item, "title")
        if not keyword:
            continue
        rows.append(_row(source_id, keyword, None, None, None, collected_at))
        for news in item.findall(f"{HT}news_item"):
            link = _text(news, f"{HT}news_item_url")
            headline = _text(news, f"{HT}news_item_title")
            if not link or not headline or link in seen_links:
                continue
            seen_links.add(link)
            outlet = _text(news, f"{HT}news_item_source")
            rows.append(_row(source_id, keyword, headline, link, outlet, collected_at))
    return rows


def _fetch(url, timeout):
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "news_radar/1.0"})
    response.raise_for_status()
    return response.content


def collect(source, now=None, fetch=_fetch):
    """sources.yaml 항목 하나를 받아 수집한다.

    실패해도 예외를 밖으로 던지지 않고 빈 목록을 돌려준 뒤 로그를 남긴다.
    (테스트에서는 fetch 에 저장된 샘플 응답을 돌려주는 함수를 넣는다.)
    """
    source_id = source.get("id", "google_trends")
    try:
        url = source["url"]
        timeout = source.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        collected_at = (now or datetime.now(KST)).isoformat(timespec="seconds")
        rows = parse(fetch(url, timeout), source_id, collected_at)
    except Exception:
        log.exception("[%s] 수집 실패 — 이번 회차는 건너뜀", source_id)
        return []
    log.info("[%s] %d줄 수집", source_id, len(rows))
    return rows
