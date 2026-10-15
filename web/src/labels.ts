// DB에 영어 값으로 저장된 것을 화면용 한글 이름으로 바꾼다 (docs/DATA.md 2장 "허용 값").
// 표에 없는 새 값이 들어오면 값 그대로 보여준다.

const STATUS: Record<string, string> = {
  watching: '관찰 중',
  found: '발견',
  picked: '찜',
  producing: '제작 중',
  published: '발행',
  passed: '패스',
}

const PHASE: Record<string, string> = {
  rising: '상승 중',
  peak: '정점',
  falling: '하락',
}

const TYPE_TAG: Record<string, string> = {
  issue: '이슈형',
  record: '기록형',
  event: '이벤트형',
  person: '인물형',
}

export const statusLabel = (v: string) => STATUS[v] ?? v
export const phaseLabel = (v: string | null) => (v ? (PHASE[v] ?? v) : '판단 전')
export const typeTagLabel = (v: string) => TYPE_TAG[v] ?? v
