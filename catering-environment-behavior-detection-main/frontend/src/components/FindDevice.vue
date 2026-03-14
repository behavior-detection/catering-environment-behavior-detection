<template>
  <div class="find-device-container">
    <!-- 哈希码兑换区域 -->
    <div class="hash-code-panel">
      <h3 class="panel-title">
        兑换访问码
      </h3>

      <div class="input-group">
        <input
          v-model="hashCode"
          type="text"
          placeholder="请输入您的访问码(哈希码)"
          class="hash-input"
          :disabled="isVerified"
        />
        <button
          @click="verifyHashCode"
          class="verify-btn"
          :disabled="!hashCode || isVerifying || isVerified"
        >
          {{ isVerifying ? '验证中...' : isVerified ? '已验证' : '兑换' }}
        </button>
        <button
          v-if="isVerified"
          @click="clearAccess"
          class="clear-btn"
        >
          清除
        </button>
      </div>

      <!-- 验证结果显示 -->
      <div v-if="verifyMessage" :class="['message', verifyMessageType]">
        {{ verifyMessage }}
      </div>

      <!-- 访问权限信息 -->
      <div v-if="isVerified && tokenInfo" class="access-info">
        <div class="info-item">
          <span class="label">访问者:</span>
          <span class="value">{{ tokenInfo.visitor_name }}</span>
        </div>
        <div class="info-item">
          <span class="label">企业EID:</span>
          <span class="value">{{ tokenInfo.eid }}</span>
        </div>
        <div class="info-item">
          <span class="label">权限类型:</span>
          <span class="value">{{ getAccessTypeText(tokenInfo.access_type) }}</span>
        </div>
        <div class="info-item">
          <span class="label">授权范围:</span>
          <span class="value">{{ tokenInfo.access_value }}</span>
        </div>
        <div class="info-item">
          <span class="label">授权人:</span>
          <span class="value">{{ tokenInfo.approved_by }}</span>
        </div>
        <div class="info-item">
          <span class="label">授权时间:</span>
          <span class="value">{{ formatDate(tokenInfo.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- 数据访问区域(仅在验证成功后显示) -->
    <div v-if="isVerified" class="data-access-panel">
      <h3 class="panel-title">
        授权数据访问
      </h3>

      <!-- 根据权限类型显示不同内容 -->
      <div v-if="tokenInfo.access_type === 'warehouse'" class="warehouse-access">
        <h4>仓库文件列表</h4>
        <button @click="loadWarehouseFiles" class="load-btn" :disabled="isLoading">
          {{ isLoading ? '加载中...' : '查看文件' }}
        </button>

        <!-- 文件列表 -->
        <div v-if="warehouseFiles.length > 0" class="file-list">
          <div class="list-header">
            <span>共找到 {{ warehouseFiles.length }} 个文件</span>
          </div>
          <div
            v-for="file in warehouseFiles"
            :key="file.id"
            class="file-item"
          >
            <div class="file-info">
              <span class="file-name">📄 {{ file.file_name }}</span>
              <span class="file-type-badge" :class="'type-' + file.file_type">
                {{ file.file_type.toUpperCase() }}
              </span>
              <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
              <span class="file-date">{{ formatDate(file.upload_date) }}</span>
            </div>
            <button @click="viewFileContent(file)" class="view-btn">
              {{ file.file_type === 'mp4' ? '播放' : '查看' }}
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="tokenInfo.access_type === 'time'" class="time-access">
        <h4>时间段数据访问</h4>
        <p class="access-desc">您被授权访问 {{ tokenInfo.access_value }} 的文件数据</p>
        <button @click="loadDateFiles" class="load-btn" :disabled="isLoading">
          {{ isLoading ? '加载中...' : '查看文件' }}
        </button>

        <!-- 文件列表 -->
        <div v-if="dateFiles.length > 0" class="file-list">
          <div class="list-header">
            <span>共找到 {{ dateFiles.length }} 个文件</span>
          </div>
          <div
            v-for="file in dateFiles"
            :key="file.id"
            class="file-item"
          >
            <div class="file-info">
              <span class="file-name">📄 {{ file.file_name }}</span>
              <span class="file-type-badge" :class="'type-' + file.file_type">
                {{ file.file_type.toUpperCase() }}
              </span>
              <span class="file-warehouse">仓库: {{ file.warehouse_name }}</span>
              <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
              <span class="file-date">{{ formatDate(file.upload_date) }}</span>
            </div>
            <button @click="viewFileContent(file)" class="view-btn">
              {{ file.file_type === 'mp4' ? '播放' : '查看' }}
            </button>
          </div>
        </div>

        <!-- 无文件提示 -->
        <div v-else-if="hasLoadedDateFiles && dateFiles.length === 0" class="no-files">
          <p>该日期暂无文件数据</p>
        </div>
      </div>
    </div>

    <!-- JSON文件内容查看对话框 -->
    <div v-if="showFileContentDialog" class="dialog-overlay" @click="closeFileDialog">
      <div class="dialog-content" @click.stop>
        <div class="dialog-header">
          <h3>文件内容</h3>
          <button @click="closeFileDialog" class="close-btn">✕</button>
        </div>
        <div class="dialog-body">
          <pre class="file-content">{{ currentFileContent }}</pre>
        </div>
      </div>
    </div>

    <!-- 视频播放弹窗 -->
    <div v-if="showVideoDialog" class="dialog-overlay" @click="closeVideoDialog">
      <div class="dialog-content video-dialog" @click.stop>
        <div class="dialog-header">
          <h3>视频播放</h3>
          <button @click="closeVideoDialog" class="close-btn">✕</button>
        </div>
        <div class="dialog-body video-body">
          <div class="video-info">
            <p><strong>文件名:</strong> {{ currentVideoInfo?.name }}</p>
            <p><strong>大小:</strong> {{ formatFileSize(currentVideoInfo?.size) }}</p>
          </div>
          <video
            :src="currentVideoUrl"
            controls
            class="video-player"
            autoplay
          >
            您的浏览器不支持视频播放
          </video>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { permissionAPI, warehouseAPI } from '@/services/api'

export default {
  name: 'FindDevice',
  data() {
    return {
      hashCode: '',
      isVerifying: false,
      isVerified: false,
      verifyMessage: '',
      verifyMessageType: '',
      tokenInfo: null,

      // 数据加载相关
      isLoading: false,
      warehouseFiles: [],
      dateFiles: [],
      hasLoadedDateFiles: false,

      // 文件内容查看
      showFileContentDialog: false,
      currentFileContent: '',

      // 视频播放器相关
      showVideoDialog: false,
      currentVideoUrl: '',
      currentVideoInfo: null
    }
  },
  mounted() {
    // 检查是否已有保存的访问码
    const savedToken = sessionStorage.getItem('visitor_access_token')
    if (savedToken) {
      this.hashCode = savedToken
      this.verifyHashCode()
    }
  },
  methods: {
    // 验证哈希码
    async verifyHashCode() {
      if (!this.hashCode.trim()) {
        this.showMessage('请输入访问码', 'error')
        return
      }

      this.isVerifying = true
      this.verifyMessage = ''

      try {
        const response = await permissionAPI.verifyToken(this.hashCode)

        if (response.success && response.valid) {
          this.isVerified = true
          this.tokenInfo = response.token_info

          // 保存到 sessionStorage
          sessionStorage.setItem('visitor_access_token', this.hashCode)
          sessionStorage.setItem('visitor_token_info', JSON.stringify(this.tokenInfo))

          this.showMessage('验证成功!您现在可以访问授权的数据', 'success')

          console.log('✅ 访问权限信息:', this.tokenInfo)
        } else {
          this.showMessage(response.message || '访问码无效或已过期', 'error')
        }
      } catch (error) {
        console.error('❌ 验证失败:', error)
        this.showMessage('验证失败,请检查访问码是否正确', 'error')
      } finally {
        this.isVerifying = false
      }
    },

    // 清除访问权限
    clearAccess() {
      this.isVerified = false
      this.tokenInfo = null
      this.hashCode = ''
      this.warehouseFiles = []
      this.dateFiles = []
      this.hasLoadedDateFiles = false

      sessionStorage.removeItem('visitor_access_token')
      sessionStorage.removeItem('visitor_token_info')

      this.showMessage('已清除访问权限', 'info')
    },

    // 加载仓库文件
    async loadWarehouseFiles() {
      if (!this.tokenInfo) return

      this.isLoading = true
      try {
        const warehouseId = this.tokenInfo.access_value
        const response = await warehouseAPI.getWarehouseFiles(warehouseId, {
          eid: this.tokenInfo.eid
        })

        if (response.data.success) {
          this.warehouseFiles = response.data.files
          this.showMessage(`成功加载 ${this.warehouseFiles.length} 个文件`, 'success')
          console.log('📦 仓库文件:', this.warehouseFiles)
        } else {
          this.showMessage('加载文件失败', 'error')
        }
      } catch (error) {
        console.error('❌ 加载文件失败:', error)
        this.showMessage('加载文件失败', 'error')
      } finally {
        this.isLoading = false
      }
    },

    // 加载指定日期的文件
    async loadDateFiles() {
      if (!this.tokenInfo || !this.hashCode) return

      this.isLoading = true
      this.hasLoadedDateFiles = false

      try {
        const response = await permissionAPI.getFilesByDate(this.hashCode)

        if (response.data.success) {
          this.dateFiles = response.data.files
          this.hasLoadedDateFiles = true

          if (this.dateFiles.length > 0) {
            this.showMessage(`成功加载 ${this.dateFiles.length} 个文件`, 'success')
            console.log('📦 日期文件:', this.dateFiles)
          } else {
            this.showMessage('该日期暂无文件数据', 'info')
          }
        } else {
          this.showMessage(response.data.message || '加载文件失败', 'error')
        }
      } catch (error) {
        console.error('❌ 加载日期文件失败:', error)
        this.showMessage('加载文件失败,请稍后重试', 'error')
      } finally {
        this.isLoading = false
      }
    },

    // 🔧 修复：查看文件内容
    async viewFileContent(file) {
      try {
        console.log('准备查看文件:', file)

        const response = await warehouseAPI.getFileContent(file.id, {
          eid: this.tokenInfo.eid
        })

        console.log('文件内容响应:', response.data)

        if (response.data.success) {
          const fileType = response.data.file_type

          // ⭐ 处理 MP4 视频文件 - 使用弹窗播放
          if (fileType === 'mp4') {
            const fileInfo = response.data.file_info
            const streamUrl = response.data.stream_url

            if (streamUrl) {
              console.log('准备播放视频:', fileInfo.name)
              // 使用弹窗播放
              this.showVideoPlayer(streamUrl, fileInfo)
              this.showMessage(`视频加载成功: ${fileInfo.name}`, 'success')
            } else {
              this.showMessage('视频播放地址不可用', 'error')
            }
            return
          }

          // ⭐ 处理 JSON 文件
          if (fileType === 'json') {
            this.currentFileContent = JSON.stringify(response.data.content, null, 2)
            this.showFileContentDialog = true
            return
          }

          // 未知文件类型
          this.showMessage(`未知的文件类型: ${fileType}`, 'warning')

        } else {
          // 处理错误响应
          let errorMsg = response.data.message || '无法加载文件内容'

          if (response.data.file_type_mismatch) {
            errorMsg = `文件类型不匹配\n\n${response.data.message}`

            if (response.data.actual_type === 'mp4') {
              errorMsg += '\n\n 这是一个视频文件,请使用视频播放功能'
            }

            if (response.data.suggestion) {
              errorMsg += `\n\n建议: ${response.data.suggestion}`
            }
          }

          this.showMessage(errorMsg, 'error')
        }

      } catch (error) {
        console.error('❌ 加载文件内容失败:', error)

        const errorData = error.response?.data
        let errorMsg = '加载文件内容失败'

        if (errorData) {
          console.log('错误详情:', errorData)

          if (errorData.file_type_mismatch) {
            errorMsg = `文件类型错误\n\n${errorData.message || ''}`

            if (errorData.actual_type === 'mp4') {
              errorMsg += '\n\n这是一个MP4视频文件,无法以文本方式查看'
              errorMsg += '\n\n请联系管理员更新文件类型标记'
            }

            if (errorData.suggestion) {
              errorMsg += `\n\n建议: ${errorData.suggestion}`
            }
          } else if (errorData.message) {
            errorMsg = errorData.message
          }
        }

        this.showMessage(errorMsg, 'error')
      }
    },

    // 在弹窗中播放视频
    showVideoPlayer(streamUrl, fileInfo) {
      this.currentVideoUrl = window.location.origin + streamUrl
      this.currentVideoInfo = fileInfo
      this.showVideoDialog = true

      console.log('播放视频:', {
        url: this.currentVideoUrl,
        info: this.currentVideoInfo,
        dialogVisible: this.showVideoDialog
      })
    },

    // 关闭视频对话框
    closeVideoDialog() {
      this.showVideoDialog = false
      this.currentVideoUrl = ''
      this.currentVideoInfo = null
      console.log('🚪 关闭视频弹窗')
    },

    // 关闭文件对话框
    closeFileDialog() {
      this.showFileContentDialog = false
      this.currentFileContent = ''
    },

    // 显示消息
    showMessage(message, type) {
      this.verifyMessage = message
      this.verifyMessageType = type

      setTimeout(() => {
        this.verifyMessage = ''
      }, 5000)
    },

    // 获取权限类型文本
    getAccessTypeText(type) {
      return type === 'warehouse' ? '仓库访问' : '时间段访问'
    },

    // 格式化日期
    formatDate(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN')
    },

    // 格式化文件大小
    formatFileSize(bytes) {
      if (!bytes || bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
.find-device-container {
  margin-top: 20px;
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1200px;
}

/* 哈希码兑换面板 */
.hash-code-panel {
  padding: 20px;
  border: 2px solid #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
  border-radius: 8px;
  background: linear-gradient(135deg, #ffffff 0%, #f0f8ff 100%);
}

.panel-title {
  margin: 0 0 15px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 输入组 */
.input-group {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.hash-input {
  flex: 1;
  padding: 12px 15px;
  border: 2px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.3s;
}

.hash-input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

.hash-input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.verify-btn,
.clear-btn,
.load-btn,
.view-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.verify-btn {
  background: #1890ff;
  color: white;
}

.verify-btn:hover:not(:disabled) {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(24, 144, 255, 0.3);
}

.verify-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.clear-btn {
  background: #ff4d4f;
  color: white;
}

.clear-btn:hover {
  background: #ff7875;
}

/* 消息提示 */
.message {
  padding: 12px 15px;
  border-radius: 6px;
  margin-top: 10px;
  font-size: 14px;
  white-space: pre-line;
}

.message.success {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
}

.message.error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
}

.message.info {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #1890ff;
}

.message.warning {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #faad14;
}

/* 访问信息 */
.access-info {
  margin-top: 20px;
  padding: 15px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
}

.info-item {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  width: 120px;
  color: #8c8c8c;
  font-weight: 500;
}

.info-item .value {
  flex: 1;
  color: #262626;
}

/* 数据访问面板 */
.data-access-panel {
  padding: 20px;
  border: 1px solid #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: white;
}

.data-access-panel h4 {
  margin: 15px 0;
  color: #262626;
}

.access-desc {
  color: #8c8c8c;
  margin: 10px 0;
}

.load-btn {
  background: var(--color-primary-dark);
  color: white;
  margin: 15px 0;
}

.load-btn:hover:not(:disabled) {
  background: rgba(8, 124, 238, 0.75);
}

.load-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

/* 文件列表 */
.file-list {
  margin-top: 15px;
}

.list-header {
  padding: 10px 15px;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
  border: 1px solid #e8e8e8;
  border-bottom: none;
  color: #595959;
  font-size: 13px;
  font-weight: 500;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border: 1px solid #e8e8e8;
  border-top: none;
  transition: all 0.3s;
}

.file-item:last-child {
  border-radius: 0 0 6px 6px;
}

.file-item:hover {
  background: #fafafa;
  border-color: #1890ff;
}

.file-info {
  display: flex;
  gap: 15px;
  align-items: center;
  flex: 1;
  flex-wrap: wrap;
}

.file-name {
  font-weight: 500;
  color: #262626;
  min-width: 200px;
}

/* 文件类型徽章 */
.file-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.file-type-badge.type-json {
  background: #e6f7ff;
  color: #1890ff;
}

.file-type-badge.type-mp4 {
  background: #fff0f6;
  color: #eb2f96;
}

.file-warehouse {
  color: #1890ff;
  font-size: 13px;
  padding: 2px 8px;
  background: #e6f7ff;
  border-radius: 4px;
}

.file-size,
.file-date {
  color: #8c8c8c;
  font-size: 13px;
}

/* 无文件提示 */
.no-files {
  margin-top: 20px;
  padding: 40px;
  text-align: center;
  color: #8c8c8c;
  background: #fafafa;
  border-radius: 6px;
}

.no-files p {
  margin: 0;
  font-size: 14px;
}

.view-btn {
  background: var(--color-primary-dark);
  color: white;
  padding: 8px 16px;
  font-size: 13px;
  white-space: nowrap;
}

.view-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.4);
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.dialog-content {
  background: white;
  border-radius: 8px;
  width: 80%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e8e8e8;
}

.dialog-header h3 {
  margin: 0;
  color: #262626;
  font-size: 16px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #8c8c8c;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f0f0f0;
  color: #262626;
}

.dialog-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.file-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  color: #262626;
}

/* 视频弹窗 */
.video-dialog {
  max-width: 1000px;
  width: 90%;
}

.video-body {
  padding: 20px;
  background: #000;
}

.video-info {
  background: #fff;
  padding: 10px 15px;
  margin-bottom: 15px;
  border-radius: 4px;
}

.video-info p {
  margin: 5px 0;
  color: #262626;
  font-size: 14px;
}

.video-player {
  width: 100%;
  max-height: 60vh;
  background: #000;
  border-radius: 4px;
  outline: none;
}

/* 响应式 */
@media (max-width: 768px) {
  .find-device-container {
    margin-left: 10px;
    margin-right: 10px;
  }

  .input-group {
    flex-direction: column;
  }

  .file-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }

  .dialog-content {
    width: 95%;
  }

  .video-dialog {
    width: 95%;
  }
}
</style>