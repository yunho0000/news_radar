import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 레포 루트의 config/*.yaml 을 읽기 위해 web/ 바깥 폴더 접근을 허용한다
    fs: { allow: ['..'] },
  },
})
