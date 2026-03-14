const state = {
  currentModule: null
}

const getters = {
  currentModule: state => state.currentModule
}

const mutations = {
  SET_CURRENT_MODULE(state, moduleName) {
    state.currentModule = moduleName
  }
}

const actions = {
  setCurrentModule({ commit }, moduleName) {
    commit('SET_CURRENT_MODULE', moduleName)
  }
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions
}