/** 마지막 수집 시각을 "10/15 21:00 (2시간 전)" 형태로 보여준다 */
export function formatCollectedAt(iso: string | null, now: Date = new Date()): string {
  if (!iso) return '기록 없음'
  const t = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  const stamp = `${t.getMonth() + 1}/${t.getDate()} ${pad(t.getHours())}:${pad(t.getMinutes())}`

  const minutes = Math.floor((now.getTime() - t.getTime()) / 60_000)
  let ago: string
  if (minutes < 1) ago = '방금'
  else if (minutes < 60) ago = `${minutes}분 전`
  else if (minutes < 60 * 24) ago = `${Math.floor(minutes / 60)}시간 전`
  else ago = `${Math.floor(minutes / (60 * 24))}일 전`
  return `${stamp} (${ago})`
}
