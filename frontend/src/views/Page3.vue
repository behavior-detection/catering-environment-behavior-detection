<template>
  <div class="page3-layout">
    <!-- 左侧栏 -->
    <SideBar @select="currentModule = $event" />

    <!-- 主体区域：根据 currentModule 动态渲染 -->
    <div class="main-content">
      <EditAccount v-if="currentModule === 'EditAccount'" />
      <Logout v-if="currentModule === 'Logout'" />
    </div>
  </div>
</template>

<script>
import SideBar from '@/components/SideBar.vue'
import EditAccount from '@/components/EditAccount.vue'
import Logout from '@/components/Logout.vue'

export default {
  name: 'Page3',
  components: {
    SideBar,
    EditAccount,
    Logout
  },
  data() {
    return {
      currentModule: 'EditAccount' // 默认打开的模块
    }
  }
}
</script>

<style scoped>
.page3-layout {
  display: flex;
}

.main-content {
  flex: 1;
  padding: 20px;
}
</style>
