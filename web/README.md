# 웹 보드 (web/)

소재 레이더의 메인 보드 화면입니다. React + TypeScript (Vite)로 만들었습니다.

## 처음 한 번

1. `.env.example`을 복사해 `.env.local`을 만들고 Supabase 주소와 anon 키를 넣습니다. (`.env.local`은 커밋되지 않습니다)
2. `npm install`

## 실행

| 명령 | 하는 일 |
| --- | --- |
| `npm run dev` | 내 컴퓨터에서 보드 열기 (주소: http://localhost:5173) |
| `npm test` | 계산 로직 테스트 |
| `npm run build` | 배포용 파일 만들기 |

카테고리와 보드 기준값(크게 보여줄 개수, "곧 올 것" 기간, "이미 다룬 소재" 기준)은
레포 루트의 `config/categories.yaml`, `config/scoring.yaml`에서 읽습니다.
