<template>
  <div class="page2-layout">
    <SideBar @select="handleModuleSelect" />

    <div class="main-content">
      <FindDevice v-if="currentModule === 'FindDevice'" />
      <MonitorLive v-if="currentModule === 'MonitorLive'" />
      <HistoricalData
        v-if="currentModule === 'HistoricalData'"
        :manager-eid="managerEid"
        :warehouse-id="warehouseId"
      />
      <FeedbackReport v-if="currentModule === 'FeedbackReport'" />
      <DeviceManagement v-if="currentModule === 'DeviceManagement'" />
      <ViewPermissionRequests v-if="currentModule === 'ViewPermissionRequests'" />
      <SubmitPermissionRequest v-if="currentModule === 'SubmitPermissionRequest'" />
      <CheckRequestStatus v-if="currentModule === 'CheckRequestStatus'" />
      <GenerateToken v-if="currentModule === 'GenerateToken'"/>
      <TokenManager v-if="currentModule === 'TokenManager'"/>
    </div>
  </div>
</template>

<script>
import { navLockManager } from '@/services/NavLockManager'
import { mapGetters, mapActions } from 'vuex'

import SideBar from '@/components/SideBar.vue'
import FindDevice from '@/components/FindDevice.vue'
import MonitorLive from '@/components/MonitorLive.vue'
import HistoricalData from '@/components/HistoricalData.vue'
import FeedbackReport from '@/components/FeedbackReport.vue'
import DeviceManagement from '@/components/DeviceManagement.vue'
import ViewPermissionRequests from '@/components/ViewPermissionRequests.vue'
import SubmitPermissionRequest from '@/components/SubmitPermissionRequest.vue'
import CheckRequestStatus from '@/components/CheckRequestStatus.vue'
import TokenManager from '@/components/TokenManager.vue'
import GenerateToken  from "@/components/GenerateToken.vue";

export default {
  name: 'Page2',
  components: {
    SideBar,
    FindDevice,
    MonitorLive,
    HistoricalData,
    FeedbackReport,
    DeviceManagement,
    ViewPermissionRequests,
    SubmitPermissionRequest,
    CheckRequestStatus,
    TokenManager,
    GenerateToken,
  },
  data() {
    return {
      managerEid: '',
      warehouseId: ''
    }
  },
  computed: {
    ...mapGetters({
      currentModule: 'navigation/currentModule'
    })
  },
  mounted() {
    navLockManager.updateLocksByRoute()

    const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')

    if (userInfo.userType === 'manager') {
      this.managerEid = userInfo.eid || ''
      this.warehouseId = userInfo.warehouseId || ''
    }
  },
  methods: {
    ...mapActions({
      setCurrentModule: 'navigation/setCurrentModule'
    }),

    handleModuleSelect(moduleName) {
      this.setCurrentModule(moduleName)
    }
  }
}
</script>

<style scoped>
/* 保持原有样式不变 */
.page2-layout {
  display: flex;
  min-height: calc(100vh - 60px);
}

.main-content {
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
  overflow-y: auto;
}

.main-content > div {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .page2-layout {
    flex-direction: column;
  }

  .main-content {
    padding: 15px;
  }
}
</style>