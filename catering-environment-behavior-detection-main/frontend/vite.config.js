// vite.config.js - 合并配置
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools' 
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'; 

export default defineConfig(({ mode }) => {
  // 根据当前工作目录加载 .env 文件
  const env = loadEnv(mode, process.cwd(), '');
  const backendPort = env.PYTHON_APP_PORT || '8081';
  const backendUrl = `http://localhost:${backendPort}`;
  const wsUrl = `ws://localhost:${backendPort}`;

  console.log(`[Vite] 代理目标已动态设置为: ${backendUrl}`); 

  return {
    plugins: [
      vue(),
      vueDevTools()
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5174,
      host: true,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true
        },
        '/admin': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/ws': {
          target: `ws://localhost:${backendPort}`,
          ws: true, // 关键：必须开启这个支持
          changeOrigin: true
        },
        '/visitor_login': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/manager_login': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/admin_login': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/get-security-questions': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/verify-security-answers': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/reset-password': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/check-enterprise': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/ocr-idcard': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/ocr-business-license': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/save-employee-verification': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/save-license-file': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/save-employee-verification-data': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/save-legal-representative-id': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/system': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/face': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/login': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/preview-registration-file': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        '/download-registration-file': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        },
        // 也添加统一的文件保存接口
        '/save-registration-file': {
          target: backendUrl,
          changeOrigin: true,
          secure: false
        }
      }
    },
    // 构建配置
    build: {
      // 生产环境移除 console 和 debugger
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true
        }
      },
      // 分包策略
      rollupOptions: {
        output: {
          manualChunks: {
            'vue-vendor': ['vue', 'vue-router', 'vuex']
          }
        }
      }
    }
  }
})