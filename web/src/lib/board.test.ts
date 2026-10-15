import { describe, expect, it } from 'vitest'
import {
  addDays,
  coveredTopicIds,
  daysUntil,
  pickedTopics,
  splitTop,
  trendingTopics,
  upcomingEvents,
  type BoardEvent,
  type Topic,
} from './board'

function topic(id: number, over: Partial<Topic>): Topic {
  return {
    id,
    title: `소재 ${id}`,
    keywords: [],
    category: 'entertainment',
    status: 'found',
    phase: 'rising',
    hot_score: 50,
    outlet_count: 3,
    type_tags: [],
    status_changed_at: '2026-10-15T00:00:00Z',
    ...over,
  }
}

function event(id: number, event_date: string, category = 'sports'): BoardEvent {
  return { id, title: `이벤트 ${id}`, event_date, category, topic_id: null }
}

describe('지금 뜨는 것', () => {
  const topics = [
    topic(1, { hot_score: 70 }),
    topic(2, { hot_score: 95, category: 'sports' }),
    topic(3, { hot_score: null }),
    topic(4, { hot_score: 99, status: 'watching' }), // 관찰 중은 안 나옴
    topic(5, { hot_score: 80, status: 'picked' }), // 찜은 찜 목록으로
    topic(6, { hot_score: 88 }),
  ]

  it('발견 상태만 점수 높은 순으로, 점수 없는 소재는 맨 뒤', () => {
    expect(trendingTopics(topics, 'all').map((t) => t.id)).toEqual([2, 6, 1, 3])
  })

  it('카테고리 필터', () => {
    expect(trendingTopics(topics, 'entertainment').map((t) => t.id)).toEqual([6, 1, 3])
    expect(trendingTopics(topics, 'sports').map((t) => t.id)).toEqual([2])
  })

  it('상위 n개와 나머지로 나눈다', () => {
    const { top, rest } = splitTop([1, 2, 3, 4, 5, 6, 7], 5)
    expect(top).toEqual([1, 2, 3, 4, 5])
    expect(rest).toEqual([6, 7])
    expect(splitTop([1, 2], 5)).toEqual({ top: [1, 2], rest: [] })
  })
})

describe('내 찜 목록', () => {
  it('찜·제작 중만, 찜한 순서대로', () => {
    const topics = [
      topic(1, { status: 'picked', status_changed_at: '2026-10-15T05:00:00Z' }),
      topic(2, { status: 'producing', status_changed_at: '2026-10-15T01:00:00Z' }),
      topic(3, { status: 'published', status_changed_at: '2026-10-14T00:00:00Z' }),
      topic(4, { status: 'found' }),
    ]
    expect(pickedTopics(topics, 'all').map((t) => t.id)).toEqual([2, 1])
  })
})

describe('곧 올 것', () => {
  const today = '2026-10-15'
  const events = [
    event(1, '2026-10-21'), // 6일 뒤
    event(2, '2026-10-16', 'entertainment'),
    event(3, '2026-10-14'), // 어제: 제외
    event(4, '2026-10-22'), // 7일 뒤: 포함
    event(5, '2026-10-23'), // 8일 뒤: 제외
    event(6, '2026-10-15'), // 오늘: 포함
  ]

  it('오늘부터 7일 안의 이벤트만 날짜순', () => {
    expect(upcomingEvents(events, 'all', today, 7).map((e) => e.id)).toEqual([6, 2, 1, 4])
  })

  it('카테고리 필터', () => {
    expect(upcomingEvents(events, 'entertainment', today, 7).map((e) => e.id)).toEqual([2])
  })

  it('날짜 계산은 월말도 넘어간다', () => {
    expect(addDays('2026-10-29', 7)).toBe('2026-11-05')
    expect(daysUntil('2026-11-02', '2026-10-30')).toBe(3)
  })
})

describe('이미 다룬 소재', () => {
  const published = topic(1, { status: 'published', keywords: ['한빛FC', '연승'] })
  const linked = topic(2, { status: 'found', keywords: ['루미나', '컴백'] }) // 게시물이 연결된 소재
  const sameTeam = topic(3, { keywords: ['한빛 fc', '감독'] }) // 띄어쓰기·대소문자만 다름
  const sameSinger = topic(4, { keywords: ['루미나', '월드투어'] })
  const unrelated = topic(5, { keywords: ['박진우', '메이저리그'] })
  const topics = [published, linked, sameTeam, sameSinger, unrelated]

  it('발행 소재나 게시물이 연결된 소재와 키워드가 겹치면 표시', () => {
    expect([...coveredTopicIds(topics, [2], 1)].sort()).toEqual([3, 4])
  })

  it('발행한 소재 자신은 표시하지 않는다', () => {
    const ids = coveredTopicIds(topics, [2], 1)
    expect(ids.has(1)).toBe(false)
    expect(ids.has(2)).toBe(false)
  })

  it('겹쳐야 하는 키워드 개수 기준을 올리면 표시가 줄어든다', () => {
    expect(coveredTopicIds(topics, [2], 2).size).toBe(0)
  })

  it('발행한 소재가 없으면 아무것도 표시하지 않는다', () => {
    expect(coveredTopicIds([sameTeam, unrelated], [], 1).size).toBe(0)
  })
})
