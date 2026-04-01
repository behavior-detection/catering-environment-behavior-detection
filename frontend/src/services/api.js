import axios from 'axios'
import store from '../../store'

// 创建axios实例
const api = axios.create({
  baseURL: '/',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    if (store) {
      store.dispatch('setLoading', true)
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }

    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }

    console.log('API请求:', config.method?.toUpperCase(), config.url, config.data || config.params)
    return config
  },
  (error) => {
    if (store) {
      store.dispatch('setLoading', false)
    }
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    if (store) {
      store.dispatch('setLoading', false)
    }
    console.log('API响应:', response.status, response.config.url, response.data)
    return response
  },
  (error) => {
    if (store) {
      store.dispatch('setLoading', false)
      store.dispatch('setError', error.response?.data?.message || error.message)
    }

    console.error('API响应错误:', error.response?.status, error.response?.data || error.message)

    if (error.response?.status === 401) {
      console.warn('令牌过期或无效，清除登录状态')
      localStorage.removeItem('authToken')
      sessionStorage.removeItem('userInfo')
      sessionStorage.removeItem('adminInfo')
      window.location.href = '/'
    } else if (error.response?.status === 403) {
      console.warn('访问被禁止')
    } else if (error.response?.status >= 500) {
      console.error('服务器内部错误')
    } else if (error.code === 'ERR_NETWORK') {
      console.error('网络错误，请检查后端服务是否启动以及前端代理是否配置正确')
    }

    return Promise.reject(error)
  }
)

// 违规数据相关API
export const violationsAPI = {
  // 获取违规数据分析（显示所有数据）
  getAnalytics: (params) => {
    return api.get('/api/monitor/violations/analytics/', { params })
      .catch(error => {
        console.error('获取分析数据失败:', error)
        // 返回模拟数据以避免页面崩溃
        return {
          data: {
            success: true,
            data: {
              summary: {
                total_violations: 0,
                total_records: 0,
                active_cameras: 0
              },
              violations_by_type: {},
              violations_by_camera: {},
              violations_by_hour: {},
              recent_records: []
            }
          }
        }
      })
  },

  // 新增：根据EID获取违规数据（仅显示特定EID的数据）
  getViolationsByEid: (params) => {
    return api.get('/api/monitor/violations/by-eid/', { params })
      .catch(error => {
        console.error('获取EID违规数据失败:', error)
        // 返回模拟数据
        return {
          data: {
            success: true,
            data: {
              summary: {
                total_violations: 0,
                total_records: 0,
                active_cameras: 0
              },
              violations_by_type: {},
              violations_by_camera: {},
              violations_by_hour: {},
              recent_records: []
            },
            eid: params.eid,
            file_count: 0
          }
        }
      })
  },

  // 保存违规记录
  saveRecord: (data) => api.post('/api/monitor/violations/save/', data),

  // 获取违规记录列表
  getList: (params) => api.get('/api/monitor/violations/list/', { params }),

  // 分析记录
  analyzeRecord: (recordId) => api.get(`/api/monitor/violations/record/${recordId}/analyze/`),

  // 获取违规统计
  getStats: (params) => api.get('/api/monitor/violations/stats/', { params }),

  // 清空违规数据
  clearData: () => api.delete('/api/monitor/violations/clear/'),
}

// 设备仓库管理相关API
export const warehouseAPI = {
  // 创建设备仓库
  createWarehouse: (data) => api.post('/api/monitor/warehouses/create/', data),

  // 获取设备仓库列表
  getWarehouses: (params) => api.get('/api/monitor/warehouses/', { params }),

  // 根据EID获取仓库列表（用于权限申请）
  getWarehousesByEid: (params) => api.get('/api/monitor/warehouses/by-eid/', { params }),

  // 获取仓库详情
  getWarehouse: (warehouseId, params) => api.get(`/api/monitor/warehouses/${warehouseId}/`, { params }),

  // 更新仓库名称
  updateWarehouseName: (warehouseId, data) => api.put(`/api/monitor/warehouses/${warehouseId}/update-name/`, data),

  // 删除设备仓库
  deleteWarehouse: (warehouseId, data) => api.delete(`/api/monitor/warehouses/${warehouseId}/delete/`, { data }),

  // 上传文件到仓库
  uploadFiles: (formData) => {
    return api.post('/api/monitor/warehouses/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取仓库文件列表
  getWarehouseFiles: (warehouseId, params) => api.get(`/api/monitor/warehouses/${warehouseId}/files/`, { params }),

  // 下载文件
  downloadFile: (fileId) => api.get(`/api/monitor/files/${fileId}/download/`, { responseType: 'blob' }),

  // 删除文件
  deleteFile: (fileId, data) => api.delete(`/api/monitor/files/${fileId}/delete/`, { data }),

  // 查看文件内容
  getFileContent: (fileId, params = {}) => api.get(`/api/monitor/files/${fileId}/content/`, { params }),

  // 检查指定日期是否有文件
  checkFileExists: (params) => api.get('/api/monitor/check-file-exists/', { params }),
}

// AI查询相关API
export const aiAPI = {
  // 提交AI查询（单独设置300秒超时，与后端Janus服务超时对齐）
  query: (data) => api.post('/api/monitor/ai-query/', data, { timeout: 300000 }),

  // 获取查询历史
  getHistory: (params) => api.get('/api/monitor/ai-query/history/', { params }),
}

// 系统相关API
export const systemAPI = {
  // 健康检查
  health: () => api.get('/api/monitor/health/'),

  // 系统状态
  status: () => api.get('/api/monitor/status/'),
}

// ==================== WebRTC P2P 文件共享相关API ====================

// 权限申请相关API
export const permissionAPI = {
  /**
   * Visitor提交权限申请
   * @param {Object} data - 申请数据
   * @param {string} data.visitorName - Visitor名称
   * @param {string} data.eid - 企业EID
   * @param {string} data.applyType - 申请类型：'time' 或 'warehouse'
   * @param {string} data.specificCategory - 具体类别（仓库ID或时间段）
   * @param {number} data.durationDays - 申请时长（天数）
   * @param {string} data.reason - 申请理由
   */
  submitRequest: (data) => {
    return api.post('/api/monitor/submit-permission/', {
      visitor_name: data.visitorName,
      eid: data.eid,
      apply_type: data.applyType,
      specific_category: data.specificCategory,
      duration_days: data.durationDays,
      reason: data.reason
    })
  },

  /**
   * Manager获取待审批的权限申请列表
   * @param {Object} params - 查询参数
   * @param {string} params.manager_name - Manager名称
   * @param {string} params.eid - 企业EID
   * @param {string} params.status - 状态：'all', 'pending', 'approved', 'rejected'
   */
  getRequests: (params) => {
    return api.get('/api/monitor/permission/requests/', { params })
  },

  /**
   * Manager审批权限申请
   * @param {Object} data - 审批数据
   * @param {string} data.requestId - 申请ID
   * @param {string} data.managerName - Manager名称
   * @param {boolean} data.approved - 是否批准
   */
  approveRequest: (data) => {
    return api.post('/api/monitor/permission/approve/', {
      request_id: data.requestId,
      manager_name: data.managerName,
      decision: data.approved ? 'approve' : 'reject'
    })
  },

  /**
   * Visitor查询自己的权限申请状态
   * @param {Object} params - 查询参数
   * @param {string} params.visitor_name - Visitor名称
   * @param {string} params.status - 状态过滤（可选）
   */
  getMyRequests: (params) => {
    return api.get('/api/monitor/permission/my-requests/', { params })
  },

  /**
   * 验证access_token是否有效
   * ✨ 修复：只需要access_token，不需要visitor_name和eid
   * @param {string} accessToken - 访问令牌（哈希码）
   * @returns {Promise<Object>} 验证结果
   */
  verifyToken: (accessToken) => {
    return api.post('/api/monitor/permission/verify-token/', {
      access_token: accessToken
    }).then(response => response.data)
      .catch(error => {
        console.error('Token验证失败:', error)
        return {
          success: false,
          valid: false,
          message: error.response?.data?.message || '验证失败'
        }
      })
  },
  // 根据 access_token 获取授权日期的文件列表
  getFilesByDate(accessToken) {
    return api.get('/api/monitor/permission/files-by-date/', {
      params: { access_token: accessToken }
    })
  }
}

// WebRTC连接相关API
export const webrtcAPI = {
  /**
   * 获取WebSocket连接URL
   * @returns {string} WebSocket连接地址
   */
  getWebSocketURL: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = process.env.VUE_APP_WS_HOST || window.location.host
    return `${protocol}//${host}/ws/file-share/`
  },

  /**
   * 获取指定用户的在线状态
   * @param {Object} params - 查询参数
   * @param {string} params.user_id - 用户ID
   * @param {string} params.user_type - 用户类型：'manager' 或 'visitor'
   * @param {string} params.eid - 企业EID
   */
  getOnlineStatus: (params) => {
    return api.get('/api/monitor/online-status/', { params })
  },

  /**
   * 获取指定EID下的所有在线用户
   * @param {Object} params - 查询参数
   * @param {string} params.eid - 企业EID
   */
  getAllOnlineUsers: (params) => {
    return api.get('/api/monitor/online-users/', { params })
  }
}

export const visitorAPI = {
  /**
   * Visitor通过access_token获取授权数据的分析结果
   * @param {string} accessToken - 访问令牌
   * @param {string} timeRange - 时间范围
   */
  getAuthorizedData: (accessToken, timeRange = '24h') => {
    return api.get('/api/monitor/visitor/authorized-data/', {
      params: {
        access_token: accessToken,
        range: timeRange
      }
    })
  },

  /**
   * Visitor通过access_token进行AI查询
   * @param {Object} data - 查询数据
   */
  aiQuery: (data) => {
    return api.post('/api/monitor/visitor/ai-query/', data)
  }
}

// 导出默认API实例
export default api

// 导出便捷方法
export const get = (url, params) => api.get(url, { params })
export const post = (url, data) => api.post(url, data)
export const put = (url, data) => api.put(url, data)
export const del = (url) => api.delete(url)