<template>
  <div class="device-management">
    <div class="header">
      <h1>设备管理</h1>
      <div class="user-info">
        <span>{{ userTypeText }}: {{ managerInfo.name }}</span>
        <span v-if="managerInfo.eid">EID: {{ managerInfo.eid }}</span>
      </div>
    </div>

    <!-- 添加设备区域 - 新增类型选择 -->
    <div class="add-device-section">
      <div class="input-group">
        <input
          v-model="newDeviceName"
          type="text"
          placeholder="请输入仓库名称"
          class="device-input"
          @keyup.enter="addDevice"
        />

        <!-- 新增：仓库类型选择器 -->
        <div class="warehouse-type-selector">
          <label class="type-label">仓库类型:</label>
          <div class="radio-group">
            <label class="radio-option">
              <input
                type="radio"
                v-model="warehouseType"
                value="json"
                name="warehouse-type"
              />
              <span class="radio-text">
                <i class="fas fa-code"></i>
                JSON数据
              </span>
            </label>
            <label class="radio-option">
              <input
                type="radio"
                v-model="warehouseType"
                value="mp4"
                name="warehouse-type"
              />
              <span class="radio-text">
                <i class="fas fa-video"></i>
                MP4视频
              </span>
            </label>
          </div>
        </div>

        <button @click="addDevice" class="add-btn" :disabled="!newDeviceName.trim()">
          <i class="fas fa-plus"></i>
          创建仓库
        </button>
      </div>

      <!-- 类型说明提示 -->
      <div class="type-hint">
        <i class="fas fa-info-circle"></i>
        <span v-if="warehouseType === 'json'">
          JSON仓库用于存储设备检测数据文件(.json格式)
        </span>
        <span v-else>
          MP4仓库用于存储监控视频文件(.mp4格式)
        </span>
      </div>
    </div>

    <!-- 设备仓库列表 -->
    <div class="device-warehouses">
      <h2>设备仓库列表</h2>
      <div class="warehouses-grid">
        <div
          v-for="warehouse in deviceWarehouses"
          :key="warehouse.id"
          class="warehouse-card"
          @click="selectWarehouse(warehouse)"
          :class="{ active: selectedWarehouse?.id === warehouse.id }"
        >
          <div class="warehouse-header">
            <h3>{{ warehouse.name }}</h3>
            <div class="warehouse-type-badge" :class="`type-${warehouse.warehouse_type}`">
              <i :class="warehouse.warehouse_type === 'json' ? 'fas fa-code' : 'fas fa-video'"></i>
              {{ warehouse.warehouse_type_display || (warehouse.warehouse_type === 'json' ? 'JSON数据' : 'MP4视频') }}
            </div>
            <span class="file-count">{{ warehouse.file_count || 0 }} 个文件</span>
          </div>
          <div class="warehouse-info">
            <p>创建时间: {{ formatDate(warehouse.created_at) }}</p>
            <p>最近更新: {{ formatDate(warehouse.updated_at) }}</p>
          </div>
          <div class="warehouse-actions">
            <button @click.stop="editWarehouseName(warehouse)" class="edit-name-btn">
              <i class="fas fa-edit"></i>
              更改名称
            </button>
            <button @click.stop="deleteWarehouse(warehouse)" class="delete-btn">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 文件上传区域 - 根据仓库类型调整 -->
    <div v-if="selectedWarehouse" class="file-upload-section">
      <h2>
        {{ selectedWarehouse.name }} - 文件管理
        <span class="warehouse-type-indicator" :class="`type-${selectedWarehouse.warehouse_type}`">
          <i :class="selectedWarehouse.warehouse_type === 'json' ? 'fas fa-code' : 'fas fa-video'"></i>
          {{ selectedWarehouse.warehouse_type_display || (selectedWarehouse.warehouse_type === 'json' ? 'JSON' : 'MP4') }}
        </span>
      </h2>

      <!-- 日期选择器 -->
      <div class="date-selector">
        <label>选择上传文件日期:</label>
        <div class="date-inputs">
          <select v-model="uploadDate.year" class="date-select">
            <option v-for="year in availableYears" :key="year" :value="year">
              {{ year }}年
            </option>
          </select>
          <select v-model="uploadDate.month" class="date-select">
            <option v-for="month in 12" :key="month" :value="month">
              {{ month }}月
            </option>
          </select>
          <select v-model="uploadDate.day" class="date-select">
            <option v-for="day in daysInMonth" :key="day" :value="day">
              {{ day }}日
            </option>
          </select>
        </div>
      </div>

      <!-- 文件上传 - 根据仓库类型显示不同的提示和accept -->
      <div class="upload-area">
        <input
          ref="fileInput"
          type="file"
          @change="handleFileSelect"
          :accept="acceptFileType"
          multiple
          style="display: none"
        />
        <div
          class="upload-zone"
          @click="$refs.fileInput.click()"
          @dragover.prevent
          @drop.prevent="handleFileDrop"
        >
          <div class="upload-icon">
            <i :class="selectedWarehouse.warehouse_type === 'json' ? 'fas fa-file-code' : 'fas fa-file-video'"></i>
          </div>
          <p v-if="selectedWarehouse.warehouse_type === 'json'">
            点击选择JSON文件或拖拽文件到此处
          </p>
          <p v-else>
            点击选择MP4视频文件或拖拽文件到此处
          </p>
          <p class="upload-hint">
            支持批量上传多个{{ selectedWarehouse.warehouse_type === 'json' ? 'JSON' : 'MP4' }}文件
          </p>
        </div>
      </div>

      <!-- 已选择的文件列表 -->
      <div v-if="selectedFiles.length > 0" class="selected-files">
        <h3>待上传文件:</h3>
        <div class="file-list">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <span class="file-icon">
              <i :class="getFileIcon(file.name)"></i>
            </span>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file.size) }}</span>
            <button @click="removeFile(index)" class="remove-btn">移除</button>
          </div>
        </div>
        <div class="upload-actions">
          <button @click="uploadFiles" class="upload-btn" :disabled="uploading">
            {{ uploading ? '上传中...' : '开始上传' }}
          </button>
          <button @click="clearSelectedFiles" class="clear-btn">清空列表</button>
        </div>
      </div>

      <!-- 仓库文件列表 -->
      <div class="warehouse-files">
        <h3>仓库文件列表</h3>
        <div class="file-filters">
          <input
            v-model="fileSearchQuery"
            type="text"
            placeholder="搜索文件..."
            class="search-input"
          />
          <select v-model="fileDateFilter" class="filter-select">
            <option value="">所有日期</option>
            <option v-for="date in availableDates" :key="date" :value="date">
              {{ date }}
            </option>
          </select>
        </div>

        <div class="files-table">
          <table>
            <thead>
              <tr>
                <th>文件名</th>
                <th>文件类型</th>
                <th>上传日期</th>
                <th>文件大小</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="file in filteredWarehouseFiles" :key="file.id">
                <td>
                  <i :class="getFileIcon(file.file_name)" style="margin-right: 8px;"></i>
                  {{ file.file_name }}
                </td>
                <td>
                  <span class="file-type-badge" :class="`type-${file.file_type || 'json'}`">
                    {{ (file.file_type || 'json').toUpperCase() }}
                  </span>
                </td>
                <td>{{ formatDate(file.upload_date) }}</td>
                <td>{{ formatFileSize(file.file_size) }}</td>
                <td>
                  <span :class="'status-' + file.status">
                    {{ getStatusText(file.status) }}
                  </span>
                </td>
                <td>
                  <button @click="downloadFile(file)" class="action-btn">下载</button>
                  <button
                    v-if="file.file_type === 'json' || !file.file_type"
                    @click="viewFile(file)"
                    class="action-btn"
                  >
                    查看
                  </button>
                  <button @click="deleteFile(file)" class="action-btn danger">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 文件查看模态框 -->
    <div v-if="viewingFile" class="modal-overlay" @click="closeFileViewer">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ viewingFile.file_name }}</h3>
          <button @click="closeFileViewer" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <pre>{{ fileContent }}</pre>
        </div>
      </div>
    </div>

    <!-- 仓库名称编辑模态框 -->
    <div v-if="editingWarehouse" class="modal-overlay" @click="cancelEditName">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>更改仓库名称</h3>
          <button @click="cancelEditName" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>仓库名称:</label>
            <input
              v-model="newWarehouseName"
              type="text"
              class="name-input"
              placeholder="请输入新的仓库名称"
              @keyup.enter="confirmEditName"
            />
          </div>
          <div class="modal-actions">
            <button @click="confirmEditName" class="confirm-btn" :disabled="!newWarehouseName.trim()">
              确认更改
            </button>
            <button @click="cancelEditName" class="cancel-btn">
              取消
            </button>
          </div>
        </div>
      </div>
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

    <!-- 调试信息（开发时使用,生产环境可删除） -->
    <div v-if="showDebugInfo" class="debug-info">
      <h4>调试信息:</h4>
      <p>用户类型: {{ userType }}</p>
      <p>用户名: {{ managerInfo.name }}</p>
      <p>EID: {{ managerInfo.eid }}</p>
      <p>Rep: {{ managerRep }}</p>
    </div>
  </div>
</template>

<script>
import { warehouseAPI } from '@/services/api'
import axios from 'axios'

export default {
  name: 'DeviceManagement',
  data() {
    return {
      managerInfo: {
        name: '',
        eid: ''
      },
      userType: '',
      managerRep: '',
      newDeviceName: '',
      warehouseType: 'json', // 新增：默认选择JSON类型
      deviceWarehouses: [],
      selectedWarehouse: null,
      uploadDate: {
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        day: new Date().getDate()
      },
      selectedFiles: [],
      uploading: false,
      warehouseFiles: [],
      fileSearchQuery: '',
      fileDateFilter: '',
      viewingFile: null,
      fileContent: '',
      showDebugInfo: false,

      // 编辑仓库名称相关
      editingWarehouse: null,
      newWarehouseName: '',

      // 消息提示
      message: {
        show: false,
        type: 'info',
        text: ''
      }
    }
  },

  computed: {
    userTypeText() {
      const typeMap = {
        'manager': '经理',
        'admin': '系统管理员',
        'visitor': '员工'
      }
      return typeMap[this.userType] || '用户'
    },

    availableYears() {
      const currentYear = new Date().getFullYear()
      const years = []
      for (let year = currentYear - 5; year <= currentYear + 1; year++) {
        years.push(year)
      }
      return years
    },

    daysInMonth() {
      return new Date(this.uploadDate.year, this.uploadDate.month, 0).getDate()
    },

    availableDates() {
      const dates = [...new Set(this.warehouseFiles.map(file =>
        file.upload_date?.substring(0, 10) || ''
      ))]
      return dates.filter(d => d).sort()
    },

    filteredWarehouseFiles() {
      let files = this.warehouseFiles

      if (this.fileSearchQuery) {
        files = files.filter(file =>
          file.file_name.toLowerCase().includes(this.fileSearchQuery.toLowerCase())
        )
      }

      if (this.fileDateFilter) {
        files = files.filter(file =>
          file.upload_date?.startsWith(this.fileDateFilter)
        )
      }

      return files
    },

    // 新增：根据选中仓库类型返回accept属性
    acceptFileType() {
      if (!this.selectedWarehouse) return '*'
      return this.selectedWarehouse.warehouse_type === 'json' ? '.json' : '.mp4'
    }
  },

  async mounted() {
    this.loadUserInfo()

    if (this.userType === 'manager' || this.userType === 'admin') {
      await this.loadDeviceWarehouses()
    }
  },

  methods: {
    loadUserInfo() {
      try {
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
        console.log('从sessionStorage获取的用户信息:', userInfo)

        this.userType = userInfo.userType || ''

        if (userInfo.userType === 'manager') {
          this.managerInfo = {
            name: userInfo.name || userInfo.data?.name || '',
            eid: userInfo.eid || ''
          }
          this.managerRep = userInfo.data?.rep || ''

          if (!this.managerInfo.name || !this.managerInfo.eid) {
            console.warn('Manager信息不完整，请检查登录信息')
            this.showMessage('用户信息不完整，某些功能可能受限', 'warning')
          }
        }
      } catch (error) {
        console.error('加载用户信息失败:', error)
        this.showMessage('用户信息加载失败', 'error')
      }
    },

    async loadDeviceWarehouses() {
      try {
        const eid = this.managerInfo.eid
        if (!eid) {
          console.warn('未找到EID，无法加载设备仓库')
          return
        }

        const response = await warehouseAPI.getWarehouses({ eid: eid })

        if (response.data.success) {
          this.deviceWarehouses = response.data.warehouses || []
          console.log('设备仓库加载成功:', this.deviceWarehouses)
        } else {
          console.error('加载设备仓库失败:', response.data.message)
          this.showMessage(response.data.message || '加载设备仓库失败', 'error')
        }
      } catch (error) {
        console.error('加载设备仓库失败:', error)
        this.showMessage('加载设备仓库失败: ' + error.message, 'error')
      }
    },

    // 修改：添加设备时包含仓库类型
    async addDevice() {
      if (!this.newDeviceName.trim()) {
        this.showMessage('请输入仓库名称', 'warning')
        return
      }

      try {
        const response = await warehouseAPI.createWarehouse({
          name: this.newDeviceName.trim(),
          eid: this.managerInfo.eid,
          warehouse_type: this.warehouseType // 新增：发送仓库类型
        })

        if (response.data.success) {
          this.showMessage(`仓库"${this.newDeviceName}"创建成功`, 'success')
          this.newDeviceName = ''
          this.warehouseType = 'json' // 重置为默认类型
          await this.loadDeviceWarehouses()
        } else {
          this.showMessage(response.data.message || '创建仓库失败', 'error')
        }
      } catch (error) {
        console.error('创建仓库失败:', error)
        this.showMessage('创建仓库失败: ' + error.message, 'error')
      }
    },

    async selectWarehouse(warehouse) {
      this.selectedWarehouse = warehouse
      await this.loadWarehouseFiles(warehouse.id)
    },

    async loadWarehouseFiles(warehouseId) {
      try {
        const response = await warehouseAPI.getWarehouseFiles(warehouseId, { eid: this.managerInfo.eid })

        if (response.data.success) {
          this.warehouseFiles = response.data.files || []
          console.log('仓库文件加载成功:', this.warehouseFiles)
        } else {
          this.showMessage(response.data.message || '加载文件列表失败', 'error')
        }
      } catch (error) {
        console.error('加载仓库文件失败:', error)
        this.showMessage('加载文件列表失败: ' + error.message, 'error')
      }
    },

    // 修改：文件选择时验证文件类型
    handleFileSelect(event) {
      const files = Array.from(event.target.files)
      this.validateAndAddFiles(files)
    },

    handleFileDrop(event) {
      const files = Array.from(event.dataTransfer.files)
      this.validateAndAddFiles(files)
    },

    // 新增：验证并添加文件
    validateAndAddFiles(files) {
      if (!this.selectedWarehouse) {
        this.showMessage('请先选择一个仓库', 'warning')
        return
      }

      const expectedType = this.selectedWarehouse.warehouse_type
      const validFiles = []
      const invalidFiles = []

      files.forEach(file => {
        const fileExtension = file.name.split('.').pop().toLowerCase()

        if (expectedType === 'json' && fileExtension === 'json') {
          validFiles.push(file)
        } else if (expectedType === 'mp4' && fileExtension === 'mp4') {
          validFiles.push(file)
        } else {
          invalidFiles.push(file.name)
        }
      })

      if (validFiles.length > 0) {
        this.selectedFiles.push(...validFiles)
      }

      if (invalidFiles.length > 0) {
        this.showMessage(
          `以下文件格式不符合要求(仓库类型: ${expectedType.toUpperCase()}): ${invalidFiles.join(', ')}`,
          'warning'
        )
      }

      if (validFiles.length > 0) {
        this.showMessage(`已添加 ${validFiles.length} 个文件`, 'success')
      }
    },

    removeFile(index) {
      this.selectedFiles.splice(index, 1)
      this.showMessage('文件已移除', 'info')
    },

    clearSelectedFiles() {
      this.selectedFiles = []
      this.showMessage('已清空文件列表', 'info')
    },

    async uploadFiles() {
      if (this.selectedFiles.length === 0) {
        this.showMessage('请先选择文件', 'warning')
        return
      }

      if (!this.selectedWarehouse) {
        this.showMessage('请先选择仓库', 'warning')
        return
      }

      this.uploading = true

      try {
        const formData = new FormData()
        formData.append('warehouseId', this.selectedWarehouse.id)
        formData.append('eid', this.managerInfo.eid)

        const uploadDateStr = `${this.uploadDate.year}-${String(this.uploadDate.month).padStart(2, '0')}-${String(this.uploadDate.day).padStart(2, '0')}`
        formData.append('uploadDate', uploadDateStr)

        this.selectedFiles.forEach(file => {
          formData.append('files', file)
        })

        const response = await warehouseAPI.uploadFiles(formData)

        if (response.data.success) {
          this.showMessage(response.data.message || '文件上传成功', 'success')
          this.selectedFiles = []
          await this.loadWarehouseFiles(this.selectedWarehouse.id)
        } else {
          this.showMessage(response.data.message || '文件上传失败', 'error')
        }
      } catch (error) {
        console.error('文件上传失败:', error)
        this.showMessage('文件上传失败: ' + error.message, 'error')
      } finally {
        this.uploading = false
      }
    },

    async downloadFile(file) {
      try {
        const response = await warehouseAPI.downloadFile(file.id, this.managerInfo.eid)

        const blob = new Blob([response.data])
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = file.file_name
        link.click()
        window.URL.revokeObjectURL(url)

        this.showMessage('文件下载成功', 'success')
      } catch (error) {
        console.error('文件下载失败:', error)
        this.showMessage('文件下载失败: ' + error.message, 'error')
      }
    },

    async viewFile(file) {
      try {
        const response = await warehouseAPI.getFileContent(file.id, this.managerInfo.eid)

        if (response.data.success) {
          this.viewingFile = file
          this.fileContent = JSON.stringify(response.data.content, null, 2)
        } else {
          this.showMessage(response.data.message || '获取文件内容失败', 'error')
        }
      } catch (error) {
        console.error('查看文件失败:', error)
        this.showMessage('查看文件失败: ' + error.message, 'error')
      }
    },

    closeFileViewer() {
      this.viewingFile = null
      this.fileContent = ''
    },

    async deleteFile(file) {
      if (!confirm(`确定要删除文件"${file.file_name}"吗？此操作不可恢复。`)) {
        return
      }

      try {
        const response = await warehouseAPI.deleteFile(file.id, { eid: this.managerInfo.eid })

        if (response.data.success) {
          this.showMessage(response.data.message || '文件删除成功', 'success')
          await this.loadWarehouseFiles(this.selectedWarehouse.id)
        } else {
          this.showMessage(response.data.message || '文件删除失败', 'error')
        }
      } catch (error) {
        console.error('删除文件失败:', error)
        this.showMessage('删除文件失败: ' + error.message, 'error')
      }
    },

    async deleteWarehouse(warehouse) {
      if (!confirm(`确定要删除仓库"${warehouse.name}"吗？这将删除仓库及其所有文件，此操作不可恢复。`)) {
        return
      }

      try {
        // 直接用 axios 调用，EID 通过 query param 传递（后端路由不含EID路径段）
        const response = await axios.delete(
          `/api/monitor/warehouses/${warehouse.id}/delete/`,
          { params: { eid: this.managerInfo.eid } }
        )

        if (response.data.success) {
          this.showMessage(response.data.message || '仓库删除成功', 'success')

          if (this.selectedWarehouse?.id === warehouse.id) {
            this.selectedWarehouse = null
            this.warehouseFiles = []
          }

          await this.loadDeviceWarehouses()
        } else {
          this.showMessage(response.data.message || '仓库删除失败', 'error')
        }
      } catch (error) {
        console.error('删除仓库失败:', error)
        this.showMessage('删除仓库失败: ' + (error.response?.data?.message || error.message), 'error')
      }
    },

    editWarehouseName(warehouse) {
      this.editingWarehouse = warehouse
      this.newWarehouseName = warehouse.name
    },

    async confirmEditName() {
      if (!this.newWarehouseName.trim()) {
        this.showMessage('仓库名称不能为空', 'warning')
        return
      }

      if (this.newWarehouseName === this.editingWarehouse.name) {
        this.cancelEditName()
        return
      }

      try {
        const response = await warehouseAPI.updateWarehouseName(
          this.editingWarehouse.id,
          this.newWarehouseName.trim(),
          this.managerInfo.eid
        )

        if (response.data.success) {
          this.showMessage('仓库名称更新成功', 'success')
          await this.loadDeviceWarehouses()

          if (this.selectedWarehouse?.id === this.editingWarehouse.id) {
            this.selectedWarehouse.name = this.newWarehouseName.trim()
          }

          this.cancelEditName()
        } else {
          this.showMessage(response.data.message || '更新仓库名称失败', 'error')
        }
      } catch (error) {
        console.error('更新仓库名称失败:', error)
        this.showMessage('更新仓库名称失败: ' + error.message, 'error')
      }
    },

    cancelEditName() {
      this.editingWarehouse = null
      this.newWarehouseName = ''
    },

    // 新增：根据文件名获取图标
    getFileIcon(fileName) {
      const extension = fileName.split('.').pop().toLowerCase()
      if (extension === 'json') {
        return 'fas fa-file-code'
      } else if (extension === 'mp4') {
        return 'fas fa-file-video'
      }
      return 'fas fa-file'
    },

    formatDate(dateString) {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    },

    getStatusText(status) {
      const statusMap = {
        'uploaded': '已上传',
        'processing': '处理中',
        'processed': '已处理',
        'error': '错误'
      }
      return statusMap[status] || status
    },

    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, 3000)
    },

    getMessageIcon(type) {
      const iconMap = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
      }
      return iconMap[type] || 'fas fa-info-circle'
    }
  }
}
</script>

<style scoped>
.device-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

.header h1 {
  margin: 0;
  color: #333;
}

.user-info {
  display: flex;
  gap: 20px;
  color: #666;
}

/* 新增：添加设备区域样式优化 */
.add-device-section {
  background: #f8f9fa;
  padding: 25px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.input-group {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: center;
}

.device-input {
  flex: 1;
  min-width: 250px;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* 新增：仓库类型选择器样式 */
.warehouse-type-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 15px;
  background: white;
  border-radius: 6px;
  border: 1px solid #ddd;
}

.type-label {
  font-weight: 500;
  color: #555;
  font-size: 14px;
  white-space: nowrap;
}

.radio-group {
  display: flex;
  gap: 15px;
}

.radio-option {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.radio-option input[type="radio"] {
  margin-right: 6px;
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.radio-text {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  color: #555;
  font-weight: 500;
}

.radio-text i {
  font-size: 16px;
}

.radio-option:hover .radio-text {
  color: #007bff;
}

/* 新增:类型提示样式 */
.type-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 15px;
  background: #e7f3ff;
  border-left: 3px solid #007bff;
  border-radius: 4px;
  font-size: 13px;
  color: #0056b3;
}

.type-hint i {
  font-size: 14px;
}

.add-btn {
  padding: 12px 24px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.3s ease;
}

.add-btn:hover:not(:disabled) {
  background: #0056b3;
}

.add-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 新增：仓库类型标识样式 */
.warehouse-type-badge {
  position: relative;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  text-transform: uppercase;
  flex-shrink: 0;
}

.warehouse-type-badge.type-json {
  background: #e3f2fd;
  color: #1976d2;
}

.warehouse-type-badge.type-mp4 {
  background: #f3e5f5;
  color: #7b1fa2;
}

.warehouse-type-badge i {
  font-size: 12px;
}

/* 新增：仓库类型指示器 */
.warehouse-type-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 12px;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.warehouse-type-indicator.type-json {
  background: #e3f2fd;
  color: #1976d2;
}

.warehouse-type-indicator.type-mp4 {
  background: #f3e5f5;
  color: #7b1fa2;
}

.device-warehouses h2 {
  margin-bottom: 20px;
  color: #333;
}

.warehouses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.warehouse-card {
  position: relative; /* 为badge定位 */
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
}

.warehouse-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.warehouse-card.active {
  border: 2px solid #007bff;
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.warehouse-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  gap: 10px;
  flex-wrap: wrap;
}

.warehouse-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
  flex: 1;
  min-width: 0;
}

.file-count {
  background: #e9ecef;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: #666;
}

.warehouse-info {
  margin-bottom: 15px;
}

.warehouse-info p {
  margin: 5px 0;
  color: #666;
  font-size: 13px;
}

.warehouse-actions {
  display: flex;
  gap: 10px;
}

.edit-name-btn {
  flex: 1;
  padding: 6px 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: background 0.3s ease;
}

.edit-name-btn:hover {
  background: #218838;
}

.delete-btn {
  padding: 6px 12px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.3s ease;
}

.delete-btn:hover {
  background: #c82333;
}

.file-upload-section {
  margin-top: 30px;
  background: white;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.file-upload-section h2 {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  color: #333;
}

.date-selector {
  margin-bottom: 20px;
}

.date-selector label {
  display: block;
  margin-bottom: 10px;
  font-weight: 500;
  color: #333;
}

.date-inputs {
  display: flex;
  gap: 10px;
}

.date-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.upload-area {
  margin-bottom: 25px;
}

.upload-zone {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-zone:hover {
  border-color: #007bff;
  background: #f8f9fa;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.upload-icon i {
  font-size: 48px;
  color: #007bff;
}

.upload-zone p {
  margin: 5px 0;
  color: #666;
}

.upload-hint {
  font-size: 12px;
  color: #999;
}

.selected-files {
  margin-bottom: 25px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.selected-files h3 {
  margin: 0 0 15px 0;
  color: #333;
}

.file-list {
  margin-bottom: 15px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  background: white;
  border-radius: 4px;
  margin-bottom: 8px;
}

.file-icon {
  font-size: 20px;
  color: #007bff;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.file-size {
  color: #666;
  font-size: 12px;
}

/* 新增：文件类型标识 */
.file-type-badge {
  padding: 3px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.file-type-badge.type-json {
  background: #e3f2fd;
  color: #1976d2;
}

.file-type-badge.type-mp4 {
  background: #f3e5f5;
  color: #7b1fa2;
}

.remove-btn {
  padding: 5px 10px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.upload-actions {
  display: flex;
  gap: 10px;
}

.upload-btn {
  padding: 10px 20px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.upload-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.clear-btn {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.warehouse-files h3 {
  margin-bottom: 20px;
  color: #333;
}

.file-filters {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.search-input,
.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.search-input {
  flex: 1;
  max-width: 300px;
}

.files-table {
  overflow-x: auto;
}

.files-table table {
  width: 100%;
  border-collapse: collapse;
}

.files-table th,
.files-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.files-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.status-uploaded { color: #28a745; }
.status-processing { color: #ffc107; }
.status-processed { color: #007bff; }
.status-error { color: #dc3545; }

.action-btn {
  padding: 5px 10px;
  margin-right: 5px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.action-btn:hover {
  background: #0056b3;
}

.action-btn.danger {
  background: #dc3545;
}

.action-btn.danger:hover {
  background: #c82333;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 80%;
  max-height: 80%;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
  overflow: auto;
}

.modal-body pre {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  overflow: auto;
  max-height: 400px;
}

/* 编辑模态框样式 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.name-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.name-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.confirm-btn {
  padding: 8px 16px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn:hover:not(:disabled) {
  background: #218838;
}

.confirm-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.cancel-btn {
  padding: 8px 16px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.cancel-btn:hover {
  background: #545b62;
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
  background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7;
}
.message-error {
  background: #FFEBEE; color: #C62828; border: 1px solid #EF9A9A;
}
.message-warning {
  background: #FFF8E1; color: #F9A825; border: 1px solid #FFE082;
}
.message-info {
  background: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9;
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
.message-enter-active, .message-leave-active {
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

.debug-info {
  margin-top: 30px;
  padding: 15px;
  background: #f8f9fa;
  border: 1px dashed #999;
  border-radius: 4px;
}

.debug-info h4 {
  margin: 0 0 10px 0;
  color: #666;
}

.debug-info p {
  margin: 5px 0;
  font-family: monospace;
  font-size: 12px;
}

@media (max-width: 768px) {
  .device-management {
    padding: 10px;
  }

  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .input-group {
    flex-direction: column;
  }

  .warehouse-type-selector {
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
  }

  .radio-group {
    width: 100%;
    justify-content: space-around;
  }

  .warehouses-grid {
    grid-template-columns: 1fr;
  }

  .date-inputs {
    flex-direction: column;
  }

  .file-filters {
    flex-direction: column;
  }

  .upload-actions {
    flex-direction: column;
  }

  .modal-content {
    max-width: 95%;
    margin: 20px;
  }

  .warehouse-actions {
    flex-direction: column;
    gap: 8px;
  }

  .edit-name-btn {
    font-size: 11px;
    padding: 5px 8px;
  }
}
</style>