<template>
  <div class="historical-data-container">
    <div class="filter-panel-card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="fas fa-filter"></i>
          数据筛选控制
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
          <button @click="clearData" class="btn btn-danger">
            <i class="fas fa-trash"></i>
            清空数据
          </button>
        </div>
      </div>

      <div class="card-content">
        <div class="time-range-section">
          <label class="section-label">选择时间段：</label>
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

    <div class="statistics-grid">
      <div class="stat-card">
        <div class="stat-icon violations">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div class="stat-content">
          <h4>总违规次数</h4>
          <div class="stat-number">{{ dashboardData.totalViolations }}</div>
          <div class="stat-change">较昨日</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon records">
          <i class="fas fa-file-alt"></i>
        </div>
        <div class="stat-content">
          <h4>总记录数</h4>
          <div class="stat-number">{{ dashboardData.totalRecords }}</div>
          <div class="stat-change">检测记录</div>
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

    <div class="data-section">
      <div class="data-row">
        <div class="data-card">
          <div class="data-header">
            <h4><i class="fas fa-list-ul"></i> 违规类型统计</h4>
            <span class="data-count">{{ violationsList.length }} 种类型</span>
          </div>
          <div class="data-content">
            <div v-if="violationsList.length === 0" class="data-empty">
              <i class="fas fa-inbox"></i>
              <p>暂无违规数据</p>
            </div>
            <div v-else class="violations-list">
              <div
                v-for="violation in violationsList.slice(0, 10)"
                :key="violation.type"
                class="violation-item"
              >
                <div class="violation-info">
                  <span class="violation-name">{{ violation.name }}</span>
                  <span class="violation-type">{{ violation.type }}</span>
                </div>
                <div class="violation-stats">
                  <span class="violation-count">{{ violation.count }}</span>
                  <div class="violation-bar">
                    <div class="violation-progress" :style="{ width: getViolationPercentage(violation.count) + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="data-card">
          <div class="data-header">
            <h4><i class="fas fa-video"></i> 摄像头统计</h4>
            <span class="data-count">{{ camerasList.length }} 个设备</span>
          </div>
          <div class="data-content">
            <div v-if="camerasList.length === 0" class="data-empty">
              <i class="fas fa-video-slash"></i>
              <p>暂无摄像头数据</p>
            </div>
            <div v-else class="cameras-list">
              <div
                v-for="camera in camerasList.slice(0, 10)"
                :key="camera.camera_id"
                class="camera-item"
              >
                <div class="camera-info">
                  <div class="camera-icon">
                    <i class="fas fa-video"></i>
                  </div>
                  <div class="camera-details">
                    <span class="camera-id">{{ camera.camera_id }}</span>
                    <span class="camera-location">{{ getCameraLocation(camera.camera_id) }}</span>
                  </div>
                </div>
                <div class="camera-stats">
                  <span class="camera-violations">{{ camera.violations }}</span>
                  <span class="camera-label">次违规</span>
                </div>
              </div>
            </div>
          </div>
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
        <div v-if="recentRecords.length === 0" class="records-empty">
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
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in recentRecords" :key="record.id" class="record-row">
                <td class="time-cell">
                  <span class="time-primary">{{ formatTime(record.detection_timestamp) }}</span>
                  <span class="time-secondary">{{ getTimeAgo(record.detection_timestamp) }}</span>
                </td>
                <td class="camera-cell">
                  <div class="camera-info">
                    <i class="fas fa-video"></i>
                    <span>{{ record.camera_id }}</span>
                  </div>
                </td>
                <td class="violations-cell">
                  <div class="violations-tags" v-if="record.formatted_violations && Object.keys(record.formatted_violations).length > 0">
                    <span
                      v-for="(count, type) in record.formatted_violations"
                      :key="type"
                      class="violation-tag"
                      :class="getViolationTagClass(type)"
                    >
                      {{ violationMapping[type] || type }} ({{ count }})
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
      <h3>记录ID: {{ analysisResult.id }} 的详细分析</h3>
      <pre>{{ analysisResult }}</pre>
      <button @click="showAnalysisModal = false">关闭</button>
    </div>
  </div>
</template>

<script>
// 引入 ECharts
import * as echarts from 'echarts'
import { violationsAPI } from '@/services/api'

export default {
  name: 'HistoricalData',
  data() {
    return {
      // 基础状态
      isLoading: false,
      lastUpdateTime: '--',

      // 筛选状态
      currentFilter: {
        timeRange: '24h'
      },

      // 时间范围选项
      timeRanges: [
        { value: '1h', title: '1小时', desc: '最近1小时' },
        { value: '24h', title: '24小时', desc: '最近1天' },
        { value: '7d', title: '7天', desc: '最近一周' },
        { value: '30d', title: '30天', desc: '最近一月' },
        { value: 'all', title: '全部', desc: '所有数据' }
      ],

      // 仪表盘数据
      dashboardData: {
        totalViolations: 0,
        totalRecords: 0,
        activeCameras: 0,
        avgViolations: 0
      },

      // 列表数据
      violationsList: [],
      camerasList: [],
      recentRecords: [],

      // 图表相关数据
      trendTimeRange: '24h',
      currentHourlyData: {},

      // 图表实例
      violationTypeChart: null,
      cameraChart: null,
      trendsChart: null,

      // 消息提示
      message: {
        show: false,
        type: 'info',
        text: ''
      },

      // 违规类型映射
      violationMapping: {
        'mask': '未佩戴口罩',
        'hat': '未佩戴工作帽',
        'phone': '使用手机',
        'cigarette': '吸烟行为',
        'mouse': '鼠患问题',
        'uniform': '工作服违规',
        'person': '人员检测',
        'no_mask': '未佩戴口罩',
        'no_hat': '未佩戴工作帽',
        'phone_usage': '使用手机',
        'smoking': '吸烟行为',
        'mouse_infestation': '鼠患问题',
        'uniform_violation': '工作服违规',
        'unknown': '未知违规'
      },

      // 违规类型颜色映射 - 浅蓝色风格
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

      // 摄像头位置映射
      cameraLocations: {
        'cam_11': '入口区域',
        'cam_28': '厨房区域',
        'cam_34': '用餐区域',
        'D11': '入口区域',
        'D28': '厨房区域',
        'D34': '用餐区域',
        'CAM001': '备菜区域',
      },

      showAnalysisModal: false,
      analysisResult: null,
    }
  },

  computed: {
    filterStatusText() {
      const rangeText = this.timeRanges.find(r => r.value === this.currentFilter.timeRange)?.desc || '最近24小时'
      return `当前筛选：${rangeText}`
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
    this.initCharts()
    this.loadData()

    // 定期刷新数据
    this.refreshInterval = setInterval(() => {
      if (!this.isLoading) {
        this.loadData()
      }
    }, 60000)

    // 窗口大小变化时重新调整图表
    window.addEventListener('resize', this.handleResize)
  },

  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }

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

    // 选择时间范围
    selectTimeRange(range) {
      this.currentFilter.timeRange = range
      this.loadData()
    },

    // 刷新数据
    async refreshData() {
      await this.loadData()
    },

    // 重置筛选
    resetFilters() {
      this.currentFilter.timeRange = '24h'
      this.loadData()
      this.showMessage('筛选条件已重置', 'info')
    },

    // 清空数据
    async clearData() {
      if (!confirm('确认清空所有违规数据？此操作不可恢复。')) {
        return
      }

      try {
        this.showMessage('正在清空数据...', 'info')
        const response = await violationsAPI.clearData()
        if (response.data.success) {
          this.showMessage(`数据已清空 - 删除了 ${response.data.cleared_records || 0} 条记录`, 'success')
          setTimeout(() => {
            this.loadData()
          }, 1000)
        } else {
          throw new Error(response.data.message || '清空数据失败')
        }
      } catch (error) {
        console.error('清空数据失败:', error)
        this.showMessage('清空数据失败: ' + error.message, 'error')
      }
    },

    // 加载数据
    async loadData() {
      if (this.isLoading) return

      this.isLoading = true

      try {
        const params = { range: this.currentFilter.timeRange }
        if (params.range === 'all') {
          params.all = 'true'
        }

        const response = await violationsAPI.getAnalytics(params)

        if (response.data && response.data.success) {
          this.updateDashboard(response.data.data)
          this.updateCharts()
          this.showMessage('数据加载成功', 'success')
        } else {
          console.warn('后端返回错误，使用默认数据')
          this.updateDashboard({
            summary: {
              total_violations: 0,
              total_records: 0,
              active_cameras: 0,
              time_description: '数据加载失败'
            },
            violations_by_type: {},
            violations_by_camera: {},
            recent_records: []
          })
          this.showMessage('后端服务暂时不可用，显示默认数据', 'warning')
        }

      } catch (error) {
        console.error('加载数据失败:', error)

        this.updateDashboard({
          summary: {
            total_violations: 0,
            total_records: 0,
            active_cameras: 0,
            time_description: '网络连接失败'
          },
          violations_by_type: {},
          violations_by_camera: {},
          recent_records: []
        })

        this.showMessage('加载数据失败: ' + (error.response?.data?.message || error.message), 'error')
      } finally {
        this.isLoading = false
        this.lastUpdateTime = new Date().toLocaleTimeString()
      }
    },

    // 更新仪表盘
    updateDashboard(data) {
      const summary = data.summary || {}

      this.dashboardData = {
        totalViolations: summary.total_violations || 0,
        totalRecords: summary.total_records || 0,
        activeCameras: summary.active_cameras || 0,
        avgViolations: summary.total_records > 0 ?
          (summary.total_violations / summary.total_records).toFixed(1) : '0'
      }

      this.currentHourlyData = data.violations_by_hour || {}

      this.updateViolationsList(data.violations_by_type || {})
      this.updateCamerasList(data.violations_by_camera || {})
      this.updateRecentRecords(data.recent_records || [])
    },

    // 更新违规类型列表
    updateViolationsList(violationsByType) {
      if (!violationsByType || Object.keys(violationsByType).length === 0) {
        this.violationsList = []
        return
      }

      this.violationsList = Object.entries(violationsByType)
        .filter(([type, count]) => count > 0)
        .sort(([,a], [,b]) => b - a)
        .map(([type, count]) => ({
          type,
          name: this.violationMapping[type] || `${type}(原始)`,
          count
        }))
    },

    // 更新摄像头列表
    updateCamerasList(violationsByCamera) {
      if (!violationsByCamera || Object.keys(violationsByCamera).length === 0) {
        this.camerasList = []
        return
      }

      this.camerasList = Object.entries(violationsByCamera)
        .sort(([,a], [,b]) => b - a)
        .map(([camera_id, violations]) => ({
          camera_id,
          violations
        }))
    },

    // 更新最近记录
    updateRecentRecords(recentRecords) {
      this.recentRecords = recentRecords.slice(0, 10).map(record => {
        return {
          id: record.id || Math.random().toString(36),
          camera_id: record.camera_id,
          detection_timestamp: record.timestamp || record.detection_timestamp,
          formatted_violations: record.violations || record.formatted_violations || {},
          total_violations: record.total_violations || 0,
          created_at: record.created_at
        }
      })
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

      const data = this.violationsList.map(violation => ({
        name: violation.name,
        value: violation.count,
        itemStyle: {
          color: this.violationColors[violation.type] || '#D1D5DB'
        }
      }))

      const option = {
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
          data: sortedCameras.map(camera => camera.camera_id),
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
            value: camera.violations,
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
            color: '#42A5F5' // Changed color
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(66, 165, 245, 0.4)' }, // Changed color
                { offset: 1, color: 'rgba(66, 165, 245, 0.1)' } // Changed color
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

    // 获取违规百分比
    getViolationPercentage(count) {
      if (this.violationsList.length === 0) return 0
      const maxCount = Math.max(...this.violationsList.map(v => v.count))
      return maxCount > 0 ? (count / maxCount) * 100 : 0
    },

    // 获取摄像头位置
    getCameraLocation(cameraId) {
      return this.cameraLocations[cameraId] || '未知区域'
    },

    // 格式化时间
    formatTime(timestamp) {
      if (!timestamp) return '--'

      try {
        const date = new Date(timestamp)
        if (isNaN(date.getTime())) {
          console.warn('Invalid timestamp:', timestamp)
          return '--'
        }
        return date.toLocaleString('zh-CN')
      } catch (error) {
        console.error('格式化时间失败:', error)
        return '--'
      }
    },

    // 获取时间间隔
    getTimeAgo(timestamp) {
      if (!timestamp) return '--'

      try {
        const now = new Date()
        const time = new Date(timestamp)

        if (isNaN(time.getTime())) {
          console.warn('Invalid timestamp for time ago:', timestamp)
          return '--'
        }

        const diff = now - time
        const minutes = Math.floor(diff / 60000)

        if (minutes < 1) return '刚刚'
        if (minutes < 60) return `${minutes}分钟前`
        if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`
        return `${Math.floor(minutes / 1440)}天前`
      } catch (error) {
        console.error('计算时间间隔失败:', error)
        return '--'
      }
    },

    // 获取违规标签样式
    getViolationTagClass(type) {
      const classMap = {
        'mask': 'tag-mask',
        'no_mask': 'tag-mask',
        'hat': 'tag-hat',
        'no_hat': 'tag-hat',
        'phone': 'tag-phone',
        'phone_usage': 'tag-phone',
        'smoking': 'tag-smoking',
        'cigarette': 'tag-smoking'
      }
      return classMap[type] || 'tag-default'
    },

    // 获取计数徽章样式
    getCountBadgeClass(count) {
      if (count >= 10) return 'badge-high'
      if (count >= 5) return 'badge-medium'
      return 'badge-low'
    },

    // 查看记录详情
    viewRecordDetails(record) {
      const details = `
记录详情：
ID: ${record.id}
摄像头: ${record.camera_id}
时间: ${this.formatTime(record.detection_timestamp)}
违规次数: ${record.total_violations}
违规类型: ${Object.entries(record.formatted_violations || {}).map(([type, count]) => `${this.violationMapping[type] || type}(${count})`).join(', ')}
      `
      alert(details)
    },

    // 分析记录
    async analyzeRecord(record) {
      this.showMessage(`正在分析记录 ${record.id}...`, 'info');
      try {
        const response = await violationsAPI.analyzeRecord(record.id);
        if (response.data && response.data.success) {
          this.analysisResult = response.data.data;
          this.showAnalysisModal = true;
          this.showMessage('分析完成', 'success');
        } else {
          throw new Error(response.data.message || '分析失败');
        }
      } catch (error) {
        console.error('分析记录失败:', error);
        this.showMessage('分析失败: ' + error.message, 'error');
      }
    },

    // 导出记录
    exportRecords() {
      this.showMessage('导出功能开发中...', 'info')
    },

    // 图表相关方法
    toggleChartType(type) {
      console.log('切换图表类型:', type)
    },

    exportChart(chartType) {
      console.log('导出图表:', chartType)
    },

    updateTrendChart() {
      console.log('更新趋势图:', this.trendTimeRange)
      this.updateTrendsChart()
    },

    // 显示消息
    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, type === 'error' ? 5000 : 3000)
    },

    // 获取消息图标
    getMessageIcon(type) {
      const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }
      return icons[type] || icons.info
    }
  }
}
</script>

<style scoped>
/* 基础容器 - 柔和蓝色主题 */
.historical-data-container {
  padding: 5px;
  /* MODIFIED: Changed background to a soft blue gradient */
  background: linear-gradient(180deg, #f0f8ff 0%, #f7fbff 100%);
  width: 100%;
}

/* 图表容器样式 */
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
}

/* 卡片基础样式 */
.filter-panel-card,
.data-card,
.chart-card,
.records-section {
  background: #ffffff;
  border: 1px solid #E3F2FD;
  border-radius: 12px;
  box-shadow: 0 1px 3px 0 rgba(66, 165, 245, 0.1), 0 1px 2px 0 rgba(66, 165, 245, 0.06);
  margin-bottom: 24px;
}

/* 筛选面板 */
.filter-panel-card {
  margin-bottom: 24px;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E3F2FD;
  display: flex;
  justify-content: space-between;
  align-items: center;
  /* MODIFIED: Changed to a lighter blue gradient */
  background: linear-gradient(135deg, #e3f2fd 0%, #f7fbff 100%);
  /* MODIFIED: Changed text color for better readability on light background */
  color: #4B5563;
}

.card-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-primary {
  /* MODIFIED: Changed color from purple to blue */
  background: #42A5F5;
  color: white;
  border-color: #42A5F5;
}

.btn-primary:hover:not(:disabled) {
  background: #1976D2;
  border-color: #1976D2;
}

.btn-outline {
  background: white;
  /* MODIFIED: Changed color from purple to blue */
  color: #42A5F5;
  border-color: #BBDEFB;
}

.btn-outline:hover {
  background: #F7FBFF;
  color: #1976D2;
  border-color: #90CAF9;
}

.btn-danger {
  background: #EF5350;
  color: white;
  border-color: #EF5350;
}

.btn-danger:hover {
  background: #E53935;
  border-color: #E53935;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-content {
  padding: 24px;
}

.time-range-section {
  margin-bottom: 24px;
}

.section-label {
  display: block;
  font-weight: 500;
  color: #6B7280;
  margin-bottom: 12px;
}

.time-range-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 12px;
}

.time-btn {
  padding: 12px;
  background: white;
  /* MODIFIED: Changed border color */
  border: 2px solid #E3F2FD;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.time-btn:hover {
  /* MODIFIED: Changed hover colors */
  border-color: #90CAF9;
  background: #F7FBFF;
}

.time-btn.active {
  /* MODIFIED: Changed active state colors */
  border-color: #42A5F5;
  background: #42A5F5;
  color: white;
}

.time-title {
  font-weight: 600;
  font-size: 14px;
}

.time-desc {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 4px;
}

.filter-status-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #E3F2FD;
}

.status-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.status-text {
  /* MODIFIED: Changed color to a neutral dark gray */
  color: #374151;
  font-weight: 500;
}

.update-time {
  /* MODIFIED: Changed color to gray as requested */
  color: #9CA3AF;
  font-size: 14px;
}

/* 统计卡片 */
.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.stat-card {
  background: white;
  border: 1px solid #E3F2FD;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(66, 165, 245, 0.1), 0 2px 4px -1px rgba(66, 165, 245, 0.06);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

/* MODIFIED: Changed stat icon colors to a blue/gray theme */
.stat-icon.violations { background: linear-gradient(135deg, #FF8A65, #FF7043); }
.stat-icon.records { background: linear-gradient(135deg, #42A5F5, #1976D2); }
.stat-icon.cameras { background: linear-gradient(135deg, #26C6DA, #00ACC1); }
.stat-icon.average { background: linear-gradient(135deg, #95a5a6, #7f8c8d); }

.stat-content h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #6B7280;
  font-weight: 500;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: #111827;
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

/* FIXED: chart-empty overflow and positioning */
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

/* 数据统计区域 */
.data-section {
  margin-bottom: 24px;
}

.data-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.data-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E3F2FD;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-count {
  /* MODIFIED: Changed data count pill color */
  background: #E3F2FD;
  color: #1976D2;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.data-content {
  padding: 24px;
  max-height: 400px;
  overflow-y: auto;
}

.data-empty {
  text-align: center;
  color: #9CA3AF;
  padding: 48px 0;
}

.data-empty i {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

/* 违规列表 */
.violations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.violation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #F3F4F6;
}

.violation-item:last-child {
  border-bottom: none;
}

.violation-info {
  flex: 1;
}

.violation-name {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}

.violation-type {
  font-size: 12px;
  color: #42A5F5;
}

.violation-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 100px;
}

.violation-count {
  font-weight: 600;
  color: #111827;
  font-size: 18px;
}

.violation-bar {
  flex: 1;
  height: 6px;
  background: #F3F4F6;
  border-radius: 3px;
  overflow: hidden;
}

.violation-progress {
  height: 100%;
  background: #42A5F5;
  transition: width 0.3s ease;
}

/* 摄像头列表 */
.cameras-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #F3F4F6;
}

.camera-item:last-child {
  border-bottom: none;
}

.camera-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.camera-icon {
  width: 40px;
  height: 40px;
  background: #F7FBFF;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #42A5F5;
}

.camera-details {
  display: flex;
  flex-direction: column;
}

.camera-id {
  font-weight: 500;
  color: #374151;
}

.camera-location {
  font-size: 12px;
  color: #42A5F5;
}

.camera-stats {
  text-align: right;
}

.camera-violations {
  display: block;
  font-weight: 600;
  color: #EF5350;
  font-size: 18px;
}

.camera-label {
  font-size: 12px;
  color: #9CA3AF;
}

/* 记录表格 */
.records-section {
  margin-bottom: 24px;
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
  color: #374151;
  background-color: #f3f4f6;
}

.tag-mask, .tag-smoking { background: #ffebee; color: #c62828; }
.tag-hat { background: #fff8e1; color: #f9a825; }
.tag-phone { background: #e3f2fd; color: #1565c0; }
.tag-default { background: #f1f5f9; color: #475569; }

.count-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
}

.badge-low { background: #e3f2fd; color: #1565c0; }
.badge-medium { background: #fff8e1; color: #f9a825; }
.badge-high { background: #ffebee; color: #c62828; }

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

/* 消息提示 */
.message-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  padding: 16px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1000;
  min-width: 320px;
  max-width: 480px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.message-success {
  background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7;
}
.message-error {
  background: #FFEBEE; color: #C62828; border: 1px solid #EF9A9A;
}
.message-warning {
  background: #FFF8E1; color: #F9A825; border: 1px solid #FFE082;
}
.message-info {
  background: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9;
}

.message-text {
  flex: 1;
  font-weight: 500;
}

.message-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  color: inherit;
}

.message-close:hover {
  opacity: 1;
}

/* 过渡动画 */
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

.modal-content pre {
  background-color: #F9FAFB;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .charts-row,
  .data-row {
    grid-template-columns: 1fr;
  }

  .time-range-buttons {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .historical-data-container {
    padding: 0px;
  }

  .header-actions {
    flex-direction: column;
    gap: 8px;
  }

  .statistics-grid {
    grid-template-columns: 1fr;
  }

  .time-range-buttons {
    grid-template-columns: 1fr;
  }

  .records-table-wrapper {
    font-size: 14px;
  }

  .records-table th,
  .records-table td {
    padding: 12px 8px;
  }
}
</style>