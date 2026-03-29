import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initUidHeader } from './lib/uid'

// 初始化匿名 UID，所有 fetch 请求自动携带 X-UID header
initUidHeader()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
