// index.js：配置每个路径对应的页面组件及元信息
import { createRouter, createWebHistory } from 'vue-router'
import Page1 from '../views/Page1.vue'
import Page2 from '../views/Page2.vue'


const routes = [
  {
    path: '/',
    name: 'Home',
    component: Page1,
    meta: { hasSidebar: false } // 不显示左侧栏
  },
  {
    path: '/Page2',
    name: 'MyDevicePage2',
    component: Page2,
    meta: { hasSidebar: true } // 显示左侧栏
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
