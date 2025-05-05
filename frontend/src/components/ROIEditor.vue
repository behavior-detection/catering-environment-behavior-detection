<template>
  <div class="roi-editor">
    <div class="roi-canvas-container">
      <!-- Background image (snapshot from video source) -->
      <img
        v-if="snapshotUrl"
        :src="snapshotUrl"
        alt="Video snapshot"
        class="roi-background"
        ref="backgroundImage"
        @load="setupCanvas"
      />
      <div v-else class="no-snapshot has-background-dark has-text-centered is-flex is-align-items-center is-justify-content-center">
        <div>
          <span v-if="loading" class="icon is-large">
            <i class="fas fa-spinner fa-pulse fa-3x"></i>
          </span>
          <p v-if="loading">Loading snapshot...</p>
          <p v-else>No snapshot available</p>
        </div>
      </div>

      <!-- Drawing canvas for ROI polygon -->
      <canvas
        ref="roiCanvas"
        class="roi-canvas"
        @mousedown="startDrawing"
        @mousemove="continueDrawing"
        @mouseup="stopDrawing"
        @mouseleave="mouseLeave"
        @touchstart="handleTouchStart"
        @touchmove="handleTouchMove"
        @touchend="handleTouchEnd"
      ></canvas>
    </div>

    <div class="roi-controls mt-3">
      <div class="field is-grouped">
        <div class="control">
          <button class="button is-warning" @click="clearPolygon">
            <span class="icon"><i class="fas fa-trash"></i></span>
            <span>Clear</span>
          </button>
        </div>

        <div class="control">
          <button class="button is-info" @click="refreshSnapshot">
            <span class="icon"><i class="fas fa-sync"></i></span>
            <span>Refresh Snapshot</span>
          </button>
        </div>
      </div>

      <div class="notification is-info is-light mt-3">
        <p><strong>Draw ROI:</strong> Click on the image to place points and create a polygon. The area inside the polygon will be used for detection.</p>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/services/api'

export default {
  name: 'ROIEditor',

  props: {
    sourceId: {
      type: [String, Number],
      required: true
    },
    points: {
      type: Array,
      default: () => []
    }
  },

  data() {
    return {
      snapshotUrl: null,
      loading: false,
      canvasContext: null,
      canvasWidth: 0,
      canvasHeight: 0,
      imageWidth: 0,
      imageHeight: 0,
      drawing: false,
      currentPoints: [],
      hoveredPointIndex: -1,
      selectedPointIndex: -1,
      draggingPoint: false,
      apiBaseUrl: this.$store.getters.apiBaseUrl
    }
  },

  watch: {
    sourceId: {
      handler(newVal) {
        if (newVal) {
          this.getSnapshot()
        } else {
          this.snapshotUrl = null
        }
      },
      immediate: true
    },

    points: {
      handler(newVal) {
        this.currentPoints = JSON.parse(JSON.stringify(newVal || []))
        this.$nextTick(() => {
          this.drawPolygon()
        })
      },
      immediate: true
    }
  },

  mounted() {
    // Set up canvas
    this.setupCanvas()

    // Handle window resize
    window.addEventListener('resize', this.resizeCanvas)
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.resizeCanvas)
  },

  methods: {
    async getSnapshot() {
      if (!this.sourceId) return

      this.loading = true

      try {
        const response = await api.get(
          `${this.apiBaseUrl}/video-sources/${this.sourceId}/snapshot/`,
          { responseType: 'blob' }
        )

        const blob = response.data
        this.snapshotUrl = URL.createObjectURL(blob)
      } catch (error) {
        console.error('Error getting snapshot:', error)
        this.snapshotUrl = null
      } finally {
        this.loading = false
      }
    },

    refreshSnapshot() {
      this.getSnapshot()
    },

    setupCanvas() {
      const canvas = this.$refs.roiCanvas
      if (!canvas) return

      this.canvasContext = canvas.getContext('2d')
      this.resizeCanvas()
    },

    resizeCanvas() {
      const canvas = this.$refs.roiCanvas
      if (!canvas) return

      const container = canvas.parentElement
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight

      this.canvasWidth = canvas.width
      this.canvasHeight = canvas.height

      this.updateImageDimensions()
      this.drawPolygon()
    },

    updateImageDimensions() {
      const img = this.$refs.backgroundImage
      if (!img) return

      const rect = img.getBoundingClientRect()
      this.imageWidth = rect.width
      this.imageHeight = rect.height
    },

    drawPolygon() {
      if (!this.canvasContext) return

      // Clear canvas
      this.canvasContext.clearRect(0, 0, this.canvasWidth, this.canvasHeight)

      if (this.currentPoints.length === 0) return

      // Convert normalized points to canvas coordinates
      const canvasPoints = this.currentPoints.map(point => this.normalizedToCanvas(point))

      // Draw polygon
      this.canvasContext.beginPath()
      this.canvasContext.moveTo(canvasPoints[0][0], canvasPoints[0][1])

      for (let i = 1; i < canvasPoints.length; i++) {
        this.canvasContext.lineTo(canvasPoints[i][0], canvasPoints[i][1])
      }

      // Close the path if we have at least 3 points
      if (canvasPoints.length >= 3) {
        this.canvasContext.closePath()
      }

      // Fill polygon with semi-transparent color
      this.canvasContext.fillStyle = 'rgba(0, 128, 255, 0.2)'
      this.canvasContext.fill()

      // Stroke polygon
      this.canvasContext.strokeStyle = 'rgba(0, 128, 255, 0.8)'
      this.canvasContext.lineWidth = 2
      this.canvasContext.stroke()

      // Draw points
      canvasPoints.forEach((point, index) => {
        this.canvasContext.beginPath()

        // Different style for hovered or selected point
        if (index === this.hoveredPointIndex || index === this.selectedPointIndex) {
          this.canvasContext.fillStyle = 'rgba(255, 128, 0, 0.8)'
          this.canvasContext.arc(point[0], point[1], 6, 0, Math.PI * 2)
        } else {
          this.canvasContext.fillStyle = 'rgba(0, 128, 255, 0.8)'
          this.canvasContext.arc(point[0], point[1], 4, 0, Math.PI * 2)
        }

        this.canvasContext.fill()
      })
    },

    // Convert normalized coordinates [0-1] to canvas coordinates
    normalizedToCanvas(point) {
      return [
        point[0] * this.imageWidth,
        point[1] * this.imageHeight
      ]
    },

    // Convert canvas coordinates to normalized coordinates [0-1]
    canvasToNormalized(point) {
      return [
        point[0] / this.imageWidth,
        point[1] / this.imageHeight
      ]
    },

    // Get canvas coordinates from mouse/touch event
    getEventCoordinates(event) {
      const canvas = this.$refs.roiCanvas
      if (!canvas) return [0, 0]

      const rect = canvas.getBoundingClientRect()

      let clientX, clientY

      if (event.touches) {
        // Touch event
        clientX = event.touches[0].clientX
        clientY = event.touches[0].clientY
      } else {
        // Mouse event
        clientX = event.clientX
        clientY = event.clientY
      }

      return [
        clientX - rect.left,
        clientY - rect.top
      ]
    },

    // Find if mouse is over a point
    findHoveredPoint(canvasX, canvasY) {
      if (this.currentPoints.length === 0) return -1

      // Convert normalized points to canvas coordinates
      const canvasPoints = this.currentPoints.map(point => this.normalizedToCanvas(point))

      // Find if we're hovering over a point
      for (let i = canvasPoints.length - 1; i >= 0; i--) {
        const dx = canvasPoints[i][0] - canvasX
        const dy = canvasPoints[i][1] - canvasY
        const distance = Math.sqrt(dx * dx + dy * dy)

        if (distance <= 10) { // 10px radius for hover detection
          return i
        }
      }

      return -1
    },

    startDrawing(event) {
      this.drawing = true

      const [canvasX, canvasY] = this.getEventCoordinates(event)

      // Check if we're clicking on an existing point
      const hoveredPointIndex = this.findHoveredPoint(canvasX, canvasY)

      if (hoveredPointIndex !== -1) {
        // Select the point for dragging
        this.selectedPointIndex = hoveredPointIndex
        this.draggingPoint = true
      } else {
        // Add a new point
        const normalizedPoint = this.canvasToNormalized([canvasX, canvasY])
        this.currentPoints.push(normalizedPoint)
        this.emitPointsUpdate()
        this.drawPolygon()
      }
    },

    continueDrawing(event) {
      if (!this.drawing) {
        // Just update hovered point
        const [canvasX, canvasY] = this.getEventCoordinates(event)
        const hoveredIndex = this.findHoveredPoint(canvasX, canvasY)

        if (hoveredIndex !== this.hoveredPointIndex) {
          this.hoveredPointIndex = hoveredIndex
          this.drawPolygon()
        }
        return
      }

      if (this.draggingPoint && this.selectedPointIndex !== -1) {
        // Drag the selected point
        const [canvasX, canvasY] = this.getEventCoordinates(event)
        const normalizedPoint = this.canvasToNormalized([canvasX, canvasY])

        // Update the point
        this.currentPoints[this.selectedPointIndex] = normalizedPoint
        this.emitPointsUpdate()
        this.drawPolygon()
      }
    },

    stopDrawing() {
      this.drawing = false
      this.draggingPoint = false
      this.selectedPointIndex = -1
    },

    mouseLeave() {
      this.hoveredPointIndex = -1
      this.drawPolygon()

      if (this.drawing) {
        this.stopDrawing()
      }
    },

    // Touch event handlers
    handleTouchStart(event) {
      event.preventDefault()
      this.startDrawing(event)
    },

    handleTouchMove(event) {
      event.preventDefault()
      this.continueDrawing(event)
    },

    handleTouchEnd(event) {
      event.preventDefault()
      this.stopDrawing()
    },

    clearPolygon() {
      this.currentPoints = []
      this.emitPointsUpdate()
      this.drawPolygon()
    },

    emitPointsUpdate() {
      this.$emit('update-points', this.currentPoints)
    }
  }
}
</script>

<style scoped>
.roi-editor {
  width: 100%;
  height: 100%;
}

.roi-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
}

.roi-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.roi-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.no-snapshot {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  color: white;
}
</style>
