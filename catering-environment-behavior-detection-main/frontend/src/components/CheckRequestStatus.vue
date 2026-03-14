<template>
  <div class="request-status-container">
    <h2>我的权限申请</h2>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon total">
          <i class="fas fa-list"></i>
        </div>
        <div class="stat-info">
          <h3>全部申请</h3>
          <p class="stat-number">{{ stats.total }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon pending">
          <i class="fas fa-clock"></i>
        </div>
        <div class="stat-info">
          <h3>待审批</h3>
          <p class="stat-number">{{ stats.pending }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon approved">
          <i class="fas fa-check-circle"></i>
        </div>
        <div class="stat-info">
          <h3>已批准</h3>
          <p class="stat-number">{{ stats.approved }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon rejected">
          <i class="fas fa-times-circle"></i>
        </div>
        <div class="stat-info">
          <h3>已拒绝</h3>
          <p class="stat-number">{{ stats.rejected }}</p>
        </div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <label>
        <input type="radio" v-model="statusFilter" value="all" @change="loadMyRequests">
        全部
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="pending" @change="loadMyRequests">
        待审批
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="approved" @change="loadMyRequests">
        已批准
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="rejected" @change="loadMyRequests">
        已拒绝
      </label>
      <button class="btn-refresh" @click="loadMyRequests" :disabled="loading">
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> 刷新
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && requests.length === 0" class="loading-container">
      <i class="fas fa-spinner fa-spin"></i>
      <p>加载中...</p>
    </div>

    <!-- 申请列表 -->
    <div v-else class="request-list">
      <h3>{{ getFilterTitle() }} ({{ requests.length }})</h3>

      <div v-if="requests.length === 0" class="empty-state">
        <i class="fas fa-inbox"></i>
        <p>暂无{{ getFilterTitle() }}</p>
        <p class="hint">您可以在"提交权限申请"页面创建新的申请</p>
      </div>

      <div v-else class="cards-container">
        <div
          v-for="request in requests"
          :key="request.id"
          class="request-card"
          :class="request.status"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <div class="card-title">
              <span class="type-badge" :class="request.request_type">
                {{ getRequestTypeText(request.request_type) }}
              </span>
              <span class="status-badge" :class="request.status">
                {{ getStatusText(request.status) }}
              </span>
            </div>
            <div class="card-meta">
              <div class="card-eid">
                <i class="fas fa-building"></i>
                <span>目标企业: {{ request.eid }}</span>
              </div>
              <div class="card-date">
                申请时间: {{ formatDateTime(request.created_at) }}
              </div>
            </div>
          </div>

          <!-- 卡片内容 -->
          <div class="card-body">
            <div class="info-row">
              <label>申请内容:</label>
              <span>{{ request.specific_value || '-' }}</span>
            </div>
            <div class="info-row">
              <label>申请时长:</label>
              <span>{{ request.duration_days }} 天</span>
            </div>
            <div class="info-row">
              <label>申请理由:</label>
              <span class="reason-text">{{ request.reason }}</span>
            </div>
          </div>

          <!-- 审批结果 -->
          <div v-if="request.status === 'approved'" class="approval-result approved-result">
            <div class="result-header">
              <i class="fas fa-check-circle"></i>
              <span>申请已批准</span>
            </div>
            <div class="result-details">
              <div class="detail-item">
                <label>审批人:</label>
                <span>{{ request.approved_by }}</span>
              </div>
              <div class="detail-item">
                <label>审批时间:</label>
                <span>{{ formatDateTime(request.approved_at) }}</span>
              </div>
              <div class="detail-item token-item">
                <label>访问令牌:</label>
                <div class="token-display">
                  <code class="access-token">{{ request.access_token }}</code>
                  <button
                    class="btn-copy"
                    @click="copyToken(request.access_token)"
                    title="复制令牌"
                  >
                    <i class="fas fa-copy"></i>
                  </button>
                </div>
              </div>
              <div class="token-hint">
                <i class="fas fa-info-circle"></i>
                请妥善保管您的访问令牌，它将用于访问相关数据
              </div>
            </div>
          </div>

          <div v-else-if="request.status === 'rejected'" class="approval-result rejected-result">
            <div class="result-header">
              <i class="fas fa-times-circle"></i>
              <span>申请已拒绝</span>
            </div>
            <div class="result-details">
              <div class="detail-item">
                <label>拒绝人:</label>
                <span>{{ request.rejected_by }}</span>
              </div>
              <div class="detail-item">
                <label>拒绝时间:</label>
                <span>{{ formatDateTime(request.rejected_at) }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="request.status === 'pending'" class="approval-result pending-result">
            <div class="result-header">
              <i class="fas fa-hourglass-half"></i>
              <span>等待审批中...</span>
            </div>
            <p class="pending-hint">您的申请正在等待管理员审批，请耐心等待</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'CheckRequestStatus',
  data() {
    return {
      requests: [],
      stats: {
        total: 0,
        pending: 0,
        approved: 0,
        rejected: 0
      },
      statusFilter: 'all',
      loading: false,
      autoRefreshInterval: null,
      // ★ visitor只需要name，不需要eid（因为visitor表没有eid字段）
      visitorName: ''
    }
  },
  mounted() {
    this.initVisitorInfo()
    this.loadMyRequests()

    // 每30秒自动刷新
    this.autoRefreshInterval = setInterval(() => {
      this.loadMyRequests(true)
    }, 30000)
  },
  beforeUnmount() {
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval)
    }
  },
  methods: {
    initVisitorInfo() {
      // 从 sessionStorage 获取用户信息
      const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')

      // ★ visitor只需要获取name（visitor表中没有EID字段）
      this.visitorName = userInfo.username || userInfo.name || ''

      console.log('获取到的访客信息:', {
        name: this.visitorName,
        userType: userInfo.userType
      })

      if (!this.visitorName) {
        console.error('未找到访客用户名')
        this.$message?.error('未找到访客信息，请重新登录')
      }
    },

    async loadMyRequests(silent = false) {
      if (!this.visitorName) {
        console.error('缺少访客用户名')
        return
      }

      if (!silent) {
        this.loading = true
      }

      try {
        // ★ 只传递visitor_name，不传递eid
        const response = await axios.get('/api/monitor/permission/my-requests/', {
          params: {
            visitor_name: this.visitorName,
            status: this.statusFilter
          }
        })

        if (response.data.success) {
          this.requests = response.data.requests || []
          this.stats = response.data.stats || {
            total: 0,
            pending: 0,
            approved: 0,
            rejected: 0
          }
          console.log('成功加载申请记录:', this.requests.length, '条')
        } else {
          console.error('获取申请列表失败:', response.data.message)
          if (!silent) {
            this.$message?.error(response.data.message || '获取申请列表失败')
          }
        }
      } catch (error) {
        console.error('加载申请记录失败:', error)
        if (!silent) {
          this.$message?.error('加载失败: ' + (error.response?.data?.message || error.message))
        }
      } finally {
        this.loading = false
      }
    },

    async copyToken(token) {
      try {
        await navigator.clipboard.writeText(token)
        this.$message?.success('访问令牌已复制到剪贴板')
      } catch (error) {
        console.error('复制失败:', error)
        // 降级方案
        const textArea = document.createElement('textarea')
        textArea.value = token
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.select()
        try {
          document.execCommand('copy')
          this.$message?.success('访问令牌已复制到剪贴板')
        } catch (err) {
          this.$message?.error('复制失败，请手动复制')
        }
        document.body.removeChild(textArea)
      }
    },

    getFilterTitle() {
      const titles = {
        all: '所有申请',
        pending: '待审批申请',
        approved: '已批准申请',
        rejected: '已拒绝申请'
      }
      return titles[this.statusFilter] || '申请列表'
    },

    getRequestTypeText(type) {
      const types = {
        time: '时间段访问',
        warehouse: '仓库访问'
      }
      return types[type] || type
    },

    getStatusText(status) {
      const statuses = {
        pending: '待审批',
        approved: '已批准',
        rejected: '已拒绝'
      }
      return statuses[status] || status
    },

    formatDateTime(dateStr) {
      if (!dateStr) return '-'
      try {
        const date = new Date(dateStr)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (e) {
        return dateStr
      }
    }
  }
}
</script>

<style scoped>
.request-status-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.request-status-container h2 {
  color: #333;
  margin-bottom: 24px;
  font-size: 28px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-icon.total {
  background-color: #e6f7ff;
  color: #1890ff;
}

.stat-icon.pending {
  background-color: #fff7e6;
  color: #faad14;
}

.stat-icon.approved {
  background-color: #f6ffed;
  color: #52c41a;
}

.stat-icon.rejected {
  background-color: #fff1f0;
  color: #ff4d4f;
}

.stat-info h3 {
  font-size: 14px;
  color: #666;
  margin: 0 0 8px 0;
  font-weight: 500;
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin: 0;
}

/* 筛选栏 */
.filter-bar {
  background: white;
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-bar label {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  color: #333;
}

.filter-bar input[type="radio"] {
  cursor: pointer;
}

.btn-refresh {
  margin-left: auto;
  padding: 8px 20px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-refresh:hover:not(:disabled) {
  background-color: #40a9ff;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 加载状态 */
.loading-container {
  text-align: center;
  padding: 80px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.loading-container i {
  font-size: 48px;
  color: #1890ff;
  margin-bottom: 16px;
}

.loading-container p {
  font-size: 18px;
  color: #666;
  margin: 0;
}

/* 申请列表 */
.request-list {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.request-list h3 {
  margin: 0 0 24px 0;
  color: #333;
  font-size: 20px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 40px;
  color: #999;
}

.empty-state i {
  font-size: 64px;
  margin-bottom: 16px;
  color: #ccc;
}

.empty-state p {
  font-size: 16px;
  margin: 8px 0;
}

.empty-state .hint {
  font-size: 14px;
  color: #1890ff;
  margin-top: 16px;
}

/* 卡片容器 */
.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 20px;
}

/* 申请卡片 */
.request-card {
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  background: white;
}

.request-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.request-card.pending {
  border-left: 4px solid #faad14;
}

.request-card.approved {
  border-left: 4px solid #52c41a;
}

.request-card.rejected {
  border-left: 4px solid #ff4d4f;
}

/* 卡片头部 */
.card-header {
  background: #fafafa;
  padding: 16px 20px;
  border-bottom: 1px solid #e8e8e8;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.card-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-eid {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #1890ff;
  font-weight: 500;
}

.card-eid i {
  font-size: 12px;
}

.card-date {
  font-size: 12px;
  color: #999;
}

.type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-badge.time {
  background-color: #e6f7ff;
  color: #1890ff;
}

.type-badge.warehouse {
  background-color: #f0f5ff;
  color: #722ed1;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.pending {
  background-color: #fff7e6;
  color: #faad14;
}

.status-badge.approved {
  background-color: #f6ffed;
  color: #52c41a;
}

.status-badge.rejected {
  background-color: #fff1f0;
  color: #ff4d4f;
}

/* 卡片主体 */
.card-body {
  padding: 20px;
}

.info-row {
  display: flex;
  margin-bottom: 12px;
  font-size: 14px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row label {
  color: #666;
  font-weight: 500;
  min-width: 80px;
  flex-shrink: 0;
}

.info-row span {
  color: #333;
  flex: 1;
}

.reason-text {
  line-height: 1.6;
}

/* 审批结果 */
.approval-result {
  padding: 20px;
  margin: 0;
  border-top: 1px solid #e8e8e8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.approved-result .result-header {
  color: #52c41a;
}

.rejected-result .result-header {
  color: #ff4d4f;
}

.pending-result .result-header {
  color: #faad14;
}

.result-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  display: flex;
  align-items: flex-start;
  font-size: 14px;
}

.detail-item label {
  color: #666;
  min-width: 80px;
  flex-shrink: 0;
}

.detail-item span {
  color: #333;
}

.token-item {
  flex-direction: column;
  align-items: stretch;
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
}

.token-item label {
  margin-bottom: 8px;
  font-weight: 500;
}

.token-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.access-token {
  flex: 1;
  background: white;
  padding: 10px 12px;
  border-radius: 4px;
  border: 1px solid #d9d9d9;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #1890ff;
  word-break: break-all;
  line-height: 1.4;
}

.btn-copy {
  padding: 8px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
  flex-shrink: 0;
}

.btn-copy:hover {
  background-color: #40a9ff;
}

.token-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #faad14;
  background: #fffbe6;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 4px;
}

.pending-hint {
  font-size: 14px;
  color: #666;
  margin: 0;
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .cards-container {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  }
}

@media (max-width: 768px) {
  .request-status-container {
    padding: 15px;
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .cards-container {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .btn-refresh {
    margin-left: 0;
    justify-content: center;
  }
}
</style>