import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// 动态构建 API 路径正则前缀，兼容可变 FRONTEND_BASE_PATH
const basePath = (process.env.FRONTEND_BASE_PATH || '/growth/').replace(/\/$/, '')
const apiRe = basePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\/api'

// https://vite.dev/config/
export default defineConfig({
  base: basePath + '/',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['vite.svg'],
      manifest: {
        name: 'Growth Assistant - 个人成长助手',
        short_name: 'Growth',
        description: '个人成长管理助手 — 任务、灵感、笔记、知识图谱',
        theme_color: '#6366F1',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '.',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          // 1. SSE/搜索/认证/反馈/意图/调试 — NetworkOnly（不缓存）
          //    覆盖：/ai/chat, /chat, /parse, /search, /auth/*, /feedback/*,
          //    /intent, /playground/*, /entries/search/*, /entries/export
          {
            urlPattern: new RegExp(apiRe + '/(ai/chat|chat|parse|search|auth|feedback|intent|playground|entries/search|entries/export)(/|$|\\?)', 'i'),
            handler: 'NetworkOnly',
          },
          // 2. 条目详情及子资源 GET /entries/{id}(/sub)? — StaleWhileRevalidate
          //    排除 /entries/export 和 /entries/search/*（已被规则 1 拦截）
          {
            urlPattern: new RegExp(apiRe + '/entries/[^/]+(/[^/]+)?(\\?.*)?$', 'i'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'entry-detail-cache',
              expiration: { maxEntries: 100, maxAgeSeconds: 60 * 30 },
            },
          },
          // 3. 条目列表 GET /entries — NetworkFirst（5min TTL）
          {
            urlPattern: new RegExp(apiRe + '/entries(\\?.*)?$', 'i'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'entry-list-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 5 },
              networkTimeoutSeconds: 10,
            },
          },
          // 4. 其他 API — NetworkFirst（5min TTL，兜底）
          {
            urlPattern: new RegExp(apiRe + '/', 'i'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 5 },
              networkTimeoutSeconds: 10,
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:18929",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
