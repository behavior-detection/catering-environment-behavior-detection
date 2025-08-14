<!-- components/MainLayout.vue -->
<template>
  <div class="layout">
    <SideBar @select="currentComponent = $event" />
    <div class="main-content">
      <component :is="currentComponentMap[currentComponent]" />
    </div>
  </div>
</template>

<script>
import FindDevice from './FindDevice.vue'
import MonitorLive from './MonitorLive.vue'
import HistoricalData from './HistoricalData.vue'
import FeedbackReport from './FeedbackReport.vue'
import DeviceManagement from './DeviceManagement.vue'

export default {
  components: {
    FindDevice,
    MonitorLive,
    HistoricalData,
    FeedbackReport,
    DeviceManagement
  },
  data() {
    return {
      currentComponent: 'FindDevice',
      currentComponentMap: {
        FindDevice: 'FindDevice',
        MonitorLive: 'MonitorLive',
        HistoricalData: 'HistoricalData',
        FeedbackReport: 'FeedbackReport',
        DeviceManagement: 'DeviceManagement'
      }
    }
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: calc(100vh - 60px); /* 假设顶部导航高度为60px */
}

.main-content {
    flex: 1; 
    padding: 20px;
    background-color: #f8f8f8;
    overflow: auto;
}
</style>
