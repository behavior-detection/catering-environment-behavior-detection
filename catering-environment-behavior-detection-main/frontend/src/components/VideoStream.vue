<template>
  <div class="video-stream">
    <div class="video-container">
      <!-- Video display area -->
      <img
        v-if="currentFrame"
        :src="currentFrame"  alt="Video stream"
        class="video-frame"
      />
      <div
        v-else
        class="no-stream has-background-dark has-text-white has-text-centered is-flex is-align-items-center is-justify-content-center"
      >
        <div>
          <span v-if="connecting" class="icon is-large">
            <i class="fas fa-spinner fa-pulse fa-3x"></i>
          </span>
          <p v-if="connecting">Connecting to stream...</p>
          <p v-else>No video stream available</p>
          <p v-if="errorMessage" class="has-text-danger">{{ errorMessage }}</p>
        </div>
      </div>

      <!-- Detection overlay canvas -->
      <canvas
        ref="detectionCanvas"
        class="detection-overlay"
        v-if="currentFrame && enableOverlay"
      ></canvas>
    </div>

    <!-- Stream controls -->
    <!-- <div class="stream-controls mt-2">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <div class="field has-addons">
              
              <p class="control">
                <button 
                  class="button" 
                  :class="enableOverlay ? 'is-warning' : 'is-light'"
                  @click="enableOverlay = !enableOverlay"
                  title="切换显示检测框"
                >
                  <span class="icon">
                    <i :class="enableOverlay ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
                  </span>
                  <span>Overlay</span>
                </button>
              </p>

              <p class="control">
                <button
                  class="button is-info"
                  :disabled="!streamActive || !sourceId"
                  @click="captureSnapshot"
                >
                  <span class="icon">
                    <i class="fas fa-camera"></i>
                  </span>
                  <span>Snapshot</span>
                </button>
              </p>
            </div>
          </div>
        </div>
        </div>
    </div> -->
  </div>
</template>

<script>
import { mapActions } from 'vuex'

export default {
  name: 'VideoStream',

  props: {
    sourceId: {
      type: [String, Number],
      default: null
    },
    streamActive: {
      type: Boolean,
      default: false
    },
    processing: {
      type: Boolean,
      default: false
    },
    processingProgress: {
      type: Number,
      default: 0
    }
  },

  data() {
    return {
      currentFrame: null,
      detections: [],
      frameCount: 0,
      lastFrameTime: null,
      fps: 0,
      connecting: false,
      errorMessage: '',
      connected: false,
      canvasContext: null,
      canvasWidth: 0,
      canvasHeight: 0,
      enableOverlay: true,
      unsubscribeStore: null // 保存取消订阅函数
    }
  },

  computed: {
    detectionCount() {
      return this.detections.length
    }
  },

  watch: {
    sourceId(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.resetStream()
        // [修复] 移除这里的自动连接，完全由父组件控制
      }
    },

    streamActive(newVal) {
      // [修复] 仅同步状态，绝不主动发起连接
      this.connected = newVal;
      if (!newVal) {
        this.resetStream();
      }
    },

    currentFrame() {
      this.$nextTick(() => {
        this.drawDetections()
      })
    }
  },

  mounted() {
    this.setupCanvas()
    // [关键修复] 无论是否连接，组件挂载时必须立即开始监听 Store
    // 这样父组件建立连接后，组件能立马收到帧
    this.setupStoreListener(); 
    
    // 同步初始状态
    if (this.streamActive) {
        this.connected = true;
    }
  },

  beforeUnmount() {
    // 组件销毁时，只取消监听，不一定断开连接（取决于业务，这里我们选择不主动断开，由父组件决定）
    if (this.unsubscribeStore) {
      this.unsubscribeStore();
    }
    this.resetStream();
  },

  methods: {
    ...mapActions({
      connectToVideoStream: 'video/connectToVideoStream',
      disconnectVideoStream: 'video/disconnectVideoStream',
      sendWebSocketCommand: 'video/sendWebSocketCommand'
    }),

    // [新方法] 独立的 Store 监听逻辑
    setupStoreListener() {
      if (this.unsubscribeStore) {
        this.unsubscribeStore();
      }
      
      this.unsubscribeStore = this.$store.subscribe((mutation, state) => {
        if (mutation.type === 'video/SET_CURRENT_FRAME') {
          this.handleNewFrame(state.video.currentFrame, state.video.lastFrameTime)
        }
        if (mutation.type === 'video/SET_FRAME_DETECTIONS') {
          this.handleDetections(state.video.frameDetections)
        }
        if (mutation.type === 'video/SET_STREAM_ERROR') {
          if (state.video.streamError) {
            this.errorMessage = state.video.streamError
            this.connecting = false
            this.$emit('stream-status', { connected: false, error: state.video.streamError })
          }
        }
        if (mutation.type === 'video/SET_STREAM_ACTIVE') {
          this.connected = state.video.streamActive
          this.connecting = false; // 状态变更意味着连接尝试结束
          
          if (state.video.streamActive) {
            this.$emit('stream-status', { connected: true, error: null })
          } else {
            this.$emit('stream-status', { connected: false, error: 'Disconnected' })
          }
        }
        if (mutation.type === 'video/SET_PROCESSING_COMPLETE') {
            this.$emit('processing-complete', state.video.processingCompleteData)
        }
      })
    },

    clearCanvas() {
      const canvas = this.$refs.detectionCanvas;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      this.currentFrame = null;
    },

    setupCanvas() {
      const canvas = this.$refs.detectionCanvas
      if (canvas) {
        this.canvasContext = canvas.getContext('2d')
        this.resizeCanvas()
        window.addEventListener('resize', this.resizeCanvas)
      }
    },

    resizeCanvas() {
      const canvas = this.$refs.detectionCanvas
      if (!canvas) return
      const container = canvas.parentElement
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight
    },

    // 仅在用户点击按钮时调用，或者父组件显式调用
    async connectToStream(sourceId) {
      if (this.connecting || this.connected) return;
      this.connecting = true;
      this.errorMessage = '';
      
      // 只负责派发 Action
      try {
        await this.connectToVideoStream(sourceId);
      } catch (e) {
        this.connecting = false;
        this.errorMessage = e.message;
      }
    },

    disconnectFromStream() {
      this.disconnectVideoStream()
      this.resetStream()
    },

    resetStream() {
      this.currentFrame = null
      this.detections = []
      this.frameCount = 0
      this.lastFrameTime = null
      this.fps = 0
      this.connecting = false
      this.connected = false
      if (this.canvasContext && this.$refs.detectionCanvas) {
        this.canvasContext.clearRect(0, 0, this.$refs.detectionCanvas.width, this.$refs.detectionCanvas.height)
      }
    },

    handleNewFrame(frameData, timestamp) {
      this.currentFrame = frameData
      if (this.lastFrameTime) {
        const elapsed = timestamp - this.lastFrameTime
        if (elapsed > 0) {
          const instantFps = 1 / elapsed
          this.fps = 0.2 * instantFps + 0.8 * this.fps
        }
      }
      this.lastFrameTime = timestamp
      this.frameCount++
    },

    handleDetections(detections) {
      this.detections = detections || []
    },

    drawDetections() {
      // (保持原有的绘图逻辑不变)
      if (!this.enableOverlay) return
      const canvas = this.$refs.detectionCanvas
      if (!canvas || !this.canvasContext) return
      this.canvasContext.clearRect(0, 0, canvas.width, canvas.height)
      if (!this.currentFrame || this.detections.length === 0) return

      const img = canvas.previousElementSibling
      if (!img || !(img instanceof HTMLImageElement)) return

      const imgRect = img.getBoundingClientRect()
      const scaleX = canvas.width / imgRect.width
      const scaleY = canvas.height / imgRect.height

      this.canvasContext.lineWidth = 2
      this.canvasContext.font = '14px Arial'
      this.canvasContext.textBaseline = 'top'

      this.detections.forEach(detection => {
        const bbox = detection.bbox
        if (!bbox || bbox.length !== 4) return
        const x = bbox[0] * scaleX
        const y = bbox[1] * scaleY
        const width = (bbox[2] - bbox[0]) * scaleX
        const height = (bbox[3] - bbox[1]) * scaleY

        let color = 'lime'
        if (detection.state) {
            if (detection.state === 'violation') color = 'red';
            else if (detection.state === 'suspicious') color = 'orange';
            else if (detection.state === 'tentative') color = 'yellow';
        }

        this.canvasContext.strokeStyle = color
        this.canvasContext.strokeRect(x, y, width, height)

        const label = `${detection.class_name} ${Math.round(detection.confidence * 100)}%`
        const textWidth = this.canvasContext.measureText(label).width

        this.canvasContext.fillStyle = color
        this.canvasContext.globalAlpha = 0.7
        this.canvasContext.fillRect(x, y - 20, textWidth + 10, 20)
        this.canvasContext.globalAlpha = 1
        this.canvasContext.fillStyle = 'white'
        this.canvasContext.fillText(label, x + 5, y - 17)
      })
    },

    toggleConnect() {
      if (this.connected) {
        this.disconnectFromStream()
      } else if (this.sourceId) {
        this.connectToStream(this.sourceId)
      }
    },
    
    captureSnapshot() {
       // (保持原样)
       const link = document.createElement('a')
       if (this.currentFrame) {
         link.href = `data:image/jpeg;base64,${this.currentFrame}`
         const timestamp = new Date().toISOString().replace(/:/g, '-')
         link.download = `snapshot-${timestamp}.jpg`
         document.body.appendChild(link)
         link.click()
         document.body.removeChild(link)
       }
    }
  }
}
</script>

<style scoped>
.video-container {
  position: relative;
  width: 100%;
  height: 100%;
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.no-stream {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.detection-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.stream-controls {
  padding: 0.5rem;
}
</style>
