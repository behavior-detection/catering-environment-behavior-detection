<template>
  <div class="historical-data-container">
    <!-- Visitor模式横幅 -->
    <div v-if="isVisitorMode && visitorInfo" class="visitor-mode-banner">
      <div class="banner-content">
        <i class="fas fa-user-shield"></i>
        <div class="banner-text">
          <strong>访问者模式</strong>
          <span>
            {{ visitorInfo.visitor_name }} |
            授权类型: {{ getAccessTypeText(visitorInfo.access_type) }} |
            授权范围: {{ visitorInfo.access_value }} |
            授权人: {{ visitorInfo.approved_by }}
          </span>
        </div>
        <button @click="exitVisitorMode" class="exit-btn">
          <i class="fas fa-sign-out-alt"></i>
          退出访问
        </button>
      </div>
    </div>

    <div class="filter-panel-card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="fas fa-filter"></i>
          历史数据分析
          <span v-if="managerEid" class="eid-badge">EID: {{ managerEid }}</span>
          <span v-if="isVisitorMode && visitorInfo" class="eid-badge visitor">
            访问: {{ visitorInfo.visitor_name  }}
          </span>
        </h3>
        <div class="header-actions">
          <button @click="refreshData" :disabled="isLoading" class="btn btn-primary">
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
            {{ isLoading ? '加载中...' : '刷新数据' }}
          </button>
          <button @click="resetFilters" class="btn btn-outline">
            <i class="fas fa-undo"></i>
            重置筛选
          </button>
        </div>
      </div>

      <div class="card-content">
        <div class="time-range-section">
          <label class="section-label">选择时间段:</label>
          <div class="time-range-buttons">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="selectTimeRange(range.value)"
              :class="['time-btn', { 'active': currentFilter.timeRange === range.value }]"
            >
              <span class="time-title">{{ range.title }}</span>
              <span class="time-desc">{{ range.desc }}</span>
            </button>
          </div>
        </div>

        <div class="filter-status-section">
          <div class="status-info">
            <span class="status-text">{{ filterStatusText }}</span>
            <span class="update-time">最后更新: {{ lastUpdateTime }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误显示区域 -->
    <div v-if="lastError" class="error-panel">
      <h4><i class="fas fa-exclamation-triangle"></i> 错误信息</h4>
      <p>{{ lastError }}</p>
      <details v-if="errorDetails">
        <summary>详细错误信息</summary>
        <pre>{{ errorDetails }}</pre>
      </details>
    </div>

    <div class="statistics-grid">
      <div class="stat-card">
        <div class="stat-icon violations">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div class="stat-content">
          <h4>总违规次数</h4>
          <div class="stat-number">{{ dashboardData.totalViolations }}</div>
          <div class="stat-change">检测违规</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon records">
          <i class="fas fa-file-alt"></i>
        </div>
        <div class="stat-content">
          <h4>总记录数</h4>
          <div class="stat-number">{{ dashboardData.totalRecords }}</div>
          <div class="stat-change">JSON记录</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon cameras">
          <i class="fas fa-video"></i>
        </div>
        <div class="stat-content">
          <h4>活跃摄像头</h4>
          <div class="stat-number">{{ dashboardData.activeCameras }}</div>
          <div class="stat-change">监控设备</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon average">
          <i class="fas fa-chart-line"></i>
        </div>
        <div class="stat-content">
          <h4>平均违规率</h4>
          <div class="stat-number">{{ dashboardData.avgViolations }}</div>
          <div class="stat-change">次/记录</div>
        </div>
      </div>
    </div>

    <!-- ECharts图表区域 -->
    <div class="charts-section">
      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-header">
            <h4><i class="fas fa-chart-pie"></i> 违规类型分布图</h4>
            <div class="chart-actions">
              <button class="chart-btn" @click="toggleChartType('pie')">
                <i class="fas fa-chart-pie"></i>
              </button>
              <button class="chart-btn" @click="toggleChartType('bar')">
                <i class="fas fa-chart-bar"></i>
              </button>
            </div>
          </div>
          <div class="chart-content">
            <div id="violationTypeChart" ref="violationTypeChart" class="chart-container"></div>
            <div v-if="!hasViolationData" class="chart-empty">
              <i class="fas fa-chart-pie"></i>
              <p>暂无违规类型数据</p>
            </div>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <h4><i class="fas fa-video"></i> 摄像头违规统计</h4>
            <div class="chart-actions">
              <button class="chart-btn" @click="exportChart('camera')">
                <i class="fas fa-download"></i>
              </button>
            </div>
          </div>
          <div class="chart-content">
            <div id="cameraChart" ref="cameraChart" class="chart-container"></div>
            <div v-if="!hasCameraData" class="chart-empty">
              <i class="fas fa-video"></i>
              <p>暂无摄像头数据</p>
            </div>
          </div>
        </div>
      </div>

      <div class="chart-card full-width">
        <div class="chart-header">
          <h4><i class="fas fa-chart-line"></i> 违规趋势分析</h4>
          <div class="chart-actions">
            <select class="trend-select" v-model="trendTimeRange" @change="updateTrendChart">
              <option value="24h">24小时</option>
              <option value="7d">7天</option>
              <option value="30d">30天</option>
            </select>
          </div>
        </div>
        <div class="chart-content">
          <div id="trendsChart" ref="trendsChart" class="chart-container"></div>
          <div v-if="!hasTrendData" class="chart-empty">
            <i class="fas fa-chart-line"></i>
            <p>暂无趋势数据</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 违规类型分布 -->
    <div v-if="violationsList.length > 0" class="violations-summary">
      <h4><i class="fas fa-chart-pie"></i> 违规类型分布</h4>
      <div class="violations-grid">
        <div v-for="violation in violationsList" :key="violation.type" class="violation-item">
          <div class="violation-type">{{ getViolationTypeName(violation.type) }}</div>
          <div class="violation-count">{{ violation.count }}</div>
        </div>
      </div>
    </div>

    <div class="records-section">
      <div class="records-header">
        <h4><i class="fas fa-history"></i> 最近检测记录</h4>
        <div class="records-actions">
          <span class="records-count">最新 {{ recentRecords.length }} 条记录</span>
          <button class="btn btn-outline" @click="exportRecords">
            <i class="fas fa-download"></i>
            导出记录
          </button>
        </div>
      </div>

      <div class="records-content">
        <!-- 数据加载提示 -->
        <div v-if="isLoading" class="loading-indicator">
          <i class="fas fa-spinner fa-spin"></i>
          <p>正在加载数据...</p>
        </div>

        <div v-else-if="recentRecords.length === 0" class="records-empty">
          <i class="fas fa-clipboard-list"></i>
          <p>暂无检测记录</p>
        </div>

        <div v-else class="records-table-wrapper">
          <table class="records-table">
            <thead>
              <tr>
                <th>检测时间</th>
                <th>摄像头ID</th>
                <th>违规类型</th>
                <th>违规次数</th>
                <th>检测数量</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in recentRecords" :key="record.id" class="record-row">
                <td class="time-cell">
                  <span class="time-primary">{{ formatChineseTime(record.detection_timestamp || record.timestamp) }}</span>
                  <span class="time-secondary">{{ getTimeAgo(record.detection_timestamp || record.timestamp) }}</span>
                </td>
                <td class="camera-cell">
                  <div class="camera-info">
                    <i class="fas fa-video"></i>
                    <span>{{ record.camera_id }}</span>
                  </div>
                </td>
                <td class="violations-cell">
                  <div class="violations-tags" v-if="record.violations && Object.keys(record.violations).length > 0">
                    <span
                      v-for="(count, type) in record.violations"
                      :key="type"
                      v-if="count > 0"
                      class="violation-tag"
                      :class="getViolationTagClass(type)"
                    >
                      {{ getViolationTypeName(type) }} ({{ count }})
                    </span>
                  </div>
                  <div v-else-if="record.total_violations > 0" class="violations-tags">
                    <span class="violation-tag tag-default">
                      检测记录 ({{ record.total_violations }})
                    </span>
                  </div>
                  <div v-else class="violations-tags">
                    <span class="violation-tag tag-default">无违规</span>
                  </div>
                </td>
                <td class="count-cell">
                  <span class="count-badge" :class="getCountBadgeClass(record.total_violations)">
                    {{ record.total_violations }}
                  </span>
                </td>
                <td class="detection-cell">
                  <div v-if="record.class_numbers" class="class-numbers">
                    <span v-for="(count, type) in record.class_numbers" :key="type" v-if="count > 0" class="class-tag">
                      {{ getViolationTypeName(type) }}: {{ count }}
                    </span>
                  </div>
                </td>
                <td class="actions-cell">
                  <button @click="viewRecordDetails(record)" class="action-btn view">
                    <i class="fas fa-eye"></i>
                  </button>
                  <button @click="analyzeRecord(record)" class="action-btn analyze">
                    <i class="fas fa-chart-bar"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <Transition name="message">
      <div v-if="message.show" :class="['message-toast', `message-${message.type}`]">
        <i :class="getMessageIcon(message.type)"></i>
        <span class="message-text">{{ message.text }}</span>
        <button @click="message.show = false" class="message-close">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </Transition>
  </div>

  <div v-if="showAnalysisModal" class="modal-overlay" @click.self="showAnalysisModal = false">
    <div class="modal-content">
      <h3>记录详细分析</h3>
      <div class="analysis-content">
        <div class="analysis-section">
          <h4>基本信息</h4>
          <p><strong>摄像头:</strong> {{ analysisResult.camera_id }}</p>
          <p><strong>原始时间:</strong> {{ analysisResult._original_timestamp }}</p>
          <p><strong>总违规:</strong> {{ analysisResult.total_violations }}</p>
        </div>
        <div class="analysis-section">
          <h4>违规详情</h4>
          <pre>{{ JSON.stringify(analysisResult.violations || {}, null, 2) }}</pre>
        </div>
        <div class="analysis-section">
          <h4>检测详情</h4>
          <pre>{{ JSON.stringify(analysisResult.class_numbers || {}, null, 2) }}</pre>
        </div>
      </div>
      <button @click="showAnalysisModal = false" class="btn btn-primary">关闭</button>
    </div>
  </div>
</template>

<script>
// 引入 ECharts
import * as echarts from 'echarts'
// 引入 API
import { visitorAPI } from '@/services/api'

export default {
  name: 'HistoricalDataChineseDate',
  props: {
    managerEid: {
      type: String,
      default: ''
    },
    warehouseId: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      isLoading: false,
      lastUpdateTime: '',
      lastError: '',
      errorDetails: '',

      // Visitor模式相关
      isVisitorMode: false,
      visitorAccessToken: '',
      visitorInfo: null,

      currentFilter: {
        timeRange: '24h'
      },

      // 数据存储
      dashboardData: {
        totalViolations: 0,
        totalRecords: 0,
        activeCameras: 0,
        avgViolations: 0
      },

      violationsList: [],
      camerasList: [],
      recentRecords: [],

      // 图表相关数据
      trendTimeRange: '24h',
      currentHourlyData: {},
      violationChartType: 'pie', // 添加：跟踪违规类型图表的当前类型

      // 图表实例
      violationTypeChart: null,
      cameraChart: null,
      trendsChart: null,

      // 时间范围选项
      timeRanges: [
        { value: '1h', title: '1小时', desc: '最近1小时' },
        { value: '24h', title: '24小时', desc: '今日数据' },
        { value: '7d', title: '7天', desc: '本周统计' },
        { value: '30d', title: '30天', desc: '月度汇总' },
        { value: 'all', title: '全部', desc: '所有历史' }
      ],

      // 违规类型映射
      violationMapping: {
        'mask': '未佩戴口罩',
        'hat': '未佩戴工作帽',
        'phone': '使用手机',
        'cigarette': '吸烟行为',
        'mouse': '鼠患问题',
        'uniform': '工作服违规',
        'person': '人员检测'
      },

      // 违规类型颜色映射
      violationColors: {
        'mask': '#A8D4F1',
        'hat': '#B5E3F7',
        'phone': '#9FC5E8',
        'cigarette': '#C2E0F4',
        'mouse': '#D6EBF5',
        'uniform': '#B8D9F1',
        'person': '#C2E0F4',
        'no_mask': '#A8D4F1',
        'no_hat': '#B5E3F7',
        'phone_usage': '#9FC5E8',
        'smoking': '#C2E0F4',
        'mouse_infestation': '#D6EBF5',
        'uniform_violation': '#B8D9F1',
        'unknown': '#D1D5DB'
      },

      message: {
        show: false,
        type: 'info',
        text: ''
      },

      showAnalysisModal: false,
      analysisResult: {}
    }
  },
  computed: {
    filterStatusText() {
      const timeDesc = this.getTimeRangeDescription(this.currentFilter.timeRange)
      return `当前显示 ${timeDesc} 数据,共 ${this.recentRecords.length} 条记录`
    },

    hasViolationData() {
      return this.violationsList.length > 0
    },

    hasCameraData() {
      return this.camerasList.length > 0
    },

    hasTrendData() {
      return this.dashboardData.totalRecords > 0
    }
  },
  mounted() {
    // 检查Visitor模式
    this.checkVisitorMode()

    this.initCharts()
    this.loadData()

    // 窗口大小变化时重新调整图表
    window.addEventListener('resize', this.handleResize)
  },
  beforeUnmount() {
    // 销毁图表实例
    if (this.violationTypeChart) {
      this.violationTypeChart.dispose()
    }
    if (this.cameraChart) {
      this.cameraChart.dispose()
    }
    if (this.trendsChart) {
      this.trendsChart.dispose()
    }

    window.removeEventListener('resize', this.handleResize)
  },
  methods: {
    // 新增: 检查Visitor模式
    checkVisitorMode() {
      const savedToken = sessionStorage.getItem('visitor_access_token')
      const savedInfo = sessionStorage.getItem('visitor_token_info')

      if (savedToken && savedInfo) {
        this.isVisitorMode = true
        this.visitorAccessToken = savedToken
        this.visitorInfo = JSON.parse(savedInfo)

        console.log('Visitor模式已启用:', this.visitorInfo)
      }
    },

    // 新增: 退出Visitor模式
    exitVisitorMode() {
      if (confirm('确定要退出访问模式吗?')) {
        sessionStorage.removeItem('visitor_access_token')
        sessionStorage.removeItem('visitor_token_info')

        this.isVisitorMode = false
        this.visitorAccessToken = ''
        this.visitorInfo = null

        this.showMessage('已退出访问模式', 'info')

        // 可选: 刷新页面或跳转
        setTimeout(() => {
          window.location.reload()
        }, 1000)
      }
    },

    // 新增: 获取授权类型文本
    getAccessTypeText(type) {
      return type === 'warehouse' ? '仓库访问' : '时间段访问'
    },

    // 初始化图表
    initCharts() {
      this.$nextTick(() => {
        if (this.$refs.violationTypeChart) {
          this.violationTypeChart = echarts.init(this.$refs.violationTypeChart)
        }
        if (this.$refs.cameraChart) {
          this.cameraChart = echarts.init(this.$refs.cameraChart)
        }
        if (this.$refs.trendsChart) {
          this.trendsChart = echarts.init(this.$refs.trendsChart)
        }
      })
    },

    // 处理窗口大小变化
    handleResize() {
      if (this.violationTypeChart) {
        this.violationTypeChart.resize()
      }
      if (this.cameraChart) {
        this.cameraChart.resize()
      }
      if (this.trendsChart) {
        this.trendsChart.resize()
      }
    },

    // 修改: 加载数据 - 支持Visitor模式
    async loadData() {
      this.isLoading = true
      this.lastError = ''
      this.errorDetails = ''

      try {
        let response
        let apiUrl

        // Visitor模式
        if (this.isVisitorMode && this.visitorAccessToken) {
          const params = new URLSearchParams({
            access_token: this.visitorAccessToken,
            range: this.currentFilter.timeRange
          })
          apiUrl = `/api/monitor/visitor/authorized-data/?${params}`

          console.log('Visitor模式 - 发送请求到:', apiUrl)

          response = await visitorAPI.getAuthorizedData(
            this.visitorAccessToken,
            this.currentFilter.timeRange
          )

          const result = response.data

          if (result.success) {
            this.processData(result.data)
            this.visitorInfo = result.visitor_info
            this.updateLastUpdateTime()
            this.showMessage(
              `数据加载成功 (访问者: ${result.visitor_info.visitor_name})`,
              'success'
            )
          } else {
            throw new Error(result.message || '数据加载失败')
          }
        }
        // Manager模式
        else if (this.managerEid) {
          const params = new URLSearchParams({
            eid: this.managerEid,
            range: this.currentFilter.timeRange
          })
          apiUrl = `/api/monitor/violations/by-eid/?${params}`

          console.log('Manager模式 - 发送请求到:', apiUrl)

          response = await fetch(apiUrl, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
          })

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const result = await response.json()

          if (result.success) {
            this.processData(result.data)
            this.updateLastUpdateTime()
            this.showMessage('数据加载成功', 'success')
          } else {
            throw new Error(result.message || '数据加载失败')
          }
        }
        // 通用分析接口
        else {
          const params = new URLSearchParams({
            range: this.currentFilter.timeRange,
            all: this.currentFilter.timeRange === 'all' ? 'true' : 'false'
          })
          apiUrl = `/api/monitor/violations/analytics/?${params}`

          response = await fetch(apiUrl, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
          })

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const result = await response.json()

          if (result.success) {
            this.processData(result.data)
            this.updateLastUpdateTime()
            this.showMessage('数据加载成功', 'success')
          } else {
            throw new Error(result.message || '数据加载失败')
          }
        }
      } catch (error) {
        console.error('加载数据失败:', error)
        this.lastError = error.message
        this.errorDetails = error.stack || ''
        this.showMessage('加载数据失败: ' + error.message, 'error')
      } finally {
        this.isLoading = false
      }
    },

    processData(data) {
      console.log('处理数据:', data)

      try {
        // 处理汇总数据
        if (data.summary) {
          this.dashboardData = {
            totalViolations: data.summary.total_violations || 0,
            totalRecords: data.summary.total_records || 0,
            activeCameras: data.summary.active_cameras || 0,
            avgViolations: data.summary.total_records > 0
              ? (data.summary.total_violations / data.summary.total_records).toFixed(2)
              : 0
          }
        }

        // 处理违规类型数据
        this.violationsList = Object.entries(data.violations_by_type || {}).map(([type, count]) => ({
          type,
          count,
          name: this.violationMapping[type] || type
        }))

        // 处理摄像头数据
        this.camerasList = Object.entries(data.violations_by_camera || {}).map(([camera, count]) => ({
          camera,
          count
        }))

        // 保存按小时数据用于图表
        this.currentHourlyData = data.violations_by_hour || {}

        // 处理最近记录
        this.recentRecords = (data.recent_records || []).map(record => {
          // 确保时间字段正确
          if (!record.detection_timestamp && record.timestamp) {
            record.detection_timestamp = record.timestamp
          }

          return record
        })

        // 更新图表
        this.updateCharts()

        console.log('处理后的记录数:', this.recentRecords.length)
        if (this.recentRecords.length > 0) {
          console.log('最近记录样本:', this.recentRecords[0])
        }

      } catch (error) {
        console.error('数据处理错误:', error)
        this.lastError = '数据处理失败: ' + error.message
      }
    },

    // 更新图表
    updateCharts() {
      this.$nextTick(() => {
        this.updateViolationTypeChart()
        this.updateCameraChart()
        this.updateTrendsChart()
      })
    },

    // 更新违规类型分布图
    updateViolationTypeChart() {
      if (!this.violationTypeChart || this.violationsList.length === 0) {
        return
      }

      let option = {}

      if (this.violationChartType === 'pie') {
        // 饼图配置
        const data = this.violationsList.map(violation => ({
          name: violation.name,
          value: violation.count,
          itemStyle: {
            color: this.violationColors[violation.type] || '#D1D5DB'
          }
        }))

        option = {
          tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
          },
          legend: {
            orient: 'vertical',
            left: 'left',
            top: 'center',
            textStyle: {
              fontSize: 12,
              color: '#6B7280'
            }
          },
          series: [{
            name: '违规类型',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['60%', '50%'],
            avoidLabelOverlap: false,
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: '16',
                fontWeight: 'bold'
              }
            },
            labelLine: {
              show: false
            },
            data: data
          }]
        }
      } else if (this.violationChartType === 'bar') {
        // 柱状图配置 - 添加必需的坐标系
        option = {
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow'
            }
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            top: '8%',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            data: this.violationsList.map(v => v.name),
            axisLabel: {
              interval: 0,
              rotate: 30,
              color: '#6B7280',
              fontSize: 11
            }
          },
          yAxis: {
            type: 'value',
            name: '违规次数',
            axisLabel: {
              color: '#6B7280'
            }
          },
          series: [{
            name: '违规次数',
            type: 'bar',
            data: this.violationsList.map((violation, index) => ({
              value: violation.count,
              itemStyle: {
                color: this.violationColors[violation.type] || this.getSoftColor(index)
              }
            })),
            barWidth: '50%'
          }]
        }
      }

      this.violationTypeChart.setOption(option, true)
    },

    // 更新摄像头统计图
    updateCameraChart() {
      if (!this.cameraChart || this.camerasList.length === 0) {
        return
      }

      const sortedCameras = this.camerasList.slice(0, 10)

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        grid: {
          left: '15%',
          right: '4%',
          bottom: '8%',
          top: '5%',
          containLabel: true
        },
        xAxis: {
          type: 'value',
          name: '违规次数',
          nameLocation: 'middle',
          nameGap: 30,
          axisLabel: {
            color: '#6B7280'
          }
        },
        yAxis: {
          type: 'category',
          data: sortedCameras.map(camera => camera.camera),
          axisLabel: {
            interval: 0,
            fontSize: 12,
            width: 100,
            overflow: 'truncate',
            color: '#6B7280'
          }
        },
        series: [{
          name: '违规次数',
          type: 'bar',
          data: sortedCameras.map((camera, index) => ({
            value: camera.count,
            itemStyle: {
              color: this.getSoftColor(index)
            }
          })),
          barWidth: '60%'
        }]
      }

      this.cameraChart.setOption(option, true)
    },

    // 更新趋势图
    updateTrendsChart() {
      if (!this.trendsChart) {
        return
      }

      const violationsByHour = this.currentHourlyData || {}
      const hours = []
      const data = []

      for (let i = 0; i < 24; i++) {
        hours.push(i + '时')
        data.push(violationsByHour[i] || 0)
      }

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            return `${params[0].name}: ${params[0].value}次违规`
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: hours,
          axisLabel: {
            interval: 2,
            color: '#6B7280'
          }
        },
        yAxis: {
          type: 'value',
          name: '违规次数',
          axisLabel: {
            color: '#6B7280'
          }
        },
        series: [{
          name: '违规次数',
          type: 'line',
          smooth: true,
          data: data,
          itemStyle: {
            color: '#42A5F5'
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(66, 165, 245, 0.4)' },
                { offset: 1, color: 'rgba(66, 165, 245, 0.1)' }
              ]
            }
          }
        }]
      }

      this.trendsChart.setOption(option, true)
    },

    // 获取柔和颜色
    getSoftColor(index) {
      const colors = ['#a8d4f1','#b5e3f7','#9fc5e8','#c2e0f4','#d6ebf5','#b8d9f1']
      return colors[index % colors.length]
    },

    selectTimeRange(range) {
      console.log('选择时间范围:', range)
      this.currentFilter.timeRange = range
      this.loadData()
    },

    refreshData() {
      console.log('刷新数据')
      this.loadData()
    },

    resetFilters() {
      console.log('重置筛选')
      this.currentFilter.timeRange = '24h'
      this.loadData()
    },

    formatChineseTime(timestamp) {
      if (!timestamp) return '无时间信息'

      try {
        const date = new Date(timestamp)
        if (isNaN(date.getTime())) {
          return '时间格式错误'
        }

        // 转换为中文格式显示
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        const hour = String(date.getHours()).padStart(2, '0')
        const minute = String(date.getMinutes()).padStart(2, '0')
        const second = String(date.getSeconds()).padStart(2, '0')

        const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
        const weekday = weekdays[date.getDay()]

        return `${year}年${month}月${day}日${weekday}${hour}:${minute}:${second}`
      } catch (error) {
        console.error('时间格式化错误:', error, timestamp)
        return '时间解析失败'
      }
    },

    getTimeAgo(timestamp) {
      if (!timestamp) return ''

      try {
        const date = new Date(timestamp)
        const now = new Date()
        const diff = now - date

        if (diff < 60000) return '刚刚'
        if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
        return `${Math.floor(diff / 86400000)}天前`
      } catch (error) {
        return ''
      }
    },

    getViolationTypeName(type) {
      return this.violationMapping[type] || type
    },

    getViolationTagClass(type) {
      const classMap = {
        'mask': 'tag-mask',
        'smoking': 'tag-smoking',
        'cigarette': 'tag-smoking',
        'hat': 'tag-hat',
        'phone': 'tag-phone',
        'uniform': 'tag-uniform',
        'mouse': 'tag-mouse',
        'person': 'tag-person'
      }
      return classMap[type] || 'tag-default'
    },

    getCountBadgeClass(count) {
      if (count === 0) return 'badge-low'
      if (count <= 2) return 'badge-low'
      if (count <= 5) return 'badge-medium'
      return 'badge-high'
    },

    getTimeRangeDescription(range) {
      const mapping = {
        '1h': '最近1小时',
        '24h': '最近24小时',
        '7d': '最近7天',
        '30d': '最近30天',
        'all': '所有历史数据'
      }
      return mapping[range] || '最近24小时'
    },

    updateLastUpdateTime() {
      this.lastUpdateTime = new Date().toLocaleString('zh-CN')
    },

    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, 5000)
    },

    getMessageIcon(type) {
      const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }
      return icons[type] || icons.info
    },

    viewRecordDetails(record) {
      console.log('查看记录详情:', record)
      this.analysisResult = record
      this.showAnalysisModal = true
    },

    analyzeRecord(record) {
      console.log('分析记录:', record)
      this.analysisResult = record
      this.showAnalysisModal = true
    },

    exportRecords() {
      console.log('导出记录')
      const dataStr = JSON.stringify(this.recentRecords, null, 2)
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)

      const exportFileDefaultName = `violations_${this.currentFilter.timeRange}_${new Date().toISOString().slice(0,10)}.json`

      const linkElement = document.createElement('a')
      linkElement.setAttribute('href', dataUri)
      linkElement.setAttribute('download', exportFileDefaultName)
      linkElement.click()
    },

    // 图表相关方法
    toggleChartType(type) {
      console.log('切换图表类型:', type)
      // 更新图表类型
      this.violationChartType = type
      // 重新渲染违规类型图表
      this.updateViolationTypeChart()
    },

    exportChart(chartType) {
      const map = {
        pie: this.violationTypeChart,
        camera: this.cameraChart,
        trend: this.trendsChart
      }
      const inst = map[chartType]
      if (!inst) {
        this.showMessage?.('暂无可导出的图表', 'warning')
        return
      }
      try {
        // 背景设为白色，像素倍数高一些导出更清晰
        const url = inst.getDataURL({
          type: 'png',
          pixelRatio: 2,
          backgroundColor: '#fff'
        })
        const a = document.createElement('a')
        const ts = new Date()
          .toISOString()
          .replace(/[:T]/g, '-')
          .split('.')[0]
        a.href = url
        a.download = `摄像头违规统计-${chartType}-${ts}.png`
        // 触发下载
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      } catch (e) {
        console.error(e)
        // 某些浏览器策略阻止 a.click()，兜底打开新窗口
        try { window.open(inst.getDataURL({ type: 'png' })) } catch (_) {}
        this.showMessage?.('导出图表失败', 'error')
      }
    },

    updateTrendChart() {
      console.log('更新趋势图:', this.trendTimeRange)
      this.updateTrendsChart()
    }
  }
}
</script>

<style scoped>
/* 基础样式 */
.historical-data-container {
  padding: 20px;
  background-color: #F8FAFC;
  min-height: 100vh;
}

/* Visitor模式横幅样式 */
.visitor-mode-banner {
  background: #5ba0c3;
  color: white;
  padding: 16px 24px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.banner-content i {
  font-size: 32px;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.banner-text strong {
  font-size: 16px;
}

.banner-text span {
  font-size: 14px;
  opacity: 0.9;
}

.exit-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  transition: all 0.3s;
}

.exit-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 调试面板样式 */
/* 卡片样式 */
.filter-panel-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E3F2FD;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 12px;
}

.eid-badge {
  background: #42A5F5;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.eid-badge.visitor {
  background: #5ba0c3;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 按钮样式 */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #42A5F5;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1E88E5;
}

.btn-outline {
  background: white;
  color: #42A5F5;
  border: 1px solid #42A5F5;
}

.btn-outline:hover {
  background: #F7FBFF;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

/* 时间范围选择 */
.card-content {
  padding: 24px;
}

.time-range-section {
  margin-bottom: 24px;
}

.section-label {
  display: block;
  margin-bottom: 12px;
  font-weight: 600;
  color: #374151;
}

.time-range-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.time-btn {
  background: white;
  border: 2px solid #E3F2FD;
  border-radius: 8px;
  padding: 16px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.time-btn:hover {
  border-color: #42A5F5;
  background: #F7FBFF;
}

.time-btn.active {
  border-color: #42A5F5;
  background: #42A5F5;
  color: white;
}

.time-title {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
}

.time-desc {
  display: block;
  font-size: 12px;
  opacity: 0.8;
}

/* 统计网格 */
.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

.stat-icon.violations { background: #EF5350; }
.stat-icon.records { background: #42A5F5; }
.stat-icon.cameras { background: #26C6DA; }
.stat-icon.average { background: #66BB6A; }

.stat-content h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #6B7280;
  font-weight: 500;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #374151;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-change {
  font-size: 12px;
  color: #9CA3AF;
}

/* 图表区域 */
.charts-section {
  margin-bottom: 24px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-card {
  background: #ffffff;
  border: 1px solid #E3F2FD;
  border-radius: 12px;
  box-shadow: 0 1px 3px 0 rgba(66, 165, 245, 0.1), 0 1px 2px 0 rgba(66, 165, 245, 0.06);
  margin-bottom: 24px;
}

.chart-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E3F2FD;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-actions {
  display: flex;
  gap: 8px;
}

.chart-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #E3F2FD;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  color: #42A5F5;
}

.chart-btn:hover {
  background: #F7FBFF;
  border-color: #90CAF9;
}

.trend-select {
  padding: 6px 12px;
  border: 1px solid #E3F2FD;
  border-radius: 6px;
  background: white;
  color: #6B7280;
}

.chart-content {
  padding: 24px;
  height: 300px;
  position: relative;
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
}

.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: #9CA3AF;
}

.chart-empty i {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

/* 违规类型分布 */
.violations-summary {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 30px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.violations-summary h4 {
  margin: 0 0 16px 0;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
}

.violations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.violation-item {
  background: #F7FBFF;
  border: 1px solid #E3F2FD;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.violation-type {
  font-size: 14px;
  color: #6B7280;
  margin-bottom: 4px;
}

.violation-count {
  font-size: 1.5rem;
  font-weight: 700;
  color: #42A5F5;
}

/* 记录表格 */
.records-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.records-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E3F2FD;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.records-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
}

.records-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.records-count {
  color: #6B7280;
  font-size: 14px;
}

.records-content {
  padding: 24px;
}

.loading-indicator {
  text-align: center;
  padding: 40px;
  color: #666;
}

.loading-indicator i {
  font-size: 24px;
  margin-bottom: 8px;
}

.records-empty {
  text-align: center;
  color: #9CA3AF;
  padding: 48px 0;
}

.records-empty i {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-hint {
  color: #999;
  font-size: 14px;
  margin-top: 8px;
}

.records-table-wrapper {
  overflow-x: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th,
.records-table td {
  padding: 16px 12px;
  text-align: left;
  border-bottom: 1px solid #F3F4F6;
}

.records-table th {
  background: #F7FBFF;
  font-weight: 600;
  color: #6B7280;
  font-size: 14px;
}

.record-row:hover {
  background: #F7FBFF;
}

.time-cell {
  font-family: 'SF Mono', Monaco, Inconsolata, 'Roboto Mono', monospace;
}

.time-primary {
  display: block;
  color: #374151;
  font-weight: 500;
}

.time-secondary {
  display: block;
  color: #6B7280;
  font-size: 12px;
  margin-top: 2px;
}

.camera-cell .camera-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #42A5F5;
}

.violations-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.violation-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: white;
}

.tag-mask { background: #EF5350; }
.tag-smoking { background: #FF7043; }
.tag-hat { background: #FFA726; }
.tag-phone { background: #42A5F5; }
.tag-uniform { background: #AB47BC; }
.tag-mouse { background: #8D6E63; }
.tag-person { background: #66BB6A; }
.tag-default { background: #9E9E9E; }

.count-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  color: white;
}

.badge-low { background: #66BB6A; }
.badge-medium { background: #FFA726; }
.badge-high { background: #EF5350; }

.detection-cell .class-numbers {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.class-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  background: #F5F5F5;
  color: #666;
}

.actions-cell {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #E3F2FD;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #F7FBFF;
}

.action-btn.view { color: #42A5F5; }
.action-btn.analyze { color: #26C6DA; }

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  min-width: 500px;
  max-width: 80%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h3 {
  margin-top: 0;
  color: #374151;
}

.analysis-content {
  margin: 20px 0;
}

.analysis-section {
  margin-bottom: 20px;
}

.analysis-section h4 {
  margin: 0 0 8px 0;
  color: #6B7280;
}

.analysis-section pre {
  background-color: #F9FAFB;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

/* 错误面板 */
.error-panel {
  background: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.error-panel h4 {
  margin: 0 0 12px 0;
  color: #c62828;
}

.error-panel p {
  margin: 8px 0;
  color: #c62828;
}

/* 消息提示样式 */
.message-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 16px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1000;
  min-width: 300px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.message-success {
  background: #e8f5e8;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.message-error {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.message-text {
  flex: 1;
}

.message-close {
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
}

.message-close:hover {
  opacity: 1;
}

/* 动画 */
.message-enter-active, .message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.message-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* 状态信息 */
.filter-status-section {
  padding-top: 20px;
  border-top: 1px solid #F3F4F6;
}

.status-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-text {
  color: #6B7280;
  font-size: 14px;
}

.update-time {
  color: #9CA3AF;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .charts-row {
    grid-template-columns: 1fr;
  }

  .statistics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .historical-data-container {
    padding: 12px;
  }

  .statistics-grid {
    grid-template-columns: 1fr;
  }

  .time-range-buttons {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }

  .records-table-wrapper {
    font-size: 14px;
  }

  .records-table th,
  .records-table td {
    padding: 12px 8px;
  }

  .banner-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>