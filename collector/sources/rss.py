"""뉴스 RSS 수집 모듈 (이슈 #4, docs/PLAN.md 4·5장, docs/DATA.md 4장).

config/categories.yaml 의 카테고리별 RSS 목록을 읽어 헤드라인·링크·언론사를 모으고
mentions 표에 저장한다.

- 기사 본문(description, content)과 이미지(media, enclosure)는 읽지도 저장하지도 않는다.
- 같은 링크는 한 번만 저장한다 (한 번의 수집 안에서 한 번 거르고, DB의 (source, link) 중복 금지로 한 번 더 거른다).
- 피드 하나가 실패해도 나머지 피드는 계속 수집하고, 모듈 전체도 예외를 밖으로 던지지 않는다.

직접 실행:
    python -m collector.sources.rss --dry-run   # 저장하지 않고 수집 결과만 확인
    python -m collector.sources.rss             # 수집 후 mentions 에 저장 (환경변수 필요)
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import yaml

logger = logging.getLogger(__name__)

MODULE_NAME = "rss"  # config/sources.yaml 에서 module: rss 인 항목이 이 모듈의 설정이다
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
TIMEOUT_SECONDS = 15
USER_AGENT = "news_radar/0.1 (+https://github.com/yunho0000/news_radar)"

# DB 저장용 환경변수 이름 (값은 GitHub Secrets / 환경변수에만 둔다)
ENV_SUPABASE_URL = "SUPABASE_URL"
ENV_SUPABASE_KEY = "SUPABASE_SERVICE_ROLE_KEY"

Fetcher = Callable[[str], bytes]
Poster = Callable[[str, bytes, dict], bytes]


# ---------------------------------------------------------------------------
# 설정 읽기
# ---------------------------------------------------------------------------

def load_settings(config_dir: Path = CONFIG_DIR) -> dict:
    """sources.yaml 에서 이 모듈의 소스 설정을, categories.yaml 에서 피드 목록을 읽는다.

    돌려주는 값: {"source_id", "enabled", "feeds": [{"category", "name", "url", "outlet"}]}
    """
    config_dir = Path(config_dir)
    sources = _read_yaml(config_dir / "sources.yaml").get("sources") or []
    source = next((s for s in sources if s.get("module") == MODULE_NAME), None)
    if source is None:
        raise ValueError(f"sources.yaml 에 module: {MODULE_NAME} 인 소스가 없습니다")

    feeds = []
    categories = _read_yaml(config_dir / "categories.yaml").get("categories") or []
    for category in categories:
        if not category.get("enabled", True):
            continue
        for feed in category.get("rss") or []:
            if not feed.get("url"):
                continue
            feeds.append({
                "category": category.get("id"),
                "name": feed.get("name") or feed["url"],
                "url": feed["url"],
                "outlet": feed.get("outlet"),
            })

    return {
        "source_id": source["id"],
        "enabled": bool(source.get("enabled", True)),
        "feeds": feeds,
    }


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# RSS 해석
# ---------------------------------------------------------------------------

def parse_feed(
    xml_bytes: bytes,
    *,
    source_id: str,
    category: str | None,
    collected_at: str,
    default_outlet: str | None = None,
) -> list[dict]:
    """RSS 2.0 문서에서 기사마다 mentions 한 줄(공통 수집 모듈 형식)을 만든다.

    제목·링크·언론사만 읽는다. 본문과 이미지는 건드리지 않는다.
    """
    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.iter():
        if _local(item.tag) != "item":
            continue
        headline = _clean(_child_text(item, "title"))
        link = _clean(_child_text(item, "link"))
        if not headline or not link:
            continue

        # 구글 뉴스처럼 <source> 태그가 있으면 그것이 언론사, 없으면 피드 설정의 outlet
        outlet = _clean(_child_text(item, "source")) or default_outlet
        headline = _strip_outlet_suffix(headline, outlet)

        rows.append({
            "source": source_id,
            "keyword": None,
            "headline": headline,
            "link": link,
            "outlet": outlet,
            "category": category,
            "collected_at": collected_at,
        })
    return rows


def _local(tag: str) -> str:
    """'{namespace}name' 형태의 태그에서 name 만 꺼낸다."""
    return tag.rsplit("}", 1)[-1]


def _child_text(elem: ET.Element, name: str) -> str | None:
    for child in elem:
        if _local(child.tag) == name:
            return child.text
    return None


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = " ".join(html.unescape(text).split())
    return text or None


def _strip_outlet_suffix(headline: str, outlet: str | None) -> str:
    """구글 뉴스 제목 끝의 ' - 언론사' 를 뗀다. 언론사는 outlet 칸에 따로 저장한다."""
    if outlet:
        suffix = f" - {outlet}"
        if headline.endswith(suffix) and len(headline) > len(suffix):
            return headline[: -len(suffix)].rstrip()
    return headline


# ---------------------------------------------------------------------------
# 수집
# ---------------------------------------------------------------------------

def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def collect(
    config_dir: Path = CONFIG_DIR,
    *,
    fetcher: Fetcher = fetch,
    now: datetime | None = None,
) -> list[dict]:
    """모든 카테고리의 RSS 를 읽어 공통 형식 목록을 돌려준다. 실패해도 예외를 던지지 않는다."""
    try:
        settings = load_settings(config_dir)
    except Exception:
        logger.exception("RSS 설정을 읽지 못해 수집을 건너뜁니다")
        return []
    if not settings["enabled"]:
        logger.info("%s 소스가 꺼져 있어 수집하지 않습니다", settings["source_id"])
        return []

    collected_at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    rows: list[dict] = []
    seen_links: set[str] = set()

    for feed in settings["feeds"]:
        try:
            feed_rows = parse_feed(
                fetcher(feed["url"]),
                source_id=settings["source_id"],
                category=feed["category"],
                collected_at=collected_at,
                default_outlet=feed["outlet"],
            )
        except Exception as e:
            logger.warning("RSS 피드 실패, 건너뜀: %s (%s: %s)", feed["name"], type(e).__name__, e)
            continue

        new_rows = [r for r in feed_rows if r["link"] not in seen_links]
        seen_links.update(r["link"] for r in new_rows)
        rows.extend(new_rows)
        logger.info("RSS %s: %d건 (중복 제외 %d건)", feed["name"], len(feed_rows), len(new_rows))

    return rows


# ---------------------------------------------------------------------------
# 저장 (Supabase REST)
# ---------------------------------------------------------------------------

def save(
    rows: Iterable[dict],
    *,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    poster: Poster | None = None,
) -> int:
    """mentions 표에 저장하고 새로 들어간 줄 수를 돌려준다.

    이미 있는 (source, link) 는 DB가 무시한다 (on conflict do nothing, docs/DATA.md 1장).
    실패해도 예외를 던지지 않고 0을 돌려준다.
    """
    rows = list(rows)
    if not rows:
        return 0
    supabase_url = supabase_url or os.environ.get(ENV_SUPABASE_URL)
    supabase_key = supabase_key or os.environ.get(ENV_SUPABASE_KEY)
    if not supabase_url or not supabase_key:
        logger.error("%s, %s 환경변수가 없어 저장하지 않습니다", ENV_SUPABASE_URL, ENV_SUPABASE_KEY)
        return 0

    url = supabase_url.rstrip("/") + "/rest/v1/mentions?on_conflict=source,link"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=representation",
    }
    body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    try:
        inserted = json.loads((poster or _post)(url, body, headers) or b"[]")
    except Exception as e:
        logger.error("mentions 저장 실패 (%s: %s)", type(e).__name__, e)
        return 0
    return len(inserted)


def _post(url: str, body: bytes, headers: dict) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


# ---------------------------------------------------------------------------
# 직접 실행
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="뉴스 RSS 수집")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 결과만 출력")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = collect()
    if args.dry_run:
        for row in rows[:10]:
            print(f"[{row['category']}] {row['headline']} — {row['outlet']}")
        print(f"총 {len(rows)}건 수집 (저장 안 함)")
        return 0

    inserted = save(rows)
    print(f"총 {len(rows)}건 수집, 새로 저장 {inserted}건 (나머지는 이미 있던 링크)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
