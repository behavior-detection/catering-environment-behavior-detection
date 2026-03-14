import api from '@/services/api'
import { markRaw } from 'vue';

// ✅ 定义detection API基础路径
const API_BASE = '/api/detection'

// 辅助函数：自动获取 WebSocket 基础地址
function getWsBaseUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

function waitForSocketInstance(state, timeout = 6000) {
  return new Promise((resolve, reject) => {
    // 1. 立即检查一次（防止运气好正好碰上）
    if (state.videoSocket && state.videoSocket.readyState === 1) {
       resolve(state.videoSocket);
       return;
    }

    const start = Date.now();
    const interval = setInterval(() => {
      // 只要 socket 存在且是 OPEN (1) 状态
      // 注意：这里只接受 OPEN，不接受 CONNECTING(0)，确保真的能用了
      if (state.videoSocket && state.videoSocket.readyState === 1) {
        clearInterval(interval);
        resolve(state.videoSocket);
      } else if (Date.now() - start > timeout) {
        clearInterval(interval);
        // 超时时，打印一下当前状态方便调试
        console.warn('[Vuex Wait] Timeout. Socket state:', state.videoSocket ? state.videoSocket.readyState : 'null');
        reject(new Error('Timeout waiting for WebSocket instance creation'));
      }
    }, 100);
  });
}

function waitForSocketConnection(socket, callback) {
  setTimeout(
    function () {
      if (socket.readyState === 1) { // 1 = OPEN
        console.log("Connection is made");
        if (callback != null){
          callback();
        }
      } else {
        console.log("wait for connection...");
        waitForSocketConnection(socket, callback);
      }
    }, 50 // 每50ms检查一次
  );
}

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
    processingCompleteData: null,
    frameRate: 0,
    frameCount: 0,
    streamActive: false,
    streamError: null,
    wsBaseUrl: getWsBaseUrl()
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

        if (state.currentSource && state.currentSource.id === updatedSource.id) {
          state.currentSource = updatedSource
        }
      }
    },

    REMOVE_VIDEO_SOURCE(state, sourceId) {
      state.videoSources = state.videoSources.filter(source => source.id !== sourceId)

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

      // 帧率计算逻辑
      if (state.lastFrameTime) {
        const elapsed = timestamp - state.lastFrameTime
        if (elapsed > 0) {
          const newFrameRate = 1000 / elapsed; // 毫秒转秒
          // 简单的平滑滤波
          state.frameRate = 0.2 * newFrameRate + 0.8 * state.frameRate
        }
      }

      state.lastFrameTime = timestamp
      state.frameCount++
    },

    SET_FRAME_DETECTIONS(state, detections) {
      state.frameDetections = detections
    },

    SET_PROCESSING_COMPLETE(state, data) {
      state.processingCompleteData = data
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
      console.log('[Vuex] Mutation: SET_STREAM_ACTIVE =', active);
      state.streamActive = active
    },

    SET_STREAM_ERROR(state, error) {
      state.streamError = error
    },

    SET_SOCKET(state, socket) {
      state.socket = socket
    },
  },

  actions: {
    async fetchVideoSources({ commit }) {
      try {
        const response = await api.get(`${API_BASE}/video-sources/`)
        commit('SET_VIDEO_SOURCES', response.data)
        return response.data
      } catch (error) {
        console.error('Error fetching video sources:', error)
        return []
      }
    },

    async createVideoSource({ commit, dispatch }, sourceData) {
      try {
        const response = await api.post(`${API_BASE}/video-sources/`, sourceData)
        commit('ADD_VIDEO_SOURCE', response.data)
        dispatch('setSuccess', 'Video source created successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to create video source', { root: true })
        throw error
      }
    },

    async updateVideoSource({ commit, dispatch }, { sourceId, sourceData }) {
      try {
        const response = await api.put(`${API_BASE}/video-sources/${sourceId}/`, sourceData)
        commit('UPDATE_VIDEO_SOURCE', response.data)
        dispatch('setSuccess', 'Video source updated successfully', { root: true })
        return response.data
      } catch (error) {
        dispatch('setError', 'Failed to update video source', { root: true })
        throw error
      }
    },

    async deleteVideoSource({ commit, dispatch }, sourceId) {
      try {
        await api.delete(`${API_BASE}/video-sources/${sourceId}/`)
        commit('REMOVE_VIDEO_SOURCE', sourceId)
        dispatch('setSuccess', 'Video source deleted successfully', { root: true })
        return true
      } catch (error) {
        dispatch('setError', 'Failed to delete video source', { root: true })
        throw error
      }
    },

    async activateVideoSource({ commit, dispatch }, sourceId) {
      try {
        await api.post(`${API_BASE}/video-sources/${sourceId}/activate/`)
        const source = await api.get(`${API_BASE}/video-sources/${sourceId}/`)
        commit('UPDATE_VIDEO_SOURCE', source.data)
        dispatch('setSuccess', 'Video source activated', { root: true })
        return source.data
      } catch (error) {
        dispatch('setError', 'Failed to activate video source', { root: true })
        throw error
      }
    },

    async deactivateVideoSource({ commit, dispatch }, sourceId) {
      try {
        await api.post(`${API_BASE}/video-sources/${sourceId}/deactivate/`)
        const source = await api.get(`${API_BASE}/video-sources/${sourceId}/`)
        commit('UPDATE_VIDEO_SOURCE', source.data)
        dispatch('setSuccess', 'Video source deactivated', { root: true })
        return source.data
      } catch (error) {
        dispatch('setError', 'Failed to deactivate video source', { root: true })
        throw error
      }
    },

    async getVideoSourceStatus({ }, sourceId) {
      try {
        const response = await api.get(`${API_BASE}/video-sources/${sourceId}/status/`)
        return response.data
      } catch (error) {
        console.error('Error getting video source status:', error)
        return null
      }
    },

    async uploadVideoFile({ dispatch }, { sourceId, file, onProgress }) {
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
          `${API_BASE}/video-sources/${sourceId}/upload_video/`,
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


    async connectToVideoStream({ commit, state, dispatch }, sourceId) {
      // 防止重复连接
      if (state.videoSocket && state.videoSocket.readyState === 1) {
        if (state.videoSocket.url.includes(sourceId)) {
            return;
        }
        state.videoSocket.close();
      }

      // ✅ 确保 wsBaseUrl 存在
      const baseUrl = state.wsBaseUrl || getWsBaseUrl();
      const wsUrl = `${baseUrl}/ws/video/${sourceId}/`;
      console.log(`[Vuex] 正在连接: ${wsUrl}`);

      try {
        const socket = new WebSocket(wsUrl);
        const rawSocket = markRaw(socket); // 使用 markRaw
        
        commit('SET_VIDEO_SOCKET', rawSocket);

        rawSocket.onopen = () => {
          console.log(`[Vuex] ✅ WebSocket 连接成功 (onopen)`);
          commit('SET_STREAM_ACTIVE', true);
        };

        rawSocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // 1. 获取 Base64 图片数据
            // 兼容多种常见的后端命名 (image, frame, img, jpg)
            const base64Data = data.image || data.frame || data.img || data.jpg;

            if (base64Data) {
              // 确保有 Base64 前缀
              const prefix = base64Data.startsWith('data:') ? '' : 'data:image/jpeg;base64,';
              const imageSrc = `${prefix}${base64Data}`;
              
              commit('SET_CURRENT_FRAME', {
                frame: imageSrc,
                timestamp: Date.now()
              });
            } else if (data.status) {
                // 只是状态更新，忽略图片警告
                console.log('[Vuex] 状态更新:', data.status);
            } else {
                // 真的有问题：收到了非状态消息，但没有图片
                // console.warn('[Vuex] 数据包缺失图片字段. Available keys:', Object.keys(data));
            }
            
            // 2. 处理检测框
            if (data.detections) {
              commit('SET_FRAME_DETECTIONS', data.detections);
            }
            
            // 3. 处理状态回执
            if (data.status === 'detection_stopped') {
                dispatch('setProcessing', false);
            }

          } catch (e) {
            console.error('[Vuex] 数据解析失败:', e);
          }
        };

        rawSocket.onclose = (event) => {
          console.log(`[Vuex] 连接关闭 code=${event.code}`);
          commit('SET_STREAM_ACTIVE', false);
        };

        rawSocket.onerror = (error) => {
          console.error('[Vuex] WebSocket 错误:', error);
          commit('SET_STREAM_ACTIVE', false);
          dispatch('setError', '视频流连接错误', { root: true });
        };

      } catch (error) {
        console.error('[Vuex] 连接建立失败:', error);
      }
    },

    sendWebSocketCommand({ state, dispatch }, commandData) {
      if (!state.videoSocket) {
          console.warn('[Vuex] Socket 为空，暂存指令失败'); 
          return; 
      }

      // 简单的重试辅助函数
      const waitAndSend = (socket, data) => {
        setTimeout(() => {
          if (socket.readyState === 1) {
             socket.send(JSON.stringify(data));
             console.log('[Vuex] 📤 延迟指令已发出:', data);
          } else {
             console.log('wait for connection...');
             waitAndSend(socket, data);
          }
        }, 50);
      }

      if (state.videoSocket.readyState === 1) {
        try {
          state.videoSocket.send(JSON.stringify(commandData));
          console.log('[Vuex] 📤 指令已发出:', commandData);
        } catch (e) {
          console.error('[Vuex] Failed to send command:', e);
        }
      } else {
        console.log('[Vuex] Socket connecting, queuing command:', commandData);
        waitAndSend(state.videoSocket, commandData);
      }
    },

    async startDetection({ dispatch, commit, state }, { use_roi } = {}) {
      if (!state.currentSource) return;
      const sourceId = state.currentSource.id;

      console.log(`[Vuex] startDetection 启动... (ROI模式: ${use_roi})`);

      const oldSocket = state.videoSocket;
      
      // 1. 初始避让 (给 Socket 建立留出时间)
      await new Promise(resolve => setTimeout(resolve, 500));

      const maxRetries = 20; 
      const interval = 300;

      for (let i = 0; i < maxRetries; i++) {
          // 每次循环都重新获取最新的 socket 对象
          const currentSocket = state.videoSocket;
          // 🔥 [关键点1] 实时检查 readyState (1 代表 OPEN)
          const isConnected = currentSocket && currentSocket.readyState === 1;
          const isNewSocket = oldSocket ? (currentSocket !== oldSocket) : true;

          if (isConnected) {
              const commandPayload = {
                  command: 'start_detection',
                  source_id: sourceId,
                  use_roi: !!use_roi 
              };

              // 🔥 [关键点2] 在发送前再次进行“双重确认”
              // 防止在 if (isConnected) 判断后到执行代码之间 Socket 突然断开
              if (state.videoSocket && state.videoSocket.readyState === 1) {
                  
                  if (isNewSocket) {
                      console.log(`[Vuex] ✅ 新连接就绪，发送指令 (ROI: ${use_roi})`);
                  } else if (i >= 2) {
                       console.log(`[Vuex] ✅ 复用旧连接，发送指令 (ROI: ${use_roi})`);
                  } else {
                      // 如果是旧连接但还没等到稳定期，跳过本次循环继续等待
                      await new Promise(resolve => setTimeout(resolve, interval));
                      continue; 
                  }

                  // 只有确认连接活着，才发送和改变状态
                  dispatch('sendWebSocketCommand', commandPayload);
                  dispatch('setProcessing', true);
                  commit('SET_STREAM_ACTIVE', true); 
                  
                  return; // 成功退出
              } else {
                  console.warn('[Vuex] ⚠️ 准备发送时发现 Socket 已关闭，重试中...');
              }
          } 
          await new Promise(resolve => setTimeout(resolve, interval));
      }

      // ⚠️ 保底重连逻辑
      console.warn('[Vuex] ⚠️ 启动超时或连接断开，尝试强制重连...');
      try {
          // 强制断开再连，确保干净
          await dispatch('disconnectVideoStream');
          await new Promise(resolve => setTimeout(resolve, 500)); // 冷却
          await dispatch('connectToVideoStream', sourceId);
          
          await new Promise(resolve => setTimeout(resolve, 1500)); // 等待连接
          
          // 保底发送时的双重检查
          if (state.videoSocket && state.videoSocket.readyState === 1) {
              dispatch('sendWebSocketCommand', {
                  command: 'start_detection',
                  source_id: sourceId,
                  use_roi: !!use_roi 
              });
              dispatch('setProcessing', true);
              commit('SET_STREAM_ACTIVE', true);
          } else {
              throw new Error('强制重连后 Socket 依然未就绪');
          }
      } catch (e) {
          console.error('[Vuex] 最终启动失败:', e);
          // 🔥 [关键点3] 如果失败，确保状态是 false，不要欺骗 UI
          commit('SET_STREAM_ACTIVE', false); 
          throw e;
      }
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