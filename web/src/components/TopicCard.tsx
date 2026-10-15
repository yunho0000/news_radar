import { categoryName } from '../config'
import type { Topic } from '../lib/board'
import { phaseLabel, statusLabel, typeTagLabel } from '../labels'

interface Props {
  topic: Topic
  covered: boolean
  size: 'large' | 'small'
  rank?: number
  showStatus?: boolean
}

export function TopicCard({ topic, covered, size, rank, showStatus }: Props) {
  return (
    <article className={`card card-${size}`}>
      <div className="card-top">
        {rank !== undefined && <span className="rank">{rank}</span>}
        <h3>{topic.title}</h3>
        <span className="score" title="화제성 점수">
          {topic.hot_score === null ? '-' : topic.hot_score.toFixed(1)}
        </span>
      </div>
      <div className="badges">
        <span className="badge">{categoryName(topic.category)}</span>
        <span className={`badge phase phase-${topic.phase ?? 'none'}`}>{phaseLabel(topic.phase)}</span>
        <span className="badge" title="이 소재를 다룬 언론사 수">언론사 {topic.outlet_count}곳</span>
        {showStatus && <span className="badge status">{statusLabel(topic.status)}</span>}
        {covered && <span className="badge covered">이미 다룬 소재</span>}
      </div>
      {size === 'large' && topic.type_tags.length > 0 && (
        <div className="tags">{topic.type_tags.map((t) => `#${typeTagLabel(t)}`).join(' ')}</div>
      )}
    </article>
  )
}
