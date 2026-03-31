<template>
  <div class="submit-permission-container">
    <h2>申请权限</h2>

    <div class="permission-form">
      <!-- 第一栏：企业EID -->
      <div class="form-group">
        <label for="enterprise-eid">企业EID <span class="required">*</span></label>
        <input
          id="enterprise-eid"
          v-model="formData.eid"
          type="text"
          class="form-control"
          placeholder="请输入企业EID"
          @blur="onEidChange"
        />
        <span v-if="eidError" class="error-text">{{ eidError }}</span>
      </div>

      <!-- 第二栏：申请类型 -->
      <div class="form-group">
        <label for="apply-type">申请类型 <span class="required">*</span></label>
        <select
          id="apply-type"
          v-model="formData.applyType"
          class="form-control"
          @change="onApplyTypeChange"
        >
          <option value="">请选择申请类型</option>
          <option value="time">时间</option>
          <option value="warehouse">仓库名称</option>
        </select>
      </div>

      <!-- 第三栏：具体类别 -->
      <div v-if="formData.applyType" class="form-group">
        <label for="specific-category">
          具体类别 <span class="required">*</span>
          <span v-if="formData.applyType === 'time'" class="label-hint">（选择JSON文件日期）</span>
        </label>

        <!-- 时间选择器（复用DeviceManagement的方式） -->
        <div v-if="formData.applyType === 'time'" class="date-selector">
          <div class="date-inputs">
            <select v-model="selectedDate.year" class="date-select" @change="checkDateFile">
              <option v-for="year in availableYears" :key="year" :value="year">
                {{ year }}年
              </option>
            </select>
            <select v-model="selectedDate.month" class="date-select" @change="checkDateFile">
              <option v-for="month in 12" :key="month" :value="month">
                {{ month }}月
              </option>
            </select>
            <select v-model="selectedDate.day" class="date-select" @change="checkDateFile">
              <option v-for="day in daysInMonth" :key="day" :value="day">
                {{ day }}日
              </option>
            </select>
          </div>
          <div v-if="checkingFile" class="checking-status">
            <i class="fas fa-spinner fa-spin"></i> 正在检查文件...
          </div>
          <div v-else-if="dateCheckResult !== null" class="file-check-result">
            <span v-if="dateCheckResult" class="success-text">
              <i class="fas fa-check-circle"></i> 该日期有对应的JSON文件
            </span>
            <span v-else class="error-text">
              <i class="fas fa-times-circle"></i> 该时间点并无对应的文件
            </span>
          </div>
        </div>

        <!-- 仓库选择器 -->
        <div v-else-if="formData.applyType === 'warehouse'">
          <select
            v-model="formData.specificCategory"
            class="form-control"
            :disabled="loadingWarehouses || warehouses.length === 0"
          >
            <option value="">{{ warehouseSelectText }}</option>
            <option v-for="warehouse in warehouses" :key="warehouse.id" :value="warehouse.id">
              {{ warehouse.name }} ({{ warehouse.file_count || 0 }}个文件)
            </option>
          </select>
          <div v-if="loadingWarehouses" class="loading-hint">
            <i class="fas fa-spinner fa-spin"></i> 正在加载仓库列表...
          </div>
        </div>
      </div>

      <!-- 第四栏：申请时长 -->
      <div class="form-group">
        <label for="apply-duration">申请时长 <span class="required">*</span></label>
        <select
          id="apply-duration"
          v-model="formData.duration"
          class="form-control"
        >
          <option value="">请选择申请时长</option>
          <option value="1">1天</option>
          <option value="7">7天</option>
          <option value="30">30天</option>
        </select>
      </div>

      <!-- 第五栏：申请理由 -->
      <div class="form-group">
        <label for="apply-reason">申请理由 <span class="required">*</span></label>
        <textarea
          id="apply-reason"
          v-model="formData.reason"
          rows="5"
          class="form-control"
          placeholder="请详细说明申请该权限的理由..."
        ></textarea>
        <div class="char-count">{{ formData.reason.length }}/500</div>
      </div>

      <!-- 提交按钮 -->
      <div class="form-actions">
        <button type="button" class="btn-cancel" @click="resetForm">
          重置
        </button>
        <button
          type="button"
          class="btn-submit"
          :disabled="!isFormValid || isSubmitting"
          @click="submitApplication"
        >
          <i v-if="!isSubmitting" class="fas fa-paper-plane"></i>
          <i v-else class="fas fa-spinner fa-spin"></i>
          {{ isSubmitting ? '提交中...' : '提交申请' }}
        </button>
      </div>
    </div>

    <!-- 提示信息 -->
    <div class="tips-section">
      <h3>申请说明</h3>
      <ul>
        <li>请确保输入正确的企业EID，这将决定您可以访问的数据范围</li>
        <li>时间类型：申请访问特定日期的JSON数据文件</li>
        <li>仓库类型：申请访问特定仓库中的所有数据文件</li>
        <li>申请提交后，需要等待管理员审核，审核结果将通过系统通知</li>
        <li>权限到期后需要重新申请</li>
      </ul>
    </div>

    <!-- 消息提示 -->
    <Transition name="message">
      <div v-if="message.show" :class="['message-toast', `message-${message.type}`]">
        <i :class="getMessageIcon(message.type)"></i>
        <span class="message-text">{{ message.text }}</span>
        <button @click="message.show = false" class="message-close">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </Transition>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_APP_API_BASE_URL || '/api/monitor';

export default {
  name: 'SubmitPermissionRequest',
  data() {
    return {
      formData: {
        eid: '',
        applyType: '',
        specificCategory: '',
        duration: '',
        reason: ''
      },

      // 时间选择相关
      selectedDate: {
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        day: new Date().getDate()
      },

      // 状态管理
      eidError: '',
      loadingWarehouses: false,
      warehouses: [],
      checkingFile: false,
      dateCheckResult: null,
      isSubmitting: false,

      // 消息提示
      message: {
        show: false,
        type: 'info',
        text: ''
      }
    }
  },

  computed: {
    availableYears() {
      const currentYear = new Date().getFullYear()
      const years = []
      for (let year = currentYear - 5; year <= currentYear + 1; year++) {
        years.push(year)
      }
      return years
    },

    daysInMonth() {
      return new Date(this.selectedDate.year, this.selectedDate.month, 0).getDate()
    },

    warehouseSelectText() {
      if (this.loadingWarehouses) {
        return '加载中...'
      } else if (this.warehouses.length === 0) {
        return '该EID下没有仓库'
      } else {
        return '请选择仓库'
      }
    },

    isFormValid() {
      // 基础字段验证
      if (!this.formData.eid || !this.formData.applyType || !this.formData.duration || !this.formData.reason) {
        return false
      }

      // 申请类型特定验证
      if (this.formData.applyType === 'time') {
        // 时间类型需要有对应的文件
        return this.dateCheckResult === true
      } else if (this.formData.applyType === 'warehouse') {
        // 仓库类型需要选择仓库
        return !!this.formData.specificCategory
      }

      return false
    },

    // 获取当前用户名称（visitor_name）
    currentVisitorName() {
      try {
        // 从 sessionStorage 读取用户信息
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')

        // 返回用户名（优先使用 name，其次 username）
        return userInfo.name || userInfo.username || ''
      } catch (error) {
        console.error('获取用户信息失败:', error)
        return ''
      }
    },

    // 新增：获取当前用户类型
    currentUserType() {
      try {
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
        return userInfo.userType || ''
      } catch (error) {
        return ''
      }
    }
},

  methods: {
    // EID输入框失焦时触发
    async onEidChange() {
      if (!this.formData.eid) {
        this.eidError = ''
        return
      }

      // 验证EID格式（这里假设EID是字母数字组合）
      if (!/^[A-Za-z0-9]+$/.test(this.formData.eid)) {
        this.eidError = 'EID格式不正确，只能包含字母和数字'
        return
      }

      this.eidError = ''

      // 如果申请类型是仓库，重新加载仓库列表
      if (this.formData.applyType === 'warehouse') {
        await this.loadWarehouses()
      }
    },

    // 申请类型改变时触发
    async onApplyTypeChange() {
      // 清空具体类别
      this.formData.specificCategory = ''
      this.dateCheckResult = null

      // 如果选择了仓库类型，加载仓库列表
      if (this.formData.applyType === 'warehouse' && this.formData.eid) {
        await this.loadWarehouses()
      }
    },

    // 加载仓库列表
    async loadWarehouses() {
      if (!this.formData.eid) {
        return
      }

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
        } else {
          throw new Error(response.data.message || '获取仓库列表失败')
        }
      } catch (error) {
        console.error('加载仓库失败:', error)
        const errorMsg = error.response?.data?.message || error.message || '加载仓库列表失败,请稍后重试'
        this.showMessage(errorMsg, 'error')
      } finally {
        this.loadingWarehouses = false
      }
    },

    // 检查选定日期是否有文件
    async checkDateFile() {
      if (!this.formData.eid) {
        this.dateCheckResult = null
        return
      }

      this.checkingFile = true
      this.dateCheckResult = null

      try {
        // 构建日期字符串
        const dateStr = `${this.selectedDate.year}-${String(this.selectedDate.month).padStart(2, '0')}-${String(this.selectedDate.day).padStart(2, '0')}`

        const response = await axios.get(`${API_BASE_URL}/check-file-exists/`, {
          params: {
            eid: this.formData.eid,
            date: dateStr
          }
        })

        if (response.data.success) {
          this.dateCheckResult = response.data.exists

          // 如果有文件，设置specificCategory为日期
          if (this.dateCheckResult) {
            this.formData.specificCategory = dateStr
          } else {
            this.formData.specificCategory = ''
          }
        } else {
          throw new Error(response.data.message || '检查文件失败')
        }
      } catch (error) {
        console.error('检查文件失败:', error)
        this.dateCheckResult = false
        this.showMessage('检查文件状态失败', 'error')
      } finally {
        this.checkingFile = false
      }
    },

    // 提交申请
    async submitApplication() {
      if (!this.isFormValid) {
        return
      }

      // 检查是否有 visitor_name
      if (!this.currentVisitorName) {
        this.showMessage('无法获取用户信息,请重新登录', 'error')
        return
      }

      this.isSubmitting = true

      try {
        // 构建提交数据
        const submitData = {
          visitor_name: this.currentVisitorName,
          eid: this.formData.eid,
          apply_type: this.formData.applyType,
          specific_category: this.formData.specificCategory,
          duration_days: parseInt(this.formData.duration),
          reason: this.formData.reason
        }

        const response = await axios.post(
          `${API_BASE_URL}/submit-permission/`,
          submitData,
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        )

        if (response.data.success) {
          this.showMessage(
            response.data.message || '权限申请已成功提交,请等待管理员审核',
            'success'
          )

          // 提交成功后重置表单
          setTimeout(() => {
            this.resetForm()
          }, 2000)
        } else {
          throw new Error(response.data.message || '提交申请失败')
        }

      } catch (error) {
        console.error('提交申请失败:', error)
        const errorMsg = error.response?.data?.message || error.message || '提交申请失败,请稍后重试'
        this.showMessage(errorMsg, 'error')
      } finally {
        this.isSubmitting = false
      }
    },

    // 重置表单
    resetForm() {
      this.formData = {
        eid: '',
        applyType: '',
        specificCategory: '',
        duration: '',
        reason: ''
      }

      this.selectedDate = {
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        day: new Date().getDate()
      }

      this.eidError = ''
      this.warehouses = []
      this.dateCheckResult = null
    },

    // 显示消息
    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      // 3秒后自动隐藏
      setTimeout(() => {
        this.message.show = false
      }, 3000)
    },

    // 获取消息图标
    getMessageIcon(type) {
      const iconMap = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }
      return iconMap[type] || iconMap.info
    }
  }
}
</script>

<style scoped>
.submit-permission-container {
  max-width: 800px;
  margin: 0 auto;
}

.submit-permission-container h2 {
  color: #333;
  margin-bottom: 30px;
  font-size: 24px;
}

.permission-form {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 25px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.required {
  color: #dc3545;
}

.label-hint {
  font-weight: normal;
  color: #666;
  font-size: 12px;
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

textarea.form-control {
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
}

.error-text {
  color: #dc3545;
  font-size: 12px;
  margin-top: 5px;
  display: block;
}

.success-text {
  color: #28a745;
  font-size: 12px;
}

/* 日期选择器样式 */
.date-selector {
  margin-top: 8px;
}

.date-inputs {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.date-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.date-select:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.checking-status,
.loading-hint {
  color: #1890ff;
  font-size: 12px;
  margin-top: 8px;
}

.file-check-result {
  margin-top: 8px;
  font-size: 12px;
}

/* 字符计数 */
.char-count {
  text-align: right;
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

/* 表单操作按钮 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn-cancel,
.btn-submit {
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

.btn-cancel {
  background-color: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e0e0e0;
}

.btn-submit {
  background-color: #1890ff;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background-color: #1677ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 提示信息区域 */
.tips-section {
  background: #f0f8ff;
  border: 1px solid #b3d9ff;
  border-radius: 8px;
  padding: 20px;
}

.tips-section h3 {
  color: #1890ff;
  margin-bottom: 15px;
  font-size: 16px;
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
  color: #333;
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

/* 消息提示样式 */
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
  max-width: 480px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
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

.message-text {
  flex: 1;
  font-weight: 500;
}

.message-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  color: inherit;
}

.message-close:hover {
  opacity: 1;
}

/* 过渡动画 */
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

/* 响应式设计 */
@media (max-width: 768px) {
  .submit-permission-container {
    padding: 0 15px;
  }

  .permission-form {
    padding: 20px;
  }

  .date-inputs {
    flex-direction: column;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .btn-cancel,
  .btn-submit {
    width: 100%;
    justify-content: center;
  }

  .message-toast {
    left: 24px;
    right: 24px;
    min-width: auto;
  }
}
</style>