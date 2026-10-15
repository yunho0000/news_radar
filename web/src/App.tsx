import { useCallback, useEffect, useState } from 'react'
import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { Board } from './components/Board'
import { Login } from './components/Login'
import { boardConfig } from './config'
import { loadBoard, type BoardData } from './lib/api'
import { supabase } from './lib/supabase'

export default function App() {
  if (!supabase) {
    return (
      <div className="notice">
        <h1>설정이 필요해요</h1>
        <p>
          <code>web/.env.local</code> 파일에 <code>VITE_SUPABASE_URL</code>과{' '}
          <code>VITE_SUPABASE_ANON_KEY</code>를 넣고 개발 서버를 다시 켜 주세요.
        </p>
        <p>형식은 <code>web/.env.example</code>을 참고하세요.</p>
      </div>
    )
  }
  return <AuthGate db={supabase} />
}

function AuthGate({ db }: { db: SupabaseClient }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined)

  useEffect(() => {
    db.auth.getSession().then(({ data }) => setSession(data.session))
    const { data } = db.auth.onAuthStateChange((_event, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [db])

  if (session === undefined) return <p className="notice">불러오는 중…</p>
  if (!session) return <Login db={db} />
  return <BoardPage db={db} />
}

function BoardPage({ db }: { db: SupabaseClient }) {
  const [data, setData] = useState<BoardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    setError(null)
    loadBoard(db, boardConfig.upcomingDays)
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [db])

  useEffect(refresh, [refresh])

  const signOut = () => void db.auth.signOut()

  if (error) {
    return (
      <div className="notice">
        <p className="error">데이터를 불러오지 못했어요: {error}</p>
        <button onClick={refresh}>다시 시도</button> <button onClick={signOut}>로그아웃</button>
      </div>
    )
  }
  if (!data) return <p className="notice">불러오는 중…</p>
  return <Board data={data} onRefresh={refresh} onSignOut={signOut} />
}
