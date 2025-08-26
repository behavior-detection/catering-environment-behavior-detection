// frontend/vite.config.js

import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },

  server: {
    proxy: {
      //当请求路径以 /api 开头时，触发此代理规则
      '/api': {
        // 目标服务器：Django后端的地址
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})