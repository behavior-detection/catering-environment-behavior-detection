// main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from '../store'

// 引入全局样式
import './assets/styles/global.css'

// 引入 Font Awesome
import '@fortawesome/fontawesome-free/css/all.min.css'

// 引入全局导航锁定管理器
import { navLockManager } from './services/NavLockManager'

const app = createApp(App)

app.use(store)
app.use(router)

// 在路由守卫中更新锁定状态
router.afterEach((to, from) => {
  // 延迟执行以确保DOM更新完成
  setTimeout(() => {
    navLockManager.updateLocksByRoute()
  }, 100)
})

app.mount('#app')

// 应用卸载时清理
window.addEventListener('beforeunload', () => {
  navLockManager.destroy()
})