<!-- components/feedback/charts/ViolationPieChart.vue -->
<template>
  <div class="chart-panel">
    <div class="chart-header">
      <span>违规类型分布图</span>
      <div class="header-actions">
        <span class="chart-info">{{ chartInfo }}</span>
        <div class="chart-type-toggle">
          <button
            :class="['toggle-btn', { active: chartType === 'pie' }]"
            @click="chartType = 'pie'"
            title="饼图"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M11 2v20c-5.07-.5-9-4.79-9-10s3.93-9.5 9-10zm2.03 0v8.99H22c-.47-4.74-4.24-8.52-8.97-8.99zm0 11.01V22c4.74-.47 8.5-4.25 8.97-8.99h-8.97z"/>
            </svg>
          </button>
          <button
            :class="['toggle-btn', { active: chartType === 'bar' }]"
            @click="chartType = 'bar'"
            title="柱状图"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div class="chart-body">
      <div ref="chartContainer" class="chart-container"></div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'

export default {
  name: 'ViolationPieChart',
  props: {
    violationsList: {
      type: Array,
      default: () => []
    },
    violationMapping: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      chart: null,
      chartInfo: '--',
      chartType: 'pie' // 'pie' or 'bar'
    }
  },
  watch: {
    violationsList: {
      handler() {
        this.$nextTick(() => {
          this.updateChart()
        })
      },
      deep: true
    },
    chartType() {
      this.updateChart()
    }
  },
  mounted() {
    this.initChart()
    window.addEventListener('resize', this.handleResize)
  },
  beforeUnmount() {
    if (this.chart) {
      this.chart.dispose()
    }
    window.removeEventListener('resize', this.handleResize)
  },
  methods: {
    initChart() {
      if (this.$refs.chartContainer) {
        this.chart = echarts.init(this.$refs.chartContainer)
        this.updateChart()
      }
    },
    updateChart() {
      if (!this.chart) return

      // 清除之前的配置 - 这是关键！
      this.chart.clear()

      if (this.violationsList.length === 0) {
        this.chart.setOption({
          title: {
            text: '暂无违规数据',
            left: 'center',
            top: 'middle',
            textStyle: { fontSize: 16, color: '#999' }
          },
          // 明确清除坐标轴配置
          xAxis: null,
          yAxis: null,
          series: []
        })
        this.chartInfo = '无数据'
        return
      }

      const data = this.violationsList.map(item => ({
        name: item.name,
        value: item.count
      }))

      // 根据图表类型生成不同的配置
      const option = this.chartType === 'pie' ? this.getPieOption(data) : this.getBarOption(data)

      // 使用 notMerge: true 确保完全替换配置
      this.chart.setOption(option, { notMerge: true })

      const totalViolations = data.reduce((sum, item) => sum + item.value, 0)
      this.chartInfo = `${totalViolations} 次违规`
    },
    getPieOption(data) {
      return {
        // 清除可能存在的坐标轴配置
        xAxis: null,
        yAxis: null,
        grid: null,
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          top: 'center'
        },
        series: [{
          name: '违规类型',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          data: data,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            formatter: '{b}: {c}次\n({d}%)'
          }
        }]
      }
    },
    getBarOption(data) {
      // 按数值降序排序
      const sortedData = [...data].sort((a, b) => b.value - a.value)

      return {
        // 清除可能存在的饼图配置
        legend: null,
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          },
          formatter: '{b}: {c}次'
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
          axisLabel: {
            fontSize: 12
          },
          // 添加更多配置确保正确初始化
          axisLine: {
            show: true
          },
          axisTick: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: sortedData.map(item => item.name),
          axisLabel: {
            interval: 0,
            fontSize: 12
          },
          // 添加更多配置确保正确初始化
          axisLine: {
            show: true
          },
          axisTick: {
            show: true
          }
        },
        series: [{
          name: '违规次数',
          type: 'bar',
          data: sortedData.map(item => item.value),
          // 确保使用正确的坐标系
          coordinateSystem: 'cartesian2d',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' }
            ])
          },
          barWidth: '60%',
          label: {
            show: true,
            position: 'right',
            formatter: '{c}',
            fontSize: 12
          }
        }]
      }
    },
    handleResize() {
      if (this.chart) {
        this.chart.resize()
      }
    }
  }
}
</script>

<style scoped>
.chart-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  overflow: hidden;
}

.chart-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 25px;
  font-size: 1.1em;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.chart-info {
  font-size: 0.9em;
  opacity: 0.9;
}

.chart-type-toggle {
  display: flex;
  gap: 5px;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px;
  border-radius: 8px;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}

.toggle-btn.active {
  color: white;
  background: rgba(255, 255, 255, 0.3);
}

.chart-body {
  padding: 25px;
  height: 400px;
}

.chart-container {
  width: 100%;
  height: 100%;
}
</style>