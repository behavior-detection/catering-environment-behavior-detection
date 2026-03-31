<template>
  <div class="token-manager-container">
    <div class="header-section">
      <div class="header-left">
        <h2>访问令牌管理</h2>
        <p class="subtitle">查看和管理所有已生成的访问令牌</p>
      </div>
      <button @click="loadTokens" :disabled="loading" class="refresh-btn">
        <i :class="['fas fa-sync-alt', { 'fa-spin': loading }]"></i>
        刷新
      </button>
    </div>

    <!-- 搜索和过滤 -->
    <div class="filter-panel">
      <div class="search-box">
        <i class="fas fa-search search-icon"></i>
        <input
          v-model="searchTerm"
          type="text"
          placeholder="搜索 EID、访问范围或令牌..."
          class="search-input"
        />
      </div>

      <select v-model="filterType" class="filter-select">
        <option value="all">所有类型</option>
        <option value="time">时间范围</option>
        <option value="warehouse">仓库访问</option>
      </select>

      <select v-model="filterStatus" class="filter-select">
        <option value="all">所有状态</option>
        <option value="active">有效</option>
        <option value="expired">已过期</option>
      </select>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-content">
          <div class="stat-text">
            <div class="stat-label">总令牌数</div>
            <div class="stat-value">{{ tokens.length }}</div>
          </div>
        </div>
      </div>

      <div class="stat-card stat-success">
        <div class="stat-content">
          <div class="stat-text">
            <div class="stat-label">有效令牌</div>
            <div class="stat-value">{{ activeTokensCount }}</div>
          </div>
        </div>
      </div>

      <div class="stat-card stat-info">
        <div class="stat-content">
          <div class="stat-text">
            <div class="stat-label">时间类型</div>
            <div class="stat-value">{{ timeTypeCount }}</div>
          </div>
        </div>
      </div>

      <div class="stat-card stat-purple">
        <div class="stat-content">
          <div class="stat-text">
            <div class="stat-label">仓库类型</div>
            <div class="stat-value">{{ warehouseTypeCount }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 令牌列表 -->
    <div class="tokens-table-container">
      <div v-if="loading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>加载中...</p>
      </div>

      <div v-else-if="filteredTokens.length === 0" class="empty-state">
        <i class="fas fa-key"></i>
        <p>{{ tokens.length === 0 ? '暂无令牌记录' : '没有符合条件的令牌' }}</p>
      </div>

      <div v-else class="table-wrapper">
        <table class="tokens-table">
          <thead>
            <tr>
              <th>EID</th>
              <th>类型</th>
              <th>访问范围</th>
              <th>访问令牌</th>
              <th>有效期</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="token in filteredTokens" :key="token.access_token">
              <td>
                <span class="token-eid">{{ token.eid }}</span>
              </td>
              <td>
                <span :class="['badge', token.access_type === 'time' ? 'badge-blue' : 'badge-purple']">
                  {{ token.access_type === 'time' ? '时间范围' : '仓库访问' }}
                </span>
              </td>
              <td>{{ token.access_value }}</td>
              <td>
                <div class="token-cell">
                  <code class="token-preview">
                    {{ showTokenIds[token.access_token]
                      ? token.access_token
                      : token.access_token.substring(0, 16) + '...'
                    }}
                  </code>
                  <div class="token-actions">
                    <button
                      @click="toggleTokenVisibility(token.access_token)"
                      class="icon-btn"
                      :title="showTokenIds[token.access_token] ? '隐藏' : '显示'"
                    >
                      <i :class="showTokenIds[token.access_token] ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                    </button>
                    <button
                      @click="copyToClipboard(token.access_token)"
                      class="icon-btn"
                      title="复制"
                    >
                      <i class="fas fa-copy"></i>
                    </button>
                  </div>
                </div>
              </td>
              <td>
                <div class="duration-cell">
                  <div>{{ token.duration_days }}天</div>
                  <div class="expiry-date">{{ formatDate(token.expires_at) }}到期</div>
                </div>
              </td>
              <td>
                <span :class="['badge', isExpired(token.expires_at) ? 'badge-danger' : 'badge-success']">
                  {{ isExpired(token.expires_at) ? '已过期' : '有效' }}
                </span>
              </td>
              <td>{{ formatDate(token.created_at) }}</td>
              <td>
                <button
                  @click="deleteToken(token.access_token)"
                  class="delete-btn"
                  title="删除令牌"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 消息提示 -->
    <transition name="message">
      <div v-if="message.show" :class="['message-toast', `message-${message.type}`]">
        <span>{{ message.text }}</span>
      </div>
    </transition>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_APP_API_BASE_URL || '/api/monitor'

export default {
  name: 'TokenManager',
  data() {
    return {
      tokens: [],
      searchTerm: '',
      filterType: 'all',
      filterStatus: 'all',
      showTokenIds: {},
      loading: false,
      message: {
        show: false,
        type: '',
        text: ''
      }
    }
  },
  computed: {
    filteredTokens() {
      let filtered = [...this.tokens]

      // 搜索过滤
      if (this.searchTerm) {
        const term = this.searchTerm.toLowerCase()
        filtered = filtered.filter(token =>
          token.eid.toLowerCase().includes(term) ||
          token.access_value.toLowerCase().includes(term) ||
          token.access_token.toLowerCase().includes(term)
        )
      }

      // 类型过滤
      if (this.filterType !== 'all') {
        filtered = filtered.filter(token => token.access_type === this.filterType)
      }

      // 状态过滤
      if (this.filterStatus !== 'all') {
        filtered = filtered.filter(token => {
          const expired = this.isExpired(token.expires_at)
          return this.filterStatus === 'active' ? !expired : expired
        })
      }

      return filtered
    },

    activeTokensCount() {
      return this.tokens.filter(t => !this.isExpired(t.expires_at)).length
    },

    timeTypeCount() {
      return this.tokens.filter(t => t.access_type === 'time').length
    },

    warehouseTypeCount() {
      return this.tokens.filter(t => t.access_type === 'warehouse').length
    }
  },

  mounted() {
    this.loadTokens()
  },

  methods: {
    async loadTokens() {
      this.loading = true
      try {
        const response = await axios.get(`${API_BASE_URL}/admin/list-tokens/`)

        if (response.data.success) {
          this.tokens = response.data.tokens || []
        } else {
          this.showMessage('加载令牌列表失败', 'error')
        }
      } catch (error) {
        this.showMessage('加载失败: ' + error.message, 'error')
      } finally {
        this.loading = false
      }
    },

    async deleteToken(tokenId) {
      if (!confirm('确定要删除这个令牌吗?删除后将无法恢复!')) {
        return
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/admin/delete-token/`, {
          access_token: tokenId
        })

        if (response.data.success) {
          this.showMessage('令牌已删除', 'success')
          await this.loadTokens()
        } else {
          throw new Error(response.data.message)
        }
      } catch (error) {
        this.showMessage('删除失败: ' + (error.response?.data?.message || error.message), 'error')
      }
    },

    toggleTokenVisibility(tokenId) {
      this.$set(this.showTokenIds, tokenId, !this.showTokenIds[tokenId])
    },

    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        this.showMessage('已复制到剪贴板', 'success')
      }).catch(() => {
        this.showMessage('复制失败', 'error')
      })
    },

    isExpired(expiresAt) {
      return new Date(expiresAt) < new Date()
    },

    formatDate(dateString) {
      return new Date(dateString).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    showMessage(text, type) {
      this.message = { show: true, type, text }
      setTimeout(() => {
        this.message.show = false
      }, 3000)
    }
  }
}
</script>

<style scoped>
.token-manager-container {
  max-width: 1400px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left h2 {
  color: #333;
  font-size: 24px;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.refresh-btn {
  padding: 10px 20px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
}

.refresh-btn:hover:not(:disabled) {
  background-color: #1677ff;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 过滤面板 */
.filter-panel {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 16px;
}

.search-box {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.filter-select {
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-select:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: #666;
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  color: #333;
  font-size: 28px;
  font-weight: bold;
}

.stat-icon {
  font-size: 32px;
  color: #1890ff;
}

.stat-success .stat-icon {
  color: #52c41a;
}

.stat-info .stat-icon {
  color: #1890ff;
}

.stat-purple .stat-icon {
  color: #722ed1;
}

/* 表格容器 */
.tokens-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.loading-state,
.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #666;
}

.loading-state i,
.empty-state i {
  font-size: 48px;
  color: #ccc;
  margin-bottom: 16px;
  display: block;
}

.table-wrapper {
  overflow-x: auto;
}

.tokens-table {
  width: 100%;
  border-collapse: collapse;
}

.tokens-table thead {
  background-color: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.tokens-table th {
  padding: 16px 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
}

.tokens-table tbody tr {
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.3s;
}

.tokens-table tbody tr:hover {
  background-color: #fafafa;
}

.tokens-table td {
  padding: 16px 12px;
  font-size: 14px;
  color: #333;
}

.token-eid {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

/* 徽章 */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.badge-blue {
  background-color: #e6f7ff;
  color: #1890ff;
}

.badge-purple {
  background-color: #f9f0ff;
  color: #722ed1;
}

.badge-success {
  background-color: #f6ffed;
  color: #52c41a;
}

.badge-danger {
  background-color: #fff2f0;
  color: #ff4d4f;
}

/* 令牌单元格 */
.token-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-preview {
  font-size: 12px;
  font-family: 'Courier New', monospace;
  color: #666;
}

.token-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.icon-btn:hover {
  color: #1890ff;
  background-color: #e6f7ff;
}

.duration-cell {
  font-size: 14px;
}

.expiry-date {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.delete-btn {
  background: none;
  border: none;
  color: #ff4d4f;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.delete-btn:hover {
  background-color: #fff2f0;
}

/* 消息提示 */
.message-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  padding: 16px 20px;
  border-radius: 8px;
  z-index: 1001;
  min-width: 320px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.message-success {
  background: #f0f9ff;
  color: #0891b2;
  border: 1px solid #67e8f9;
}

.message-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.message-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .filter-panel {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .refresh-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>