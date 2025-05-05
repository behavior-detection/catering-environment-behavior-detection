<template>
  <div class="video-stream">
    <div class="video-container">
      <!-- Video display area -->
      <img
        v-if="currentFrame"
        :src="`data:image/jpeg;base64,${currentFrame}`"
        alt="Video stream"
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
        v-if="currentFrame"
      ></canvas>
    </div>

    <!-- Stream controls -->
    <div class="stream-controls mt-2">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <div class="field has-addons">
              <p class="control">
                <button
                  class="button"
                  :class="{ 'is-success': streamActive, 'is-danger': !streamActive }"
                  :disabled="!sourceId"
                  @click="toggleConnect"
                >
                  <span class="icon">
                    <i :class="streamActive ? 'fas fa-video' : 'fas fa-video-slash'"></i>
                  </span>
                  <span>{{ streamActive ? 'Connected' : 'Disconnected' }}</span>
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

        <div class="level-right">
          <div class="level-item">
            <div class="tags has-addons">
              <span class="tag is-dark">FPS</span>
              <span class="tag is-info">{{ fps.toFixed(1) }}</span>
            </div>
          </div>

          <div class="level-item">
            <div class="tags has-addons">
              <span class="tag is-dark">Detections</span>
              <span class="tag is-primary">{{ detectionCount }}</span>
            </div>
          </div>

          <div class="level-item" v-if="processing">
            <div class="tags has-addons">
              <span class="tag is-dark">Processing</span>
              <span class="tag is-success">{{ processingProgress }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
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
      canvasHeight: 0
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
        if (newVal && this.streamActive) {
          this.connectToStream(newVal)
        }
      }
    },

    streamActive(newVal, oldVal) {
      if (newVal !== oldVal) {
        if (newVal && this.sourceId) {
          this.connectToStream(this.sourceId)
        } else if (!newVal) {
          this.disconnectFromStream()
        }
      }
    },

    currentFrame() {
      this.$nextTick(() => {
        this.drawDetections()
      })
    }
  },

  mounted() {
    // Set up canvas for drawing detections
    this.setupCanvas()

    // Connect to stream if sourceId is provided
    if (this.sourceId && this.streamActive) {
      this.connectToStream(this.sourceId)
    }
  },

  beforeDestroy() {
    this.disconnectFromStream()
  },

  methods: {
    ...mapActions({
      connectToVideoStream: 'video/connectToVideoStream',
      disconnectVideoStream: 'video/disconnectVideoStream',
      sendWebSocketCommand: 'video/sendWebSocketCommand',
      updateCurrentFrame: 'video/updateCurrentFrame',
      updateFrameDetections: 'video/updateFrameDetections'
    }),

    setupCanvas() {
      const canvas = this.$refs.detectionCanvas
      if (canvas) {
        this.canvasContext = canvas.getContext('2d')
        this.resizeCanvas()

        // Resize canvas when window is resized
        window.addEventListener('resize', this.resizeCanvas)
      }
    },

    resizeCanvas() {
      const canvas = this.$refs.detectionCanvas
      if (!canvas) return

      const container = canvas.parentElement
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight

      this.canvasWidth = canvas.width
      this.canvasHeight = canvas.height
    },

    connectToStream(sourceId) {
      this.connecting = true
      this.errorMessage = ''

      // Connect to WebSocket stream via Vuex
      this.connectToVideoStream(sourceId)

      // Set up frame listener
      this.$store.subscribe((mutation, state) => {
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
          if (state.video.streamActive) {
            this.connecting = false
            this.$emit('stream-status', { connected: true, error: null })
          } else {
            this.$emit('stream-status', { connected: false, error: 'Disconnected' })
          }
        }
      })
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

      // Clear canvas
      if (this.canvasContext && this.canvasWidth > 0) {
        this.canvasContext.clearRect(0, 0, this.canvasWidth, this.canvasHeight)
      }
    },

    handleNewFrame(frameData, timestamp) {
      this.currentFrame = frameData

      // Calculate FPS
      if (this.lastFrameTime) {
        const elapsed = timestamp - this.lastFrameTime
        if (elapsed > 0) {
          const instantFps = 1 / elapsed
          // Smooth FPS calculation with running average
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
      const canvas = this.$refs.detectionCanvas
      if (!canvas || !this.canvasContext) return

      // Clear canvas
      this.canvasContext.clearRect(0, 0, canvas.width, canvas.height)

      // If no frame or detections, exit
      if (!this.currentFrame || this.detections.length === 0) return

      // Get image element to calculate scaling
      const img = canvas.previousElementSibling
      if (!img || !(img instanceof HTMLImageElement)) return

      // Calculate scale factors
      const imgRect = img.getBoundingClientRect()
      const scaleX = canvas.width / imgRect.width
      const scaleY = canvas.height / imgRect.height

      // Set up context styles
      this.canvasContext.lineWidth = 2
      this.canvasContext.font = '14px Arial'
      this.canvasContext.textBaseline = 'top'

      // Draw each detection
      this.detections.forEach(detection => {
        const bbox = detection.bbox
        if (!bbox || bbox.length !== 4) return

        // Scale bounding box to canvas size
        const x = bbox[0] * scaleX
        const y = bbox[1] * scaleY
        const width = (bbox[2] - bbox[0]) * scaleX
        const height = (bbox[3] - bbox[1]) * scaleY

        // Determine color based on detection state
        let color
        if (detection.state) {
          switch (detection.state) {
            case 'tentative':
              color = 'yellow'
              break
            case 'confirmed':
              color = 'lime'
              break
            case 'suspicious':
              color = 'orange'
              break
            case 'violation':
              color = 'red'
              break
            default:
              color = 'lime'
          }
        } else {
          color = 'lime' // Default color
        }

        // Draw bounding box
        this.canvasContext.strokeStyle = color
        this.canvasContext.strokeRect(x, y, width, height)

        // Draw label background
        const label = `${detection.class_name} ${Math.round(detection.confidence * 100)}%`
        const textWidth = this.canvasContext.measureText(label).width

        this.canvasContext.fillStyle = color
        this.canvasContext.globalAlpha = 0.7
        this.canvasContext.fillRect(x, y - 20, textWidth + 10, 20)
        this.canvasContext.globalAlpha = 1

        // Draw label text
        this.canvasContext.fillStyle = 'black'
        this.canvasContext.fillText(label, x + 5, y - 17)

        // Draw track ID if available
        if (detection.track_id !== undefined) {
          const trackText = `ID: ${detection.track_id}`

          this.canvasContext.fillStyle = color
          this.canvasContext.globalAlpha = 0.7
          this.canvasContext.fillRect(x, y + height, textWidth + 10, 20)
          this.canvasContext.globalAlpha = 1

          this.canvasContext.fillStyle = 'black'
          this.canvasContext.fillText(trackText, x + 5, y + height + 3)
        }
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
      // Create a temporary link element
      const link = document.createElement('a')

      // Set the href to the data URL of the current frame
      if (this.currentFrame) {
        link.href = `data:image/jpeg;base64,${this.currentFrame}`

        // Set download attribute with timestamp
        const timestamp = new Date().toISOString().replace(/:/g, '-')
        link.download = `snapshot-${timestamp}.jpg`

        // Append to body, click, and remove
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
