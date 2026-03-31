<template>
  <div class="generate-token-container">
    <div class="header-section">
      <h2>生成访问令牌</h2>
      <p class="subtitle">管理员权限 - 直接生成访问令牌,无需审批流程</p>
    </div>

    <div class="token-form">
      <!-- EID输入 -->
      <div class="form-group">
        <label class="form-label">
          企业EID <span class="required">*</span>
        </label>
        <input
          v-model="formData.eid"
          type="text"
          class="form-control"
          placeholder="请输入企业EID"
          @blur="onEidChange"
        />
      </div>

      <!-- 访问类型 -->
      <div class="form-group">
        <label class="form-label">
          访问类型 <span class="required">*</span>
        </label>
        <select
          v-model="formData.accessType"
          class="form-control"
          @change="onAccessTypeChange"
        >
          <option value="">请选择访问类型</option>
          <option value="time">时间范围</option>
          <option value="warehouse">仓库访问</option>
        </select>
      </div>

      <!-- 具体访问值 - 时间类型 -->
      <div v-if="formData.accessType === 'time'" class="form-group">
        <label class="form-label">
          选择日期 <span class="required">*</span>
        </label>
        <div v-if="loadingDates" class="loading-hint">
          <i class="fas fa-spinner fa-spin"></i> 正在加载可用日期...
        </div>
        <select
          v-else
          v-model="formData.accessValue"
          class="form-control"
          :disabled="!formData.eid || availableDates.length === 0"
        >
          <option value="">
            {{ availableDates.length === 0 ? '该EID下没有可用日期' : '请选择日期' }}
          </option>
          <option v-for="date in availableDates" :key="date.date" :value="date.date">
            {{ date.display }}
          </option>
        </select>
      </div>

      <!-- 具体访问值 - 仓库类型 -->
      <div v-if="formData.accessType === 'warehouse'" class="form-group">
        <label class="form-label">
          选择仓库 <span class="required">*</span>
        </label>
        <div v-if="loadingWarehouses" class="loading-hint">
          <i class="fas fa-spinner fa-spin"></i> 正在加载仓库列表...
        </div>
        <select
          v-else
          v-model="formData.accessValue"
          class="form-control"
          :disabled="!formData.eid || warehouses.length === 0"
        >
          <option value="">
            {{ warehouses.length === 0 ? '该EID下没有仓库' : '请选择仓库' }}
          </option>
          <option v-for="warehouse in warehouses" :key="warehouse.id" :value="warehouse.id">
            {{ warehouse.name }} ({{ warehouse.file_count || 0 }}个文件)
          </option>
        </select>
      </div>

      <!-- 有效时长 -->
      <div class="form-group">
        <label class="form-label">
          有效时长 <span class="required">*</span>
        </label>
        <select v-model="formData.duration" class="form-control">
          <option value="">请选择有效时长</option>
          <option value="1">1天</option>
          <option value="7">7天</option>
          <option value="30">30天</option>
        </select>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button type="button" class="btn-reset" @click="resetForm">
          重置
        </button>
        <button
          type="button"
          class="btn-generate"
          :disabled="!isFormValid || isGenerating"
          @click="generateToken"
        >
          <i v-if="!isGenerating" class="fas fa-key"></i>
          <i v-else class="fas fa-spinner fa-spin"></i>
          {{ isGenerating ? '生成中...' : '生成令牌' }}
        </button>
      </div>
    </div>

    <!-- 生成结果显示 -->
    <div v-if="generatedToken" class="result-panel">
      <div class="result-header">
        <i class="fas fa-check-circle"></i>
        <h3>令牌生成成功</h3>
      </div>

      <div class="result-body">
        <div class="token-display">
          <div class="token-label">
            <span>访问令牌</span>
            <button @click="copyToClipboard(generatedToken.access_token)" class="copy-btn">
              <i class="fas fa-copy"></i> 复制
            </button>
          </div>
          <code class="token-code">{{ generatedToken.access_token }}</code>
        </div>

        <div class="token-info-grid">
          <div class="info-item">
            <div class="info-label">访问类型</div>
            <div class="info-value">
              {{ generatedToken.access_type === 'time' ? '时间范围' : '仓库访问' }}
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">访问范围</div>
            <div class="info-value">{{ generatedToken.access_value }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">有效期</div>
            <div class="info-value">{{ generatedToken.duration_days }}天</div>
          </div>
          <div class="info-item">
            <div class="info-label">创建时间</div>
            <div class="info-value">{{ formatDate(generatedToken.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="tips-section">
      <h3><i class="fas fa-info-circle"></i> 使用说明</h3>
      <ul>
        <li>管理员可直接生成访问令牌,无需经过审批流程</li>
        <li>时间类型:授权访问特定日期的所有数据文件</li>
        <li>仓库类型:授权访问特定仓库中的所有数据文件</li>
        <li>生成的令牌可直接提供给访问者使用,有效期到期后自动失效</li>
      </ul>
    </div>

    <!-- 消息提示 -->
    <transition name="message">
      <div v-if="message.show" :class="['message-toast', `message-${message.type}`]">
        <i :class="getMessageIcon(message.type)"></i>
        <span>{{ message.text }}</span>
      </div>
    </transition>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_APP_API_BASE_URL || '/api/monitor'

export default {
  name: 'GenerateToken',
  data() {
    return {
      formData: {
        eid: '',
        accessType: '',
        accessValue: '',
        duration: ''
      },
      warehouses: [],
      availableDates: [],
      loadingWarehouses: false,
      loadingDates: false,
      isGenerating: false,
      generatedToken: null,
      message: {
        show: false,
        type: '',
        text: ''
      }
    }
  },
  computed: {
    isFormValid() {
      return this.formData.eid &&
             this.formData.accessType &&
             this.formData.accessValue &&
             this.formData.duration
    }
  },
  watch: {
    'formData.eid'() {
      if (this.formData.eid && this.formData.accessType) {
        this.loadAccessData()
      }
    },
    'formData.accessType'() {
      this.formData.accessValue = ''
      if (this.formData.eid && this.formData.accessType) {
        this.loadAccessData()
      }
    }
  },
  methods: {
    async onEidChange() {
      if (this.formData.eid && this.formData.accessType) {
        await this.loadAccessData()
      }
    },

    async onAccessTypeChange() {
      this.formData.accessValue = ''
      if (this.formData.eid && this.formData.accessType) {
        await this.loadAccessData()
      }
    },

    async loadAccessData() {
      if (this.formData.accessType === 'warehouse') {
        await this.loadWarehouses()
      } else if (this.formData.accessType === 'time') {
        await this.loadAvailableDates()
      }
    },

    async loadWarehouses() {
      this.loadingWarehouses = true
      this.warehouses = []

      try {
        const response = await axios.get(`${API_BASE_URL}/warehouses/by-eid/`, {
          params: { eid: this.formData.eid }
        })

        if (response.data.success) {
          this.warehouses = response.data.warehouses || []
          if (this.warehouses.length === 0) {
            this.showMessage('该EID下没有找到任何仓库', 'warning')
          }
        }
      } catch (error) {
        this.showMessage('加载仓库失败: ' + error.message, 'error')
      } finally {
        this.loadingWarehouses = false
      }
    },

    async loadAvailableDates() {
      this.loadingDates = true
      this.availableDates = []

      try {
        const response = await axios.get(`${API_BASE_URL}/permission/available-dates/`, {
          params: { eid: this.formData.eid }
        })

        if (response.data.success) {
          this.availableDates = response.data.dates || []
          if (this.availableDates.length === 0) {
            this.showMessage('该EID下没有找到任何文件日期', 'warning')
          }
        }
      } catch (error) {
        this.showMessage('加载日期失败: ' + error.message, 'error')
      } finally {
        this.loadingDates = false
      }
    },

    async generateToken() {
      if (!this.isFormValid) return

      this.isGenerating = true
      this.generatedToken = null

      try {
        const response = await axios.post(`${API_BASE_URL}/admin/generate-token/`, {
          eid: this.formData.eid,
          access_type: this.formData.accessType,
          access_value: this.formData.accessValue,
          duration_days: parseInt(this.formData.duration)
        })

        if (response.data.success) {
          this.generatedToken = response.data.token_info
          this.showMessage('访问令牌生成成功!', 'success')
          this.resetForm()
        } else {
          throw new Error(response.data.message || '生成令牌失败')
        }
      } catch (error) {
        this.showMessage(error.response?.data?.message || error.message, 'error')
      } finally {
        this.isGenerating = false
      }
    },

    resetForm() {
      this.formData = {
        eid: '',
        accessType: '',
        accessValue: '',
        duration: ''
      }
      this.warehouses = []
      this.availableDates = []
    },

    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        this.showMessage('已复制到剪贴板', 'success')
      }).catch(() => {
        this.showMessage('复制失败', 'error')
      })
    },

    formatDate(dateString) {
      return new Date(dateString).toLocaleString('zh-CN')
    },

    showMessage(text, type) {
      this.message = { show: true, type, text }
      setTimeout(() => {
        this.message.show = false
      }, 3000)
    },

    getMessageIcon(type) {
      const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }
      return icons[type] || icons.info
    }
  }
}
</script>

<style scoped>
.generate-token-container {
  max-width: 900px;
  margin: 0 auto;
}

.header-section {
  margin-bottom: 30px;
}

.header-section h2 {
  color: #333;
  font-size: 24px;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.token-form {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.required {
  color: #dc3545;
}

.form-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.3s;
}

.form-control:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.form-control:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.loading-hint {
  color: #1890ff;
  font-size: 14px;
  padding: 8px 0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-reset,
.btn-generate {
  padding: 10px 24px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-reset {
  background-color: #f5f5f5;
  color: #666;
}

.btn-reset:hover {
  background-color: #e0e0e0;
}

.btn-generate {
  background-color: #1890ff;
  color: white;
}

.btn-generate:hover:not(:disabled) {
  background-color: #1677ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 结果面板 */
.result-panel {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.result-header i {
  font-size: 24px;
  color: #10b981;
}

.result-header h3 {
  color: #047857;
  margin: 0;
  font-size: 18px;
}

.token-display {
  background: white;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #bae6fd;
}

.token-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.token-label span {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.copy-btn {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.copy-btn:hover {
  background: #e6f7ff;
}

.token-code {
  display: block;
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  color: #1f2937;
  word-break: break-all;
}

.token-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #bae6fd;
}

.info-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.info-value {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

/* 提示部分 */
.tips-section {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 20px;
}

.tips-section h3 {
  color: #1e40af;
  margin-bottom: 15px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tips-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tips-section li {
  padding: 8px 0;
  padding-left: 20px;
  position: relative;
  color: #374151;
  font-size: 14px;
  line-height: 1.6;
}

.tips-section li:before {
  content: "•";
  color: #1890ff;
  font-weight: bold;
  position: absolute;
  left: 0;
}

/* 消息提示 */
.message-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  padding: 16px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
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

.message-warning {
  background: #fffbeb;
  color: #d97706;
  border: 1px solid #fbbf24;
}

.message-info {
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #93c5fd;
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

@media (max-width: 768px) {
  .token-info-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .btn-reset,
  .btn-generate {
    width: 100%;
    justify-content: center;
  }
}
</style>