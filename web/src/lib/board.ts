// 메인 보드 계산 로직 (docs/PLAN.md 9장). 화면과 분리해 테스트할 수 있게 둔다.

export interface Topic {
  id: number
  title: string
  keywords: string[]
  category: string | null
  status: string
  phase: string | null
  hot_score: number | null
  outlet_count: number
  type_tags: string[]
  status_changed_at: string
}

export interface BoardEvent {
  id: number
  title: string
  event_date: string // 'YYYY-MM-DD'
  category: string | null
  topic_id: number | null
}

/** 'all' 이면 전체, 아니면 카테고리 id */
export type CategoryFilter = string

/** "지금 뜨는 것"에 나오는 상태 (필터를 통과한 소재) */
export const TRENDING_STATUSES = ['found']
/** "내 찜 목록"에 나오는 상태 */
export const PICKED_STATUSES = ['picked', 'producing']
/** 이미 발행한 소재로 보는 상태 */
export const PUBLISHED_STATUSES = ['published']

export function byCategory<T extends { category: string | null }>(
  items: T[],
  filter: CategoryFilter,
): T[] {
  return filter === 'all' ? items : items.filter((i) => i.category === filter)
}

/** 지금 뜨는 것: 화제성 점수 높은 순. 점수가 없으면 맨 뒤 */
export function trendingTopics(topics: Topic[], filter: CategoryFilter): Topic[] {
  return byCategory(topics, filter)
    .filter((t) => TRENDING_STATUSES.includes(t.status))
    .sort((a, b) => (b.hot_score ?? -Infinity) - (a.hot_score ?? -Infinity))
}

/** 내 찜 목록: 찜한 순서대로 (상태가 바뀐 시각이 이른 것부터) */
export function pickedTopics(topics: Topic[], filter: CategoryFilter): Topic[] {
  return byCategory(topics, filter)
    .filter((t) => PICKED_STATUSES.includes(t.status))
    .sort((a, b) => a.status_changed_at.localeCompare(b.status_changed_at))
}

/** 날짜 문자열('YYYY-MM-DD')에 일수를 더한다 */
export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** 사용자 컴퓨터 기준 오늘 날짜 'YYYY-MM-DD' */
export function localToday(now: Date = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** 곧 올 것: 오늘부터 days일 안의 이벤트, 날짜순 */
export function upcomingEvents(
  events: BoardEvent[],
  filter: CategoryFilter,
  today: string,
  days: number,
): BoardEvent[] {
  const end = addDays(today, days)
  return byCategory(events, filter)
    .filter((e) => e.event_date >= today && e.event_date <= end)
    .sort((a, b) => a.event_date.localeCompare(b.event_date))
}

/** 오늘로부터 며칠 남았는지 (0 = 오늘) */
export function daysUntil(date: string, today: string): number {
  const ms = Date.parse(`${date}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)
  return Math.round(ms / 86_400_000)
}

/** 키워드 비교용: 공백 제거 + 소문자 */
export function normalizeKeyword(k: string): string {
  return k.replace(/\s+/g, '').toLowerCase()
}

/**
 * "이미 다룬 소재" 판정.
 * 발행한 소재(상태가 발행이거나 게시물이 연결된 소재)와 키워드가
 * minShared개 이상 겹치는 다른 소재의 id 목록을 돌려준다.
 */
export function coveredTopicIds(
  topics: Topic[],
  postedTopicIds: number[],
  minShared: number,
): Set<number> {
  const posted = new Set(postedTopicIds)
  const published = topics.filter(
    (t) => PUBLISHED_STATUSES.includes(t.status) || posted.has(t.id),
  )
  const publishedKeywordSets = published.map(
    (t) => [t.id, new Set(t.keywords.map(normalizeKeyword))] as const,
  )

  const covered = new Set<number>()
  for (const t of topics) {
    if (published.includes(t)) continue
    const mine = new Set(t.keywords.map(normalizeKeyword))
    for (const [, theirs] of publishedKeywordSets) {
      let shared = 0
      for (const k of mine) if (theirs.has(k)) shared++
      if (shared >= minShared) {
        covered.add(t.id)
        break
      }
    }
  }
  return covered
}

/** 상위 n개(크게)와 나머지(접기)로 나눈다 */
export function splitTop<T>(items: T[], n: number): { top: T[]; rest: T[] } {
  return { top: items.slice(0, n), rest: items.slice(n) }
}
