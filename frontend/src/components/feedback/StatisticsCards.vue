<!-- components/feedback/StatisticsCards.vue -->
<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{{ dashboardData.totalViolations || '--' }}</div>
      <div class="stat-label">总违规次数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ dashboardData.totalRecords || '--' }}</div>
      <div class="stat-label">检测记录数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ dashboardData.activeCameras || '--' }}</div>
      <div class="stat-label">活跃摄像头</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ dashboardData.avgViolations || '--' }}</div>
      <div class="stat-label">平均违规/记录</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatisticsCards',
  props: {
    dashboardData: {
      type: Object,
      required: true,
      default: () => ({
        totalViolations: 0,
        totalRecords: 0,
        activeCameras: 0,
        avgViolations: 0
      })
    }
  }
}
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 25px;
  margin-bottom: 40px;
}

.stat-card {
  background: white;
  padding: 30px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.15);
}

.stat-value {
  font-size: 2.8em;
  font-weight: 800;
  color: #667eea;
  margin-bottom: 10px;
  line-height: 1;
}

.stat-label {
  color: #6c757d;
  font-size: 0.95em;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>