<template>
  <div class="webrtc-manager">
    <!-- 连接状态和控制 -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <el-tag :type="connectionStatusType" size="large">
        {{ connectionStatusText }}
      </el-tag>
      <el-button
        v-if="!isOnline"
        type="primary"
        @click="connectWebRTC"
      >
        上线
      </el-button>
      <el-button
        v-else
        type="danger"
        @click="disconnect"
      >
        下线
      </el-button>
    </div>

    <!-- Manager信息 -->
    <el-card style="margin-top: 16px;">
      <template #header>
        <span>Manager信息</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="Manager">{{ managerName }}</el-descriptions-item>
        <el-descriptions-item label="EID">{{ eid }}</el-descriptions-item>
        <el-descriptions-item label="在线状态">
          <el-tag :type="isOnline ? 'success' : 'info'" size="small">
            {{ isOnline ? '在线' : '离线' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 文件索引 -->
    <el-card style="margin-top: 16px;">
      <template #header>
        <span>本地文件索引</span>
      </template>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileSelect"
        :file-list="fileList"
        multiple
        accept=".json,.txt,.csv"
      >
        <template #trigger>
          <el-button type="primary">选择文件</el-button>
        </template>
        <el-button
          style="margin-left: 12px;"
          type="success"
          :disabled="selectedFiles.length === 0"
          @click="indexFiles"
        >
          索引 {{ selectedFiles.length }} 个文件
        </el-button>
      </el-upload>
    </el-card>

    <!-- 已索引文件列表 -->
    <el-card v-if="indexedFilesArray.length > 0" style="margin-top: 16px;">
      <template #header>
        <span>已索引文件 ({{ indexedFilesArray.length }})</span>
      </template>
      <el-table :data="indexedFilesArray" style="width: 100%;">
        <el-table-column prop="name" label="文件名" />
        <el-table-column label="大小" width="120">
          <template #default="scope">
            {{ formatSize(scope.row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" />
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button
              type="danger"
              size="small"
              @click="removeFile(scope.row.path)"
            >
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 在线Visitor列表 -->
    <el-card v-if="onlineVisitors.length > 0" style="margin-top: 16px;">
      <template #header>
        <span>在线Visitor ({{ onlineVisitors.length }})</span>
      </template>
      <el-space direction="vertical" style="width: 100%;">
        <div
          v-for="visitor in onlineVisitors"
          :key="visitor.user_id"
          style="display: flex; align-items: center;"
        >
          <el-tag type="success" size="small">在线</el-tag>
          <span style="margin-left: 8px;">{{ visitor.user_id }}</span>
        </div>
      </el-space>
    </el-card>

    <!-- 待处理的访问请求 -->
    <div v-if="pendingRequests.length > 0" style="margin-top: 16px;">
      <el-alert
        v-for="request in pendingRequests"
        :key="request.id"
        type="warning"
        :closable="false"
        style="margin-bottom: 12px;"
      >
        <template #title>
          <strong>{{ request.from_user }}</strong> 请求访问文件
        </template>
        <div style="margin-top: 8px;">
          <p style="margin: 4px 0;"><strong>文件路径:</strong> {{ request.file_path }}</p>
          <p style="margin: 4px 0;"><strong>仓库:</strong> {{ request.warehouse_id }}</p>
        </div>
        <div style="margin-top: 12px;">
          <el-button
            size="small"
            @click="handleAccessRequest(request, false)"
          >
            拒绝
          </el-button>
          <el-button
            size="small"
            type="success"
            @click="handleAccessRequest(request, true)"
          >
            批准
          </el-button>
        </div>
      </el-alert>
    </div>

    <!-- 文件传输进度 -->
    <el-card v-if="isSending" style="margin-top: 16px;">
      <template #header>
        <span>正在发送: {{ sendingFileName }}</span>
      </template>
      <el-progress
        :percentage="sendProgress"
        :stroke-width="20"
        :text-inside="true"
      />
      <div style="text-align: center; margin-top: 8px; color: #909399;">
        发送给: {{ sendingToUser }}
      </div>
    </el-card>

    <!-- 传输历史 -->
    <el-card v-if="transferHistory.length > 0" style="margin-top: 16px;">
      <template #header>
        <span>传输历史</span>
      </template>
      <el-table :data="transferHistory" style="width: 100%;">
        <el-table-column prop="fileName" label="文件名" />
        <el-table-column prop="toUser" label="发送给" width="150" />
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column label="状态" width="100">
          <template #default>
            <el-tag type="success" size="small">完成</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import ManagerWebRTCClient from '@/services/ManagerWebRTCClient.js'

export default {
  name: 'WebRTCManager',

  props: {
    managerName: {
      type: String,
      required: true
    },
    eid: {
      type: String,
      required: true
    },
    autoConnect: {
      type: Boolean,
      default: true
    }
  },

  data() {
    return {
      webrtcClient: null,

      connectionStatus: 'disconnected',
      connectionStatusText: '未连接',
      isOnline: false,

      selectedFiles: [],
      fileList: [],
      indexedFiles: new Map(),

      onlineVisitors: [],
      pendingRequests: [],

      isSending: false,
      sendingFileName: '',
      sendingToUser: '',
      sendProgress: 0,

      transferHistory: []
    }
  },

  computed: {
    connectionStatusType() {
      const typeMap = {
        connected: 'success',
        connecting: 'warning',
        disconnected: 'info'
      }
      return typeMap[this.connectionStatus] || 'info'
    },

    indexedFilesArray() {
      return Array.from(this.indexedFiles.entries()).map(([path, file]) => ({
        path,
        name: file.name,
        size: file.size
      }))
    }
  },

  mounted() {
    if (this.autoConnect) {
      this.connectWebRTC()
    }
  },

  beforeUnmount() {
    if (this.webrtcClient) {
      this.webrtcClient.disconnect()
    }
  },

  methods: {
    connectWebRTC() {
      this.connectionStatus = 'connecting'
      this.connectionStatusText = '正在连接...'

      this.webrtcClient = new ManagerWebRTCClient(
        this.managerName,
        this.eid
      )

      this.setupWebRTCCallbacks()
      this.webrtcClient.connect()
    },

    setupWebRTCCallbacks() {
      this.webrtcClient.onAuthSuccess = () => {
        this.connectionStatus = 'connected'
        this.connectionStatusText = '已上线'
        this.isOnline = true
        this.$message?.success('已上线，可以接收访问请求')
        this.$emit('connected')
      }

      this.webrtcClient.onFileAccessRequest = (data, callback) => {
        const request = {
          id: Date.now(),
          from_user: data.from_user,
          warehouse_id: data.warehouse_id,
          file_path: data.file_path,
          callback: callback
        }

        this.pendingRequests.push(request)

        // 浏览器通知
        if (Notification.permission === 'granted') {
          new Notification('新的文件访问请求', {
            body: `${data.from_user} 请求访问 ${data.file_path}`
          })
        }

        this.$emit('access-request', data)
      }

      this.webrtcClient.onDataChannelOpen = (visitorId) => {
        this.$message?.success(`已建立连接: ${visitorId}`)
        this.$emit('channel-opened', visitorId)
      }

      this.webrtcClient.onSendProgress = (filePath, progress) => {
        this.sendProgress = progress
      }

      this.webrtcClient.onUserOnline = (data) => {
        if (data.user_type === 'visitor') {
          const exists = this.onlineVisitors.find(v => v.user_id === data.user_id)
          if (!exists) {
            this.onlineVisitors.push(data)
          }
        }
        this.$emit('user-online', data)
      }

      this.webrtcClient.onUserOffline = (data) => {
        if (data.user_type === 'visitor') {
          const index = this.onlineVisitors.findIndex(v => v.user_id === data.user_id)
          if (index !== -1) {
            this.onlineVisitors.splice(index, 1)
          }
        }
        this.$emit('user-offline', data)
      }

      this.webrtcClient.onError = (error) => {
        this.connectionStatus = 'disconnected'
        this.connectionStatusText = '连接错误'
        this.isOnline = false
        this.$message?.error(error)
        this.$emit('error', error)
      }
    },

    handleFileSelect(file, fileList) {
      this.selectedFiles = fileList.map(f => f.raw).filter(Boolean)
      this.fileList = fileList
    },

    indexFiles() {
      if (this.selectedFiles.length === 0) {
        this.$message?.warning('请先选择文件')
        return
      }

      const files = this.selectedFiles.map(file => ({
        path: `warehouse1/${file.name}`,
        file: file
      }))

      this.webrtcClient.indexLocalFiles(files)

      files.forEach(item => {
        this.indexedFiles.set(item.path, item.file)
      })

      this.$message?.success(`已索引 ${files.length} 个文件`)
      this.$emit('files-indexed', files)

      // 清空选择
      this.selectedFiles = []
      this.fileList = []
      if (this.$refs.uploadRef) {
        this.$refs.uploadRef.clearFiles()
      }
    },

    removeFile(path) {
      this.indexedFiles.delete(path)
      this.webrtcClient.localFiles.delete(path)
      this.$message?.success('文件已移除')
    },

    handleAccessRequest(request, approved) {
      request.callback(approved)

      const index = this.pendingRequests.findIndex(r => r.id === request.id)
      if (index !== -1) {
        this.pendingRequests.splice(index, 1)
      }

      if (approved) {
        this.$message?.success(`已批准 ${request.from_user} 的访问请求`)
        this.$emit('access-approved', request)

        this.isSending = true
        this.sendingFileName = request.file_path
        this.sendingToUser = request.from_user
        this.sendProgress = 0

        setTimeout(() => {
          this.isSending = false
          this.transferHistory.unshift({
            fileName: request.file_path,
            toUser: request.from_user,
            time: new Date().toLocaleTimeString()
          })

          if (this.transferHistory.length > 10) {
            this.transferHistory = this.transferHistory.slice(0, 10)
          }
        }, 500)
      } else {
        this.$message?.info(`已拒绝 ${request.from_user} 的访问请求`)
        this.$emit('access-denied', request)
      }
    },

    disconnect() {
      if (this.webrtcClient) {
        this.webrtcClient.disconnect()
        this.connectionStatus = 'disconnected'
        this.connectionStatusText = '已下线'
        this.isOnline = false
        this.onlineVisitors = []
        this.$message?.info('已下线')
        this.$emit('disconnected')
      }
    },

    formatSize(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
.webrtc-manager {
  /* 无需额外样式，使用UI框架的样式 */
}
</style>