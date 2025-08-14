<!-- App.vue：根组件，包含顶部导航条和路由内容展示区域 -->
<template>
  <div>
    <TopNav />
    <!-- 路由匹配的页面将在此插入 -->
    <RouterView />
  </div>
</template>

<script>
import TopNav from './components/TopNav.vue'
import RouterView from './components/RouterView.vue'
import { useRoute } from 'vue-router'
import { computed } from 'vue'

export default {
  components: { TopNav },
}
</script>
