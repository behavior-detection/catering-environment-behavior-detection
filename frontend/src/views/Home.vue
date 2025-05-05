<template>
  <div class="home">
    <div class="columns">
      <!-- Left Side: Video Stream -->
      <div class="column is-8">
        <div class="box">
          <h2 class="title is-4">Video Stream</h2>

          <div class="source-selector mb-3">
            <div class="field is-grouped">
              <div class="control is-expanded">
                <div class="select is-fullwidth">
                  <select v-model="selectedSourceId" @change="changeVideoSource">
                    <option value="">Select a video source</option>
                    <option
                      v-for="source in videoSources"
                      :key="source.id"
                      :value="source.id"
                    >
                      {{ source.name }} ({{ source.source_type }})
                    </option>
                  </select>
                </div>
              </div>

              <div class="control">
                <button
                  class="button is-success"
                  :disabled="!selectedSourceId || isProcessing"
                  @click="startDetection"
                >
                  <span class="icon"><i class="fas fa-play"></i></span>
                  <span>Start</span>
                </button>
              </div>

              <div class="control">
                <button
                  class="button is-danger"
                  :disabled="!selectedSourceId || !isProcessing"
                  @click="stopDetection"
                >
                  <span class="icon"><i class="fas fa-stop"></i></span>
                  <span>Stop</span>
                </button>
              </div>
            </div>

            <div v-if="isProcessing" class="mt-2">
              <progress
                class="progress is-success is-small"
                :value="processingProgress"
                max="100"
              ></progress>
              <p class="has-text-right is-size-7">
                FPS: {{ frameRate }} | Processing: {{ processingProgress }}%
              </p>
            </div>
          </div>

          <div class="video-container">
            <video-stream
              :source-id="selectedSourceId"
              :stream-active="streamActive"
              :processing="isProcessing"
              @stream-status="handleStreamStatus"
            />
          </div>

          <div v-if="streamError" class="notification is-danger mt-3">
            <button class="delete" @click="streamError = null"></button>
            Stream Error: {{ streamError }}
          </div>
        </div>
      </div>

      <!-- Right Side: Violation Snapshots -->
      <div class="column is-4">
        <div class="box violation-panel">
          <h2 class="title is-4">
            Violation Snapshots
            <span v-if="connectingViolationSource" class="is-size-6">
              <i class="fas fa-spinner fa-spin"></i> Connecting...
            </span>
          </h2>

          <div v-if="recentViolations.length === 0" class="notification is-info">
            No violations detected yet. Start detection to monitor for violations.
          </div>

          <div v-else>
            <div
              v-for="violation in recentViolations"
              :key="violation.id"
              class="violation-card card mb-3"
            >
              <header class="card-header">
                <p class="card-header-title">
                  <span
                    class="status-indicator"
                    :class="{
                      'status-active': violation.status === 'detected' || violation.status === 'confirmed',
                      'status-warning': violation.status === 'suspicious',
                      'status-inactive': violation.status === 'false_alarm' || violation.status === 'resolved'
                    }"
                  ></span>
                  {{ formatViolationTime(violation.timestamp) }}
                </p>
                <div class="card-header-icon">
                  <span class="tag" :class="getViolationStatusClass(violation.status)">
                    {{ violation.status }}
                  </span>
                </div>
              </header>

              <div class="card-content">
                <div class="columns is-mobile">
                  <!-- Original snapshot -->
                  <div class="column is-6">
                    <div class="snapshot-container" @click="enlargeSnapshot(violation.snapshot_url)">
                      <img :src="getApiUrl(violation.snapshot_url)" alt="Violation">
                      <div class="snapshot-overlay">
                        <span class="icon is-large">
                          <i class="fas fa-search-plus fa-2x"></i>
                        </span>
                      </div>
                    </div>
                    <p class="has-text-centered is-size-7">Original</p>
                  </div>

                  <!-- Zoomed snapshot -->
                  <div class="column is-6">
                    <div class="snapshot-container" @click="enlargeSnapshot(violation.zoomed_snapshot_url)">
                      <img
                        :src="getApiUrl(violation.zoomed_snapshot_url)"
                        alt="Zoomed Violation"
                      >
                      <div class="snapshot-overlay">
                        <span class="icon is-large">
                          <i class="fas fa-search-plus fa-2x"></i>
                        </span>
                      </div>
                    </div>
                    <p class="has-text-centered is-size-7">Zoomed</p>
                  </div>
                </div>

                <div class="content">
                  <p>
                    <strong>Confidence:</strong> {{ Math.round(violation.confidence * 100) }}%
                    <br>
                    <strong>Source:</strong> {{ getSourceName(violation.source_id) }}
                  </p>

                  <div class="field is-grouped">
                    <div class="control">
                      <button
                        class="button is-small"
                        :class="{ 'is-info': violation.status !== 'confirmed' }"
                        @click="updateViolationStatus(violation.id, 'confirmed')"
                      >
                        <span class="icon is-small"><i class="fas fa-check"></i></span>
                        <span>Confirm</span>
                      </button>
                    </div>

                    <div class="control">
                      <button
                        class="button is-small"
                        :class="{ 'is-warning': violation.status !== 'false_alarm' }"
                        @click="updateViolationStatus(violation.id, 'false_alarm')"
                      >
                        <span class="icon is-small"><i class="fas fa-times"></i></span>
                        <span>False</span>
                      </button>
                    </div>

                    <div class="control">
                      <button
                        class="button is-small"
                        :class="{ 'is-success': violation.status !== 'resolved' }"
                        @click="updateViolationStatus(violation.id, 'resolved')"
                      >
                        <span class="icon is-small"><i class="fas fa-check-double"></i></span>
                        <span>Resolved</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal for enlarged snapshots -->
    <div class="modal" :class="{ 'is-active': enlargedSnapshotUrl }">
      <div class="modal-background" @click="enlargedSnapshotUrl = null"></div>
      <div class="modal-content">
        <p class="image">
          <img :src="getApiUrl(enlargedSnapshotUrl)" alt="Enlarged snapshot">
        </p>
      </div>
      <button
        class="modal-close is-large"
        aria-label="close"
        @click="enlargedSnapshotUrl = null"
      ></button>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import VideoStream from '@/components/VideoStream.vue'

export default {
  name: 'Home',

  components: {
    VideoStream
  },

  data() {
    return {
      selectedSourceId: '',
      enlargedSnapshotUrl: null,
      streamError: null
    }
  },

  computed: {
    ...mapGetters({
      videoSources: 'video/allVideoSources',
      isProcessing: 'video/isProcessing',
      processingProgress: 'video/processingProgress',
      recentViolations: 'detection/recentViolations',
      streamActive: 'video/streamActive',
      frameRate: 'video/frameRate',
      connectingViolationSource: 'detection/connectingViolationSource'
    }),

    apiBaseUrl() {
      return this.$store.getters.apiBaseUrl
    }
  },

  created() {
    this.fetchVideoSources()
    this.connectToViolationStream()
  },

  beforeDestroy() {
    this.disconnectVideoStream()
    this.disconnectViolationStream()
  },

  methods: {
    ...mapActions({
      fetchVideoSources: 'video/fetchVideoSources',
      activateVideoSource: 'video/activateVideoSource',
      deactivateVideoSource: 'video/deactivateVideoSource',
      setCurrentSource: 'video/setCurrentSource',
      disconnectVideoStream: 'video/disconnectVideoStream',
      startDetection: 'video/startDetection',
      stopDetection: 'video/stopDetection',
      updateViolationStatus: 'detection/updateViolationStatus',
      connectToViolationStream: 'detection/connectToViolationStream',
      disconnectViolationStream: 'detection/disconnectViolationStream'
    }),

    async changeVideoSource() {
      if (!this.selectedSourceId) {
        this.setCurrentSource(null)
        return
      }

      // Find selected source
      const source = this.videoSources.find(s => s.id == this.selectedSourceId)
      if (source) {
        this.setCurrentSource(source)
      }
    },

    formatViolationTime(timestamp) {
      if (!timestamp) return ''

      const date = new Date(timestamp)
      return date.toLocaleString()
    },

    getViolationStatusClass(status) {
      switch (status) {
        case 'detected':
          return 'is-warning'
        case 'confirmed':
          return 'is-danger'
        case 'false_alarm':
          return 'is-info'
        case 'resolved':
          return 'is-success'
        default:
          return 'is-light'
      }
    },

    enlargeSnapshot(url) {
      if (url) {
        this.enlargedSnapshotUrl = url
      }
    },

    getApiUrl(url) {
      if (!url) return ''

      // If already a full URL, return as is
      if (url.startsWith('http')) {
        return url
      }

      // Remove leading slash if present
      const cleanPath = url.startsWith('/') ? url.slice(1) : url

      // Get the base URL without the /api part
      const baseUrlParts = this.apiBaseUrl.split('/api')
      const baseUrl = baseUrlParts[0]

      return `${baseUrl}/${cleanPath}`
    },

    getSourceName(sourceId) {
      const source = this.videoSources.find(s => s.id == sourceId)
      return source ? source.name : `Source ${sourceId}`
    },

    handleStreamStatus(status) {
      this.streamError = status.error
    }
  }
}
</script>

<style scoped>
.video-container {
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
  height: 480px;
}

.violation-panel {
  max-height: 700px;
  overflow-y: auto;
}

.snapshot-container {
  position: relative;
  height: 120px;
  overflow: hidden;
  background-color: #000;
  border-radius: 4px;
}

.snapshot-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.modal-content .image img {
  max-height: 80vh;
  width: auto;
  margin: 0 auto;
}
</style>
