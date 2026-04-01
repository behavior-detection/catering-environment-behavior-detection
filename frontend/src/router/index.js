import { createRouter, createWebHistory } from 'vue-router'
import Page1 from '../views/Page1.vue'
import Page2 from '../views/Page2.vue'
import Page3 from '../views/Page3.vue'

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
    meta: { hasSidebar: true, title: '设备管理', requireAuth: true }
  },
  {
    path: '/Page3',
    name: 'AccountManagement',
    component: Page3,
    meta: { hasSidebar: true, title: '账号管理', requireAuth: true }
  },
  {
    path: '/Page2_2',
    name: 'DeviceDetail',
    component: () => import('../views/Page2_2.vue'),
    meta: { hasSidebar: true, title: '设备详情', requireAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '餐饮环境监测系统'

  if (to.meta.requireAuth) {
    const token = localStorage.getItem('authToken')
    const userInfo = sessionStorage.getItem('userInfo') || sessionStorage.getItem('adminInfo')
    if (!token && !userInfo) {
      next({ path: '/' })
      return
    }
  }

  next()
})

export default router