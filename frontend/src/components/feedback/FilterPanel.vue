<!-- components/feedback/FilterPanel.vue -->
<template>
  <div class="filter-panel">
    <div class="filter-header">
      <div class="filter-title">
        <i class="icon">🔍</i>
        <span>数据筛选控制</span>
      </div>
      <div class="last-update">
        最后更新: {{ lastUpdateTime }}
      </div>
    </div>

    <div class="filter-body">
      <!-- 时间范围选择 -->
      <div class="filter-section">
        <label class="filter-label">
          <i class="icon">📅</i>
          时间范围选择
        </label>
        <div class="time-range-grid">
          <button
            v-for="range in timeRanges"
            :key="range.value"
            :class="['time-range-btn', { active: currentFilter.timeRange === range.value }]"
            @click="selectTimeRange(range.value)"
          >
            <div class="range-title">{{ range.title }}</div>
            <div class="range-desc">{{ range.desc }}</div>
          </button>
        </div>
      </div>

      <!-- 筛选状态 -->
      <div class="filter-status">
        <i class="icon">ℹ️</i>
        <span>{{ filterStatusText }}</span>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button class="btn btn-primary" @click="refreshData" :disabled="isLoading">
          <i class="icon">🔄</i>
          {{ isLoading ? '加载中...' : '刷新数据' }}
        </button>
        <button class="btn btn-secondary" @click="resetFilters">
          <i class="icon">↩️</i>
          重置筛选
        </button>
        <button class="btn btn-secondary" @click="clearData">
          <i class="icon">🗑️</i>
          清空数据
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FilterPanel',
  props: {
    currentFilter: {
      type: Object,
      required: true
    },
    timeRanges: {
      type: Array,
      required: true
    },
    filterStatusText: {
      type: String,
      required: true
    },
    lastUpdateTime: {
      type: String,
      required: true
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['time-range-change', 'refresh-data', 'reset-filters', 'clear-data'],
  methods: {
    selectTimeRange(range) {
      this.$emit('time-range-change', range)
    },
    refreshData() {
      this.$emit('refresh-data')
    },
    resetFilters() {
      this.$emit('reset-filters')
    },
    clearData() {
      this.$emit('clear-data')
    }
  }
}
</script>

<style scoped>
.filter-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  margin-bottom: 30px;
  overflow: hidden;
}

.filter-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.2em;
  font-weight: 600;
}

.last-update {
  font-size: 0.9em;
  opacity: 0.9;
}

.filter-body {
  padding: 30px;
}

.filter-section {
  margin-bottom: 25px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 15px;
  font-size: 1.1em;
}

.time-range-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 15px;
}

.time-range-btn {
  padding: 16px 12px;
  border: 2px solid #e1e5e9;
  border-radius: 12px;
  background: #f8f9fa;
  cursor: pointer;
  text-align: center;
  transition: all 0.3s ease;
  font-size: 0.95em;
}

.time-range-btn:hover {
  border-color: #667eea;
  background: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.time-range-btn.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.range-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.range-desc {
  font-size: 0.8em;
  opacity: 0.8;
}

.filter-status {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border: 1px solid #90caf9;
  border-radius: 10px;
  padding: 15px 20px;
  margin-bottom: 25px;
  font-size: 0.95em;
  color: #1565c0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-buttons {
  display: flex;
  gap: 15px;
  padding-top: 25px;
  border-top: 1px solid #e1e5e9;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.btn-secondary:hover {
  background: #e9ecef;
  border-color: #ced4da;
}

.icon {
  font-size: 1.1em;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-body {
    padding: 20px;
  }

  .time-range-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>