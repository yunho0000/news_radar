"""수집 실행: python -m collector [--source ID] [--dry-run]

config/sources.yaml 에서 켜진(enabled: true) 소스를 하나씩 수집해 mentions 에 저장한다.
소스 하나가 실패해도(모듈이 없거나 오류가 나도) 나머지 소스는 계속 수집한다.
--dry-run 이면 DB에 저장하지 않고 수집 결과만 화면에 보여준다.
"""

import argparse
import importlib
import json
import logging
from pathlib import Path

import yaml

from collector.store import save_mentions

log = logging.getLogger("collector")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_sources(path=CONFIG_DIR / "sources.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("sources", [])


def run_source(source):
    """소스 하나를 수집한다. 어떤 오류가 나도 빈 목록을 돌려준다."""
    try:
        module = importlib.import_module(f"collector.sources.{source['module']}")
        return module.collect(source)
    except Exception:
        log.exception("[%s] 수집 모듈 실행 실패 — 다른 소스는 계속 진행", source.get("id"))
        return []


def run(sources, only=None, dry_run=False, save=save_mentions):
    """켜진 소스를 모두 수집하고 저장한다. 소스별 {수집 줄 수, 저장 줄 수}를 돌려준다."""
    summary = {}
    for source in sources:
        if not source.get("enabled") or (only and source.get("id") != only):
            continue
        rows = run_source(source)
        if dry_run:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            saved = 0
        else:
            saved = save(rows)
        summary[source["id"]] = {"collected": len(rows), "saved": saved}
    return summary


def main():
    parser = argparse.ArgumentParser(description="소재 레이더 수집 실행")
    parser.add_argument("--source", help="이 소스 id 하나만 수집 (예: google_trends)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 저장하지 않고 결과만 출력")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    summary = run(load_sources(), only=args.source, dry_run=args.dry_run)
    log.info("수집 요약: %s", summary)


if __name__ == "__main__":
    main()
