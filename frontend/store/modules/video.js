import api from '@/services/api'

export default {
  namespaced: true,

  state: {
    videoSources: [],
    currentSource: null,
    currentFrame: null,
    lastFrameTime: null,
    frameDetections: [],
    isProcessing: false,
    processingProgress: 0,
    videoSocket: null,
    frameRate: 0,
    frameCount: 0,
    streamActive: false,
    streamError: null
  },

  mutations: {
    SET_VIDEO_SOURCES(state, sources) {
      state.videoSources = sources
    },

    ADD_VIDEO_SOURCE(state, source) {
      state.videoSources.push(source)
    },

    UPDATE_VIDEO_SOURCE(state, updatedSource) {
      const index = state.videoSources.findIndex(source => source.id === updatedSource.id)
      if (index !== -1) {
        state.videoSources.splice(index, 1, updatedSource)

        // Update current source if it's the one being updated
        if (state.currentSource && state.currentSource.id === updatedSource.id) {
          state.currentSource = updatedSource
        }
      }
    },

    REMOVE_VIDEO_SOURCE(state, sourceId) {
      state.videoSources = state.videoSources.filter(source => source.id !== sourceId)

      // Clear current source if it's the one being removed
      if (state.currentSource && state.currentSource.id === sourceId) {
        state.currentSource = null
      }
    },

    SET_CURRENT_SOURCE(state, source) {
      state.currentSource = source
      state.frameDetections = []
      state.currentFrame = null
      state.lastFrameTime = null
      state.frameRate = 0
      state.frameCount = 0
      state.processingProgress = 0
    },

    SET_CURRENT_FRAME(state, { frame, timestamp }) {
      state.currentFrame = frame

      // Calculate frame rate
      if (state.lastFrameTime) {
        const elapsed = timestamp - state.lastFrameTime
        if (elapsed > 0) {
          // Smooth FPS calculation with running average
          const newFrameRate = 1 / elapsed
          state.frameRate = 0.2 * newFrameRate + 0.8 * state.frameRate
        }
      }

      state.lastFrameTime = timestamp
      state.frameCount++
    },

    SET_FRAME_DETECTIONS(state, detections) {
      state.frameDetections = detections
    },

    SET_PROCESSING(state, isProcessing) {
      state.isProcessing = isProcessing
    },

    SET_PROCESSING_PROGRESS(state, progress) {
      state.processingProgress = progress
    },

    SET_VIDEO_SOCKET(state, socket) {
      state.videoSocket = socket
    },

    SET_STREAM_ACTIVE(state, active) {
      state.streamActive = active
    },

    SET_STREAM_ERROR(state, error) {
      state.streamError = error
    }
  },

  actions: {
    async fetchVideoSources({ commit, rootState }) {
      try {
        const response = await api.get(`${rootState.apiBaseUrl}/video-sources/`)
        commit('SET_VIDEO_SOURCES', response.data)
        return response.data
      } catch (error) {
        console.error('Error fetching video sources:', error)
        return []
      }
    },

    async createVideoSource({ commit, rootState, dispatch }, sourceData) {
      try {
        const response = await api.post(`${rootState.apiBaseUrl}/video-sources/`, sourceData)
        commit('ADD_VIDEO_SOURCE', response.data)
        dispatch('setSuccess', 'Video source created successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to create video source', { root: true })
        throw error
      }
    },

    async updateVideoSource({ commit, rootState, dispatch }, { sourceId, sourceData }) {
      try {
        const response = await api.put(`${rootState.apiBaseUrl}/video-sources/${sourceId}/`, sourceData)
        commit('UPDATE_VIDEO_SOURCE', response.data)
        dispatch('setSuccess', 'Video source updated successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to update video source', { root: true })
        throw error
      }
    },

    async deleteVideoSource({ commit, rootState, dispatch }, sourceId) {
      try {
        await api.delete(`${rootState.apiBaseUrl}/video-sources/${sourceId}/`)
        commit('REMOVE_VIDEO_SOURCE', sourceId)
        dispatch('setSuccess', 'Video source deleted successfully', { root: true })
        return true
      } catch (error) {
        dispatch('setError', 'Failed to delete video source', { root: true })
        throw error
      }
    },

    async activateVideoSource({ commit, rootState, dispatch }, sourceId) {
      try {
        const response = await api.post(`${rootState.apiBaseUrl}/video-sources/${sourceId}/activate/`)
        const source = await api.get(`${rootState.apiBaseUrl}/video-sources/${sourceId}/`)
        commit('UPDATE_VIDEO_SOURCE', source.data)
        dispatch('setSuccess', 'Video source activated', { root: true })
        return source.data
      } catch (error) {
        dispatch('setError', 'Failed to activate video source', { root: true })
        throw error
      }
    },

    async deactivateVideoSource({ commit, rootState, dispatch }, sourceId) {
      try {
        const response = await api.post(`${rootState.apiBaseUrl}/video-sources/${sourceId}/deactivate/`)
        const source = await api.get(`${rootState.apiBaseUrl}/video-sources/${sourceId}/`)
        commit('UPDATE_VIDEO_SOURCE', source.data)
        dispatch('setSuccess', 'Video source deactivated', { root: true })
        return source.data
      } catch (error) {
        dispatch('setError', 'Failed to deactivate video source', { root: true })
        throw error
      }
    },

    async getVideoSourceStatus({ rootState }, sourceId) {
      try {
        const response = await api.get(`${rootState.apiBaseUrl}/video-sources/${sourceId}/status/`)
        return response.data
      } catch (error) {
        console.error('Error getting video source status:', error)
        return null
      }
    },

    async uploadVideoFile({ rootState, dispatch }, { sourceId, file, onProgress }) {
      try {
        const formData = new FormData()
        formData.append('file', file)

        const config = {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: progressEvent => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            if (onProgress) onProgress(percentCompleted)
          }
        }

        const response = await api.post(
          `${rootState.apiBaseUrl}/video-sources/${sourceId}/upload_video/`,
          formData,
          config
        )

        dispatch('setSuccess', 'Video uploaded successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to upload video', { root: true })
        throw error
      }
    },

    setCurrentSource({ commit }, source) {
      commit('SET_CURRENT_SOURCE', source)
    },

    updateCurrentFrame({ commit }, { frame, timestamp }) {
      commit('SET_CURRENT_FRAME', { frame, timestamp })
    },

    updateFrameDetections({ commit }, detections) {
      commit('SET_FRAME_DETECTIONS', detections)
    },

    setProcessing({ commit }, isProcessing) {
      commit('SET_PROCESSING', isProcessing)
    },

    setProcessingProgress({ commit }, progress) {
      commit('SET_PROCESSING_PROGRESS', progress)
    },

    connectToVideoStream({ commit, state, rootState, dispatch }, sourceId) {
      // Close existing connection if any
      if (state.videoSocket && state.videoSocket.readyState !== WebSocket.CLOSED) {
        state.videoSocket.close()
      }

      // Create new WebSocket connection
      const socket = new WebSocket(`${rootState.wsBaseUrl}/ws/video/${sourceId}/`)
      commit('SET_VIDEO_SOCKET', socket)
      commit('SET_STREAM_ACTIVE', false)
      commit('SET_STREAM_ERROR', null)

      socket.onopen = () => {
        commit('SET_STREAM_ACTIVE', true)
        console.log(`WebSocket connected for source ${sourceId}`)
      }

      socket.onmessage = event => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'frame') {
            // Update current frame
            dispatch('updateCurrentFrame', {
              frame: data.frame,
              timestamp: data.timestamp
            })

            // Update detections
            if (data.detections) {
              dispatch('updateFrameDetections', data.detections)
            }

            // Update processing progress
            if (data.progress !== undefined) {
              dispatch('setProcessingProgress', data.progress)
            }
          }
          else if (data.type === 'metadata') {
            // Store source metadata
            dispatch('settings/updateSourceSettings', {
              sourceId,
              settings: data.metadata
            }, { root: true })
          }
          else if (data.type === 'processing_complete') {
            dispatch('setProcessing', false)
            dispatch('setSuccess', `Processing complete. ${data.violations_detected} violations detected.`, { root: true })
          }
          else if (data.type === 'error') {
            commit('SET_STREAM_ERROR', data.message)
            dispatch('setError', `Stream error: ${data.message}`, { root: true })
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      socket.onerror = error => {
        console.error('WebSocket error:', error)
        commit('SET_STREAM_ERROR', 'Connection error')
        dispatch('setError', 'WebSocket connection error', { root: true })
      }

      socket.onclose = event => {
        commit('SET_STREAM_ACTIVE', false)
        if (!event.wasClean) {
          commit('SET_STREAM_ERROR', `Connection closed unexpectedly (code: ${event.code})`)
        }
        console.log(`WebSocket closed for source ${sourceId}:`, event)
      }
    },

    sendWebSocketCommand({ state, dispatch }, command) {
      if (state.videoSocket && state.videoSocket.readyState === WebSocket.OPEN) {
        state.videoSocket.send(JSON.stringify(command))
      } else {
        dispatch('setError', 'WebSocket connection not open', { root: true })
      }
    },

    startDetection({ dispatch, state }) {
      if (!state.currentSource) return

      dispatch('setProcessing', true)
      dispatch('sendWebSocketCommand', {
        command: 'start_detection'
      })
    },

    stopDetection({ dispatch, state }) {
      if (!state.currentSource) return

      dispatch('sendWebSocketCommand', {
        command: 'stop_detection'
      })
    },

    disconnectVideoStream({ state, commit }) {
      if (state.videoSocket) {
        state.videoSocket.close()
        commit('SET_VIDEO_SOCKET', null)
        commit('SET_STREAM_ACTIVE', false)
      }
    }
  },

  getters: {
    allVideoSources: state => state.videoSources,
    activeVideoSources: state => state.videoSources.filter(source => source.active),
    currentSource: state => state.currentSource,
    currentFrame: state => state.currentFrame,
    frameDetections: state => state.frameDetections,
    isProcessing: state => state.isProcessing,
    processingProgress: state => state.processingProgress,
    streamActive: state => state.streamActive,
    streamError: state => state.streamError,
    frameRate: state => Math.round(state.frameRate * 10) / 10,
    frameCount: state => state.frameCount
  }
}
