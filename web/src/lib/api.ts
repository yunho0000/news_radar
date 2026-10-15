import type { SupabaseClient } from '@supabase/supabase-js'
import { addDays, localToday, PICKED_STATUSES, PUBLISHED_STATUSES, TRENDING_STATUSES } from './board'
import type { BoardEvent, Topic } from './board'

export interface BoardData {
  topics: Topic[]
  postedTopicIds: number[]
  events: BoardEvent[]
  lastCollectedAt: string | null
}

/** 보드에 필요한 데이터를 한 번에 읽는다. 하나라도 실패하면 오류를 던진다. */
export async function loadBoard(db: SupabaseClient, upcomingDays: number): Promise<BoardData> {
  const today = localToday()
  const statuses = [...TRENDING_STATUSES, ...PICKED_STATUSES, ...PUBLISHED_STATUSES]

  const [topics, posts, events, snapshot] = await Promise.all([
    db
      .from('topics')
      .select('id,title,keywords,category,status,phase,hot_score,outlet_count,type_tags,status_changed_at')
      .in('status', statuses),
    db.from('posts').select('topic_id').not('topic_id', 'is', null),
    db
      .from('events')
      .select('id,title,event_date,category,topic_id')
      .gte('event_date', today)
      .lte('event_date', addDays(today, upcomingDays)),
    // 마지막 수집 시각 = topic_snapshots.collected_at 의 최댓값 (docs/DATA.md)
    db.from('topic_snapshots').select('collected_at').order('collected_at', { ascending: false }).limit(1),
  ])

  for (const r of [topics, posts, events, snapshot]) {
    if (r.error) throw new Error(r.error.message)
  }

  return {
    topics: (topics.data ?? []).map((t) => ({ ...t, hot_score: t.hot_score === null ? null : Number(t.hot_score) })),
    postedTopicIds: (posts.data ?? []).map((p) => p.topic_id as number),
    events: events.data ?? [],
    lastCollectedAt: snapshot.data?.[0]?.collected_at ?? null,
  }
}
