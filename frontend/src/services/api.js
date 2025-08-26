// src/services/api.js
import axios from 'axios'

// 创建axios实例
const api = axios.create({
  // baseURL 设置为 '/'，以配合Vite的代理配置。
  // 在生产环境中，它会请求同源下的路径，由Nginx等Web服务器转发。
  baseURL: '/',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    // 注意：Access-Control-* 相关的 headers 是由服务器在响应中设置的，
    // 前端不应该在请求中发送它们，因此已移除。
  },
  // 启用跨域cookies (如果您的登录依赖Cookie/Session，请设为 true)
  withCredentials: false
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加CSRF token (如果需要)
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }

    console.log('API请求:', config.method?.toUpperCase(), config.url, config.data || config.params)
    return config
  },
  (error) => {
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('API响应:', response.status, response.config.url, response.data)
    return response
  },
  (error) => {
    console.error('API响应错误:', error.response?.status, error.response?.data || error.message)

    // 统一错误处理
    if (error.response?.status === 401) {
      console.warn('未授权访问，可能需要重新登录')
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

// --- ↓↓↓ 关键修改：更新所有API路径以匹配新的后端URL结构 /api/monitor/... ↓↓↓ ---

// 违规数据相关API
export const violationsAPI = {
  // 获取违规数据分析
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
              recent_records: []
            }
          }
        }
      })
  },

  // 保存违规记录
  saveRecord: (data) => api.post('/api/monitor/violations/save/', data),

  // 获取违规记录列表
  getList: (params) => api.get('/api/monitor/violations/list/', { params }),

  analyzeRecord: (recordId) => api.get(`/api/monitor/violations/record/${recordId}/analyze/`),

  // 获取违规统计
  getStats: (params) => api.get('/api/monitor/violations/stats/', { params }),

  // 清空违规数据
  clearData: () => api.post('/api/monitor/violations/clear/'),
}

// AI查询相关API
export const aiAPI = {
  // 提交AI查询
  query: (data) => api.post('/api/monitor/ai-query/', data),

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

// 导出默认API实例
export default api

// 导出便捷方法
export const get = (url, params) => api.get(url, { params })
export const post = (url, data) => api.post(url, data)
export const put = (url, data) => api.put(url, data)
export const del = (url) => api.delete(url)