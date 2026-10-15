// 레포 루트 config/ 폴더의 설정 파일을 읽는다.
// 카테고리·기준값은 코드에 쓰지 않고 항상 여기서 가져온다 (CLAUDE.md 확장성 규칙).
import { parse } from 'yaml'
import categoriesYaml from '../../config/categories.yaml?raw'
import scoringYaml from '../../config/scoring.yaml?raw'

export interface Category {
  id: string
  name: string
}

export interface BoardConfig {
  topNExpanded: number
  upcomingDays: number
  coveredMinSharedKeywords: number
}

interface RawCategory {
  id: string
  name: string
  enabled?: boolean
}

export function parseCategories(text: string): Category[] {
  const raw = parse(text) as { categories?: RawCategory[] }
  return (raw.categories ?? [])
    .filter((c) => c.enabled !== false)
    .map((c) => ({ id: c.id, name: c.name }))
}

export function parseBoardConfig(text: string): BoardConfig {
  const board = (parse(text) as { board?: Record<string, number> }).board ?? {}
  return {
    topNExpanded: board.top_n_expanded,
    upcomingDays: board.upcoming_days,
    coveredMinSharedKeywords: board.covered_min_shared_keywords,
  }
}

export const categories = parseCategories(categoriesYaml)
export const boardConfig = parseBoardConfig(scoringYaml)

export function categoryName(id: string | null): string {
  if (!id) return '미분류'
  return categories.find((c) => c.id === id)?.name ?? id
}
