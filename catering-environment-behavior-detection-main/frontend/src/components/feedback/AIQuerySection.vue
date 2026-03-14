<!-- components/feedback/AIQuerySection.vue -->
<template>
  <div class="ai-chat-section">
    <div class="chat-header">
      <div class="chat-title">
        <span>AI智能问答助手</span>
      </div>
      <div class="chat-subtitle">用自然语言询问违规数据相关问题</div>
      <div v-if="!currentEid" class="eid-warning">
        ⚠️ 请先登录获取企业信息
      </div>
      <div v-else class="eid-info">
        <span>当前企业: {{ currentEid }}</span>
      </div>
    </div>

    <div class="chat-body">
      <!-- 查询输入区域 -->
      <div class="query-input-section">
        <div class="input-wrapper">
          <div class="query-controls">
            <div v-if="timeRangeAdjusted" class="time-range-notice">
              <i class="icon">🔄</i>
              <span>AI已根据问题自动调整时间范围</span>
            </div>
            <select v-model="queryTimeRange" class="time-select">
              <option value="1">最近1小时</option>
              <option value="24">最近24小时</option>
              <option value="48">最近48小时</option>
              <option value="168">最近7天</option>
              <option value="720">最近30天</option>
              <option value="0">所有数据</option>
            </select>
          </div>

          <div class="input-container">
            <textarea
              v-model="aiQuery"
              class="query-input"
              placeholder="请用自然语言描述您的问题，例如：今天哪个区域违规最多？口罩佩戴情况如何？"
              rows="3"
              @keypress="handleQueryKeypress"
              :disabled="!currentEid"
            ></textarea>

            <div class="input-actions">
              <button class="btn btn-primary" @click="submitAIQuery" :disabled="aiLoading || !aiQuery.trim() || !currentEid">
                <i class="icon">🔍</i>
                {{ aiLoading ? 'AI分析中...' : 'AI分析' }}
              </button>
              <button class="btn btn-secondary" @click="clearAIQuery">
                <i class="icon">🗑️</i>
                清空
              </button>
            </div>
          </div>
        </div>

        <!-- 快速查询示例 -->
        <div class="quick-queries" v-if="currentEid">
          <div class="quick-label">快速查询:</div>
          <div class="quick-buttons">
            <button
              v-for="example in enhancedQueryExamples"
              :key="example.text"
              class="quick-btn"
              @click="setAIQuery(example.text, example.suggestedTimeRange)"
            >
              {{ example.text }}
            </button>
          </div>
        </div>
      </div>

      <!-- AI分析结果显示 -->
      <AIQueryResult
        v-if="aiResult"
        :result="aiResult"
        :query-time-range="actualTimeRangeUsed"
      />

      <!-- 加载状态 -->
      <div v-if="aiLoading" class="ai-loading">
        <div class="loading-spinner"></div>
        <div class="loading-text">AI正在分析数据，请稍候...</div>
      </div>

      <!-- 错误提示 -->
      <div v-if="aiError" class="ai-error">
        <i class="icon">❌</i>
        <span>{{ aiError }}</span>
      </div>

      <!-- 调试信息 -->
      <div v-if="showDebugInfo" class="debug-info">
        <h4>调试信息:</h4>
        <p>用户类型: {{ userType }}</p>
        <p>当前EID: {{ currentEid }}</p>
        <p>用户名: {{ userName }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { aiAPI } from '@/services/api'
import AIQueryResult from './AIQueryResult.vue'

export default {
  name: 'AIQuerySection',
  components: {
    AIQueryResult
  },
  props: {
    queryExamples: {
      type: Array,
      default: () => []
    },
    showDebugInfo: {
      type: Boolean,
      default: false
    }
  },
  emits: ['ai-query'],
  data() {
    return {
      // 用户信息
      userType: '',
      userName: '',
      currentEid: '',

      // AI查询相关
      aiQuery: '',
      queryTimeRange: '24',
      aiLoading: false,
      aiResult: null,
      aiError: null,
      timeRangeAdjusted: false,
      actualTimeRangeUsed: '24'
    }
  },
  computed: {
    // 增强的查询示例，包含建议的时间范围
    enhancedQueryExamples() {
      const baseExamples = [
        { text: '今天违规情况如何？', suggestedTimeRange: '24' },
        { text: '哪个摄像头违规最多？', suggestedTimeRange: null },
        { text: '口罩佩戴情况怎么样？', suggestedTimeRange: null },
        { text: '当前风险等级如何？', suggestedTimeRange: null },
        { text: '最近一周的违规趋势', suggestedTimeRange: '168' },
        { text: '昨天的安全情况', suggestedTimeRange: '48' },
        { text: '本月违规统计', suggestedTimeRange: '720' },
        { text: '所有历史数据分析', suggestedTimeRange: '0' }
      ]

      return [...baseExamples]
    }
  },
  mounted() {
    this.loadUserInfo()
  },
  methods: {
    loadUserInfo() {
      try {
        const userInfo = JSON.parse(sessionStorage.getItem('userInfo') || '{}')
        console.log('从sessionStorage获取的用户信息:', userInfo)

        this.userType = userInfo.userType || ''
        this.userName = userInfo.name || ''

        if (userInfo.userType === 'manager') {
          this.currentEid = userInfo.eid || ''

          if (!this.currentEid) {
            console.warn('Manager信息中缺少EID')
            this.aiError = '用户信息不完整，缺少企业ID'
          }
        } else if (userInfo.userType === 'admin') {
          this.currentEid = 'SYSTEM-ADMIN'
        } else if (userInfo.userType === 'visitor') {
          // visitor 的真实 EID 存在 visitor_token_info 里（由 access token 授权时写入）
          const tokenInfo = JSON.parse(sessionStorage.getItem('visitor_token_info') || '{}')
          this.currentEid = tokenInfo.eid || ''

          if (!this.currentEid) {
            console.warn('Visitor 未找到授权 EID，请先验证访问令牌')
            this.aiError = '请先在设备查找页面验证访问令牌，获取授权后方可使用AI查询'
          } else {
            console.log('Visitor 使用授权 EID:', this.currentEid)
          }
        } else {
          console.error('未识别的用户类型或未登录')
          this.aiError = '请先登录系统'
        }

        console.log('AI查询组件 - 用户类型:', this.userType, '当前EID:', this.currentEid)

      } catch (error) {
        console.error('解析用户信息失败:', error)
        this.aiError = '获取用户信息失败，请重新登录'
      }
    },

    setAIQuery(query, suggestedTimeRange = null) {
      this.aiQuery = query

      // 如果有建议的时间范围，自动设置
      if (suggestedTimeRange !== null) {
        this.queryTimeRange = suggestedTimeRange.toString()
        this.actualTimeRangeUsed = suggestedTimeRange.toString()
        this.timeRangeAdjusted = true

        setTimeout(() => {
          this.timeRangeAdjusted = false
        }, 3000)
      }
    },

    clearAIQuery() {
      this.aiQuery = ''
      this.aiResult = null
      this.aiError = null
      this.timeRangeAdjusted = false
      this.actualTimeRangeUsed = this.queryTimeRange
    },

    handleQueryKeypress(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.submitAIQuery()
      }
    },

    // 智能检测查询中的时间关键词
    detectTimeKeywords(query) {
      const queryLower = query.toLowerCase()

      // 今天/今日相关
      if (queryLower.includes('今天') || queryLower.includes('今日') || queryLower.includes('today')) {
        return '24'
      }

      // 昨天相关
      if (queryLower.includes('昨天') || queryLower.includes('昨日') || queryLower.includes('yesterday')) {
        return '48'
      }

      // 本周相关
      if (queryLower.includes('本周') || queryLower.includes('这周') || queryLower.includes('这一周') || queryLower.includes('this week') || queryLower.includes('一周')) {
        return '168'
      }

      // 本月相关
      if (queryLower.includes('本月') || queryLower.includes('这个月') || queryLower.includes('this month') || queryLower.includes('一个月')) {
        return '720'
      }

      // 所有/全部/历史
      if (queryLower.includes('所有') || queryLower.includes('全部') || queryLower.includes('历史') || queryLower.includes('all')) {
        return '0'
      }

      // 最近X小时
      const hourMatch = queryLower.match(/(\d+)\s*小时/)
      if (hourMatch) {
        return hourMatch[1]
      }

      // 最近X天
      const dayMatch = queryLower.match(/(\d+)\s*天/)
      if (dayMatch) {
        return (parseInt(dayMatch[1]) * 24).toString()
      }

      return null
    },

    async submitAIQuery() {
      if (!this.aiQuery.trim()) {
        this.aiError = '请输入您的问题'
        return
      }

      // 检查 EID 参数
      if (!this.currentEid) {
        this.aiError = '缺少企业ID，请先登录系统'
        return
      }

      this.aiLoading = true
      this.aiError = null
      this.aiResult = null
      this.timeRangeAdjusted = false

      try {
        // 智能检测时间范围
        const detectedTimeRange = this.detectTimeKeywords(this.aiQuery)
        // 修复：parseInt('0') || 24 会错误地将"所有数据"(0)替换为24
        // 改用 ?? 空值合并，只在结果为 null/undefined 时才回退到24
        const parsedRange = parseInt(this.queryTimeRange)
        let finalTimeRange = Number.isNaN(parsedRange) ? 24 : parsedRange
        let shouldAdjustTimeRange = false

        // 如果检测到明确的时间关键词，优先使用检测到的时间范围
        if (detectedTimeRange !== null) {
          finalTimeRange = parseInt(detectedTimeRange)
          shouldAdjustTimeRange = true
          console.log(`检测到时间关键词，自动调整时间范围: ${this.queryTimeRange} -> ${detectedTimeRange}`)
        } else {
          console.log(`使用用户选择的时间范围: ${this.queryTimeRange}，finalTimeRange=${finalTimeRange}`)
        }

        const queryData = {
          query: this.aiQuery,
          time_range_hours: finalTimeRange,
          eid: this.currentEid
        }

        console.log('提交AI查询:', queryData)
        console.log('当前EID值:', this.currentEid)

        const response = await aiAPI.query(queryData)

        if (response.data.success) {
          this.aiResult = response.data

          // 从后端响应中获取实际使用的时间范围
          if (response.data.query_info && response.data.query_info.smart_detected_hours !== undefined) {
            const backendTimeRange = response.data.query_info.smart_detected_hours
            this.actualTimeRangeUsed = backendTimeRange === 0 ? '0' : backendTimeRange.toString()

            // 如果后端调整了时间范围，更新前端显示和标记调整状态
            if (response.data.query_info.time_range_adjusted || shouldAdjustTimeRange) {
              this.queryTimeRange = this.actualTimeRangeUsed
              this.timeRangeAdjusted = true

              // 3秒后隐藏调整提示
              setTimeout(() => {
                this.timeRangeAdjusted = false
              }, 3000)
            }
          } else {
            // 如果后端没有返回时间信息，使用前端检测的结果
            this.actualTimeRangeUsed = finalTimeRange === 0 ? '0' : finalTimeRange.toString()
            if (shouldAdjustTimeRange) {
              this.queryTimeRange = this.actualTimeRangeUsed
              this.timeRangeAdjusted = true

              setTimeout(() => {
                this.timeRangeAdjusted = false
              }, 3000)
            }
          }

          this.$emit('ai-query', queryData)

        } else {
          throw new Error(response.data.message || 'AI查询失败')
        }

      } catch (error) {
        console.error('AI查询失败:', error)
        this.aiError = 'AI查询失败: ' + (error.response?.data?.message || error.message)
      } finally {
        this.aiLoading = false
      }
    }
  }
}
</script>

<style scoped>
.ai-chat-section {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(139, 126, 200, 0.08);
  margin-bottom: 40px;
  overflow: hidden;
}

.chat-header {
  background: linear-gradient(135deg, #90CAF9 0%, #64B5F6 100%);
  color: white;
  padding: 25px 30px;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.3em;
  font-weight: 600;
  margin-bottom: 8px;
}

.chat-subtitle {
  font-size: 1em;
  opacity: 0.9;
  margin-bottom: 8px;
}

.eid-warning {
  background: rgba(255, 193, 7, 0.2);
  color: #856404;
  padding: 10px 15px;
  border-radius: 6px;
  font-size: 0.9em;
  font-weight: 500;
}

.eid-info {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 8px 15px;
  border-radius: 6px;
  font-size: 0.85em;
  font-weight: 500;
}

.chat-body {
  padding: 30px;
}

.query-input-section {
  margin-bottom: 30px;
}

.input-wrapper {
  margin-bottom: 20px;
}

.query-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 15px;
  margin-bottom: 15px;
}

.time-select {
  padding: 10px 15px;
  border: 2px solid #E3F2FD;
  border-radius: 8px;
  background: white;
  font-size: 14px;
  color: #6B7280;
  min-width: 150px;
}

.time-range-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #F7FBFF;
  color: #42A5F5;
  border-radius: 6px;
  font-size: 0.85em;
  font-weight: 500;
  animation: fadeInOut 3s ease-in-out;
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translateY(-10px); }
  20% { opacity: 1; transform: translateY(0); }
  80% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-10px); }
}

.input-container {
  border: 2px solid #E3F2FD;
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.3s ease;
}

.input-container:focus-within {
  border-color: #90CAF9;
  box-shadow: 0 0 0 3px rgba(144, 202, 249, 0.1);
}

.query-input {
  width: 100%;
  padding: 20px;
  border: none;
  font-size: 16px;
  line-height: 1.5;
  resize: vertical;
  min-height: 100px;
  outline: none;
  font-family: inherit;
}

.query-input:disabled {
  background: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.query-input::placeholder {
  color: #cccccc;
}

.input-actions {
  display: flex;
  gap: 10px;
  padding: 15px 20px;
  background: #F7FBFF;
  border-top: 1px solid #E3F2FD;
}

.quick-queries {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.quick-label {
  font-size: 0.9em;
  color: #42A5F5;
  font-weight: 600;
}

.quick-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-btn {
  padding: 8px 16px;
  border: 1px solid #E3F2FD;
  border-radius: 20px;
  background: white;
  color: #6B7280;
  font-size: 0.85em;
  cursor: pointer;
  transition: all 0.3s ease;
}

.quick-btn:hover {
  border-color: #90CAF9;
  color: #42A5F5;
  background: #F7FBFF;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #90CAF9 0%, #64B5F6 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(144, 202, 249, 0.3);
}

.btn-secondary {
  background: #F7FBFF;
  color: #42A5F5;
  border: 1px solid #E3F2FD;
}

.btn-secondary:hover {
  background: #F0F8FF;
  border-color: #BBDEFB;
}

.ai-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #42A5F5;
}

.ai-error {
  background: #FDF2F2;
  color: #DC2626;
  padding: 15px 20px;
  border-radius: 8px;
  border-left: 4px solid #EF4444;
  display: flex;
  align-items: center;
  gap: 10px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #F7FBFF;
  border-top: 3px solid #90CAF9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  font-size: 1.05em;
}

.icon {
  font-size: 1.1em;
}

.debug-info {
  margin-top: 30px;
  padding: 15px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
}

.debug-info h4 {
  margin: 0 0 10px 0;
  color: #666;
}

.debug-info p {
  margin: 5px 0;
  font-family: monospace;
  font-size: 12px;
  color: #333;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .query-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .time-range-notice {
    order: -1;
  }

  .quick-queries {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>