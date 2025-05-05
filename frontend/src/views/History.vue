<template>
  <div class="history">
    <h1 class="title">Violation History</h1>

    <div class="box">
      <div class="columns">
        <!-- Filters -->
        <div class="column is-3">
          <div class="field">
            <label class="label">Source</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="filterSourceId">
                  <option value="all">All Sources</option>
                  <option
                    v-for="source in videoSources"
                    :key="source.id"
                    :value="source.id"
                  >
                    {{ source.name }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Status</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="filterStatus">
                  <option value="all">All Status</option>
                  <option value="detected">Detected</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="false_alarm">False Alarm</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">Date Range</label>
            <div class="control">
              <input
                v-model="filterStartDate"
                class="input"
                type="date"
                placeholder="Start Date"
              >
            </div>
          </div>

          <div class="field">
            <div class="control">
              <input
                v-model="filterEndDate"
                class="input"
                type="date"
                placeholder="End Date"
              >
            </div>
          </div>

          <div class="field">
            <div class="control">
              <button
                class="button is-primary is-fullwidth"
                @click="applyFilters"
              >
                <span class="icon"><i class="fas fa-filter"></i></span>
                <span>Apply Filters</span>
              </button>
            </div>
          </div>

          <div class="field">
            <div class="control">
              <button
                class="button is-light is-fullwidth"
                @click="resetFilters"
              >
                <span class="icon"><i class="fas fa-times"></i></span>
                <span>Clear Filters</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Violation List -->
        <div class="column is-9">
          <div class="field">
            <label class="label">
              Violation Records
              <span class="tag is-info ml-2">{{ violations.length }}</span>
            </label>
          </div>

          <div v-if="loading" class="has-text-centered p-5">
            <span class="icon is-large">
              <i class="fas fa-spinner fa-pulse fa-2x"></i>
            </span>
            <p>Loading violations...</p>
          </div>

          <div v-else-if="violations.length === 0" class="notification is-info">
            No violations found matching the current filters.
          </div>

          <div v-else class="violation-grid">
            <div
              v-for="violation in violations"
              :key="violation.id"
              class="violation-card card"
            >
              <div class="card-image">
                <figure class="image is-4by3">
                  <img
                    :src="getApiUrl(violation.snapshot_url)"
                    alt="Violation snapshot"
                    @click="enlargeSnapshot(violation)"
                  >
                </figure>
              </div>

              <div class="card-content">
                <div class="content">
                  <p class="is-size-7">
                    <strong>ID:</strong> {{ violation.id }}<br>
                    <strong>Time:</strong> {{ formatDateTime(violation.timestamp) }}<br>
                    <strong>Source:</strong> {{ getSourceName(violation.source_id) }}<br>
                    <strong>Confidence:</strong> {{ Math.round(violation.confidence * 100) }}%
                  </p>

                  <div class="tags">
                    <span class="tag" :class="getViolationStatusClass(violation.status)">
                      {{ violation.status }}
                    </span>
                  </div>
                </div>
              </div>

              <footer class="card-footer">
                <a class="card-footer-item" @click="updateViolationStatus(violation.id, 'confirmed')">
                  <span class="icon"><i class="fas fa-check"></i></span>
                  <span>Confirm</span>
                </a>
                <a class="card-footer-item" @click="updateViolationStatus(violation.id, 'false_alarm')">
                  <span class="icon"><i class="fas fa-times"></i></span>
                  <span>False</span>
                </a>
                <a class="card-footer-item" @click="editNotes(violation)">
                  <span class="icon"><i class="fas fa-comment"></i></span>
                  <span>Notes</span>
                </a>
              </footer>
            </div>
          </div>

          <div class="mt-4 has-text-centered" v-if="hasMoreViolations">
            <button class="button is-primary" @click="loadMoreViolations">
              <span class="icon"><i class="fas fa-plus"></i></span>
              <span>Load More</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal for enlarged snapshot -->
    <div class="modal" :class="{ 'is-active': selectedViolation !== null }">
      <div class="modal-background" @click="selectedViolation = null"></div>
      <div class="modal-content">
        <div class="box">
          <div class="columns">
            <div class="column is-6">
              <figure class="image">
                <img
                  v-if="selectedViolation"
                  :src="getApiUrl(selectedViolation.snapshot_url)"
                  alt="Violation snapshot"
                >
              </figure>
              <p class="has-text-centered mt-2">Original</p>
            </div>

            <div class="column is-6">
              <figure class="image">
                <img
                  v-if="selectedViolation && selectedViolation.zoomed_snapshot_url"
                  :src="getApiUrl(selectedViolation.zoomed_snapshot_url)"
                  alt="Zoomed snapshot"
                >
                <div
                  v-else
                  class="no-image has-background-grey-lighter has-text-centered is-flex is-align-items-center is-justify-content-center"
                >
                  <p>No zoomed snapshot available</p>
                </div>
              </figure>
              <p class="has-text-centered mt-2">Zoomed</p>
            </div>
          </div>

          <div class="content mt-4" v-if="selectedViolation">
            <h4>Violation Details</h4>
            <p>
              <strong>ID:</strong> {{ selectedViolation.id }}<br>
              <strong>Time:</strong> {{ formatDateTime(selectedViolation.timestamp) }}<br>
              <strong>Source:</strong> {{ getSourceName(selectedViolation.source_id) }}<br>
              <strong>Status:</strong> {{ selectedViolation.status }}<br>
              <strong>Confidence:</strong> {{ Math.round(selectedViolation.confidence * 100) }}%
            </p>

            <div class="field">
              <label class="label">Notes</label>
              <div class="control">
                <textarea
                  v-model="editingNotes"
                  class="textarea"
                  placeholder="Add notes about this violation..."
                  rows="3"
                ></textarea>
              </div>
            </div>

            <div class="field is-grouped">
              <div class="control">
                <button
                  class="button is-primary"
                  @click="saveNotes"
                >
                  <span class="icon"><i class="fas fa-save"></i></span>
                  <span>Save Notes</span>
                </button>
              </div>

              <div class="control">
                <button
                  class="button is-danger"
                  @click="updateViolationStatus(selectedViolation.id, 'resolved')"
                >
                  <span class="icon"><i class="fas fa-check-double"></i></span>
                  <span>Mark as Resolved</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <button class="modal-close is-large" aria-label="close" @click="selectedViolation = null"></button>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'History',

  data() {
    return {
      filterSourceId: 'all',
      filterStatus: 'all',
      filterStartDate: '',
      filterEndDate: '',
      loading: false,
      page: 1,
      limit: 30,
      hasMoreViolations: false,
      selectedViolation: null,
      editingNotes: ''
    }
  },

  computed: {
    ...mapGetters({
      violations: 'detection/allViolations',
      videoSources: 'video/allVideoSources'
    }),

    apiBaseUrl() {
      return this.$store.getters.apiBaseUrl
    }
  },

  created() {
    this.fetchVideoSources()
    this.loadViolations()
  },

  methods: {
    ...mapActions({
      fetchVideoSources: 'video/fetchVideoSources',
      fetchViolations: 'detection/fetchViolations',
      updateViolationStatus: 'detection/updateViolationStatus',
      updateViolationNotes: 'detection/updateViolationNotes'
    }),

    async loadViolations(append = false) {
      this.loading = true

      try {
        const params = {
          limit: this.limit,
          page: this.page
        }

        if (this.filterSourceId !== 'all') {
          params.sourceId = this.filterSourceId
        }

        if (this.filterStatus !== 'all') {
          params.status = this.filterStatus
        }

        if (this.filterStartDate) {
          params.start_date = this.filterStartDate
        }

        if (this.filterEndDate) {
          params.end_date = this.filterEndDate
        }

        await this.fetchViolations(params)

        // If we got fewer violations than the limit, there are no more to load
        this.hasMoreViolations = this.violations.length >= this.limit
      } catch (error) {
        console.error('Error loading violations:', error)
      } finally {
        this.loading = false
      }
    },

    loadMoreViolations() {
      this.page += 1
      this.loadViolations(true)
    },

    applyFilters() {
      this.page = 1
      this.loadViolations()
    },

    resetFilters() {
      this.filterSourceId = 'all'
      this.filterStatus = 'all'
      this.filterStartDate = ''
      this.filterEndDate = ''
      this.page = 1
      this.loadViolations()
    },

    formatDateTime(dateTimeStr) {
      if (!dateTimeStr) return ''

      const date = new Date(dateTimeStr)
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

    enlargeSnapshot(violation) {
      this.selectedViolation = violation
      this.editingNotes = violation.notes || ''
    },

    editNotes(violation) {
      this.selectedViolation = violation
      this.editingNotes = violation.notes || ''
    },

    async saveNotes() {
      if (!this.selectedViolation) return

      try {
        await this.updateViolationNotes({
          violationId: this.selectedViolation.id,
          notes: this.editingNotes
        })

        // Refresh data
        await this.loadViolations()

        this.selectedViolation = null
      } catch (error) {
        console.error('Error saving notes:', error)
      }
    }
  }
}
</script>

<style scoped>
.violation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.violation-card {
  transition: transform 0.2s ease-in-out;
}

.violation-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.violation-card .card-image {
  cursor: pointer;
}

.violation-card .card-image img {
  height: 180px;
  object-fit: cover;
}

.no-image {
  height: 100%;
  min-height: 200px;
}

.modal .image img {
  max-height: 350px;
  width: auto;
  margin: 0 auto;
  object-fit: contain;
}
</style>
