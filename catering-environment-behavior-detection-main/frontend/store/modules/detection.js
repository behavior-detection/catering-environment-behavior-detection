import api from '@/services/api'

export default {
  namespaced: true,

  state: {
    violations: [],
    recentViolations: [],
    violationSocket: null,
    connectingViolationSource: false,
    violationStreamActive: false,
  },

  mutations: {
    SET_VIOLATIONS(state, violations) {
      state.violations = violations
    },

    ADD_VIOLATION(state, violation) {
      // Add to both lists
      state.violations.unshift(violation)
      state.recentViolations.unshift(violation)

      // Keep recent violations list limited
      if (state.recentViolations.length > 20) {
        state.recentViolations.pop()
      }
    },

    UPDATE_VIOLATION(state, updatedViolation) {
      // Update in violations list
      const index = state.violations.findIndex(v => v.id === updatedViolation.id)
      if (index !== -1) {
        state.violations.splice(index, 1, updatedViolation)
      }

      // Update in recent violations list
      const recentIndex = state.recentViolations.findIndex(v => v.id === updatedViolation.id)
      if (recentIndex !== -1) {
        state.recentViolations.splice(recentIndex, 1, updatedViolation)
      }
    },

    SET_RECENT_VIOLATIONS(state, violations) {
      state.recentViolations = violations
    },

    SET_VIOLATION_SOCKET(state, socket) {
      state.violationSocket = socket
    },

    SET_CONNECTING_VIOLATION_SOURCE(state, connecting) {
      state.connectingViolationSource = connecting
    },

    SET_VIOLATION_STREAM_ACTIVE(state, active) {
      state.violationStreamActive = active
    }
  },

  actions: {
    async fetchViolations({ commit, rootState }, { sourceId = null, status = null, limit = 50 } = {}) {
      try {
        let url = `${rootState.apiBaseUrl}/violation-events/`

        // Add query parameters
        const params = new URLSearchParams()
        if (sourceId) params.append('video_source', sourceId)
        if (status) params.append('status', status)
        if (limit) params.append('limit', limit)

        // Append params to URL if any
        if (params.toString()) {
          url += `?${params.toString()}`
        }

        const response = await api.get(url)
        commit('SET_VIOLATIONS', response.data)
        return response.data
      } catch (error) {
        console.error('Error fetching violations:', error)
        return []
      }
    },

    async updateViolationStatus({ commit, rootState, dispatch }, { violationId, status }) {
      try {
        let response

        if (status === 'false_alarm') {
          response = await api.post(`${rootState.apiBaseUrl}/violation-events/${violationId}/mark_false_alarm/`)
        } else if (status === 'resolved') {
          response = await api.post(`${rootState.apiBaseUrl}/violation-events/${violationId}/mark_resolved/`)
        } else {
          // Direct update using PUT
          response = await api.patch(`${rootState.apiBaseUrl}/violation-events/${violationId}/`, {
            status
          })
        }

        const updatedViolation = await api.get(`${rootState.apiBaseUrl}/violation-events/${violationId}/`)
        commit('UPDATE_VIOLATION', updatedViolation.data)
        dispatch('setSuccess', `Violation status updated to ${status}`, { root: true })
        return updatedViolation.data
      } catch (error) {
        dispatch('setError', 'Failed to update violation status', { root: true })
        throw error
      }
    },

    async updateViolationNotes({ commit, rootState, dispatch }, { violationId, notes }) {
      try {
        const response = await api.patch(`${rootState.apiBaseUrl}/violation-events/${violationId}/`, {
          notes
        })
        commit('UPDATE_VIOLATION', response.data)
        dispatch('setSuccess', 'Violation notes updated', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to update violation notes', { root: true })
        throw error
      }
    },

    connectToViolationStream({ commit, state, rootState, dispatch }, sourceId = 'all') {
      // 现在state是正确传入的

      // 设置connecting状态
      commit('SET_CONNECTING_VIOLATION_SOURCE', true)

      // 关闭已存在的连接
      if (state.violationSocket && state.violationSocket.readyState !== WebSocket.CLOSED) {
        state.violationSocket.close()
      }

      let wsUrl
      if (sourceId === 'all') {
        wsUrl = `${rootState.wsBaseUrl}/ws/violations/`
      } else {
        wsUrl = `${rootState.wsBaseUrl}/ws/violations/${sourceId}/`
      }

      // Create new WebSocket connection
      const socket = new WebSocket(wsUrl)
      commit('SET_VIOLATION_SOCKET', socket)

      socket.onopen = () => {
        commit('SET_VIOLATION_STREAM_ACTIVE', true)
        commit('SET_CONNECTING_VIOLATION_SOURCE', false)
        console.log(`Violation WebSocket connected for source ${sourceId}`)
      }

      socket.onmessage = event => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'new_violation') {
            // Add new violation to the store
            const violation = {
              id: data.violation_id,
              source_id: data.source_id,
              timestamp: data.timestamp,
              snapshot_url: data.snapshot_url,
              zoomed_snapshot_url: data.zoomed_snapshot_url,
              confidence: data.confidence,
              class_name: data.class_name,
              status: 'detected',
              video_timestamp: data.video_timestamp
            }

            commit('ADD_VIOLATION', violation)

            // Show notification
            dispatch('setSuccess', `New violation detected with confidence ${Math.round(data.confidence * 100)}%`, { root: true })
          }
          else if (data.type === 'recent_violations') {
            commit('SET_RECENT_VIOLATIONS', data.violations)
          }
          else if (data.type === 'status_updated') {
            // Refresh violation data in case other fields were updated
            dispatch('fetchViolations')
          }
          else if (data.type === 'violation_list') {
            commit('SET_VIOLATIONS', data.violations)
          }
        } catch (error) {
          console.error('Error parsing violation WebSocket message:', error)
        }
      }

      socket.onerror = error => {
        console.error('Violation WebSocket error:', error)
        commit('SET_CONNECTING_VIOLATION_SOURCE', false)
        dispatch('setError', 'Violation WebSocket connection error', { root: true })
      }

      socket.onclose = event => {
        commit('SET_VIOLATION_STREAM_ACTIVE', false)
        commit('SET_CONNECTING_VIOLATION_SOURCE', false)
        console.log(`Violation WebSocket closed for source ${sourceId}:`, event)
      }
    },

    sendViolationWebSocketCommand({ state, dispatch }, command) {
      if (state.violationSocket && state.violationSocket.readyState === WebSocket.OPEN) {
        state.violationSocket.send(JSON.stringify(command))
      } else {
        dispatch('setError', 'Violation WebSocket connection not open', { root: true })
      }
    },

    requestViolationsByFilter({ dispatch }, { sourceId = 'all', status = null, limit = 20 }) {
      dispatch('sendViolationWebSocketCommand', {
        command: 'get_violations',
        source_id: sourceId,
        status,
        limit
      })
    },

    disconnectViolationStream({ state, commit }) {
      if (state.violationSocket) {
        state.violationSocket.close()
        commit('SET_VIOLATION_SOCKET', null)
        commit('SET_VIOLATION_STREAM_ACTIVE', false)
      }
    }
  },

  getters: {
    allViolations: state => state.violations,
    recentViolations: state => state.recentViolations,
    violationStreamActive: state => state.violationStreamActive,
    connectingViolationSource: state => state.connectingViolationSource,

    // Get violations count by status
    violationCountByStatus: state => {
      const counts = {
        total: state.violations.length,
        detected: 0,
        confirmed: 0,
        false_alarm: 0,
        resolved: 0
      }

      state.violations.forEach(v => {
        if (counts[v.status] !== undefined) {
          counts[v.status]++
        }
      })

      return counts
    },

    // Get violations by source
    violationsBySource: state => {
      const bySource = {}

      state.violations.forEach(violation => {
        const sourceId = violation.source_id
        if (!bySource[sourceId]) {
          bySource[sourceId] = []
        }
        bySource[sourceId].push(violation)
      })

      return bySource
    },

    // Filter violations by status
    getViolationsByStatus: state => status => {
      return state.violations.filter(v => v.status === status)
    }
  }
}
