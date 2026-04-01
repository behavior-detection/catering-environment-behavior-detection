<template>
  <div class="feedback-report">
    <!-- Visitor模式横幅 -->
    <div v-if="isVisitorMode && visitorInfo" class="visitor-mode-banner">
      <div class="banner-content">
        <i class="fas fa-user-shield"></i>
        <div class="banner-text">
          <strong>访问者模式</strong>
          <span>
            {{ visitorInfo.visitor_name }} |
            授权类型: {{ getAccessTypeText(visitorInfo.access_type) }} |
            授权范围: {{ visitorInfo.access_value }} |
            授权人: {{ visitorInfo.approved_by }}
          </span>
        </div>
        <button @click="exitVisitorMode" class="exit-btn">
          <i class="fas fa-sign-out-alt"></i>
          退出访问
        </button>
      </div>
    </div>

    <div v-if="aiMode === 'loading'" class="ai-loading-placeholder" style="text-align:center;padding:40px;color:#999;">
      <i class="fas fa-spinner fa-spin" style="font-size:24px;margin-bottom:10px;display:block;"></i>
      正在检测AI引擎状态...
    </div>

    <ChatInterface v-else-if="aiMode === 'smart'" />

    <AIQuerySection
      v-else
      :query-examples="queryExamples"
      :is-visitor-mode="isVisitorMode"
      :visitor-access-token="visitorAccessToken"
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
import { violationsAPI, aiAPI, visitorAPI } from '@/services/api'
import { ElMessageBox } from 'element-plus'
import AIQuerySection from './feedback/AIQuerySection.vue'
import ChatInterface from './feedback/ChatInterface.vue'
import MessageToast from './common/MessageToast.vue'
import axios from 'axios'

export default {
  name: 'FeedbackReport',
  components: {
    AIQuerySection,
    ChatInterface,
    MessageToast
  },
  data() {
    return {
      aiMode: 'loading',
      aiModeTimer: null,
      // 用户类型检测
      userType: '',
      currentEid: '',
      isVisitorMode: false,
      visitorAccessToken: '',
      visitorInfo: null,  // 添加完整的visitorInfo对象

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
        'person': '人员检测'
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
    this.detectUserType()
    this.loadData()
    this.detectAIMode()

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
    if (this.aiModeTimer) {
      clearTimeout(this.aiModeTimer)
    }
},

  methods: {
    async detectAIMode() {
      try {
        const res = await axios.get('/api/monitor/ai-query/routing-status/')
        if (res.data.success) {
          const status = res.data.routing_status.janus_pro_status
          if (status === 'LOADED') {
            this.aiMode = 'smart'
          } else if (status === 'LOADING') {
            this.aiMode = 'loading'
            this.aiModeTimer = setTimeout(() => this.detectAIMode(), 10000)
          } else {
            this.aiMode = 'basic'
          }
        } else {
          this.aiMode = 'basic'
        }
      } catch (e) {
        this.aiMode = 'basic'
      }
    },
    // 检测用户类型
    detectUserType() {
      try {
        // 首先检查是否有visitor access token
        const visitorToken = sessionStorage.getItem('visitor_access_token')
        const visitorTokenInfo = sessionStorage.getItem('visitor_token_info')

        if (visitorToken && visitorTokenInfo) {
          // Visitor模式
          this.isVisitorMode = true
          this.visitorAccessToken = visitorToken
          this.visitorInfo = JSON.parse(visitorTokenInfo)
          this.currentEid = this.visitorInfo.eid

          console.log('检测到Visitor模式，access_token:', visitorToken)
          return
        }

        // 检查普通用户登录信息
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
        this.userType = userInfo.userType || ''

        if (userInfo.userType === 'manager') {
          this.currentEid = userInfo.eid || ''
        } else if (userInfo.userType === 'admin') {
          this.currentEid = 'SYSTEM-ADMIN'
        }

        console.log('用户类型:', this.userType, 'EID:', this.currentEid)

      } catch (error) {
        console.error('检测用户类型失败:', error)
      }
    },

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

    // 加载数据
    async loadData() {
      if (this.isLoading) return

      this.isLoading = true

      try {
        if (this.isVisitorMode) {
          // Visitor模式：使用专门的visitor API
          await this.loadVisitorData()
        } else {
          // 普通用户模式：使用原有API
          await this.loadManagerData()
        }

        this.showMessage('数据加载成功', 'success')

      } catch (error) {
        console.error('加载数据失败:', error)
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
          this.showMessage('网络连接失败，请检查后端服务', 'error')
        } else {
          this.showMessage('加载数据失败: ' + (error.response?.data?.message || error.message), 'error')
        }
      } finally {
        this.isLoading = false
        this.lastUpdateTime = new Date().toLocaleTimeString()
      }
    },

    // Visitor模式加载数据
    async loadVisitorData() {
      console.log('使用Visitor API加载授权数据...')

      const response = await visitorAPI.getAuthorizedData(
        this.visitorAccessToken,
        this.currentFilter.timeRange
      )

      if (response.data && response.data.success) {
        this.updateDashboard(response.data.data)
        console.log('Visitor数据加载成功:', response.data)
      } else {
        throw new Error(response.data.message || '加载授权数据失败')
      }
    },

    // Manager模式加载数据
    async loadManagerData() {
      console.log('使用Manager API加载数据...')

      const params = {
        eid: this.currentEid
      }

      if (this.currentFilter.timeRange === 'all') {
        params.range = 'all'
      } else {
        params.range = this.currentFilter.timeRange
      }

      const response = await violationsAPI.getViolationsByEid(params)

      if (response.data && response.data.success) {
        this.updateDashboard(response.data.data)
      } else {
        throw new Error(response.data.message || '加载数据失败')
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
      // AIQuerySection 已经自己调用了 aiAPI.query 并展示了结果
      // FeedbackReport 只需处理 manager 模式的额外通知逻辑
      // Visitor 模式直接跳过，避免重复调用 visitorAPI.aiQuery 导致 500 报错弹窗
      if (this.isVisitorMode) {
        return
      }

      try {
        const response = await aiAPI.query(queryData)

        if (response.data.success) {
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
    },

    // 退出Visitor模式
    async exitVisitorMode() {
      try {
        await ElMessageBox.confirm('确定要退出访问模式吗?', '提示', { type: 'warning' })
      } catch { return }
      sessionStorage.removeItem('visitor_access_token')
      sessionStorage.removeItem('visitor_token_info')

      this.isVisitorMode = false
      this.visitorAccessToken = ''
      this.visitorInfo = null

      this.showMessage('已退出访问模式', 'info')

      // 可选: 刷新页面或跳转
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    },
    
    // 获取授权类型文本
    getAccessTypeText(type) {
      return type === 'warehouse' ? '仓库访问' : '时间段访问'
    }
  }
}
</script>

<style scoped>
.feedback-report {
  padding: 15px;
  background: linear-gradient(180deg, #f0f8ff 0%, #f7fbff 100%);
  min-height: calc(100vh - 60px);
  overflow-y: auto;
}

/* Visitor模式横幅样式 */
.visitor-mode-banner {
  background: #5ba0c3;
  color: white;
  padding: 16px 24px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.banner-content i {
  font-size: 32px;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.banner-text strong {
  font-size: 16px;
}

.banner-text span {
  font-size: 14px;
  opacity: 0.9;
}

.exit-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  transition: all 0.3s;
}

.exit-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.feedback-report :deep(.chat-interface) {
  background: white;
  border: 1px solid #E3F2FD;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(66, 165, 245, 0.05);
}
</style>