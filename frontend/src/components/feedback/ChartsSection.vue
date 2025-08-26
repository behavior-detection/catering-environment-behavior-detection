<!-- components/feedback/ChartsSection.vue -->
<template>
  <div class="charts-section">
    <div class="charts-grid">
      <!-- 违规类型分布图 -->
      <ViolationPieChart
        :violations-list="violationsList"
        :violation-mapping="violationMapping"
      />

      <!-- 摄像头违规对比图 -->
      <CameraCompareChart
        :cameras-list="camerasList"
      />

      <!-- 24小时分布图 -->
      <HourlyDistributionChart />
    </div>
  </div>
</template>

<script>
import ViolationPieChart from './charts/ViolationPieChart.vue'
import CameraCompareChart from './charts/CameraCompareChart.vue'
import HourlyDistributionChart from './charts/HourlyDistributionChart.vue'

export default {
  name: 'ChartsSection',
  components: {
    ViolationPieChart,
    CameraCompareChart,
    HourlyDistributionChart
  },
  props: {
    violationsList: {
      type: Array,
      default: () => []
    },
    camerasList: {
      type: Array,
      default: () => []
    },
    violationMapping: {
      type: Object,
      default: () => ({})
    }
  }
}
</script>

<style scoped>
.charts-section {
  margin-bottom: 40px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 25px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>