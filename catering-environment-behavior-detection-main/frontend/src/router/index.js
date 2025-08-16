import { createRouter, createWebHistory } from 'vue-router'
import Page1 from '../views/Page1.vue'
import Page2 from '../views/Page2.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Page1,
    meta: { hasSidebar: false, title: '餐饮环境监测系统' }
  },
  {
    path: '/Page2',
    name: 'MyDevicePage2',
    component: Page2,
    meta: { hasSidebar: true, title: '设备管理' }
  },
  {
    path: '/admin-login',
    name: 'AdminLogin',
    component: () => import('../views/Page1_1.vue'),
    meta: { title: '系统管理员登录' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '餐饮环境监测系统'
  next()
})

export default router