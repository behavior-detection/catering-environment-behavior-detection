<template>
  <div class="permission-container">
    <h2>查看权限申请</h2>

    <!-- 统计卡片 -->
    <div class="stats-cards">
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
        <input type="radio" v-model="statusFilter" value="all" @change="loadRequests">
        全部
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="pending" @change="loadRequests">
        待审批
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="approved" @change="loadRequests">
        已批准
      </label>
      <label>
        <input type="radio" v-model="statusFilter" value="rejected" @change="loadRequests">
        已拒绝
      </label>
      <button class="btn-refresh" @click="loadRequests" :disabled="loading">
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
      <h3>{{ getFilterTitle() }} ({{ filteredRequests.length }})</h3>

      <div v-if="filteredRequests.length === 0" class="empty-state">
        <i class="fas fa-inbox"></i>
        <p>暂无{{ getFilterTitle() }}</p>
      </div>

      <div v-else class="table-wrapper">
        <table class="request-table">
          <thead>
            <tr>
              <th>申请人</th>
              <th>EID</th>
              <th>申请类型</th>
              <th>具体内容</th>
              <th>申请时长</th>
              <th>申请时间</th>
              <th>申请理由</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="request in filteredRequests" :key="request.id">
              <td><strong>{{ request.visitor_name }}</strong></td>
              <td><code>{{ request.eid }}</code></td>
              <td>
                <span class="type-badge" :class="request.request_type">
                  {{ getRequestTypeText(request.request_type) }}
                </span>
              </td>
              <td>{{ request.specific_value || '-' }}</td>
              <td>{{ request.duration_days }} 天</td>
              <td>{{ formatDateTime(request.created_at) }}</td>
              <td class="reason-cell" :title="request.reason">
                {{ request.reason }}
              </td>
              <td>
                <span class="status-badge" :class="request.status">
                  {{ getStatusText(request.status) }}
                </span>
              </td>
              <td>
                <div v-if="request.status === 'pending'" class="action-buttons">
                  <button
                    class="btn-approve"
                    @click="handleApprove(request)"
                    :disabled="processing"
                  >
                    <i class="fas fa-check"></i> 批准
                  </button>
                  <button
                    class="btn-reject"
                    @click="handleReject(request)"
                    :disabled="processing"
                  >
                    <i class="fas fa-times"></i> 拒绝
                  </button>
                </div>
                <div v-else-if="request.status === 'approved'" class="result-info">
                  <div><i class="fas fa-user-check"></i> {{ request.approved_by }}</div>
                  <div v-if="request.access_token" class="token-info">
                    <i class="fas fa-key"></i> {{ request.access_token.substring(0, 12) }}...
                  </div>
                  <div class="time-info">{{ formatDateTime(request.approved_at) }}</div>
                  <button class="btn-webrtc-manager" @click="goToWebRTCManager">
                    <i class="fas fa-share-alt"></i> 上线分享文件
                  </button>
                </div>
                <div v-else-if="request.status === 'rejected'" class="result-info">
                  <div><i class="fas fa-user-times"></i> {{ request.rejected_by }}</div>
                  <div class="time-info">{{ formatDateTime(request.rejected_at) }}</div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'ViewPermissionRequests',
  data() {
    return {
      requests: [],
      stats: {
        pending: 0,
        approved: 0,
        rejected: 0,
        total: 0
      },
      statusFilter: 'pending',
      loading: false,
      processing: false,
      managerEid: '',
      managerName: '',
      autoRefreshInterval: null
    }
  },
  computed: {
    filteredRequests() {
      if (this.statusFilter === 'all') {
        return this.requests
      }
      return this.requests.filter(r => r.status === this.statusFilter)
    }
  },
  mounted() {
    this.initManagerInfo()
    this.loadRequests()
    // 每30秒自动刷新
    this.autoRefreshInterval = setInterval(() => {
      this.loadRequests(true)
    }, 30000)
  },
  beforeUnmount() {
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval)
    }
  },
  methods: {
    initManagerInfo() {
      // 从 sessionStorage 获取用户信息（与 Page2.vue 保持一致）
      const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
      this.managerEid = userInfo.eid || ''
      this.managerName = userInfo.username || userInfo.name || ''

      console.log('获取到的用户信息:', {
        eid: this.managerEid,
        name: this.managerName,
        userType: userInfo.userType
      })

      if (!this.managerEid) {
        console.error('未找到管理员EID信息')
        this.$message?.error('未找到管理员信息，请重新登录')
      }
    },

    async loadRequests(silent = false) {
      if (!this.managerEid) {
        console.error('缺少管理员EID')
        return
      }

      if (!silent) {
        this.loading = true
      }

      try {
        const response = await axios.get('/api/monitor/permission/requests/', {
          params: {
            eid: this.managerEid,
            status: this.statusFilter,
            manager_name: this.managerName
          }
        })

        if (response.data.success) {
          this.requests = response.data.requests || []
          this.stats = response.data.stats || {
            pending: 0,
            approved: 0,
            rejected: 0,
            total: 0
          }
          console.log('成功加载权限申请:', this.requests.length, '条')
        } else {
          console.error('获取申请列表失败:', response.data.message)
          if (!silent) {
            this.$message?.error(response.data.message || '获取申请列表失败')
          }
        }
      } catch (error) {
        console.error('加载权限申请失败:', error)
        if (!silent) {
          this.$message?.error('加载失败: ' + (error.response?.data?.message || error.message))
        }
      } finally {
        this.loading = false
      }
    },

    async handleApprove(request) {
      // 确认对话框
      if (!confirm(`确定要批准 ${request.visitor_name} 的权限申请吗？`)) {
        return
      }

      this.processing = true
      try {
        const response = await axios.post('/api/monitor/permission/approve/', {
          request_id: request.id,
          decision: 'approve',
          manager_name: this.managerName
        })

        if (response.data.success) {
          this.$message?.success('申请已批准')
          if (response.data.access_token) {
            console.log('访问令牌:', response.data.access_token)
            // 可以显示令牌给用户
            alert(`批准成功！\n访问令牌: ${response.data.access_token}`)
          }
          await this.loadRequests()
        } else {
          this.$message?.error(response.data.message || '批准失败')
        }
      } catch (error) {
        console.error('批准申请失败:', error)
        this.$message?.error('批准失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.processing = false
      }
    },

    async handleReject(request) {
      // 确认对话框
      if (!confirm(`确定要拒绝 ${request.visitor_name} 的权限申请吗？`)) {
        return
      }

      this.processing = true
      try {
        const response = await axios.post('/api/monitor/permission/approve/', {
          request_id: request.id,
          decision: 'reject',
          manager_name: this.managerName
        })

        if (response.data.success) {
          this.$message?.success('申请已拒绝')
          await this.loadRequests()
        } else {
          this.$message?.error(response.data.message || '拒绝失败')
        }
      } catch (error) {
        console.error('拒绝申请失败:', error)
        this.$message?.error('拒绝失败: ' + (error.response?.data?.message || error.message))
      } finally {
        this.processing = false
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
    },

    goToWebRTCManager() {
      this.$store.dispatch('navigation/setCurrentModule', 'WebRTCManager')
    }
  }
}
</script>

<style scoped>
.permission-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.permission-container h2 {
  color: #333;
  margin-bottom: 24px;
  font-size: 28px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
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
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
}

.stat-icon.pending {
  background-color: #fff7e6;
  color: #faad14;
}

.stat-icon.approved {
  background-color: #f0f9ff;
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
  font-size: 32px;
  font-weight: bold;
  color: #333;
  margin: 0;
}

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

.request-list {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.request-list h3 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 20px;
}

.empty-state {
  text-align: center;
  padding: 80px;
  color: #999;
}

.empty-state i {
  font-size: 64px;
  margin-bottom: 16px;
  color: #ccc;
}

.empty-state p {
  font-size: 16px;
  margin: 0;
}

.table-wrapper {
  overflow-x: auto;
}

.request-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1200px;
}

.request-table th {
  text-align: left;
  padding: 14px 12px;
  background-color: #fafafa;
  border-bottom: 2px solid #e8e8e8;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  font-size: 14px;
}

.request-table td {
  padding: 14px 12px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  color: #333;
}

.request-table tbody tr:hover {
  background-color: #fafafa;
}

code {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #d46b08;
}

.type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  display: inline-block;
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
  display: inline-block;
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

.reason-cell {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
}

.btn-approve,
.btn-reject {
  padding: 6px 14px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-approve {
  background-color: #52c41a;
  color: white;
}

.btn-approve:hover:not(:disabled) {
  background-color: #45a716;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
}

.btn-reject {
  background-color: #ff4d4f;
  color: white;
}

.btn-reject:hover:not(:disabled) {
  background-color: #e04142;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(255, 77, 79, 0.3);
}

.btn-approve:disabled,
.btn-reject:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.result-info div {
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
}

.result-info i {
  color: #999;
  font-size: 11px;
}

.token-info {
  color: #1890ff !important;
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.time-info {
  color: #999 !important;
  font-size: 11px !important;
}

.btn-webrtc-manager {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  padding: 4px 10px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.btn-webrtc-manager:hover {
  background-color: #40a9ff;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.3);
}
</style>