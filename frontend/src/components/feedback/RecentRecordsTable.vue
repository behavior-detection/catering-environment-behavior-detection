<template>
  <div class="recent-records">
    <div class="panel-header">最近检测记录</div>
    <div class="panel-body">
      <table class="records-table">
        <thead>
          <tr>
            <th>摄像头ID</th>
            <th>检测时间</th>
            <th>创建时间</th>
            <th>违规次数</th>
            <th>违规类型</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="recentRecords.length === 0">
            <td colspan="5" class="empty-state">
              <div class="loading-spinner"></div>
              <div>加载中...</div>
            </td>
          </tr>
          <tr v-for="record in recentRecords" :key="record.record_id" class="record-row">
            <td>{{ record.camera_id }}</td>
            <td><span class="timestamp">{{ formatDateTime(record.timestamp) }}</span></td>
            <td><span class="timestamp">{{ formatDateTime(record.created_at) }}</span></td>
            <td><strong>{{ record.total_violations || 0 }}</strong></td>
            <td>{{ formatViolationTypes(record.violations) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RecentRecordsTable',
  props: {
    recentRecords: {
      type: Array,
      default: () => []
    },
    violationMapping: {
      type: Object,
      default: () => ({})
    }
  },
  methods: {
    formatViolationTypes(violations) {
      if (!violations || Object.keys(violations).length === 0) {
        return '无违规'
      }

      return Object.entries(violations)
        .filter(([type, count]) => count > 0)
        .map(([type, count]) => {
          const displayName = this.violationMapping[type] || `${type}(原始)`
          return `${displayName}(${count}次)`
        })
        .join(', ')
    },
    formatDateTime(dateTimeStr) {
      if (!dateTimeStr) return '--'
      try {
        return new Date(dateTimeStr).toLocaleString()
      } catch {
        return dateTimeStr
      }
    }
  }
}
</script>

<style scoped>
.recent-records {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  overflow: hidden;
  margin-bottom: 40px;
}

.panel-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 25px;
  font-size: 1.2em;
  font-weight: 600;
}

.panel-body {
  padding: 0;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th {
  background: #f8f9fa;
  padding: 18px 20px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
  font-size: 0.95em;
}

.records-table td {
  padding: 18px 20px;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
}

.record-row:hover {
  background: #f8f9fa;
}

.timestamp {
  color: #6c757d;
  font-size: 0.9em;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .records-table {
    font-size: 0.9em;
  }
}
</style>