import { useState, type FormEvent } from 'react'
import type { SupabaseClient } from '@supabase/supabase-js'

// 개발용 간단 로그인 (이메일 + 비밀번호). 정식 로그인 화면은 이슈 #12에서 만든다.
export function Login({ db }: { db: SupabaseClient }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const { error } = await db.auth.signInWithPassword({ email, password })
    if (error) setError('로그인 실패: 이메일과 비밀번호를 확인해 주세요.')
    setBusy(false)
  }

  return (
    <form className="login" onSubmit={submit}>
      <h1>소재 레이더</h1>
      <label>
        이메일
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
      </label>
      <label>
        비밀번호
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? '로그인 중…' : '로그인'}</button>
    </form>
  )
}
