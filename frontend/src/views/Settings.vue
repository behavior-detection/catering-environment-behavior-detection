<template>
  <div class="settings">
    <h1 class="title">System Settings</h1>

    <div class="tabs">
      <ul>
        <li :class="{ 'is-active': activeTab === 'sources' }">
          <a @click="activeTab = 'sources'">Video Sources</a>
        </li>
        <li :class="{ 'is-active': activeTab === 'roi' }">
          <a @click="activeTab = 'roi'">ROI Configuration</a>
        </li>
        <li :class="{ 'is-active': activeTab === 'detection' }">
          <a @click="activeTab = 'detection'">Detection Settings</a>
        </li>
      </ul>
    </div>

    <!-- Video Sources Tab -->
    <div v-if="activeTab === 'sources'" class="tab-content">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <h2 class="subtitle">Video Sources</h2>
          </div>
        </div>
        <div class="level-right">
          <div class="level-item">
            <button class="button is-primary" @click="showNewSourceModal = true">
              <span class="icon"><i class="fas fa-plus"></i></span>
              <span>Add Source</span>
            </button>
          </div>
        </div>
      </div>

      <div class="table-container">
        <table class="table is-fullwidth is-striped is-hoverable">
          <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>URL/Path</th>
            <th>Resolution</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
          </thead>
          <tbody>
          <tr v-if="videoSources.length === 0">
            <td colspan="6" class="has-text-centered">No video sources added yet.</td>
          </tr>
          <tr v-for="source in videoSources" :key="source.id">
            <td>{{ source.name }}</td>
            <td>{{ formatSourceType(source.source_type) }}</td>
            <td>{{ source.source_url }}</td>
            <td>{{ source.resolution_width }}x{{ source.resolution_height }}</td>
            <td>
                <span
                  class="tag"
                  :class="source.active ? 'is-success' : 'is-danger'"
                >
                  {{ source.active ? 'Active' : 'Inactive' }}
                </span>
            </td>
            <td>
              <div class="buttons are-small">
                <button
                  class="button is-info"
                  @click="editSource(source)"
                  title="Edit"
                >
                  <span class="icon"><i class="fas fa-edit"></i></span>
                </button>

                <button
                  class="button"
                  :class="source.active ? 'is-danger' : 'is-success'"
                  @click="toggleSourceActive(source)"
                  title="Toggle Active State"
                >
                    <span class="icon">
                      <i :class="source.active ? 'fas fa-power-off' : 'fas fa-play'"></i>
                    </span>
                </button>

                <button
                  v-if="source.source_type === 'file'"
                  class="button is-warning"
                  @click="showUploadFileModal(source)"
                  title="Upload Video"
                >
                  <span class="icon"><i class="fas fa-upload"></i></span>
                </button>

                <button
                  class="button is-danger"
                  @click="confirmDeleteSource(source)"
                  title="Delete"
                >
                  <span class="icon"><i class="fas fa-trash"></i></span>
                </button>
              </div>
            </td>
          </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ROI Configuration Tab -->
    <div v-else-if="activeTab === 'roi'" class="tab-content">
      <div class="columns">
        <div class="column is-4">
          <div class="box">
            <h3 class="subtitle">ROI Configuration</h3>

            <div class="field">
              <label class="label">Select Video Source</label>
              <div class="control">
                <div class="select is-fullwidth">
                  <select v-model="selectedSourceId" @change="loadRoiPolygons">
                    <option value="">Select a source</option>
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

            <div v-if="selectedSourceId">
              <div class="field">
                <label class="label">ROI Polygons</label>
                <div class="control">
                  <div class="panel">
                    <div v-if="roiPolygons.length === 0" class="panel-block">
                      No ROI polygons defined.
                    </div>
                    <div
                      v-for="polygon in roiPolygons"
                      :key="polygon.id"
                      class="panel-block"
                      :class="{ 'is-active': selectedPolygon && selectedPolygon.id === polygon.id }"
                      @click="selectPolygon(polygon)"
                    >
                      <span class="panel-icon">
                        <i class="fas fa-draw-polygon"></i>
                      </span>
                      {{ polygon.name }}
                      <div class="is-pulled-right">
                        <div class="buttons are-small">
                          <button
                            class="button is-small is-info"
                            @click.stop="editPolygon(polygon)"
                          >
                            <span class="icon is-small"><i class="fas fa-edit"></i></span>
                          </button>
                          <button
                            class="button is-small is-danger"
                            @click.stop="deletePolygon(polygon)"
                          >
                            <span class="icon is-small"><i class="fas fa-trash"></i></span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <button
                class="button is-primary is-fullwidth"
                @click="createNewPolygon"
              >
                <span class="icon"><i class="fas fa-plus"></i></span>
                <span>Add ROI Polygon</span>
              </button>
            </div>
          </div>
        </div>

        <div class="column is-8">
          <div class="box">
            <h3 class="subtitle">ROI Editor</h3>
            <div v-if="!selectedSourceId" class="notification is-info">
              Please select a video source to edit ROI polygons.
            </div>
            <div v-else-if="editingPolygon" class="roi-editor">
              <div class="field">
                <label class="label">Polygon Name</label>
                <div class="control">
                  <input
                    v-model="editingPolygon.name"
                    class="input"
                    type="text"
                    placeholder="Enter polygon name"
                  >
                </div>
              </div>

              <div class="video-container mb-3">
                <roi-editor
                  :source-id="selectedSourceId"
                  :points="editingPolygonPoints"
                  @update-points="updateEditingPoints"
                />
              </div>

              <div class="field is-grouped">
                <div class="control">
                  <button class="button is-primary" @click="savePolygon">
                    <span class="icon"><i class="fas fa-save"></i></span>
                    <span>Save</span>
                  </button>
                </div>
                <div class="control">
                  <button class="button is-light" @click="cancelEditPolygon">
                    <span class="icon"><i class="fas fa-times"></i></span>
                    <span>Cancel</span>
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="notification is-light">
              Select or create a ROI polygon to edit.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detection Settings Tab -->
    <div v-else-if="activeTab === 'detection'" class="tab-content">
      <div class="columns">
        <div class="column is-4">
          <div class="box">
            <h3 class="subtitle">Detection Configuration</h3>

            <div class="field">
              <label class="label">Select Video Source</label>
              <div class="control">
                <div class="select is-fullwidth">
                  <select v-model="selectedSourceId" @change="loadDetectionSettings">
                    <option value="">Select a source</option>
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
          </div>
        </div>

        <div class="column is-8">
          <div class="box">
            <h3 class="subtitle">Detection Parameters</h3>

            <div v-if="!selectedSourceId" class="notification is-info">
              Please select a video source to configure detection settings.
            </div>
            <div v-else-if="detectionSettings" class="detection-settings">
              <div class="field">
                <label class="label">Confidence Threshold</label>
                <div class="control">
                  <input
                    v-model.number="detectionSettings.confidence_threshold"
                    class="input"
                    type="number"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                  >
                </div>
                <p class="help">Detection confidence threshold (0.1 - 1.0)</p>
              </div>

              <div class="field">
                <label class="label">IoU Threshold</label>
                <div class="control">
                  <input
                    v-model.number="detectionSettings.iou_threshold"
                    class="input"
                    type="number"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                  >
                </div>
                <p class="help">Intersection over Union threshold for NMS (0.1 - 1.0)</p>
              </div>

              <div class="field">
                <label class="label">Target Classes</label>
                <div class="control">
                  <div class="select is-multiple is-fullwidth">
                    <select
                      v-model="selectedClasses"
                      multiple
                      size="6"
                    >
                      <option
                        v-for="cls in availableClasses"
                        :key="cls.id"
                        :value="cls.id"
                      >
                        {{ cls.name }} ({{ cls.id }})
                      </option>
                    </select>
                  </div>
                </div>
                <p class="help">Select classes to detect (empty for all classes)</p>
              </div>

              <div class="field">
                <div class="control">
                  <label class="checkbox">
                    <input
                      v-model="detectionSettings.enable_tracking"
                      type="checkbox"
                    >
                    Enable Object Tracking
                  </label>
                </div>
              </div>

              <div class="field">
                <div class="control">
                  <label class="checkbox">
                    <input
                      v-model="detectionSettings.save_snapshots"
                      type="checkbox"
                    >
                    Save Violation Snapshots
                  </label>
                </div>
              </div>

              <div class="field">
                <div class="control">
                  <button
                    class="button is-primary"
                    @click="saveDetectionSettings"
                  >
                    <span class="icon"><i class="fas fa-save"></i></span>
                    <span>Save Settings</span>
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="notification is-light">
              Loading detection settings...
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- New Source Modal -->
    <div class="modal" :class="{ 'is-active': showNewSourceModal }">
      <div class="modal-background" @click="cancelSourceModal"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">{{ editingExistingSource ? 'Edit' : 'Add' }} Video Source</p>
          <button class="delete" aria-label="close" @click="cancelSourceModal"></button>
        </header>
        <section class="modal-card-body">
          <div class="field">
            <label class="label">Name</label>
            <div class="control">
              <input
                v-model="newSource.name"
                class="input"
                type="text"
                placeholder="Enter a name for this source"
              >
            </div>
          </div>

          <div class="field">
            <label class="label">Source Type</label>
            <div class="control">
              <div class="select is-fullwidth">
                <select v-model="newSource.source_type">
                  <option value="camera">Camera</option>
                  <option value="rtsp">RTSP Stream</option>
                  <option value="file">Video File</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="label">{{ getSourceUrlLabel() }}</label>
            <div class="control">
              <input
                v-model="newSource.source_url"
                class="input"
                type="text"
                :placeholder="getSourceUrlPlaceholder()"
              >
            </div>
            <p class="help">{{ getSourceUrlHelp() }}</p>
          </div>

          <div class="field">
            <label class="label">Resolution</label>
            <div class="columns">
              <div class="column">
                <div class="field">
                  <label class="label is-small">Width</label>
                  <div class="control">
                    <input
                      v-model.number="newSource.resolution_width"
                      class="input"
                      type="number"
                      min="320"
                      step="1"
                    >
                  </div>
                </div>
              </div>
              <div class="column">
                <div class="field">
                  <label class="label is-small">Height</label>
                  <div class="control">
                    <input
                      v-model.number="newSource.resolution_height"
                      class="input"
                      type="number"
                      min="240"
                      step="1"
                    >
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="field">
            <div class="control">
              <label class="checkbox">
                <input
                  v-model="newSource.active"
                  type="checkbox"
                >
                Activate source
              </label>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button class="button is-primary" @click="saveSource">
            Save
          </button>
          <button class="button" @click="cancelSourceModal">
            Cancel
          </button>
        </footer>
      </div>
    </div>

    <!-- Upload File Modal -->
    <div class="modal" :class="{ 'is-active': showUploadModal }">
      <div class="modal-background" @click="showUploadModal = false"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Upload Video File</p>
          <button class="delete" aria-label="close" @click="showUploadModal = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="field">
            <label class="label">Select Video File</label>
            <div class="file has-name is-fullwidth">
              <label class="file-label">
                <input
                  class="file-input"
                  type="file"
                  accept="video/*"
                  @change="handleFileSelection"
                >
                <span class="file-cta">
                  <span class="file-icon">
                    <i class="fas fa-upload"></i>
                  </span>
                  <span class="file-label">
                    Choose a file…
                  </span>
                </span>
                <span class="file-name">
                  {{ selectedFile ? selectedFile.name : 'No file selected' }}
                </span>
              </label>
            </div>
          </div>

          <div v-if="uploadProgress > 0" class="field">
            <label class="label">Upload Progress</label>
            <progress
              class="progress is-primary"
              :value="uploadProgress"
              max="100"
            ></progress>
            <p class="has-text-centered">{{ uploadProgress }}%</p>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            class="button is-primary"
            :disabled="!selectedFile || uploadProgress > 0"
            @click="uploadFile"
          >
            Upload
          </button>
          <button
            class="button"
            :disabled="uploadProgress > 0"
            @click="showUploadModal = false"
          >
            Cancel
          </button>
        </footer>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div class="modal" :class="{ 'is-active': showDeleteModal }">
      <div class="modal-background" @click="showDeleteModal = false"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Confirm Deletion</p>
          <button class="delete" aria-label="close" @click="showDeleteModal = false"></button>
        </header>
        <section class="modal-card-body">
          <p>Are you sure you want to delete <strong>{{ sourceToDelete ? sourceToDelete.name : '' }}</strong>?</p>
          <p class="has-text-danger">This action cannot be undone.</p>
        </section>
        <footer class="modal-card-foot">
          <button class="button is-danger" @click="deleteSource">
            Delete
          </button>
          <button class="button" @click="showDeleteModal = false">
            Cancel
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import RoiEditor from '@/components/ROIEditor.vue'

export default {
  name: 'Settings',

  components: {
    RoiEditor
  },

  data() {
    return {
      activeTab: 'sources',

      // Video source management
      showNewSourceModal: false,
      editingExistingSource: false,
      newSource: this.getEmptySourceObject(),
      showDeleteModal: false,
      sourceToDelete: null,

      // ROI management
      selectedSourceId: '',
      selectedPolygon: null,
      editingPolygon: null,
      editingPolygonPoints: [],

      // File upload
      showUploadModal: false,
      uploadSourceId: null,
      selectedFile: null,
      uploadProgress: 0,

      // Detection settings
      selectedClasses: []
    }
  },

  computed: {
    ...mapGetters({
      videoSources: 'video/allVideoSources',
      roiPolygons: 'settings/getRoiPolygons',
      detectionSettings: 'settings/getDetectionSettings',
      availableClasses: 'settings/availableClasses'
    })
  },

  created() {
    this.fetchVideoSources()
  },

  methods: {
    ...mapActions({
      fetchVideoSources: 'video/fetchVideoSources',
      createVideoSource: 'video/createVideoSource',
      updateVideoSource: 'video/updateVideoSource',
      deleteVideoSource: 'video/deleteVideoSource',
      activateVideoSource: 'video/activateVideoSource',
      deactivateVideoSource: 'video/deactivateVideoSource',
      uploadVideoFile: 'video/uploadVideoFile',

      fetchRoiPolygons: 'settings/fetchRoiPolygons',
      createRoiPolygon: 'settings/createRoiPolygon',
      updateRoiPolygon: 'settings/updateRoiPolygon',
      deleteRoiPolygon: 'settings/deleteRoiPolygon',

      fetchDetectionSettings: 'settings/fetchDetectionSettings',
      updateDetectionSettings: 'settings/updateDetectionSettings'
    }),

    // Source form helpers
    getEmptySourceObject() {
      return {
        name: '',
        source_type: 'camera',
        source_url: '',
        resolution_width: 640,
        resolution_height: 480,
        active: true
      }
    },

    getSourceUrlLabel() {
      switch (this.newSource.source_type) {
        case 'file':
          return 'File Path'
        default:
          return 'Source URL'
      }
    },

    getSourceUrlPlaceholder() {
      switch (this.newSource.source_type) {
        case 'camera':
          return '0 (for default camera)'
        case 'rtsp':
          return 'rtsp://username:password@ip:port/path'
        case 'file':
          return '/path/to/video.mp4 or upload after creating'
        default:
          return 'Enter source URL'
      }
    },

    getSourceUrlHelp() {
      switch (this.newSource.source_type) {
        case 'camera':
          return 'Use 0 for default camera, 1 for second camera, etc.'
        case 'rtsp':
          return 'Enter the full RTSP URL for the stream'
        case 'file':
          return 'Enter the file path or upload a video file after creating the source'
        default:
          return ''
      }
    },

    formatSourceType(type) {
      switch (type) {
        case 'camera':
          return 'Camera'
        case 'rtsp':
          return 'RTSP Stream'
        case 'file':
          return 'Video File'
        default:
          return type
      }
    },

    // Source CRUD operations
    editSource(source) {
      this.editingExistingSource = true
      this.newSource = { ...source }
      this.showNewSourceModal = true
    },

    async saveSource() {
      try {
        if (this.editingExistingSource) {
          const sourceId = this.newSource.id
          const sourceData = { ...this.newSource }
          delete sourceData.id // Remove ID from payload

          await this.updateVideoSource({ sourceId, sourceData })
        } else {
          await this.createVideoSource(this.newSource)
        }

        this.cancelSourceModal()
      } catch (error) {
        console.error('Error saving source:', error)
      }
    },

    cancelSourceModal() {
      this.showNewSourceModal = false
      this.editingExistingSource = false
      this.newSource = this.getEmptySourceObject()
    },

    confirmDeleteSource(source) {
      this.sourceToDelete = source
      this.showDeleteModal = true
    },

    async deleteSource() {
      if (!this.sourceToDelete) return

      try {
        await this.deleteVideoSource(this.sourceToDelete.id)
        this.showDeleteModal = false
        this.sourceToDelete = null
      } catch (error) {
        console.error('Error deleting source:', error)
      }
    },

    async toggleSourceActive(source) {
      try {
        if (source.active) {
          await this.deactivateVideoSource(source.id)
        } else {
          await this.activateVideoSource(source.id)
        }
      } catch (error) {
        console.error('Error toggling source active state:', error)
      }
    },

    // File upload
    showUploadFileModal(source) {
      this.uploadSourceId = source.id
      this.selectedFile = null
      this.uploadProgress = 0
      this.showUploadModal = true
    },

    handleFileSelection(event) {
      const files = event.target.files
      if (files.length > 0) {
        this.selectedFile = files[0]
      }
    },

    async uploadFile() {
      if (!this.selectedFile || !this.uploadSourceId) return

      try {
        await this.uploadVideoFile({
          sourceId: this.uploadSourceId,
          file: this.selectedFile,
          onProgress: progress => {
            this.uploadProgress = progress
          }
        })

        // Refresh sources after upload
        await this.fetchVideoSources()

        this.selectedFile = null
        this.uploadProgress = 0
        this.showUploadModal = false
      } catch (error) {
        console.error('Error uploading file:', error)
      }
    },

    // ROI Polygon management
    async loadRoiPolygons() {
      if (!this.selectedSourceId) return

      try {
        await this.fetchRoiPolygons(this.selectedSourceId)
        this.selectedPolygon = null
        this.editingPolygon = null
      } catch (error) {
        console.error('Error loading ROI polygons:', error)
      }
    },

    selectPolygon(polygon) {
      this.selectedPolygon = polygon
    },

    createNewPolygon() {
      this.editingPolygon = {
        name: 'New ROI Polygon',
        points: '[]',
        active: true
      }
      this.editingPolygonPoints = []
    },

    editPolygon(polygon) {
      this.editingPolygon = { ...polygon }
      this.editingPolygonPoints = polygon.points_list || []
    },

    updateEditingPoints(points) {
      this.editingPolygonPoints = points
    },

    async savePolygon() {
      if (!this.editingPolygon) return

      try {
        const polygonData = {
          ...this.editingPolygon,
          points: JSON.stringify(this.editingPolygonPoints)
        }

        if (this.editingPolygon.id) {
          // Update existing polygon
          await this.updateRoiPolygon({
            polygonId: this.editingPolygon.id,
            updates: polygonData
          })
        } else {
          // Create new polygon
          await this.createRoiPolygon({
            sourceId: this.selectedSourceId,
            name: polygonData.name,
            points: this.editingPolygonPoints
          })
        }

        this.editingPolygon = null
        this.editingPolygonPoints = []

        // Refresh polygons
        await this.fetchRoiPolygons(this.selectedSourceId)
      } catch (error) {
        console.error('Error saving ROI polygon:', error)
      }
    },

    cancelEditPolygon() {
      this.editingPolygon = null
      this.editingPolygonPoints = []
    },

    async deletePolygon(polygon) {
      if (!polygon || !polygon.id) return

      if (!confirm(`Are you sure you want to delete the ROI polygon "${polygon.name}"?`)) {
        return
      }

      try {
        await this.deleteRoiPolygon({
          sourceId: this.selectedSourceId,
          polygonId: polygon.id
        })

        if (this.selectedPolygon && this.selectedPolygon.id === polygon.id) {
          this.selectedPolygon = null
        }

        // Refresh polygons
        await this.fetchRoiPolygons(this.selectedSourceId)
      } catch (error) {
        console.error('Error deleting ROI polygon:', error)
      }
    },

    // Detection settings
    async loadDetectionSettings() {
      if (!this.selectedSourceId) return

      try {
        const settings = await this.fetchDetectionSettings(this.selectedSourceId)

        if (settings && settings.target_classes_list) {
          this.selectedClasses = settings.target_classes_list
        } else {
          this.selectedClasses = []
        }
      } catch (error) {
        console.error('Error loading detection settings:', error)
      }
    },

    async saveDetectionSettings() {
      if (!this.selectedSourceId || !this.detectionSettings) return

      try {
        // Prepare target classes as comma-separated string
        const targetClasses = this.selectedClasses.join(',')

        await this.updateDetectionSettings({
          settingId: this.detectionSettings.id,
          updates: {
            ...this.detectionSettings,
            target_classes: targetClasses
          }
        })

        // Refresh settings
        await this.loadDetectionSettings()
      } catch (error) {
        console.error('Error saving detection settings:', error)
      }
    }
  }
}
</script>

<style scoped>
.tab-content {
  margin-top: 1.5rem;
}

.roi-editor {
  min-height: 400px;
}

.video-container {
  background-color: #000;
  border-radius: 4px;
  overflow: hidden;
  height: 400px;
}

.panel-block .buttons {
  display: none;
}

.panel-block:hover .buttons {
  display: flex;
}
</style>
'camera':
return 'Camera Index'
case 'rtsp':
return 'RTSP URL'
case
