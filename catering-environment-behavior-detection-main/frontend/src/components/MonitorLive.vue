<template>
  <div class="find-device-container">
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

        <!-- ========== JSON文件选择器模态框 ========== -->
        <div v-if="showJsonSelector" class="json-selector-overlay" @click.self="closeJsonSelector">
          <div class="json-selector-modal">
            <div class="modal-header">
              <h3>
                <i class="fas fa-file-code"></i>
                选择要保存的JSON检测数据
              </h3>
              <button @click="closeJsonSelector" class="close-btn">
                <i class="fas fa-times"></i>
              </button>
            </div>

            <div class="modal-body">
              <div class="selector-info">
                <p>本次检测共生成 <strong>{{ jsonFilesCount }}</strong> 个JSON文件</p>
                <p class="hint">
                  <i class="fas fa-info-circle"></i>
                  选择您需要保留的文件，未选择的文件将被自动删除以节省空间
                </p>
              </div>

              <div class="selector-actions">
                <button @click="selectAllJsonFiles" class="action-btn">
                  <i class="fas fa-check-double"></i>
                  {{ selectedJsonFiles.length === detectionJsonFiles.length ? '取消全选' : '全选' }}
                </button>
                <span class="selection-count">
                  已选择: {{ selectedJsonFiles.length }} / {{ detectionJsonFiles.length }}
                </span>
              </div>

              <div v-if="loadingJsonFiles" class="loading-state">
                <i class="fas fa-spinner fa-spin"></i>
                <p>正在加载JSON文件列表...</p>
              </div>

              <div v-else class="json-files-list">
                <div
                  v-for="file in detectionJsonFiles"
                  :key="file.path"
                  class="json-file-item"
                  :class="{ selected: selectedJsonFiles.includes(file.path) }"
                  @click="toggleJsonFileSelection(file)"
                >
                  <div class="file-checkbox">
                    <i
                      class="fas"
                      :class="selectedJsonFiles.includes(file.path) ? 'fa-check-square' : 'fa-square'"
                    ></i>
                  </div>

                  <div class="file-info">
                    <div class="file-name">
                      <i class="fas fa-file-code"></i>
                      {{ getJsonFileDisplayName(file) }}
                    </div>
                    <div class="file-details">
                      <span class="detail-item">
                        <i class="fas fa-exclamation-triangle"></i>
                        违规数: {{ file.total_violations }}
                      </span>
                      <span class="detail-item">
                        <i class="fas fa-database"></i>
                        大小: {{ formatBytes(file.size) }}
                      </span>
                    </div>

                    <!-- 显示检测到的类别数量 -->
                    <div v-if="file.class_numbers" class="class-summary">
                      <span
                        v-for="(count, className) in file.class_numbers"
                        :key="className"
                        v-show="count > 0"
                        class="class-badge"
                      >
                        {{ className }}: {{ count }}
                      </span>
                    </div>
                  </div>

                  <div class="file-actions">
                    <button
                      @click.stop="previewJsonFile(file)"
                      class="preview-btn"
                      title="预览JSON内容"
                    >
                      <i class="fas fa-eye"></i>
                    </button>
                  </div>
                </div>

                <div v-if="detectionJsonFiles.length === 0" class="empty-files">
                  <i class="fas fa-folder-open"></i>
                  <p>没有找到JSON文件</p>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="deleteAllJsonFiles" class="footer-btn delete-all-btn">
                <i class="fas fa-trash-alt"></i>
                全部删除
              </button>
              <button @click="closeJsonSelector" class="footer-btn cancel-btn">
                取消
              </button>
              <button
                @click="saveSelectedJsonFiles"
                class="footer-btn save-btn"
                :disabled="selectedJsonFiles.length === 0"
              >
                <i class="fas fa-save"></i>
                保存选中项 ({{ selectedJsonFiles.length }})
              </button>
            </div>
          </div>
        </div>

        <!-- 消息提示 -->
        <MessageToast
          v-if="toast.show"
          :type="toast.type"
          :text="toast.text"
        />
      </div>
    <div class="control-panel">
      <div class="panel-header">
        <h3>实时监测控制台</h3>
        <div v-if="userInfo.userType === 'visitor'" class="user-badge visitor-badge">
          访问者
        </div>
        <div v-if="userInfo.userType === 'admin'" class="user-badge visitor-badge">
          管理员
        </div>
        <div v-if="userInfo.userType === 'manager'" class="user-badge manager-badge">
          经理
        </div>
      </div>

      <!-- Manager 模式:原有的三步流程 -->
      <template v-if="userInfo.userType === 'manager'">
        <div class="control-row">
          <div class="control-group">
            <label class="control-label">选择仓库</label>
            <select v-model="selectedWarehouseId" class="control-select" @change="onWarehouseChange">
              <option disabled value="">请选择视频仓库</option>
              <option v-for="warehouse in mp4Warehouses" :key="warehouse.id" :value="warehouse.id">
                {{ warehouse.name }} ({{ warehouse.file_count }}个视频)
              </option>
            </select>
          </div>

          <div class="control-group">
            <label class="control-label">选择视频</label>
            <select
              v-model="selectedFileId"
              class="control-select"
              :disabled="!selectedWarehouseId"
              @change="onVideoFileChange"
            >
              <option disabled value="">{{ selectedWarehouseId ? '请选择视频文件' : '请先选择仓库' }}</option>
              <option v-for="file in warehouseFiles" :key="file.id" :value="file.id">
                {{ file.file_name }} ({{ formatFileSize(file.file_size) }})
              </option>
            </select>
          </div>

          <div class="control-group" v-if="selectedSourceId">
            <label class="control-label">当前视频源</label>
            <div class="video-source-info">
              <span class="source-name">{{ currentVideoSource?.name || '未命名' }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Visitor||Admin 模式:只显示视频选择 -->
      <template v-else-if="userInfo.userType === 'visitor'|| userInfo.userType === 'admin'">
        <!-- 访问信息卡片 - 复刻 AI 样式 -->
        <div v-if="visitorTokenInfo" class="visitor-info-card">
          <div class="info-card-header">
            <span>访问令牌已验证</span>
          </div>
          <div class="info-card-body">
            <div class="info-item">
              <span class="info-label">授权类型:</span>
              <span class="info-value">{{ visitorTokenInfo.access_type === 'time' ? '日期范围' : '仓库访问' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">授权范围:</span>
              <span class="info-value">{{ visitorTokenInfo.access_value }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">批准人:</span>
              <span class="info-value">{{ visitorTokenInfo.approved_by }}</span>
            </div>
          </div>
        </div>

        <!-- 视频选择区域 -->
        <div v-if="visitorTokenInfo" class="control-row">
          <div class="control-group">
            <label class="control-label">选择视频</label>
            <select
              v-model="selectedFileId"
              class="control-select"
              @change="onVisitorVideoFileChange"
            >
              <option disabled value="">{{ visitorAuthorizedFiles.length > 0 ? '请选择视频文件' : '暂无可用视频' }}</option>
              <option v-for="file in visitorAuthorizedFiles" :key="file.id" :value="file.id">
                {{ file.file_name }} ({{ formatFileSize(file.file_size) }})
              </option>
            </select>
          </div>

          <div class="control-group" v-if="selectedSourceId">
            <label class="control-label">当前视频源</label>
            <div class="video-source-info visitor-source">
              <span class="source-name">{{ currentVideoSource?.name || '未命名' }}</span>
              <span class="source-type">授权访问</span>
            </div>
          </div>
        </div>

        <!-- 提示信息 - 复刻 AI 样式 -->
        <div v-if="!visitorTokenInfo" class="ai-error">
          <i class="icon">⚠️</i>
          <span>请先在"设备查找"页面验证您的访问令牌</span>
        </div>
        <div v-else-if="visitorAuthorizedFiles.length === 0" class="ai-error">
          <span>当前授权信息并无 MP4 格式视频</span>
        </div>
      </template>

      <!-- 通用控制区域 -->
      <div class="control-row" v-if="selectedSourceId">
        <!-- <div class="control-group">
          <label class="control-label">连接状态</label>
          <button
            :disabled="!selectedSourceId"
            @click="toggleConnect"
            class="control-btn"
            :class="{ 'btn-danger': streamActive, 'btn-primary': !streamActive }"
          >
            {{ streamActive ? '断开连接' : '连接' }}
          </button>
        </div> -->

        <div class="control-group" >
          <label class="control-label">
            <input type="checkbox" v-model="useRoi" class="control-checkbox" />
            启用ROI区域检测
          </label>
          <span v-if="detecting" class="roi-status">
            {{ useRoi ? 'ROI已启用' : '显示全部目标' }}
          </span>
        </div>

        <div class="control-group">
          <label class="control-label">检测控制</label>
          <div class="button-group">
            <button 
              :disabled="!canStartDetection || isStarting || detecting" 
              @click="onStartDetection" 
              class="control-btn btn-success"
            >
              <i v-if="isStarting" class="fas fa-spinner fa-spin"></i>
              {{ isStarting ? '启动中' : '开始检测' }}
            </button>
            <button
              :disabled="!selectedSourceId || (!connected && !detecting)"
              @click="onStopDetection"
              class="control-btn btn-danger"
            >
              停止检测
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isRoiEditing" class="roi-editor-wrapper">
        <roi-editor
          :snapshot-url="snapshotUrl"
          :source-id="selectedSourceId"
          v-model="roiPolygons"
          @change="handleRoiChange"
          @roi-saved="onRoiSaved"
          class="roi-editor-panel"
        />
    </div>

    <div v-show="!isRoiEditing" class="monitor-panel">
        <div class="panel-header">
            <h3>监控画面</h3>
            <div class="status-indicators">
                <span class="status-indicator" :class="{ active: connected }">
                    连接状态: {{ connected ? '已连接' : '未连接' }}
                </span>
                <span class="status-indicator" :class="{ active: detecting }">
                    检测状态: {{ detecting ? '检测中' : '未检测' }}
                </span>
            </div>
        </div>

        <div v-if="selectedSourceId" class="stream-wrapper">
            <video 
                v-show="!detecting && !isStarting && previewUrl" 
                :src="previewUrl" 
                controls 
                class="video-preview"
            ></video>

            <VideoStream 
                v-show="detecting || isStarting || !previewUrl"
                ref="videoStreamComp"
                :key="streamKey"
                :source-id="selectedSourceId" 
                :stream-active="streamActive" 
                @stream-status="onStreamStatus" 
                class="video-stream" 
            />
        </div>

        <div v-else class="empty-state">
            <div class="empty-icon">🎬</div>
            <p>请选择视频文件以开始监控</p>
        </div>
    </div>

    <!-- <div v-show="selectedSourceId && !useRoi" class="monitor-panel">
      <div class="panel-header">
        <h3>监控画面</h3>
        <div class="status-indicators">
          <span class="status-indicator" :class="{ active: connected }">
            连接状态: {{ connected ? '已连接' : '未连接' }}
          </span>
          <span class="status-indicator" :class="{ active: detecting }">
            检测状态: {{ detecting ? '检测中' : '未检测' }}
          </span>
        </div>
      </div>

      <video 
        v-show="!detecting && !isStarting && previewUrl" 
        :src="previewUrl" 
        controls 
        class="video-preview"
      ></video>

      <VideoStream 
        ref="videoStreamComp"
        v-if="selectedSourceId"
        v-show="detecting || isStarting || !previewUrl" 
        :source-id="selectedSourceId" 
        :stream-active="streamActive" 
        @stream-status="onStreamStatus" 
        class="video-stream" 
      />

      <div v-if="!selectedSourceId" class="empty-state">
        <div class="empty-icon">🎬</div>
        <p v-if="userInfo.userType === 'visitor'">
          {{ visitorTokenInfo ? '请选择视频文件以开始监控' : '请先在设备查找页面验证访问令牌' }}
        </p>
        <p v-else>请选择仓库和视频文件以开始监控</p>
      </div>
    </div> -->

    <MessageToast
      v-if="toast.show"
      :type="toast.type"
      :text="toast.text"
    />
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import api from '@/services/api'
import { warehouseAPI, permissionAPI } from '@/services/api'
import VideoStream from './VideoStream.vue'
import ROIEditor from '@/components/ROIEditor.vue'
import MessageToast from '@/components/MessageToast.vue'

export default {
  name: 'MonitorLive',
  components: {
    VideoStream,
    'roi-editor': ROIEditor,
    MessageToast
  },
  data() {
    return {
      userInfo: {
        eid: '',
        name: '',
        userType: ''
      },
      streamKey: 0,
      isStarting: false,
      mp4Warehouses: [],
      selectedWarehouseId: '',
      warehouseFiles: [],
      selectedFileId: '',
      currentVideoSource: null,
      isVisitorMode: false,
      visitorTokenInfo: null,
      visitorInfo: null,
      visitorAuthorizedFiles: [],
      selectedSourceId: '',
      streamActive: false,
      connected: false,
      uploadProgress: 0,
      useRoi: false,
      detecting: false,
      previewUrl: '',
      roiPoints: [],
      isRestarting: false,
      restartReason: '',
      showJsonSelector: false,
      detectionJsonFiles: [],
      selectedJsonFiles: [],
      loadingJsonFiles: false,
      jsonFilesCount: 0,
      toast: {
        show: false,
        type: 'info',
        text: ''
      },
      snapshotUrl: '',       // MUST BE HERE for ROI Editor
      roiPolygons: [],       // MUST BE HERE for v-model
      isRefreshing: false,
      isSaving: false,
    }
  },

  computed: {
    ...mapGetters({ videoSources: 'video/allVideoSources' }),
    isRoiEditing() {
      // 条件：开启了ROI + 已选视频 + 没有在检测 + 没有正在启动
      return this.useRoi &&
             this.selectedSourceId &&
             !this.detecting &&
             !this.isStarting;
    },
    streamActiveStore() {
      return this.$store.state.video?.streamActive
    },
    canStartDetection() {
      if (!this.selectedSourceId || this.isRestarting) return false
      if (this.useRoi) {
        return this.roiPoints.length >= 3 || (this.roiPolygons.length > 0 && this.roiPolygons[0].points.length >= 3)
      }
      return true
    }
  },

  watch: {
    streamActiveStore(val) {
      console.log('[MonitorLive] Vuex streamActive 变更:', val);
      this.connected = !!val;

      this.streamActive = !!val;
    },
    useRoi: {
      handler(newVal, oldVal) {
        if (this.detecting && oldVal !== undefined && newVal !== oldVal && !this.isRestarting) {
          this.restartDetectionForROIStateChange(newVal)
        }
      }
    }
  },

  async mounted() {
    console.log('检查 Store Actions:', Object.keys(this.$store._actions));
    await this.loadUserInfo()
    if (this.userInfo.userType === 'manager') {
      await this.loadMp4Warehouses()
    } else if (this.userInfo.userType === 'visitor' || this.userInfo.userType === 'admin') {
      await this.loadVisitorTokenFromSession()
    }
  },

  methods: {
    ...mapActions({
      fetchVideoSources: 'video/fetchVideoSources',
      setCurrentSource: 'video/setCurrentSource',
      startDetection: 'video/startDetection',
      stopDetection: 'video/stopDetection',
      connectToVideoStream: 'video/connectToVideoStream',
      disconnectVideoStream: 'video/disconnectVideoStream',
      uploadVideoFile: 'video/uploadVideoFile',
      activateVideoSource: 'video/activateVideoSource',
    }),

    clearVideoStreamBuffer() {
      // 尝试调用子组件的方法清理画布
      if (this.$refs.videoStreamComp && typeof this.$refs.videoStreamComp.clearCanvas === 'function') {
        this.$refs.videoStreamComp.clearCanvas();
      }
    },

    async handleRefreshSnapshot() {
      // 容错处理：优先用 currentVideoSource，没有则尝试 selectedSourceId
      const sourceId = this.currentVideoSource?.id || this.selectedSourceId;

      if (!sourceId) return;

      try {
        this.isRefreshing = true;
        // 请求快照，重点是 responseType: 'blob'
        const res = await api.get(`/api/detection/video-sources/${sourceId}/snapshot/?t=${Date.now()}`, {
          responseType: 'blob'
        });

        // 释放旧内存
        if (this.snapshotUrl && this.snapshotUrl.startsWith('blob:')) {
          URL.revokeObjectURL(this.snapshotUrl);
        }

        // 生成图片地址
        this.snapshotUrl = URL.createObjectURL(res.data);
        console.log('快照加载成功:', this.snapshotUrl);

      } catch (error) {
        console.error('获取快照失败:', error);
      } finally {
        this.isRefreshing = false;
      }
    },

    async fetchDetectionJsonFiles() {
      if (!this.selectedSourceId) {
        console.log('[JSON] ⚠️ No source ID, skipping fetch')
        return
      }

      this.loadingJsonFiles = true
      console.log('[JSON] 📡 正在获取 source', this.selectedSourceId, '的JSON文件...')

      try {
        const response = await api.get(`/api/detection/json-files/${this.selectedSourceId}/`)
        console.log('[JSON] 📥 API响应:', response.data)

        if (response.data.success) {
          this.detectionJsonFiles = response.data.files || []
          this.jsonFilesCount = response.data.total_count || 0

          console.log('[JSON] ✅ 成功获取', this.jsonFilesCount, '个文件')
          console.log('[JSON] 📄 文件列表:', this.detectionJsonFiles)

          if (this.jsonFilesCount > 0) {
            // ✅ 强制显示模态框
            this.showJsonSelector = true
            this.selectedJsonFiles = this.detectionJsonFiles.map(f => f.path)

            console.log('[JSON] 🎯 显示选择器模态框')
            this.showToast('success', `检测生成了 ${this.jsonFilesCount} 个JSON文件,请选择要保存的文件`)
          } else {
            console.log('[JSON] ℹ️ 没有生成JSON文件')
            this.showToast('info', '本次检测未生成JSON文件')
          }
        } else {
          console.log('[JSON] ⚠️ API返回失败:', response.data.message)
          this.showToast('warning', response.data.message || '未找到JSON文件')
        }
      } catch (error) {
        console.error('[JSON] ❌ 获取JSON文件失败:', error)

        if (error.response) {
          console.error('[JSON] 错误详情:', {
            status: error.response.status,
            data: error.response.data
          })
          this.showToast('error', `获取JSON文件失败: ${error.response.status}`)
        } else {
          this.showToast('error', '获取JSON文件列表失败: ' + error.message)
        }
      } finally {
        this.loadingJsonFiles = false
        console.log('[JSON] 🏁 获取流程结束')
      }
    },

    toggleJsonFileSelection(file) {
      const index = this.selectedJsonFiles.indexOf(file.path)
      if (index > -1) {
        this.selectedJsonFiles.splice(index, 1)
      } else {
        this.selectedJsonFiles.push(file.path)
      }
    },

    selectAllJsonFiles() {
      if (this.selectedJsonFiles.length === this.detectionJsonFiles.length) {
        this.selectedJsonFiles = []
      } else {
        this.selectedJsonFiles = this.detectionJsonFiles.map(f => f.path)
      }
    },

    async saveSelectedJsonFiles() {
      if (this.selectedJsonFiles.length === 0) {
        this.showToast('warning', '请至少选择一个JSON文件')
        return
      }

      try {
        const response = await api.post(
          `/api/detection/json-files/${this.selectedSourceId}/save/`,
          { selected_files: this.selectedJsonFiles }
        )
        console.log('[JSON] 保存结果:', response.data)

        if (response.data.success) {
          this.showToast('success', `已保存 ${response.data.kept_count} 个文件,删除 ${response.data.deleted_count} 个文件`)
          this.closeJsonSelector()
        } else {
          this.showToast('error', '保存失败: ' + response.data.error)
        }
      } catch (error) {
        console.error('[JSON] 保存JSON文件失败:', error)
        this.showToast('error', '保存失败: ' + error.message)
      }
    },

    async deleteAllJsonFiles() {
      if (!confirm('确定要删除所有JSON文件吗?此操作不可恢复!')) {
        return
      }

      try {
        const response = await api.post(`/api/detection/json-files/${this.selectedSourceId}/delete-all/`)
        if (response.data.success) {
          this.showToast('success', `已删除 ${response.data.deleted_count} 个文件`)
          this.closeJsonSelector()
        }
      } catch (error) {
        console.error('[JSON] 删除所有JSON文件失败:', error)
        this.showToast('error', '删除失败: ' + error.message)
      }
    },

    closeJsonSelector() {
      this.showJsonSelector = false
      this.detectionJsonFiles = []
      this.selectedJsonFiles = []
      this.jsonFilesCount = 0
    },

    getJsonFileDisplayName(file) {
      const filename = file.filename
      if (filename.startsWith('ts_')) {
        return `时间戳: ${file.timestamp}`
      } else if (filename.startsWith('frame_')) {
        const frameNum = filename.match(/\d+/)
        return `帧 ${frameNum ? frameNum[0] : 'Unknown'} - ${file.timestamp}`
      }
      return filename
    },

    formatBytes(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    },

    previewJsonFile(file) {
      const content = {
        文件名: file.filename,
        时间戳: file.timestamp,
        总违规数: file.total_violations,
        检测类别数量: file.class_numbers,
        违规详情: file.violations
      }
      const formattedJson = JSON.stringify(content, null, 2)
      const previewWindow = window.open('', '_blank', 'width=600,height=800')
      previewWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>JSON 预览 - ${file.filename}</title>
          <style>
            body { font-family: 'Courier New', monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
            h2 { color: #4ec9b0; margin-bottom: 20px; }
            pre { background: #252526; padding: 20px; border-radius: 8px; overflow-x: auto; border: 1px solid #3e3e42; line-height: 1.6; }
            .close-btn { position: fixed; top: 20px; right: 20px; padding: 10px 20px; background: #0e639c; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .close-btn:hover { background: #1177bb; }
          </style>
        </head>
        <body>
          <button class="close-btn" onclick="window.close()">关闭</button>
          <h2>📄 ${file.filename}</h2>
          <pre>${this.escapeHtml(formattedJson)}</pre>
        </body>
        </html>
      `)
      previewWindow.document.close()
    },

    escapeHtml(text) {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
      return text.replace(/[&<>"']/g, m => map[m])
    },

    async loadUserInfo() {
      try {
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
        console.log('[MonitorLive] 用户信息:', userInfo)
        this.userInfo.userType = userInfo.userType || ''

        if (userInfo.userType === 'manager') {
          this.userInfo.eid = userInfo.eid || ''
          this.userInfo.name = userInfo.name || userInfo.data?.name || ''
        } else if (userInfo.userType === 'visitor' || userInfo.userType === 'admin') {
          this.isVisitorMode = true
          this.userInfo.name = userInfo.name || userInfo.username || ''
          console.log('[MonitorLive] Visitor 模式:', this.userInfo.name)
        }

        if (!this.userInfo.eid && this.userInfo.userType !== 'visitor') {
          this.showToast('error', '未找到用户EID信息')
        }
      } catch (error) {
        console.error('[MonitorLive] 加载用户信息失败:', error)
        this.showToast('error', '加载用户信息失败')
      }
    },

    async loadMp4Warehouses() {
      if (!this.userInfo.eid) {
        console.warn('[MonitorLive] EID为空,无法加载仓库')
        return
      }

      try {
        const response = await warehouseAPI.getWarehouses({ eid: this.userInfo.eid })
        if (response.data.success) {
          this.mp4Warehouses = (response.data.warehouses || []).filter(
            warehouse => warehouse.warehouse_type === 'mp4'
          )
          console.log('[MonitorLive] MP4仓库加载成功:', this.mp4Warehouses.length)
          if (this.mp4Warehouses.length === 0) {
            this.showToast('warning', '未找到视频仓库,请先在设备管理中创建MP4类型的仓库')
          }
        } else {
          this.showToast('error', response.data.message || '加载仓库失败')
        }
      } catch (error) {
        console.error('[MonitorLive] 加载仓库失败:', error)
        this.showToast('error', '加载仓库失败: ' + error.message)
      }
    },

    async loadVisitorTokenFromSession() {
      try {
        const tokenInfoStr = sessionStorage.getItem('visitor_token_info')
        const accessToken = sessionStorage.getItem('visitor_access_token')
        console.log('[MonitorLive] 读取 sessionStorage:', { tokenInfoStr, accessToken })

        if (tokenInfoStr && accessToken) {
          this.visitorTokenInfo = JSON.parse(tokenInfoStr)
          this.visitorInfo = this.visitorTokenInfo
          console.log('[MonitorLive] Visitor token 信息已加载:', this.visitorTokenInfo)
          this.showToast('success', '访问令牌已自动加载')
          await this.loadVisitorAuthorizedFiles(accessToken)
        } else {
          console.log('[MonitorLive] 未找到已验证的访问令牌')
          this.showToast('warning', '请先在设备查找页面验证访问令牌')
        }
      } catch (error) {
        console.error('[MonitorLive] 加载 visitor token 失败:', error)
        this.showToast('error', '加载访问信息失败')
      }
    },

    async loadVisitorAuthorizedFiles(accessToken) {
      try {
        let response
        if (this.visitorTokenInfo.access_type === 'time') {
          response = await permissionAPI.getFilesByDate(accessToken)
        } else if (this.visitorTokenInfo.access_type === 'warehouse') {
          const warehouseId = this.visitorTokenInfo.access_value
          response = await warehouseAPI.getWarehouseFiles(warehouseId, {
            eid: this.visitorTokenInfo.eid
          })
        }
        console.log('[MonitorLive] 授权文件响应:', response.data)

        if (response.data.success) {
          const allFiles = response.data.files || []
          this.visitorAuthorizedFiles = allFiles.filter(
            file => file.file_type === 'mp4' || file.file_name.toLowerCase().endsWith('.mp4')
          )
          console.log(`[MonitorLive] 找到 ${this.visitorAuthorizedFiles.length} 个MP4文件`)
          if (this.visitorAuthorizedFiles.length === 0) {
            this.showToast('warning', '当前授权信息并无 MP4 格式视频')
          } else {
            this.showToast('success', `找到 ${this.visitorAuthorizedFiles.length} 个可访问的视频`)
          }
        } else {
          this.showToast('error', response.data.message || '加载授权文件失败')
        }
      } catch (error) {
        console.error('[MonitorLive] 加载授权文件失败:', error)
        this.showToast('error', '加载文件失败: ' + error.message)
      }
    },

    async onVisitorVideoFileChange() {
      await this.cleanupBeforeSwitch();

      console.log('[MonitorLive] Visitor 视频文件变更:', this.selectedFileId)
      if (!this.selectedFileId) {
        this.selectedSourceId = ''
        this.currentVideoSource = null
        return
      }
      const selectedFile = this.visitorAuthorizedFiles.find(f => f.id === this.selectedFileId)
      if (!selectedFile) {
        this.showToast('error', '未找到选中的文件')
        return
      }
      try {
        await this.createVideoSource(selectedFile)
      } catch (error) {
        console.error('[MonitorLive] 创建视频源失败:', error)
        this.showToast('error', '创建视频源失败: ' + error.message)
      }
    },

    async onWarehouseChange() {
      await this.cleanupBeforeSwitch();

      console.log('[MonitorLive] 仓库变更:', this.selectedWarehouseId)
      this.selectedFileId = ''
      this.warehouseFiles = []
      this.selectedSourceId = ''
      this.currentVideoSource = null
      if (!this.selectedWarehouseId) return

      try {
        const response = await warehouseAPI.getWarehouseFiles(
          this.selectedWarehouseId,
          { eid: this.userInfo.eid }
        )
        if (response.data.success) {
          this.warehouseFiles = (response.data.files || []).filter(
            file => file.file_name.toLowerCase().endsWith('.mp4')
          )
          console.log('[MonitorLive] 仓库文件加载成功:', this.warehouseFiles.length)
          if (this.warehouseFiles.length === 0) {
            this.showToast('warning', '该仓库中没有视频文件')
          }
        } else {
          this.showToast('error', response.data.message || '加载文件列表失败')
        }
      } catch (error) {
        console.error('[MonitorLive] 加载文件列表失败:', error)
        this.showToast('error', '加载文件列表失败: ' + error.message)
      }
    },

    async onVideoFileChange() {
      // 先清理旧环境
      await this.cleanupBeforeSwitch();

      console.log('[MonitorLive] 视频文件变更:', this.selectedFileId)
      if (!this.selectedFileId) {
        this.selectedSourceId = ''
        this.currentVideoSource = null
        return
      }
      const selectedFile = this.warehouseFiles.find(f => f.id === this.selectedFileId)
      if (!selectedFile) {
        this.showToast('error', '未找到选中的文件')
        return
      }
      try {
        await this.createVideoSource(selectedFile)
      } catch (error) {
        console.error('[MonitorLive] 创建视频源失败:', error)
        this.showToast('error', '创建视频源失败: ' + error.message)
      }
    },

    async createVideoSource(fileInfo) {
      try {
        console.log('[MonitorLive] 创建视频源:', fileInfo)
        const sourceName = `${fileInfo.file_name}_${Date.now()}`
        const createResponse = await api.post('api/detection/video-sources/', {
          name: sourceName,
          source_type: 'file',
          source_url: fileInfo.file_path,
          description: `来自文件: ${fileInfo.file_name}`
        })

        if (createResponse.data) {
          this.selectedSourceId = createResponse.data.id
          this.currentVideoSource = createResponse.data

          await this.fetchVideoSources()
          this.setCurrentSource(createResponse.data)
          await this.refreshPreviewUrl()

          await this.handleRefreshSnapshot()

          this.showToast('success', '视频源创建成功')
        }
      } catch (error) {
        console.error('[MonitorLive] 创建视频源失败:', error)
        this.showToast('error', '创建视频源失败: ' + error.message)
      }
    },

    handleRoiChange(polygons) {
        // Sync the polygons to the format expected by validation
        if (polygons && polygons.length > 0) {
            this.roiPoints = polygons[0].points;
            this.roiPolygons = polygons;
        } else {
            this.roiPoints = [];
            this.roiPolygons = [];
        }
    },

    async refreshPreviewUrl() {
      if (!this.selectedSourceId) return
      try {
        const { data } = await api.get(`api/detection/video-sources/${this.selectedSourceId}/`)
        if (data && data.source_url) {
          const mediaRoot = '/media'
          let relPath = data.source_url
          if (relPath.includes('media')) {
            relPath = relPath.split('media').pop()
            if (relPath.startsWith('\\') || relPath.startsWith('/')) {
              relPath = relPath.substring(1)
            }
          }
          relPath = relPath.replace(/\\/g, '/')
          this.previewUrl = `${mediaRoot}/${relPath}`
          console.log('[MonitorLive] 预览URL:', this.previewUrl)
        }
      } catch (err) {
        console.error('[MonitorLive] 刷新预览URL失败:', err)
        this.previewUrl = ''
      }
    },

    exitVisitorMode() {
      if (confirm('确定要退出访问模式吗?')) {
        sessionStorage.removeItem('visitor_access_token')
        sessionStorage.removeItem('visitor_token_info')
        this.isVisitorMode = false
        this.visitorTokenInfo = null
        this.visitorInfo = null
        this.visitorAuthorizedFiles = []
        this.selectedFileId = ''
        this.selectedSourceId = ''
        this.showToast('info', '已退出访问模式')
        setTimeout(() => {
          window.location.reload()
        }, 1000)
      }
    },

    showToast(type, text) {
      this.toast = { show: true, type, text }
      setTimeout(() => {
        this.toast.show = false
      }, 3000)
    },

    setSuccess(message) {
      this.showToast('success', message)
    },

    setError(message) {
      this.showToast('error', message)
    },

    getAccessTypeText(type) {
      return type === 'warehouse' ? '仓库访问' : '时间段访问'
    },

    toggleConnect() {
      if (!this.selectedSourceId) return
      this.streamActive = !this.streamActive
      if (this.streamActive) {
        if (this.currentVideoSource) {
          this.setCurrentSource(this.currentVideoSource)
        }
        this.activateVideoSource(this.selectedSourceId).then(() => {
          this.connectToVideoStream(this.selectedSourceId)
          this.refreshPreviewUrl()
        }).catch(err => {
          this.setError('激活视频源失败')
          this.streamActive = false
        })
      } else {
        this.disconnectVideoStream()
        this.connected = false
      }
    },

    onStreamStatus({ connected }) {
      this.connected = connected
    },

    async restartDetectionForROIStateChange(useRoi) {
      if (this.isRestarting) return
      this.isRestarting = true
      this.restartReason = useRoi ? '启用ROI' : '禁用ROI'
      try {
        this.setSuccess(`${this.restartReason}中,正在重启检测...`)
        await this.stopDetectionAndWait()
        if (useRoi) {
          await this.verifyROIData()
        }
        await this.startDetectionWithState(useRoi)
        this.setSuccess(useRoi ? 'ROI检测已启用' : 'ROI已禁用,显示所有目标')
      } catch (error) {
        this.setError(`重启检测失败: ${error.message}`)
        this.detecting = false
      } finally {
        this.isRestarting = false
        this.restartReason = ''
      }
    },

    async onRoiSaved(roiData) {
      if (!this.selectedSourceId) return;

      this.isSaving = true;

      try {
        // 1. 数据准备
        const pointsToSend = roiData.normalizedPoints || [];
        if (pointsToSend.length < 3) {
            this.showToast('error', 'ROI数据无效，请重新绘制');
            this.isSaving = false;
            return;
        }

        // 2. 提交到后端 (必须 await 确保保存完成)
        const payload = {
          video_source: this.selectedSourceId,
          polygons: [{
            name: roiData.name || 'ROI-Area',
            points: pointsToSend,
            active: true
          }]
        };

        console.log('[ROI] 正在保存 ROI 配置...');
        await api.post('api/detection/roi-polygons/bulk_replace/', payload);
        this.showToast('success', 'ROI 区域已保存');

        // 3. 执行“硬重启”流程
        // 我们不在这里写一堆连接逻辑，而是调用封装好的 restartStream
        this.$nextTick(async () => {
             await this.restartStream(true); // 参数 true 代表启用 ROI
        });

      } catch (error) {
        console.error('[ROI] 保存失败:', error);
        this.showToast('error', '保存 ROI 失败: ' + error.message);
      } finally {
        this.isSaving = false;
      }
    },

    async restartStream(enableRoi) {
        if (this.isStarting) return;

        console.log(`[Flow] 开始重启流 (ROI: ${enableRoi})...`);
        this.isStarting = true;
        this.detecting = true; // 保持界面处于监控模式

        try {
            // 1. 断开旧连接
            if (this.streamActive || this.connected) {
                console.log('📍 [Debug 6] 执行断开旧连接...');
                await this.$store.dispatch('video/sendWebSocketCommand', { command: 'stop_detection' }).catch(e => {});
                await this.disconnectVideoStream();
            }

            // 2. 强制刷新
            this.streamKey++;
            await this.$nextTick();

            // 3. [🔥 关键修改] 延长冷却时间，给后端足够的时间释放资源
            console.log('📍 [Debug] 等待后端冷却 (2.5s)...');
            await new Promise(resolve => setTimeout(resolve, 2500));


            // === 第二阶段：建立新现场 ===

            // 4. 强制重绘 VideoStream 组件
            // 这会销毁旧的 canvas 和 socket 监听器，防止内存泄漏
            this.streamKey++;
            await this.$nextTick();

            // 5. 激活视频源 (API调用)
            console.log('[Flow] 4. 激活视频源...');
            await this.activateVideoSource(this.selectedSourceId);

            // 6. 建立物理连接
            console.log('[Flow] 5. 建立新连接...');
            await this.connectToVideoStream(this.selectedSourceId);

            // 7. [关键] 等待 WebSocket 握手完成
            // 如果连上瞬间就发 start，可能会丢失消息
            await this.waitForConnection(5000);

            // 8. 发送启动指令
            console.log(`[Flow] 6. 发送启动指令 (use_roi: ${enableRoi})...`);
            await this.$store.dispatch('video/startDetection', { use_roi: enableRoi });

            this.useRoi = enableRoi; // 同步 UI 开关状态
            this.setSuccess('检测已重新启动');

        } catch (error) {
            console.error('[Flow] 重启失败:', error);
            this.setError('重启失败: ' + error.message);
            this.detecting = false; // 出错回退到预览页
        } finally {
            this.isStarting = false;
        }
    },

    async stopDetectionAndWait() {
      this.$store.dispatch('video/sendWebSocketCommand', { command: 'stop_detection' })
      await new Promise(resolve => setTimeout(resolve, 3000))
    },

    async verifyROIData() {
      try {
        const roiResponse = await api.get('api/detection/roi-polygons/', {
          params: { video_source: this.selectedSourceId }
        })
        const allRois = Array.isArray(roiResponse.data) ? roiResponse.data : (roiResponse.data.results || [])
        if (allRois.length === 0) {
          throw new Error('未找到ROI区域,请先绘制并保存ROI区域')
        }
        const activeRois = allRois.filter(roi => roi.active)
        if (activeRois.length === 0) {
          throw new Error('未找到活跃的ROI区域,请先绘制并保存ROI区域')
        }
        const roi = activeRois[0]
        if (!roi.points_list || roi.points_list.length < 3) {
          throw new Error('ROI 点数据不足,需要至少3个点')
        }
        return true
      } catch (error) {
        throw new Error(error.message || '验证ROI失败')
      }
    },

    async startDetection({ dispatch, commit, state }, { use_roi } = {}) {
      if (!state.currentSource) return;
      const sourceId = state.currentSource.id;

      console.log(`[Vuex] startDetection 启动... (ROI模式: ${use_roi})`);

      const oldSocket = state.videoSocket;

      // 1. 初始避让 (给 Socket 建立留出时间)
      await new Promise(resolve => setTimeout(resolve, 500));

      const maxRetries = 20;
      const interval = 300;

      for (let i = 0; i < maxRetries; i++) {
          // 🔥 每次循环都获取最新的引用，不要用外部变量
          const currentSocket = state.videoSocket;
          const isConnected = currentSocket && currentSocket.readyState === 1;
          const isNewSocket = oldSocket ? (currentSocket !== oldSocket) : true;

          if (isConnected) {
              const commandPayload = {
                  command: 'start_detection',
                  source_id: sourceId,
                  use_roi: !!use_roi
              };

              // 🔥 [防弹逻辑] 在发送前一毫秒，再次检查 Socket 是否还活着！
              // 防止在 if(isConnected) 判断后，Socket 突然断开 (code 1000)
              if (state.videoSocket && state.videoSocket.readyState === 1) {

                  if (isNewSocket) {
                      console.log(`[Vuex] ✅ 新连接就绪，发送指令 (ROI: ${use_roi})`);
                  } else if (i >= 2) {
                       console.log(`[Vuex] ✅ 复用旧连接，发送指令 (ROI: ${use_roi})`);
                  } else {
                      // 旧连接且时间太短，可能不稳定，继续观察
                      await new Promise(resolve => setTimeout(resolve, interval));
                      continue;
                  }

                  // 只有确认活着，才发送和改变状态
                  dispatch('sendWebSocketCommand', commandPayload);
                  dispatch('setProcessing', true);
                  commit('SET_STREAM_ACTIVE', true); // 使用 commit

                  return; // 成功退出
              } else {
                  console.warn('[Vuex] ⚠️ 准备发送时发现 Socket 已关闭，正在重试...');
              }
          }
          await new Promise(resolve => setTimeout(resolve, interval));
      }

      // ⚠️ 保底重连逻辑
      console.warn('[Vuex] ⚠️ 启动超时或连接断开，尝试强制重连...');
      try {
          // 强制断开再连，确保干净
          await dispatch('disconnectVideoStream');
          await new Promise(resolve => setTimeout(resolve, 500)); // 冷却
          await dispatch('connectToVideoStream', sourceId);

          await new Promise(resolve => setTimeout(resolve, 2000)); // 等待连接

          // 保底发送时的双重检查
          if (state.videoSocket && state.videoSocket.readyState === 1) {
              dispatch('sendWebSocketCommand', {
                  command: 'start_detection',
                  source_id: sourceId,
                  use_roi: !!use_roi
              });
              dispatch('setProcessing', true);
              commit('SET_STREAM_ACTIVE', true);
          } else {
              throw new Error('强制重连后 Socket 依然未就绪');
          }
      } catch (e) {
          console.error('[Vuex] 最终启动失败:', e);
          // 🔥 失败时必须确保状态为 false
          commit('SET_STREAM_ACTIVE', false);
          throw e;
      }
    },

    async onStartDetection() {
      if (!this.selectedSourceId || this.isRestarting) return
      if (this.useRoi && this.roiPoints.length < 3) {
        this.setError('启用了ROI但未找到有效区域,请先绘制并保存ROI区域')
        return
      }
      this.detecting = true
      this.activateAndStartDetection()
    },

    async waitForConnection(timeout = 5000) {
      const start = Date.now();
      // 轮询检查 connected 状态
      while (!this.connected) {
        if (Date.now() - start > timeout) {
            throw new Error('等待 WebSocket 连接超时');
        }
        await new Promise(r => setTimeout(r, 100));
      }
      return true;
    },

    // === 1. 启动检测的流水线 ===
    async activateAndStartDetection() {
      // 1. 基础状态设置
      if (!this.selectedSourceId) return;
      this.isStarting = true;
      this.detecting = true; // 立即设为 true，配合上面的 Template 修改确保显示
      this.previewUrl = ''; 
      
      try {
        console.log('[Flow] 1. 强制刷新组件...');
        this.streamKey++; // 强制 VideoStream 组件重新挂载，清除旧状态
        await this.$nextTick(); // 等待 DOM 更新

        console.log('[Flow] 2. 激活视频源...');
        await this.activateVideoSource(this.selectedSourceId);

        console.log('[Flow] 3. 建立 WebSocket 连接...');
        // 不管之前连没连，直接调用 connect。Vuex 内部会处理去重或重连。
        await this.connectToVideoStream(this.selectedSourceId);
        
        console.log('[Flow] 4. 发送启动指令 (交给 Vuex 智能重试)...');
        await this.$store.dispatch('video/startDetection', { use_roi: this.useRoi });

        this.setSuccess('检测指令已发送');

      } catch (error) {
        console.error('[Flow] 启动失败:', error);
        this.setError('启动失败: ' + error.message);
        // 出错后不要急着把 detecting 设为 false，方便用户看错误日志
        // 只有在明确失败时才断开
        if (error.message.includes('Socket')) {
            this.streamActive = false;
            this.detecting = false; 
        }
      } finally {
        this.isStarting = false;
      }
    },

    // === 2. 停止检测的流水线 ===
    async onStopDetection() {
      if (!this.selectedSourceId) return;

      const currentSourceId = this.selectedSourceId;
      console.log('[Flow] 停止检测...');

      // 1. 立即更新 UI 状态，让用户感觉到停止了
      this.detecting = false; 
      
      // 2. 发送停止指令 (后端会杀掉 Celery 任务)
      this.$store.dispatch('video/sendWebSocketCommand', { command: 'stop_detection' });

      // 3. 等待后端处理 (给一点时间让后端生成最后的 JSON 并释放锁)
      this.setSuccess('正在停止任务并生成报告...');
      await new Promise(resolve => setTimeout(resolve, 2000));

      // 4. 安全检查：防止用户在这2秒内切换了视频
      if (this.selectedSourceId !== currentSourceId) return;

      // 5. 拉取 JSON 文件 (弹出窗口)
      try {
        await this.fetchDetectionJsonFiles();
      } catch (e) {
        console.warn('获取报告失败:', e);
      }

      // 6. 🟢 关键：彻底断开连接，确保单任务
      // 停止后断开 WS，这样下次点击“开始”时会重新走一遍完整的连接流程
      // 这能 100% 保证不会有僵尸任务残留
      if (this.streamActive) {
          console.log('[Flow] 任务结束，断开连接以释放资源');
          await this.disconnectVideoStream();
          this.streamActive = false;
          this.connected = false;
      }
    },

    async cleanupBeforeSwitch() {
      // 1. 如果正在检测，先发指令停止后端任务
      if (this.detecting) {
        console.log('[Switch] 正在停止旧任务...');
        this.$store.dispatch('video/sendWebSocketCommand', { command: 'stop_detection' });
        this.detecting = false;
      }

      // 2. 强制断开 WebSocket 连接 (防止旧画面残留)
      if (this.streamActive || this.connected) {
        console.log('[Switch] 断开旧连接...');
        await this.disconnectVideoStream(); 
        this.streamActive = false;
        this.connected = false;
      }

      // 3. 清空本地状态 (防止旧 ROI/快照 闪现)
      this.snapshotUrl = '';
      this.roiPoints = [];
      this.roiPolygons = [];
      this.previewUrl = '';
      this.showJsonSelector = false; // 关闭可能存在的弹窗
      this.detectionJsonFiles = [];
    },

    async onStopDetection() {
      if (!this.selectedSourceId) return

      // 记录下当前停止的是哪个 Source ID
      const stoppingSourceId = this.selectedSourceId;

      console.log('[JSON] 🛑 停止检测,准备获取JSON文件...')
      
      this.detecting = false;
      this.$store.dispatch('video/sendWebSocketCommand', { command: 'stop_detection' })

      // 等待后端处理
      console.log('[JSON] ⏳ 等待检测完全停止...')
      await new Promise(resolve => setTimeout(resolve, 3000))

      // 如果用户在这 3 秒内切换了视频，就不弹窗了
      if (this.selectedSourceId !== stoppingSourceId) {
          console.log('[JSON] 用户已切换视频源，取消弹出旧任务的JSON窗口');
          return;
      }

      try {
        console.log('[JSON] 📡 开始请求JSON文件列表...')
        await this.fetchDetectionJsonFiles()
      } catch (error) {
        console.error('[JSON] ❌ 获取JSON文件列表失败:', error)
        this.showToast('warning', '无法获取检测数据文件')
      }

      this.setSuccess('检测已停止')
    },

    onRoiPointsUpdate(points) {
      this.roiPoints = Array.isArray(points) ? points : []
    },

    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }
  }
}
</script>

<style scoped>
/* 基础容器 */
.find-device-container {
  margin-top: 20px;
  margin-left: 20px;
  margin-right: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
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

/* AI 错误提示样式 */
.ai-error {
  background: #FDF2F2;
  color: #DC2626;
  padding: 15px 20px;
  border-radius: 8px;
  border-left: 4px solid #EF4444;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.ai-error .icon {
  font-size: 24px;
}

/* 访问信息卡片 */
.visitor-info-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
  overflow: hidden;
  border: 1px solid #e8e8e8;
}

.info-card-header {
  background: #5ba0c3;
  color: white;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.info-card-header .icon {
  font-size: 18px;
}

.info-card-body {
  padding: 15px 20px;
}

.info-item {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  width: 100px;
  color: #8c8c8c;
  font-weight: 500;
  font-size: 14px;
}

.info-value {
  flex: 1;
  color: #262626;
  font-size: 14px;
}

/* 控制面板 */
.control-panel {
  padding: 20px;
  border: 1px solid #cce7ff;
  box-shadow: 0 4px 8px -2px #cce7ff;
  border-radius: 8px;
  background-color: #ffffff;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

/* 用户身份徽章 */
.user-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.manager-badge {
  background: linear-gradient(135deg, #90CAF9 0%, #64B5F6 100%);
  color: white;
}

.visitor-badge {
  background: #5ba0c3;
  color: white;
}

.control-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 15px;
  align-items: flex-end;
}

.control-row:last-child {
  margin-bottom: 0;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 200px;
  flex: 1;
}

.control-label {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-select, .control-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  background-color: #fff;
  transition: border-color 0.3s ease;
}

.control-select:focus, .control-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.control-select:disabled, .control-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
}

/* 视频源信息 */
.video-source-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background-color: #e7f3ff;
  border-radius: 4px;
  border: 1px solid #90caf9;
}

.video-source-info.visitor-source {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-color: #5ba0c3;
}

.source-name {
  font-weight: 500;
  color: #1976d2;
}

.visitor-source .source-name {
  color: #5ba0c3;
}

.source-type {
  font-size: 12px;
  padding: 2px 8px;
  background-color: #1976d2;
  color: white;
  border-radius: 12px;
}

.visitor-source .source-type {
  background-color: #5ba0c3;
}

.control-btn {
  padding: 8px 64px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 80px;
}

.control-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #545b62;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #1e7e34;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #c82333;
}

.button-group {
  display: flex;
  gap: 15px;
}

.control-checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
}

.status-indicators {
  display: flex;
  gap: 15px;
}

.status-indicator {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  background-color: #f8f9fa;
  color: #6c757d;
  transition: all 0.3s ease;
}

.status-indicator.active {
  background-color: #d4edda;
  color: #155724;
}

.roi-status {
  font-size: 12px;
  font-weight: bold;
  color: #007bff;
  background-color: #e7f3ff;
  padding: 2px 6px;
  border-radius: 3px;
}

.roi-editor-panel {
  border: 1px solid #cce7ff;
  box-shadow: 0 4px 8px -2px #cce7ff;
  border-radius: 8px;
  background-color: #ffffff;
}

.monitor-panel {
  padding: 20px;
  border: 1px solid #cce7ff;
  border-radius: 8px;
  background-color: #ffffff;
}

.stream-wrapper {
  position: relative;
  width: 100%;
  max-width: 960px;
  aspect-ratio: 16 / 9;
  background-color: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-preview,
.video-stream {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #6c757d;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
  margin: 0;
}

.icon {
  font-size: 1.1em;
}

@media (max-width: 768px) {
  .find-device-container {
    margin-left: 10px;
    margin-right: 10px;
  }

  .control-row {
    flex-direction: column;
    gap: 15px;
  }

  .control-group {
    min-width: auto;
  }

  .status-indicators {
    flex-direction: column;
    gap: 5px;
  }

  .button-group {
    flex-direction: column;
  }

  .banner-content {
    flex-direction: column;
    align-items: flex-start;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.control-panel,
.monitor-panel,
.roi-editor-panel,
.visitor-info-card {
  animation: fadeIn 0.3s ease-out;
}

/* ========== 新增：JSON选择器样式 ========== */
.json-selector-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

.json-selector-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e8e8e8;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-header h3 i {
  color: #5ba0c3;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.selector-info {
  background: #f0f7ff;
  border-left: 4px solid #5ba0c3;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.selector-info p {
  margin: 8px 0;
  color: #333;
}

.selector-info strong {
  color: #5ba0c3;
  font-weight: 600;
}

.selector-info .hint {
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}

.selector-info .hint i {
  color: #5ba0c3;
}

.selector-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e8e8e8;
}

.action-btn {
  padding: 8px 16px;
  background: #5ba0c3;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #4a8fb0;
  transform: translateY(-1px);
}

.selection-count {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.loading-state i {
  font-size: 32px;
  margin-bottom: 10px;
}

.json-files-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.json-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.json-file-item:hover {
  border-color: #5ba0c3;
  background: #f9fcff;
  transform: translateX(4px);
}

.json-file-item.selected {
  border-color: #5ba0c3;
  background: #f0f7ff;
}

.file-checkbox {
  font-size: 20px;
  color: #999;
}

.json-file-item.selected .file-checkbox {
  color: #5ba0c3;
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name i {
  color: #5ba0c3;
}

.file-details {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #666;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-item i {
  color: #999;
}

.class-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.class-badge {
  padding: 2px 8px;
  background: #e8f4f8;
  color: #5ba0c3;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.preview-btn {
  padding: 6px 12px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}

.preview-btn:hover {
  background: #5ba0c3;
  color: white;
  border-color: #5ba0c3;
}

.empty-files {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-files i {
  font-size: 48px;
  margin-bottom: 10px;
  opacity: 0.5;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 24px;
  border-top: 1px solid #e8e8e8;
  background: #fafafa;
  border-radius: 0 0 12px 12px;
}

.footer-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.delete-all-btn {
  background: #fff;
  color: #dc3545;
  border: 1px solid #dc3545;
  margin-right: auto;
}

.delete-all-btn:hover {
  background: #dc3545;
  color: white;
}

.cancel-btn {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}

.cancel-btn:hover {
  background: #e8e8e8;
}

.save-btn {
  background: #5ba0c3;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #4a8fb0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(91, 160, 195, 0.3);
}

.save-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .json-selector-modal {
    width: 95%;
    max-height: 90vh;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 15px;
  }

  .json-file-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .file-details {
    flex-direction: column;
    gap: 5px;
  }

  .modal-footer {
    flex-wrap: wrap;
  }

  .delete-all-btn {
    width: 100%;
    margin: 0 0 10px 0;
  }

  .roi-editor-wrapper {
    width: 100%;
    height: 600px; /* 给一个固定高度，确保画布够大 */
    margin-bottom: 20px;
    border: 2px dashed #5ba0c3; /* 加个边框区分 */
  }

  .stream-wrapper {
    max-width: 100%;
  }

}
</style>