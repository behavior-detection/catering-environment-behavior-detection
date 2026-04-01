// main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from '../store'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import './assets/styles/global.css'
import '@fortawesome/fontawesome-free/css/all.min.css'

import { navLockManager } from './services/NavLockManager'

const app = createApp(App)

app.use(store)
app.use(router)
app.use(ElementPlus)

router.afterEach((to, from) => {
  setTimeout(() => {
    navLockManager.updateLocksByRoute()
  }, 100)
})

app.mount('#app')

window.addEventListener('beforeunload', () => {
  navLockManager.destroy()
})