import { describe, expect, it } from 'vitest'
import { boardConfig, categories, parseCategories } from './config'

describe('설정 파일 읽기', () => {
  it('config/categories.yaml 의 카테고리를 읽는다', () => {
    expect(categories.map((c) => c.id)).toEqual(['entertainment', 'sports'])
  })

  it('꺼진 카테고리(enabled: false)는 빠진다', () => {
    const text = `categories:
  - { id: a, name: A, enabled: true }
  - { id: b, name: B, enabled: false }
  - { id: c, name: C }`
    expect(parseCategories(text).map((c) => c.id)).toEqual(['a', 'c'])
  })

  it('config/scoring.yaml 의 보드 설정을 읽는다', () => {
    expect(boardConfig.topNExpanded).toBeGreaterThan(0)
    expect(boardConfig.upcomingDays).toBeGreaterThan(0)
    expect(boardConfig.coveredMinSharedKeywords).toBeGreaterThan(0)
  })
})
