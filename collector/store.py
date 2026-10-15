"""수집 결과를 Supabase 의 mentions 표에 저장한다. (docs/DATA.md 1장)

접속 정보는 환경변수에서만 읽는다 (코드·커밋에 넣지 않는다).
- SUPABASE_URL: 프로젝트 주소 (예: https://xxxx.supabase.co)
- SUPABASE_SERVICE_ROLE_KEY: service_role(secret) 키. GitHub Secrets 에 보관한다.

같은 (source, link)가 이미 있으면 무시한다 (on conflict do nothing).
"""

import logging
import os

import requests

log = logging.getLogger(__name__)

MENTION_FIELDS = ("source", "keyword", "headline", "link", "outlet", "category", "collected_at")
DEFAULT_TIMEOUT_SECONDS = 30


def save_mentions(rows, url=None, key=None, post=requests.post, timeout=DEFAULT_TIMEOUT_SECONDS):
    """mentions 표에 여러 줄을 넣는다. 보낸 줄 수를 돌려주고, 실패하면 0을 돌려준다.

    실패해도 예외를 밖으로 던지지 않는다. (테스트에서는 post 에 가짜 함수를 넣는다.)
    """
    if not rows:
        return 0
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log.error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 환경변수가 없어 저장하지 못함")
        return 0

    payload = [{field: row.get(field) for field in MENTION_FIELDS} for row in rows]
    try:
        response = post(
            f"{url.rstrip('/')}/rest/v1/mentions",
            params={"on_conflict": "source,link"},
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except Exception:
        log.exception("mentions 저장 실패 (%d줄)", len(payload))
        return 0
    return len(payload)
