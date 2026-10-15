import { useMemo, useState } from 'react'
import { boardConfig, categories, categoryName } from '../config'
import type { BoardData } from '../lib/api'
import {
  coveredTopicIds,
  daysUntil,
  localToday,
  pickedTopics,
  splitTop,
  trendingTopics,
  upcomingEvents,
  type CategoryFilter,
} from '../lib/board'
import { formatCollectedAt } from '../lib/format'
import { TopicCard } from './TopicCard'

interface Props {
  data: BoardData
  onRefresh?: () => void
  onSignOut?: () => void
  now?: Date
}

export function Board({ data, onRefresh, onSignOut, now = new Date() }: Props) {
  const [filter, setFilter] = useState<CategoryFilter>('all')
  const [showRest, setShowRest] = useState(false)
  const today = localToday(now)

  const covered = useMemo(
    () => coveredTopicIds(data.topics, data.postedTopicIds, boardConfig.coveredMinSharedKeywords),
    [data],
  )
  const trending = splitTop(trendingTopics(data.topics, filter), boardConfig.topNExpanded)
  const upcoming = upcomingEvents(data.events, filter, today, boardConfig.upcomingDays)
  const picked = pickedTopics(data.topics, filter)

  return (
    <div className="board">
      <header className="board-header">
        <h1>소재 레이더</h1>
        <nav className="filter" aria-label="카테고리 필터">
          {[{ id: 'all', name: '전체' }, ...categories].map((c) => (
            <button
              key={c.id}
              className={filter === c.id ? 'active' : ''}
              aria-pressed={filter === c.id}
              onClick={() => setFilter(c.id)}
            >
              {c.name}
            </button>
          ))}
        </nav>
        <div className="meta">
          <span>마지막 수집: {formatCollectedAt(data.lastCollectedAt, now)}</span>
          {onRefresh && <button className="link" onClick={onRefresh}>새로고침</button>}
          {onSignOut && <button className="link" onClick={onSignOut}>로그아웃</button>}
        </div>
      </header>

      <main className="columns">
        <section className="column">
          <h2>지금 뜨는 것 <small>{trending.top.length + trending.rest.length}</small></h2>
          {trending.top.length === 0 && <p className="empty">아직 뜨는 소재가 없어요.</p>}
          {trending.top.map((t, i) => (
            <TopicCard key={t.id} topic={t} rank={i + 1} covered={covered.has(t.id)} size="large" />
          ))}
          {trending.rest.length > 0 && (
            <>
              <button className="toggle" onClick={() => setShowRest((v) => !v)} aria-expanded={showRest}>
                {showRest ? '접기' : `나머지 ${trending.rest.length}개 더 보기`}
              </button>
              {showRest &&
                trending.rest.map((t, i) => (
                  <TopicCard
                    key={t.id}
                    topic={t}
                    rank={trending.top.length + i + 1}
                    covered={covered.has(t.id)}
                    size="small"
                  />
                ))}
            </>
          )}
        </section>

        <section className="column">
          <h2>곧 올 것 <small>{upcoming.length}</small></h2>
          {upcoming.length === 0 && (
            <p className="empty">{boardConfig.upcomingDays}일 안에 예정된 이벤트가 없어요.</p>
          )}
          <ul className="events">
            {upcoming.map((e) => {
              const d = daysUntil(e.event_date, today)
              return (
                <li key={e.id} className="event">
                  <span className="dday">{d === 0 ? '오늘' : `D-${d}`}</span>
                  <div>
                    <div className="event-title">{e.title}</div>
                    <div className="sub">
                      {e.event_date.slice(5).replace('-', '/')} · {categoryName(e.category)}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="column">
          <h2>내 찜 목록 <small>{picked.length}</small></h2>
          {picked.length === 0 && <p className="empty">찜한 소재가 없어요.</p>}
          {picked.map((t) => (
            <TopicCard key={t.id} topic={t} covered={covered.has(t.id)} size="small" showStatus />
          ))}
        </section>
      </main>
    </div>
  )
}
