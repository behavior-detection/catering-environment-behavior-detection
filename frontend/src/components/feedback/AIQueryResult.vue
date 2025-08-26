<!-- components/feedback/AIQueryResult.vue -->
<template>
  <div class="ai-result-section">
    <div class="result-header">
      <i class="icon">🎯</i>
      <span>AI分析结果</span>
    </div>

    <div class="result-content">
      <!-- 查询问题 -->
      <div class="query-display">
        <div class="query-label">查询问题:</div>
        <div class="query-text">{{ result.query }}</div>
      </div>

      <!-- 分析范围 -->
      <div class="analysis-scope">
        <div class="scope-label">分析范围:</div>
        <div class="scope-text">
          {{ getTimeRangeDescription() }}
          <span v-if="isTimeRangeAdjusted()" class="adjusted-notice">
            <i class="icon">🔄</i>
            (AI自动调整)
          </span>
        </div>
      </div>

      <!-- AI回答 -->
      <div v-if="result.analysis?.direct_answer" class="direct-answer">
        <div class="answer-label">AI回答:</div>
        <div class="answer-text">{{ result.analysis.direct_answer }}</div>
      </div>

      <!-- 详细分析 -->
      <div v-if="result.analysis?.detailed_explanation" class="detailed-analysis">
        <div class="analysis-label">详细分析:</div>
        <div class="analysis-text" v-html="formatAnalysisText(result.analysis.detailed_explanation)"></div>
      </div>

      <!-- 改进建议 -->
      <div v-if="result.analysis?.suggestions?.length" class="suggestions">
        <div class="suggestions-label">改进建议:</div>
        <ul class="suggestions-list">
          <li v-for="suggestion in result.analysis.suggestions" :key="suggestion">
            {{ suggestion }}
          </li>
        </ul>
      </div>

      <!-- 数据概览 -->
      <div v-if="result.data_summary" class="data-overview">
        <div class="overview-label">数据概览:</div>
        <div class="overview-stats">
          <div class="overview-item">
            <div class="overview-value">{{ result.data_summary.total_violations || 0 }}</div>
            <div class="overview-desc">总违规</div>
          </div>
          <div class="overview-item">
            <div class="overview-value">{{ result.data_summary.total_records || 0 }}</div>
            <div class="overview-desc">检测记录</div>
          </div>
          <div class="overview-item">
            <div class="overview-value">{{ result.data_summary.active_cameras || 0 }}</div>
            <div class="overview-desc">活跃摄像头</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AIQueryResult',
  props: {
    result: {
      type: Object,
      required: true
    },
    queryTimeRange: {
      type: String,
      default: '24'
    }
  },
  computed: {
    showDebugInfo() {
      return process.env.NODE_ENV === 'development'
    }
  },
  methods: {
    formatAnalysisText(text) {
      if (!text) return ''
      return text
        .replace(/\n/g, '<br>')
        .replace(/•\s*/g, '• ')
        .replace(/(\d+\.)/g, '<strong>$1</strong>')
        .replace(/(📊|📈|📉|🎯|💡|⚠️|✅|🔴|🟡|🟢|🟠|❌|🔄|📌|🚨|👷|😷|📱|🚭|🔍)/g, '<span class="emoji">$1</span>')
    },

    getTimeRangeDescription() {
      // 优先使用后端返回的时间描述
      if (this.result.data_summary?.time_description) {
        return `基于${this.result.data_summary.time_description}的数据`
      }

      // 如果后端没有返回，从查询信息中获取实际使用的时间范围
      const actualHours = this.result.query_info?.smart_detected_hours

      if (actualHours !== undefined && actualHours !== null) {
        return `基于${this.formatTimeRange(actualHours)}的数据`
      }

      // 最后的备用方案
      const fallbackHours = parseInt(this.queryTimeRange) || 24
      return `基于${this.formatTimeRange(fallbackHours)}的数据`
    },

    formatTimeRange(hours) {
      if (hours === 0) return '所有历史数据'
      if (hours === 1) return '最近1小时'
      if (hours === 24) return '最近24小时'
      if (hours === 48) return '最近48小时'
      if (hours === 168) return '最近7天'
      if (hours === 720) return '最近30天'
      return `最近${hours}小时`
    },

    isTimeRangeAdjusted() {
      return this.result.query_info?.time_range_adjusted === true
    }
  }
}
</script>

<style scoped>
.ai-result-section {
  margin-top: 30px;
  border: 2px solid #E3F2FD;
  border-radius: 12px;
  background: linear-gradient(135deg, #FDFDFF 0%, #F7FBFF 100%);
  overflow: hidden;
}

.result-header {
  background: linear-gradient(135deg, #90CAF9 0%, #64B5F6 100%);
  color: white;
  padding: 15px 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.result-content {
  padding: 25px;
}

.query-display,
.analysis-scope,
.direct-answer,
.detailed-analysis,
.suggestions,
.data-overview,
.debug-info {
  margin-bottom: 20px;
}

.query-label,
.scope-label,
.answer-label,
.analysis-label,
.suggestions-label,
.overview-label,
.debug-label {
  font-weight: 600;
  color: #6B7280;
  margin-bottom: 8px;
  font-size: 1.05em;
}

.query-text {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #90CAF9;
  font-style: italic;
}

.scope-text {
  background: #F7FBFF;
  padding: 12px 15px;
  border-radius: 8px;
  color: #42A5F5;
  font-size: 0.95em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.adjusted-notice {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.8);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 500;
}

.answer-text {
  background: white;
  padding: 20px;
  border-radius: 8px;
  font-size: 1.1em;
  line-height: 1.6;
  border-left: 4px solid #A8C8EC;
}

.analysis-text {
  background: white;
  padding: 20px;
  border-radius: 8px;
  line-height: 1.6;
  color: #6B7280;
}

.analysis-text :deep(.emoji) {
  font-size: 1.1em;
}

.suggestions-list {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin: 0;
  padding-left: 40px;
}

.suggestions-list li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
}

.overview-item {
  background: white;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.overview-value {
  font-size: 1.8em;
  font-weight: bold;
  color: #90CAF9;
  margin-bottom: 5px;
}

.overview-desc {
  font-size: 0.85em;
  color: #42A5F5;
}

.debug-info {
  background: #F7FBFF;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #E3F2FD;
}

.debug-label {
  color: #EF4444;
  font-size: 0.9em;
  margin-bottom: 10px;
}

.debug-content {
  font-size: 0.85em;
  color: #42A5F5;
  line-height: 1.4;
}

.debug-content div {
  margin-bottom: 4px;
}

.icon {
  font-size: 1.1em;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .overview-stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .scope-text {
    flex-direction: column;
    align-items: flex-start;
  }

  .adjusted-notice {
    align-self: flex-start;
  }
}
</style>