-- 소재 레이더 데이터베이스 구조 (docs/PLAN.md 8장, docs/DATA.md)
-- 실행: Supabase 대시보드 → SQL Editor → 이 파일 내용 붙여넣기 → Run
-- 여러 번 실행해도 안전하다 (이미 있는 표는 건너뜀).
--
-- 원칙: 플랫폼·지표·상태·태그·카테고리는 고정 칸이 아니라 text "값"으로 저장한다.
--       새 값(틱톡, 새 지표 등)이 생겨도 구조를 바꾸지 않는다. 허용 값 목록은 docs/DATA.md에 있다.

-- 1. mentions: 수집한 원시 데이터 한 줄 ---------------------------------------
create table if not exists mentions (
  id            bigint generated always as identity primary key,
  source        text        not null,             -- config/sources.yaml 의 id (google_trends, news_rss …)
  keyword       text,                             -- 트렌드 검색어 등. 뉴스는 비어 있을 수 있음
  headline      text,                             -- 기사 제목 (본문은 저장하지 않는다)
  link          text,
  outlet        text,                             -- 언론사
  category      text,                             -- config/categories.yaml 의 id. 모르면 비움
  collected_at  timestamptz not null default now(),
  unique (source, link)                           -- 같은 소스에서 같은 링크는 한 번만 저장
);
create index if not exists mentions_collected_at_idx on mentions (collected_at desc);

-- 2. topics: 묶어서 정리한 소재 ------------------------------------------------
create table if not exists topics (
  id                 bigint generated always as identity primary key,
  title              text        not null,
  keywords           text[]      not null default '{}',
  category           text,
  status             text        not null default 'watching',  -- watching/found/picked/producing/published/passed
  phase              text,                                     -- rising/peak/falling, 판단 전이면 비움
  hot_score          numeric,                                  -- 화제성 점수
  fit_score          numeric,                                  -- 적합도 점수 (데이터가 쌓이면 생김)
  outlet_count       integer     not null default 0,           -- 다룬 언론사 수
  type_tags          text[]      not null default '{}',        -- issue/record/event/person
  pass_reason        text,                                     -- late/off_tone/rumor/too_minor
  memo               text,
  first_seen_at      timestamptz not null default now(),
  last_seen_at       timestamptz not null default now(),
  status_changed_at  timestamptz not null default now(),       -- "찜한 순" 정렬용
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create index if not exists topics_status_idx on topics (status);
create index if not exists topics_category_score_idx on topics (category, hot_score desc);

-- 3. topic_snapshots: 수집 회차별 소재 기록 (국면 계산용) ------------------------
create table if not exists topic_snapshots (
  id             bigint generated always as identity primary key,
  topic_id       bigint      not null references topics (id) on delete cascade,
  collected_at   timestamptz not null,
  mention_count  integer     not null default 0,
  score          numeric,
  unique (topic_id, collected_at)
);

-- 4. posts: 발행한 게시물 -------------------------------------------------------
create table if not exists posts (
  id            bigint generated always as identity primary key,
  topic_id      bigint      references topics (id) on delete set null,  -- 소급 게시물은 비어 있을 수 있음
  platform      text        not null,                                   -- instagram/youtube/naver_clip …
  title         text,                                                   -- 성과 입력 표에서 알아보기 위한 제목
  url           text,
  published_at  timestamptz not null,                                   -- 업로드 시각 (시간대 분석용)
  created_at    timestamptz not null default now()
);
create index if not exists posts_platform_published_idx on posts (platform, published_at desc);

-- 5. post_metrics: 게시물 성과 --------------------------------------------------
create table if not exists post_metrics (
  id           bigint generated always as identity primary key,
  post_id      bigint      not null references posts (id) on delete cascade,
  metric       text        not null,             -- saves_shares/views/plays/likes …
  value        numeric     not null,
  measured_at  timestamptz not null default now(),
  is_backfill  boolean     not null default false, -- "소급" 입력 여부
  unique (post_id, metric, measured_at)
);

-- 6. watchlist: 관심 인물·팀·작품 -----------------------------------------------
create table if not exists watchlist (
  id          bigint generated always as identity primary key,
  name        text   not null,
  kind        text   not null,                   -- person/team/work
  category    text,
  hashtags    text[] not null default '{}',
  memo        text,
  created_at  timestamptz not null default now()
);

-- 7. events: 예정 이벤트 --------------------------------------------------------
create table if not exists events (
  id          bigint generated always as identity primary key,
  title       text   not null,
  event_date  date   not null,
  category    text,
  memo        text,
  topic_id    bigint references topics (id) on delete set null,
  created_at  timestamptz not null default now()
);
create index if not exists events_date_idx on events (event_date);

-- 8. api_ledger: 한도 장부 ------------------------------------------------------
create table if not exists api_ledger (
  id         bigint generated always as identity primary key,
  source     text        not null,               -- config/sources.yaml 의 id
  query      text        not null,               -- 조회어 (해시태그 등)
  called_at  timestamptz not null default now()
);
create index if not exists api_ledger_source_called_idx on api_ledger (source, called_at desc);

-- topics.updated_at 자동 갱신 ---------------------------------------------------
create or replace function set_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists topics_set_updated_at on topics;
create trigger topics_set_updated_at
  before update on topics
  for each row execute function set_updated_at();

-- 접근 권한 ---------------------------------------------------------------------
-- RLS(행 단위 보안)를 켜면, 아래 정책에 맞는 사람만 표를 읽고 쓸 수 있다.
--  - 로그인한 사용자(authenticated): 읽기·쓰기 가능
--  - 로그인 안 한 방문자(anon): 아무것도 못 함 (정책 없음)
--  - 자동 수집 프로그램: service_role 키를 쓰므로 RLS와 무관하게 접근
-- "나만" 쓰도록 하려면 Supabase에서 새 회원가입을 꺼서 로그인 가능한 계정을 담당자 1명으로 제한한다
-- (docs/DATA.md "접근 권한" 참고).
do $$
declare t text;
begin
  foreach t in array array['mentions','topics','topic_snapshots','posts','post_metrics',
                           'watchlist','events','api_ledger']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists owner_all on %I', t);
    execute format('create policy owner_all on %I for all to authenticated using (true) with check (true)', t);
  end loop;
end;
$$;
