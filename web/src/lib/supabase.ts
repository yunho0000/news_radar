import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// 주소와 anon 키는 web/.env.local 에서 읽는다 (커밋하지 않음). 형식은 web/.env.example 참고.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null
