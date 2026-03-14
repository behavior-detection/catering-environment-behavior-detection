const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,

  // 禁用ESLint
  lintOnSave: false,

  // Configure dev server for proxy to backend
  devServer: {
    proxy: {
      '/api': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:8000',
        changeOrigin: true
      },
      '/media': {
        target: process.env.VUE_APP_API_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },

  // Output to Django static directory in production
  outputDir: process.env.NODE_ENV === 'production'
    ? '../backend/staticfiles/vue'
    : 'dist'
})
