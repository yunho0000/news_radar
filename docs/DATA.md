# 데이터 형식 (DATA.md)

이 문서는 수집 쪽(#3~#6)과 화면 쪽(#7~#10)이 함께 지키는 **데이터 약속**이다.
데이터 형식을 바꿔야 하면 코드보다 먼저 이 문서 변경을 PR로 올린다 (CLAUDE.md 규칙).

- 규칙(자주 안 바뀜) → `config/*.yaml` (변경은 PR로)
- 기록(매일 쌓임) → Supabase 데이터베이스 (`db/schema.sql`)

## 1. 데이터베이스 표 8개

모든 표에는 자동 증가 번호 `id`가 있다. 시각은 모두 `timestamptz`(시간대 포함 시각)로 저장한다.

### mentions — 수집한 원시 데이터 한 줄

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| source | text, 필수 | 수집 소스 id (`config/sources.yaml`의 `id`) |
| keyword | text | 검색어·키워드 (트렌드). 뉴스는 비어 있을 수 있음 |
| headline | text | 기사 제목. **본문은 저장하지 않는다** |
| link | text | 기사·트렌드 링크 |
| outlet | text | 언론사 이름 |
| category | text | 카테고리 id (`config/categories.yaml`의 `id`). 모르면 비움 |
| collected_at | timestamptz, 필수 | 수집 시각 |

- `(source, link)`는 중복될 수 없다. 같은 소스에서 같은 링크는 한 번만 저장된다. 링크가 비어 있는 줄은 제한이 없다.
- 이미 있는 링크를 다시 넣을 때는 `on conflict (source, link) do nothing`으로 무시한다.

### topics — 묶어서 정리한 소재

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| title | text, 필수 | 소재 제목 |
| keywords | text[] | 이 소재로 묶인 키워드 목록 |
| category | text | 카테고리 id |
| status | text, 기본 `watching` | 상태 (아래 "허용 값") |
| phase | text | 국면. 판단 전이면 비움 |
| hot_score | numeric | 화제성 점수 |
| fit_score | numeric | 적합도 점수 (데이터가 쌓이면 생김) |
| outlet_count | integer | 다룬 언론사 수 (신뢰도 표시) |
| type_tags | text[] | 유형 태그 |
| pass_reason | text | 패스 이유 (패스일 때만) |
| memo | text | 메모 |
| first_seen_at / last_seen_at | timestamptz | 처음·마지막 발견 시각 |
| status_changed_at | timestamptz | 상태가 마지막으로 바뀐 시각 ("찜한 순" 정렬) |
| created_at / updated_at | timestamptz | 만든 시각 / 고친 시각 (`updated_at`은 자동 갱신) |

### topic_snapshots — 수집 회차별 소재 기록 (국면 계산용)

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| topic_id | → topics, 필수 | 소재 (소재를 지우면 함께 지워짐) |
| collected_at | timestamptz, 필수 | 수집 회차 시각 |
| mention_count | integer | 이 회차의 언급 수 |
| score | numeric | 이 회차의 화제성 점수 |

- `(topic_id, collected_at)`은 중복될 수 없다.
- 보드의 "마지막 수집 시각"은 `topic_snapshots.collected_at`의 최댓값이다.

### posts — 발행한 게시물

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| topic_id | → topics | 소재. 소급 게시물은 비어 있을 수 있음 |
| platform | text, 필수 | 플랫폼 (아래 "허용 값") |
| title | text | 성과 입력 표에서 알아보기 위한 제목 |
| url | text | 게시물 링크 |
| published_at | timestamptz, 필수 | 업로드 시각 (시간대 분석용) |

### post_metrics — 게시물 성과

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| post_id | → posts, 필수 | 게시물 (게시물을 지우면 함께 지워짐) |
| metric | text, 필수 | 지표 이름 (아래 "허용 값") |
| value | numeric, 필수 | 숫자 |
| measured_at | timestamptz | 측정 시각 (원칙: 발행 3일 후) |
| is_backfill | boolean, 기본 false | "소급" 입력 여부 |

- `(post_id, metric, measured_at)`은 중복될 수 없다.

### watchlist — 관심 인물·팀·작품

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| name | text, 필수 | 이름 |
| kind | text, 필수 | 종류 (`person` / `team` / `work`) |
| category | text | 카테고리 id |
| hashtags | text[] | 인스타 조회용 해시태그 (공백·이모지 없이, `#` 없이) |
| memo | text | 메모 |

### events — 예정 이벤트

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| title | text, 필수 | 이벤트 이름 |
| event_date | date, 필수 | 날짜 |
| category | text | 카테고리 id |
| memo | text | 메모 |
| topic_id | → topics | 연결된 소재 (선택) |

### api_ledger — 한도 장부

| 필드 | 형식 | 설명 |
| --- | --- | --- |
| source | text, 필수 | 소스 id |
| query | text, 필수 | 조회어 (해시태그 등) |
| called_at | timestamptz | 호출 시각 |

- 한도가 있는 API는 호출 **전에** 이 표로 남은 한도를 계산하고, 호출 **후에** 한 줄을 남긴다.
- 인스타 해시태그 남은 한도 = 30 − (최근 7일 동안 `source = 'instagram_hashtag'`인 서로 다른 `query` 수). 이미 조회한 해시태그를 다시 조회하는 것은 한도를 쓰지 않는다.

## 2. 허용 값

DB에는 영어 값으로 저장하고, 화면에는 한글 이름으로 보여준다. 새 값이 필요하면 이 표에 한 줄 추가하는 PR을 올린다. DB 구조는 바꾸지 않는다.

**status (소재 상태)**: 관찰 중 → 발견 → 찜 → 제작 중 → 발행, 또는 어느 단계에서든 패스

| 값 | 화면 이름 |
| --- | --- |
| `watching` | 관찰 중 (필터 탈락, 다음 수집 때 재평가) |
| `found` | 발견 |
| `picked` | 찜 |
| `producing` | 제작 중 |
| `published` | 발행 |
| `passed` | 패스 |

**phase (국면)**

| 값 | 화면 이름 |
| --- | --- |
| `rising` | 상승 중 |
| `peak` | 정점 |
| `falling` | 하락 |

**type_tags (유형 태그)**: `issue` 이슈형, `record` 기록형, `event` 이벤트형, `person` 인물형

**pass_reason (패스 이유)**: `late` 이미 늦음, `off_tone` 우리 톤 아님, `rumor` 루머성, `too_minor` 너무 마이너

**category (카테고리)**: `config/categories.yaml`의 `id`를 따른다. 지금은 `entertainment` 연예, `sports` 스포츠

**platform (플랫폼)과 핵심 지표**

| platform | 화면 이름 | 핵심 지표 metric | 설명 |
| --- | --- | --- | --- |
| `instagram` | 인스타그램 | `saves_shares` | 저장 + 공유 |
| `youtube` | 유튜브 | `views` | 조회수 |
| `naver_clip` | 네이버클립 | `plays` | 재생수 |

보조 지표 예시: `likes` 좋아요, `comments` 댓글. 플랫폼과 지표가 늘어나도 값만 추가하면 된다.

## 3. 평소 대비 배수 (기획서 7장)

```text
배수 = 이번 게시물의 핵심 지표 ÷ 같은 플랫폼 최근 20개 게시물 핵심 지표의 중앙값
```

- "최근 20개"는 이번 게시물보다 **먼저** 발행된 같은 플랫폼 게시물 20개다 (`published_at` 기준).
- 비교 대상이 하나도 없거나 중앙값이 0이면 배수는 비운다.

## 4. 공통 수집 모듈 형식 (기획서 4장)

`collector/sources/`의 모든 모듈은 같은 모양의 결과 목록을 돌려준다. 이 결과가 그대로 `mentions` 한 줄이 된다.

```python
{
    "source": "news_rss",            # config/sources.yaml 의 id
    "keyword": None,                 # 없으면 None
    "headline": "기사 제목",
    "link": "https://...",
    "outlet": "언론사 이름",           # 모르면 None
    "category": "entertainment",     # 모르면 None
    "collected_at": "2026-10-15T09:00:00+09:00",  # ISO 8601, 시간대 포함
}
```

- 모듈 하나가 실패해도 예외를 밖으로 던지지 않고 빈 목록을 돌려준 뒤 로그를 남긴다. 그래야 다른 모듈이 계속 동작한다.

## 5. 접근 권한

모든 표에 RLS(행 단위 보안: 정해진 사람만 표를 읽고 쓰게 하는 Supabase 기능)가 켜져 있다.

| 누가 | 쓰는 키 | 할 수 있는 것 |
| --- | --- | --- |
| 로그인 안 한 방문자 | anon (publishable) 키 | 아무것도 못 봄 |
| 로그인한 담당자 (웹 보드) | anon 키 + 로그인 | 모든 표 읽기·쓰기 |
| 자동 수집 프로그램 (GitHub Actions) | service_role (secret) 키 | 모든 표 읽기·쓰기 (RLS와 무관) |

"나만" 쓰게 하는 방법: Supabase에서 새 회원가입을 끄고, 담당자 계정 1개만 직접 만든다. 그러면 로그인할 수 있는 사람이 담당자뿐이다.

## 6. DB 만들기·샘플 넣기

Supabase 대시보드 → **SQL Editor** → **New query**에 파일 내용을 붙여넣고 **Run**을 누른다.

| 순서 | 파일 | 하는 일 |
| --- | --- | --- |
| 1 | `db/schema.sql` | 표 8개와 접근 권한 만들기. 여러 번 실행해도 안전함 |
| 2 | `db/seed.sql` | 샘플 데이터 넣기 (소재 20, 게시물 10, 성과 30, 수집 회차 기록, 워치리스트 5, 이벤트 5). 이미 데이터가 있으면 멈춤 |
| 나중에 | `db/clear_sample.sql` | 실제 운영 시작 전에 샘플만 지우기 |

샘플 표시: `topics.memo = '샘플 데이터'`, `posts.title`이 `[샘플]`로 시작, `watchlist`·`events`의 `memo = '샘플'`. 이름은 모두 가상이다.
