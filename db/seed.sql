-- 소재 레이더 샘플 데이터 (화면 개발·테스트용)
-- 실행: schema.sql 실행 후, SQL Editor에 이 파일 내용 붙여넣기 → Run
-- 구성: 소재 20개, 게시물 10개, 성과 30개 + 수집 회차 기록, 워치리스트 5개, 예정 이벤트 5개
--
-- 모든 이름은 가상이다. 날짜는 실행 시각 기준으로 계산되므로 언제 넣어도 "최근" 데이터가 된다.
-- 샘플 표시: topics.memo = '샘플 데이터', posts.title 은 '[샘플]'로 시작, watchlist·events 의 memo = '샘플'.
-- 실제 운영을 시작하면 db/clear_sample.sql 로 샘플만 지운다.
-- 안전장치: topics 표에 이미 데이터가 있으면 아무것도 넣지 않고 멈춘다.

do $$
begin
  if exists (select 1 from topics) then
    raise exception 'topics 표에 이미 데이터가 있어 샘플을 넣지 않습니다. (샘플을 다시 넣으려면 clear_sample.sql 먼저 실행)';
  end if;
end;
$$;

-- 소재 20개 ---------------------------------------------------------------------
-- h = 몇 시간 전에 처음 발견됐는지
insert into topics (title, keywords, category, status, phase, hot_score, outlet_count,
                    type_tags, pass_reason, memo, first_seen_at, last_seen_at, status_changed_at)
select title, keywords, category, status, phase, hot_score, outlet_count,
       type_tags, pass_reason, '샘플 데이터',
       now() - make_interval(hours => h),
       now() - make_interval(hours => least(h, 3)),
       now() - make_interval(hours => greatest(h - 2, 0))
from (values
  -- 연예
  ('루미나 새 앨범 컴백 티저 공개',        array['루미나','컴백','티저'],      'entertainment', 'found',     'rising',  92.5, 14, array['event'],  null,        6),
  ('드라마 「푸른 계절」 첫방 시청률 8%',   array['푸른 계절','첫방','시청률'], 'entertainment', 'found',     'rising',  88.0, 11, array['record'], null,        5),
  ('배우 한서윤 영화제 신인상 수상',       array['한서윤','신인상'],           'entertainment', 'found',     'peak',    75.3,  9, array['person'], null,       10),
  ('그룹 노바 월드투어 서울 추가 공연',    array['노바','월드투어'],           'entertainment', 'found',     'rising',  71.0,  7, array['event'],  null,        4),
  ('예능 「주말 캠핑」 출연진 교체',        array['주말 캠핑','출연진'],        'entertainment', 'found',     'falling', 54.2,  6, array['issue'],  null,       20),
  ('가수 윤도하 음원 차트 1위 4주째',      array['윤도하','음원차트'],         'entertainment', 'picked',    'peak',    80.1, 12, array['record'], null,        9),
  ('아이돌 소속사 이적설',                 array['이적설','소속사'],           'entertainment', 'passed',    'rising',  66.0,  3, array['issue'],  'rumor',     7),
  ('웹툰 원작 「달빛 식당」 드라마화 확정', array['달빛 식당','드라마화'],      'entertainment', 'published', 'peak',    70.4,  8, array['event'],  null,       30),
  ('배우 김하람 예능 첫 고정 출연',        array['김하람','고정 출연'],        'entertainment', 'watching',  null,      31.0,  1, '{}',           null,        2),
  ('뮤지컬 「별의 노래」 캐스팅 공개',      array['별의 노래','캐스팅'],        'entertainment', 'watching',  null,      22.5,  1, '{}',           null,        3),
  -- 스포츠
  ('한빛FC 리그 10연승 신기록',            array['한빛FC','연승','신기록'],    'sports',        'found',     'rising',  95.0, 16, array['record'], null,        3),
  ('투수 박진우 메이저리그 진출 확정',     array['박진우','메이저리그'],       'sports',        'found',     'rising',  90.2, 15, array['person'], null,        5),
  ('여자배구 국가대표 최종 명단 발표',     array['여자배구','국가대표'],       'sports',        'found',     'peak',    68.7,  8, array['event'],  null,       12),
  ('골프 이수아 시즌 3승',                 array['이수아','골프','시즌 3승'],  'sports',        'found',     'falling', 58.9,  6, array['record'], null,       26),
  ('농구 신인 드래프트 1순위 지명',        array['드래프트','1순위'],          'sports',        'picked',    'rising',  77.7, 10, array['person'], null,        8),
  ('축구 대표팀 감독 교체 논란',           array['대표팀','감독 교체'],        'sports',        'producing', 'peak',    84.3, 13, array['issue'],  null,       11),
  ('e스포츠 결승 티켓 1분 매진',           array['e스포츠','결승','매진'],     'sports',        'published', 'falling', 62.0,  7, array['event'],  null,       48),
  ('마라톤 대회 코스 변경',                array['마라톤','코스 변경'],        'sports',        'passed',    'falling', 35.0,  4, '{}',           'too_minor', 15),
  ('수영 김태오 아시아 신기록',            array['김태오','아시아 신기록'],    'sports',        'published', 'peak',    73.5,  9, array['record'], null,       40),
  ('야구 올스타 팬투표 중간 집계',         array['올스타','팬투표'],           'sports',        'watching',  null,      28.0,  2, '{}',           null,        1)
) as t(title, keywords, category, status, phase, hot_score, outlet_count, type_tags, pass_reason, h);

-- 수집 회차 기록: 관찰 중이 아닌 소재마다 최근 3회차 (3시간 간격) -------------------
-- 국면에 맞게 언급 수가 늘거나(rising) 멈추거나(peak) 줄어든다(falling).
insert into topic_snapshots (topic_id, collected_at, mention_count, score)
select t.id,
       date_trunc('hour', now()) - make_interval(hours => 3 * r),
       case t.phase
         when 'rising'  then t.outlet_count * (3 - r)
         when 'peak'    then t.outlet_count * 2
         when 'falling' then t.outlet_count * (1 + r)
       end,
       round(t.hot_score * case t.phase when 'rising' then 1 - 0.1 * r
                                        when 'falling' then 1 + 0.1 * r
                                        else 1 end, 1)
from topics t
cross join generate_series(0, 2) as r
where t.memo = '샘플 데이터' and t.phase is not null;

-- 게시물 10개: 발행된 소재 3개 × 플랫폼 3개 + 소급 게시물 1개 -----------------------
insert into posts (topic_id, platform, title, url, published_at)
select t.id, p.platform, '[샘플] ' || t.title,
       'https://example.com/' || p.platform || '/' || t.id,
       t.status_changed_at + make_interval(mins => p.offset_min)
from topics t
cross join (values ('instagram', 0), ('youtube', 10), ('naver_clip', 20)) as p(platform, offset_min)
where t.memo = '샘플 데이터' and t.status = 'published';

insert into posts (topic_id, platform, title, url, published_at)
values (null, 'instagram', '[샘플] 지난달 카드뉴스 (소급)', 'https://example.com/instagram/backfill-1',
        now() - interval '25 days');

-- 성과 30개: 게시물마다 핵심 지표 1개 + 좋아요 + 댓글 ----------------------------------
-- 핵심 지표: instagram = saves_shares (저장+공유), youtube = views, naver_clip = plays
insert into post_metrics (post_id, metric, value, measured_at, is_backfill)
select p.id, m.metric,
       round(m.base * (0.6 + (p.id % 7) * 0.15)),
       case when p.topic_id is null then now() - interval '1 day'
            else p.published_at + interval '3 days' end,
       p.topic_id is null
from posts p
cross join lateral (values
  (case p.platform when 'instagram' then 'saves_shares' when 'youtube' then 'views' else 'plays' end,
   case p.platform when 'instagram' then 420 when 'youtube' then 15000 else 8000 end),
  ('likes',    case p.platform when 'instagram' then 2300 when 'youtube' then 600 else 300 end),
  ('comments', case p.platform when 'instagram' then 85   when 'youtube' then 120 else 40  end)
) as m(metric, base)
where p.title like '[샘플]%';

-- 워치리스트 5개 ---------------------------------------------------------------
insert into watchlist (name, kind, category, hashtags, memo) values
  ('루미나',   'person', 'entertainment', array['루미나','LUMINA'], '샘플'),
  ('노바',     'person', 'entertainment', array['노바','NOVA'], '샘플'),
  ('푸른 계절', 'work',  'entertainment', array['푸른계절'], '샘플'),
  ('한빛FC',   'team',   'sports',        array['한빛FC'], '샘플'),
  ('박진우',   'person', 'sports',        array['박진우'], '샘플');

-- 예정 이벤트 5개 (4개는 7일 이내, 1개는 그 이후) -----------------------------------
insert into events (title, event_date, category, memo, topic_id) values
  ('루미나 정규 3집 발매',      current_date + 2,  'entertainment', '샘플',
     (select id from topics where title = '루미나 새 앨범 컴백 티저 공개')),
  ('연말 가요 시상식',          current_date + 5,  'entertainment', '샘플', null),
  ('한빛FC vs 바다유나이티드',   current_date + 1,  'sports',        '샘플',
     (select id from topics where title = '한빛FC 리그 10연승 신기록')),
  ('여자배구 국가대표 평가전',   current_date + 6,  'sports',        '샘플', null),
  ('드라마 「겨울 정원」 첫방',  current_date + 12, 'entertainment', '샘플', null);
