import api from '@/services/api'

export default {
  namespaced: true,

  state: {
    sourceSettings: {}, // Indexed by source ID
    roiPolygons: {}, // Indexed by source ID
    detectionSettings: {}, // Indexed by source ID
    availableClasses: [
      { id: 0, name: 'person' },
      { id: 1, name: 'bicycle' },
      { id: 2, name: 'car' },
      { id: 3, name: 'motorcycle' },
      { id: 4, name: 'airplane' },
      { id: 5, name: 'bus' },
      { id: 6, name: 'train' },
      { id: 7, name: 'truck' },
      { id: 8, name: 'boat' },
      { id: 16, name: 'dog' },
      { id: 17, name: 'horse' },
      { id: 18, name: 'sheep' },
      { id: 19, name: 'cow' },
      { id: 20, name: 'elephant' },
      { id: 21, name: 'bear' },
      { id: 22, name: 'zebra' },
      { id: 23, name: 'giraffe' }
    ]
  },

  mutations: {
    SET_SOURCE_SETTINGS(state, { sourceId, settings }) {
      state.sourceSettings = {
        ...state.sourceSettings,
        [sourceId]: settings
      }
    },

    SET_ROI_POLYGONS(state, { sourceId, polygons }) {
      state.roiPolygons = {
        ...state.roiPolygons,
        [sourceId]: polygons
      }
    },

    ADD_ROI_POLYGON(state, { sourceId, polygon }) {
      if (!state.roiPolygons[sourceId]) {
        state.roiPolygons[sourceId] = []
      }

      state.roiPolygons[sourceId].push(polygon)
    },

    UPDATE_ROI_POLYGON(state, { sourceId, polygonId, updatedPolygon }) {
      if (!state.roiPolygons[sourceId]) return

      const index = state.roiPolygons[sourceId].findIndex(p => p.id === polygonId)
      if (index !== -1) {
        state.roiPolygons[sourceId].splice(index, 1, updatedPolygon)
      }
    },

    REMOVE_ROI_POLYGON(state, { sourceId, polygonId }) {
      if (!state.roiPolygons[sourceId]) return

      state.roiPolygons[sourceId] = state.roiPolygons[sourceId].filter(p => p.id !== polygonId)
    },

    SET_DETECTION_SETTINGS(state, { sourceId, settings }) {
      state.detectionSettings = {
        ...state.detectionSettings,
        [sourceId]: settings
      }
    },

    UPDATE_DETECTION_SETTINGS(state, { sourceId, settings }) {
      state.detectionSettings = {
        ...state.detectionSettings,
        [sourceId]: {
          ...state.detectionSettings[sourceId],
          ...settings
        }
      }
    }
  },

  actions: {
    updateSourceSettings({ commit }, { sourceId, settings }) {
      commit('SET_SOURCE_SETTINGS', { sourceId, settings })
    },

    async fetchRoiPolygons({ commit, rootState }, sourceId) {
      try {
        const response = await api.get(`${rootState.apiBaseUrl}/roi-polygons/?video_source=${sourceId}`)
        commit('SET_ROI_POLYGONS', { sourceId, polygons: response.data })
        return response.data
      } catch (error) {
        console.error('Error fetching ROI polygons:', error)
        return []
      }
    },

    async createRoiPolygon({ commit, rootState, dispatch }, { sourceId, name, points }) {
      try {
        const response = await api.post(`${rootState.apiBaseUrl}/roi-polygons/`, {
          video_source: sourceId,
          name,
          points: JSON.stringify(points),
          active: true
        })

        commit('ADD_ROI_POLYGON', { sourceId, polygon: response.data })
        dispatch('setSuccess', 'ROI polygon created successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to create ROI polygon', { root: true })
        throw error
      }
    },

    async updateRoiPolygon({ commit, rootState, dispatch }, { polygonId, updates }) {
      try {
        const response = await api.patch(`${rootState.apiBaseUrl}/roi-polygons/${polygonId}/`, updates)

        // Extract sourceId from response
        const sourceId = response.data.video_source

        commit('UPDATE_ROI_POLYGON', {
          sourceId,
          polygonId,
          updatedPolygon: response.data
        })

        dispatch('setSuccess', 'ROI polygon updated successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to update ROI polygon', { root: true })
        throw error
      }
    },

    async deleteRoiPolygon({ commit, rootState, dispatch }, { sourceId, polygonId }) {
      try {
        await api.delete(`${rootState.apiBaseUrl}/roi-polygons/${polygonId}/`)

        commit('REMOVE_ROI_POLYGON', { sourceId, polygonId })
        dispatch('setSuccess', 'ROI polygon deleted successfully', { root: true })
        return true
      } catch (error) {
        dispatch('setError', 'Failed to delete ROI polygon', { root: true })
        throw error
      }
    },

    async fetchDetectionSettings({ commit, rootState }, sourceId) {
      try {
        const response = await api.get(`${rootState.apiBaseUrl}/detection-settings/?video_source=${sourceId}`)

        if (response.data.length > 0) {
          commit('SET_DETECTION_SETTINGS', { sourceId, settings: response.data[0] })
          return response.data[0]
        }
        return null
      } catch (error) {
        console.error('Error fetching detection settings:', error)
        return null
      }
    },

    async updateDetectionSettings({ commit, rootState, dispatch }, { settingId, updates }) {
      try {
        const response = await api.patch(`${rootState.apiBaseUrl}/detection-settings/${settingId}/`, updates)

        // Extract sourceId
        const sourceId = response.data.video_source

        commit('SET_DETECTION_SETTINGS', { sourceId, settings: response.data })
        dispatch('setSuccess', 'Detection settings updated successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to update detection settings', { root: true })
        throw error
      }
    }
  },

  getters: {
    getSourceSettings: state => sourceId => state.sourceSettings[sourceId] || null,
    getRoiPolygons: state => sourceId => state.roiPolygons[sourceId] || [],
    getDetectionSettings: state => sourceId => state.detectionSettings[sourceId] || null,
    availableClasses: state => state.availableClasses,

    getClassNameById: state => id => {
      const classItem = state.availableClasses.find(c => c.id === id)
      return classItem ? classItem.name : `Class ${id}`
    },

    getSourceResolution: state => sourceId => {
      const settings = state.sourceSettings[sourceId]
      return settings ? settings.resolution : '640x480'
    }
  }
}
