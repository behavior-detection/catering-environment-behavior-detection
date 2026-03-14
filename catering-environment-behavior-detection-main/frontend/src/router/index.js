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
    meta: { hasSidebar: true, title: '设备管理' }
  },
  {
    path: '/Page3',
    name: 'AccountManagement',
    component: Page3,
    meta: { hasSidebar: true, title: '账号管理' }
  },
  {
    path: '/Page2_2',
    name: 'DeviceDetail',
    component: () => import('../views/Page2_2.vue'),
    meta: { hasSidebar: true, title: '设备详情' }
  }
  // 注意：已移除 HistoricalData 独立路由
  // HistoricalData 现在是 Page2 的子组件，通过 Page2 的侧边栏访问
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  // 动态设置页面标题
  let title = to.meta.title || '餐饮环境监测系统'

  document.title = title
  next()
})

export default router