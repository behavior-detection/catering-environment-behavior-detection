<template>
  <div class="page2-layout">
    <!-- 左侧栏 -->
    <SideBar @select="currentModule = $event" />

    <!-- 主体区域：根据 currentModule 动态渲染 -->
    <div class="main-content">
      <FindDevice v-if="currentModule === 'FindDevice'" />
      <MonitorLive v-if="currentModule === 'MonitorLive'" />
      <HistoricalData v-if="currentModule === 'HistoricalData'" />
      <FeedbackReport v-if="currentModule === 'FeedbackReport'" />
      <DeviceManagement v-if="currentModule === 'DeviceManagement'" />
    </div>
  </div>
</template>

<script>
import SideBar from '@/components/SideBar.vue'
import FindDevice from '@/components/FindDevice.vue'
import MonitorLive from '@/components/MonitorLive.vue'
import HistoricalData from '@/components/HistoricalData.vue'
import FeedbackReport from '@/components/FeedbackReport.vue'
import DeviceManagement from '@/components/DeviceManagement.vue'

export default {
  name: 'Page2',
  components: {
    SideBar,
    FindDevice,
    MonitorLive,
    HistoricalData,
    FeedbackReport,
    DeviceManagement
  },
  data() {
    return {
      currentModule: 'FindDevice' // 默认打开的模块
    }
  }
}
</script>

<style scoped>
.page2-layout {
  display: flex;
}

.main-content {
  flex: 1;
  padding: 20px;
}
</style>