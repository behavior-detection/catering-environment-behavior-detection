<template>
  <div class="feedback-report">
    <AIQuerySection
      :query-examples="queryExamples"
      @ai-query="handleAIQuery"
    />
    <MessageToast
      v-if="message.show"
      :type="message.type"
      :text="message.text"
    />
  </div>
</template>

<script>
// Script部分与之前相同，保持不变
import { violationsAPI, aiAPI } from '@/services/api'
import AIQuerySection from './feedback/AIQuerySection.vue'
import MessageToast from './common/MessageToast.vue'

export default {
  name: 'FeedbackReport',
  components: {
    AIQuerySection,
    MessageToast
  },
  data() {
    return {
      // 基础状态
      isLoading: false,
      lastUpdateTime: '--',

      // 筛选状态
      currentFilter: {
        timeRange: '24h'
      },

      // 时间范围选项
      timeRanges: [
        { value: '1h', title: '1小时', desc: '最近1小时' },
        { value: '24h', title: '24小时', desc: '最近1天' },
        { value: '7d', title: '7天', desc: '最近一周' },
        { value: '30d', title: '30天', desc: '最近一月' },
        { value: 'all', title: '全部', desc: '所有数据' }
      ],

      // 仪表盘数据
      dashboardData: {
        totalViolations: 0,
        totalRecords: 0,
        activeCameras: 0,
        avgViolations: 0
      },

      // 列表数据
      violationsList: [],
      camerasList: [],
      recentRecords: [],

      // AI查询示例
      queryExamples: [
        '今天违规情况如何？',
        '哪个摄像头违规最多？',
        '口罩佩戴情况怎么样？',
        '当前风险等级如何？',
        '最近一周的违规趋势'
      ],

      // 消息提示
      message: {
        show: false,
        type: 'info',
        text: ''
      },

      // 违规类型映射
      violationMapping: {
        'mask': '未佩戴口罩',
        'hat': '未佩戴工作帽',
        'phone': '使用手机',
        'cigarette': '吸烟行为',
        'mouse': '鼠患问题',
        'uniform': '工作服违规',
        'person': '人员检测',
        'no_mask': '未佩戴口罩',
        'no_hat': '未佩戴工作帽',
        'phone_usage': '使用手机',
        'smoking': '吸烟行为',
        'mouse_infestation': '鼠患问题',
        'uniform_violation': '工作服违规',
        'unknown': '未知违规'
      }
    }
  },

  computed: {
    filterStatusText() {
      const rangeText = this.timeRanges.find(r => r.value === this.currentFilter.timeRange)?.desc || '最近24小时'
      return `当前筛选：${rangeText}`
    }
  },

  mounted() {
    this.loadData()

    // 定期刷新数据
    this.refreshInterval = setInterval(() => {
      if (!this.isLoading) {
        this.loadData()
      }
    }, 60000)
  },

  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },

  methods: {
    // 选择时间范围
    selectTimeRange(range) {
      this.currentFilter.timeRange = range
      this.loadData()
    },

    // 刷新数据
    async refreshData() {
      await this.loadData()
    },

    // 重置筛选
    resetFilters() {
      this.currentFilter.timeRange = '24h'
      this.loadData()
      this.showMessage('筛选条件已重置', 'info')
    },

    // 清空数据
    async clearData() {
      if (!confirm('确认清空所有违规数据？此操作不可恢复。')) {
        return
      }

      try {
        this.showMessage('正在清空数据...', 'info')
        const response = await violationsAPI.clearData()

        if (response.data.success) {
          this.showMessage(`数据已清空 - 删除了 ${response.data.cleared_records || 0} 条记录`, 'success')
          setTimeout(() => {
            this.loadData()
          }, 1000)
        } else {
          throw new Error(response.data.message || '清空数据失败')
        }
      } catch (error) {
        console.error('清空数据失败:', error)
        this.showMessage('清空数据失败: ' + error.message, 'error')
      }
    },

    // 加载数据
    async loadData() {
      if (this.isLoading) return

      this.isLoading = true

      try {
        const params = {}

        if (this.currentFilter.timeRange === 'all') {
          params.range = 'all'
          params.all = 'true'
        } else {
          params.range = this.currentFilter.timeRange
        }

        console.log('开始加载数据，参数:', params)
        const response = await violationsAPI.getAnalytics(params)

        if (response.data && response.data.success) {
          this.updateDashboard(response.data.data)
          this.showMessage('数据加载成功', 'success')
        } else {
          // 如果后端返回错误，使用默认数据
          console.warn('后端返回错误，使用默认数据')
          this.updateDashboard({
            summary: {
              total_violations: 0,
              total_records: 0,
              active_cameras: 0
            },
            violations_by_type: {},
            violations_by_camera: {},
            recent_records: []
          })
          this.showMessage('后端服务暂时不可用，显示默认数据', 'warning')
        }

      } catch (error) {
        console.error('加载数据失败:', error)

        // 使用默认数据避免页面崩溃
        this.updateDashboard({
          summary: {
            total_violations: 0,
            total_records: 0,
            active_cameras: 0
          },
          violations_by_type: {},
          violations_by_camera: {},
          recent_records: []
        })

        if (error.code === 'ERR_NETWORK') {
          this.showMessage('网络连接失败，请检查后端服务是否启动', 'error')
        } else {
          this.showMessage('加载数据失败: ' + (error.response?.data?.message || error.message), 'error')
        }
      } finally {
        this.isLoading = false
        this.lastUpdateTime = new Date().toLocaleTimeString()
      }
    },

    // 更新仪表盘
    updateDashboard(data) {
      const summary = data.summary || {}

      this.dashboardData = {
        totalViolations: summary.total_violations || 0,
        totalRecords: summary.total_records || 0,
        activeCameras: summary.active_cameras || 0,
        avgViolations: summary.total_records > 0 ?
          (summary.total_violations / summary.total_records).toFixed(1) : '0'
      }

      this.updateViolationsList(data.violations_by_type || {})
      this.updateCamerasList(data.violations_by_camera || {})
      this.updateRecentRecords(data.recent_records || [])
    },

    // 更新违规类型列表
    updateViolationsList(violationsByType) {
      if (!violationsByType || Object.keys(violationsByType).length === 0) {
        this.violationsList = []
        return
      }

      this.violationsList = Object.entries(violationsByType)
        .filter(([type, count]) => count > 0)
        .sort(([,a], [,b]) => b - a)
        .map(([type, count]) => ({
          type,
          name: this.violationMapping[type] || `${type}(原始)`,
          count
        }))
    },

    // 更新摄像头列表
    updateCamerasList(violationsByCamera) {
      if (!violationsByCamera || Object.keys(violationsByCamera).length === 0) {
        this.camerasList = []
        return
      }

      this.camerasList = Object.entries(violationsByCamera)
        .sort(([,a], [,b]) => b - a)
        .map(([camera_id, violations]) => ({
          camera_id,
          violations
        }))
    },

    // 更新最近记录
    updateRecentRecords(recentRecords) {
      this.recentRecords = recentRecords.slice(0, 10)
    },

    // 处理AI查询
    async handleAIQuery(queryData) {
      try {
        const response = await aiAPI.query(queryData)

        if (response.data.success) {
          // AI查询成功，结果将在AIQuerySection组件中处理
          this.showMessage('AI分析完成', 'success')
        } else {
          throw new Error(response.data.message || 'AI查询失败')
        }
      } catch (error) {
        console.error('AI查询失败:', error)
        this.showMessage('AI查询失败: ' + error.message, 'error')
      }
    },

    // 显示消息
    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, type === 'error' ? 5000 : 3000)
    }
  }
}
</script>

<style scoped>
/* 定义主题颜色变量 */
:root {
  --primary-color: #42A5F5;
  --primary-color-dark: #1976D2;
  --background-gradient: linear-gradient(180deg, #f0f8ff 0%, #f7fbff 100%);
  --text-color-primary: #111827; /* 近黑色 */
  --text-color-secondary: #6B7280; /* 灰色 */
  --card-border-color: #E3F2FD;
  --card-background-color: #ffffff;
}

.feedback-report {
  padding: 15px;
  background: var(--background-gradient);
  min-height: calc(100vh - 60px);
  overflow-y: auto;
  color: var(--text-color-primary);
}

/* 使用 :deep() 来影响子组件的样式 */
.feedback-report :deep(.ai-query-section) {
  background: var(--card-background-color);
  border: 1px solid var(--card-border-color);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(66, 165, 245, 0.05);
}

.feedback-report :deep(h2) {
    color: var(--text-color-primary);
}

.feedback-report :deep(.query-input-area .input-group .query-input) {
    border-color: var(--card-border-color);
    color: var(--text-color-primary);
}

.feedback-report :deep(.query-input-area .input-group .query-input:focus) {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.2);
}

.feedback-report :deep(.query-input-area .input-group .send-button) {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: white;
}
.feedback-report :deep(.query-input-area .input-group .send-button:hover) {
    background-color: var(--primary-color-dark);
    border-color: var(--primary-color-dark);
}

.feedback-report :deep(.example-queries .example-btn) {
    background-color: #F7FBFF;
    border: 1px solid var(--card-border-color);
    color: var(--primary-color-dark);
}

.feedback-report :deep(.example-queries .example-btn:hover) {
    background-color: #E3F2FD;
    border-color: #90CAF9;
}

.feedback-report :deep(.ai-response-area .response-content) {
    background-color: #F7FBFF;
    border: 1px solid var(--card-border-color);
    color: var(--text-color-primary);
}

.feedback-report :deep(.response-content pre) {
    background-color: #EFF6FF;
    color: var(--text-color-primary);
}

</style>