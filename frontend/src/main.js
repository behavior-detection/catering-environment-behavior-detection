// main.js：Vue 应用入口文件，挂载 Vue 实例，并使用路由
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 引入 Font Awesome 图标库
import '@fortawesome/fontawesome-free/css/all.min.css'

const app = createApp(App)

app.use(router)
app.use(ElementPlus)

app.mount('#app') // 将 Vue 应用挂载到 index.html 的 #app 上
