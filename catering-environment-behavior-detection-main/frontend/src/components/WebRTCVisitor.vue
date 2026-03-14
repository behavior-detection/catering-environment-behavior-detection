<template>
  <div class="webrtc-visitor">
    <!-- Token输入区域 -->
    <div v-if="!tokenVerified" class="token-section">
      <el-input
        v-model="accessToken"
        placeholder="请输入访问令牌(access_token)"
        @keyup.enter="verifyToken"
      >
        <template #append>
          <el-button
            type="primary"
            :loading="loading"
            @click="verifyToken"
          >
            验证并连接
          </el-button>
        </template>
      </el-input>
      <div v-if="errorMessage" style="color: #f56c6c; margin-top: 8px;">
        {{ errorMessage }}
      </div>
    </div>

    <!-- 连接成功后的内容 -->
    <div v-if="tokenVerified">
      <!-- 连接状态 -->
      <el-tag :type="connectionStatusType" size="large">
        {{ connectionStatusText }}
      </el-tag>

      <!-- Token信息卡片 -->
      <el-card style="margin-top: 16px;">
        <template #header>
          <span>访问信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Visitor">{{ visitorName }}</el-descriptions-item>
          <el-descriptions-item label="EID">{{ eid }}</el-descriptions-item>
          <el-descriptions-item label="访问类型">{{ tokenInfo.access_type }}</el-descriptions-item>
          <el-descriptions-item label="批准人">{{ tokenInfo.approved_by }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 在线Manager列表 -->
      <el-card v-if="onlineManagers.length > 0" style="margin-top: 16px;">
        <template #header>
          <span>在线Manager ({{ onlineManagers.length }})</span>
        </template>
        <el-space direction="vertical" style="width: 100%;">
          <div
            v-for="manager in onlineManagers"
            :key="manager.user_id"
            style="display: flex; justify-content: space-between; align-items: center;"
          >
            <div>
              <el-tag type="success" size="small">在线</el-tag>
              <span style="margin-left: 8px;">{{ manager.user_id }}</span>
            </div>
            <el-button
              size="small"
              type="primary"
              :disabled="selectedManager === manager.user_id"
              @click="selectManager(manager.user_id)"
            >
              {{ selectedManager === manager.user_id ? '已选择' : '选择' }}
            </el-button>
          </div>
        </el-space>
      </el-card>

      <!-- 空状态 -->
      <el-empty
        v-else
        description="暂无在线Manager"
        style="margin-top: 16px;"
      />

      <!-- 文件请求 -->
      <el-card v-if="selectedManager" style="margin-top: 16px;">
        <template #header>
          <span>请求文件</span>
        </template>
        <el-input
          v-model="requestFilePath"
          placeholder="输入文件路径，如: warehouse1/data.json"
        >
          <template #append>
            <el-button
              type="success"
              :disabled="!dataChannelOpen || requesting"
              :loading="requesting"
              @click="requestFile"
            >
              {{ requesting ? '请求中...' : '请求文件' }}
            </el-button>
          </template>
        </el-input>
      </el-card>

      <!-- 传输进度 -->
      <el-card v-if="isReceiving" style="margin-top: 16px;">
        <template #header>
          <span>{{ receivingFileName }}</span>
        </template>
        <el-progress
          :percentage="receiveProgress"
          :stroke-width="20"
          :text-inside="true"
        />
        <div style="text-align: center; margin-top: 8px; color: #909399;">
          {{ receivedSize }} / {{ totalSize }}
        </div>
      </el-card>

      <!-- 已下载文件列表 -->
      <el-card v-if="downloadedFiles.length > 0" style="margin-top: 16px;">
        <template #header>
          <span>已下载文件 ({{ downloadedFiles.length }})</span>
        </template>
        <el-table :data="downloadedFiles" style="width: 100%;">
          <el-table-column prop="name" label="文件名" />
          <el-table-column label="大小" width="120">
            <template #default="scope">
              {{ formatSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column label="时间" width="180">
            <template #default="scope">
              {{ scope.row.time }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default>
              <el-tag type="success" size="small">完成</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script>
import VisitorWebRTCClient from '@/services/VisitorWebRTCClient.js'
import { permissionAPI } from '@/services/api.js'

export default {
  name: 'WebRTCVisitor',

  props: {
    // 可选：从父组件传入token
    initialToken: {
      type: String,
      default: ''
    }
  },

  data() {
    return {
      accessToken: this.initialToken,
      tokenVerified: false,
      tokenInfo: {},
      visitorName: '',
      eid: '',

      webrtcClient: null,

      connectionStatus: 'disconnected',
      connectionStatusText: '未连接',

      onlineManagers: [],
      selectedManager: null,

      requestFilePath: '',
      dataChannelOpen: false,
      requesting: false,

      isReceiving: false,
      receivingFileName: '',
      receiveProgress: 0,
      receivedSize: 0,
      totalSize: 0,

      downloadedFiles: [],

      loading: false,
      errorMessage: ''
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
    }
  },

  mounted() {
    // 从URL参数或localStorage获取token
    const urlParams = new URLSearchParams(window.location.search)
    const tokenFromUrl = urlParams.get('access_token')
    const tokenFromStorage = localStorage.getItem('access_token')

    this.accessToken = this.accessToken || tokenFromUrl || tokenFromStorage || ''

    // 如果有token，自动验证
    if (this.accessToken) {
      this.verifyToken()
    }
  },

  beforeUnmount() {
    if (this.webrtcClient) {
      this.webrtcClient.disconnect()
    }
  },

  methods: {
    async verifyToken() {
      if (!this.accessToken.trim()) {
        this.errorMessage = '请输入access_token'
        return
      }

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await permissionAPI.verifyToken(
          this.accessToken,
          this.visitorName || 'visitor_temp',
          this.eid || 'temp_eid'
        )

        if (response.valid) {
          this.tokenVerified = true
          this.tokenInfo = response.token_info
          this.visitorName = response.token_info.visitor_name
          this.eid = response.token_info.eid

          localStorage.setItem('access_token', this.accessToken)

          // 触发事件通知父组件
          this.$emit('token-verified', {
            visitorName: this.visitorName,
            eid: this.eid,
            tokenInfo: this.tokenInfo
          })

          this.connectWebRTC()
        } else {
          this.errorMessage = response.message || 'Token验证失败'
        }
      } catch (error) {
        console.error('验证失败:', error)
        this.errorMessage = '验证失败，请检查网络或token是否正确'
      } finally {
        this.loading = false
      }
    },

    async connectWebRTC() {
      this.connectionStatus = 'connecting'
      this.connectionStatusText = '正在连接...'

      this.webrtcClient = new VisitorWebRTCClient(
        this.visitorName,
        this.eid,
        this.accessToken
      )

      this.setupWebRTCCallbacks()
      this.webrtcClient.connect()
    },

    setupWebRTCCallbacks() {
      this.webrtcClient.onAuthSuccess = () => {
        this.connectionStatus = 'connected'
        this.connectionStatusText = '已连接'
        this.$message?.success('连接成功')
        this.$emit('connected')
      }

      this.webrtcClient.onOnlineManagersUpdate = (managers) => {
        this.onlineManagers = managers
        this.$emit('managers-updated', managers)
      }

      this.webrtcClient.onAccessApproved = (managerId) => {
        this.$message?.success(`Manager ${managerId} 已批准访问`)
        this.$emit('access-approved', managerId)
      }

      this.webrtcClient.onAccessDenied = (managerId) => {
        this.$message?.error(`Manager ${managerId} 拒绝了访问请求`)
        this.requesting = false
        this.$emit('access-denied', managerId)
      }

      this.webrtcClient.onDataChannelOpen = () => {
        this.dataChannelOpen = true
        this.$message?.success('连接建立成功，可以请求文件了')
      }

      this.webrtcClient.onDataChannelClose = () => {
        this.dataChannelOpen = false
      }

      this.webrtcClient.onFileReceiveStart = (metadata) => {
        this.isReceiving = true
        this.receivingFileName = metadata.name
        this.totalSize = this.formatSize(metadata.size)
        this.receiveProgress = 0
        this.requesting = false
        this.$emit('file-receive-start', metadata)
      }

      this.webrtcClient.onFileReceiveProgress = (progress) => {
        this.receiveProgress = progress
        const metadata = this.webrtcClient.receivedFileMetadata
        if (metadata) {
          const receivedBytes = (metadata.size * progress) / 100
          this.receivedSize = this.formatSize(receivedBytes)
        }
      }

      this.webrtcClient.onFileReceiveComplete = (metadata, blob) => {
        this.isReceiving = false
        this.downloadedFiles.push({
          name: metadata.name,
          size: metadata.size,
          time: new Date().toLocaleString()
        })
        this.$message?.success(`文件 ${metadata.name} 下载完成`)
        this.$emit('file-downloaded', { metadata, blob })
      }

      this.webrtcClient.onFileReceiveError = (error) => {
        this.isReceiving = false
        this.requesting = false
        this.$message?.error(`文件接收失败: ${error}`)
      }

      this.webrtcClient.onUserOnline = () => {
        this.webrtcClient.requestOnlineUsers()
      }

      this.webrtcClient.onUserOffline = (data) => {
        if (data.user_id === this.selectedManager) {
          this.selectedManager = null
          this.$message?.warning(`Manager ${data.user_id} 已下线`)
        }
        this.webrtcClient.requestOnlineUsers()
      }

      this.webrtcClient.onError = (error) => {
        this.connectionStatus = 'disconnected'
        this.connectionStatusText = '连接错误'
        this.$message?.error(error)
        this.$emit('error', error)
      }
    },

    selectManager(managerId) {
      this.selectedManager = managerId
      this.$emit('manager-selected', managerId)
    },

    requestFile() {
      if (!this.requestFilePath.trim()) {
        this.$message?.warning('请输入文件路径')
        return
      }

      if (!this.selectedManager) {
        this.$message?.warning('请先选择一个Manager')
        return
      }

      this.requesting = true
      this.webrtcClient.requestFileAccess(
        this.selectedManager,
        'warehouse1',
        this.requestFilePath
      )
    },

    formatSize(bytes) {
      if (typeof bytes === 'string') return bytes
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
.webrtc-visitor {
  /* 无需额外样式，使用UI框架的样式 */
}
</style>