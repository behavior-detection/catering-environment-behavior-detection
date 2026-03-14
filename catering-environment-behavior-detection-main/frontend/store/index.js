import { createStore } from 'vuex'
import video from './modules/video'
import detectionModule from './modules/detection'
import settingsModule from './modules/settings'
import navigation from './modules/navigation'

// 使用 Vite 的环境变量
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export default createStore({
  state: {
    apiBaseUrl,
    wsBaseUrl,
    loading: false,
    errorMessage: '',
    successMessage: '',
  },

  mutations: {
    SET_LOADING(state, isLoading) {
      state.loading = isLoading
    },
    SET_ERROR(state, message) {
      state.errorMessage = message
    },
    CLEAR_ERROR(state) {
      state.errorMessage = ''
    },
    SET_SUCCESS(state, message) {
      state.successMessage = message
    },
    CLEAR_SUCCESS(state) {
      state.successMessage = ''
    }
  },

  actions: {
    setLoading({ commit }, isLoading) {
      commit('SET_LOADING', isLoading)
    },
    setError({ commit }, message) {
      commit('SET_ERROR', message)
      setTimeout(() => {
        commit('CLEAR_ERROR')
      }, 5000)
    },
    clearError({ commit }) {
      commit('CLEAR_ERROR')
    },
    setSuccess({ commit }, message) {
      commit('SET_SUCCESS', message)
      setTimeout(() => {
        commit('CLEAR_SUCCESS')
      }, 5000)
    },
    clearSuccess({ commit }) {
      commit('CLEAR_SUCCESS')
    }
  },

  getters: {
    apiBaseUrl: state => state.apiBaseUrl,
    wsBaseUrl: state => state.wsBaseUrl,
    isLoading: state => state.loading,
    errorMessage: state => state.errorMessage,
    successMessage: state => state.successMessage,
  },

  modules: {
    video: video,
    detection: detectionModule,
    settings: settingsModule,
    navigation: navigation 
  }
})