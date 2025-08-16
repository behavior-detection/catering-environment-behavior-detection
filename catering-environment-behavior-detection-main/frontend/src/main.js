// main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 引入全局样式
import './assets/styles/global.css'

// 引入 Font Awesome
import '@fortawesome/fontawesome-free/css/all.min.css'

const app = createApp(App)
app.use(router)
app.mount('#app')