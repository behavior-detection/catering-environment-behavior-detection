<!-- components/feedback/charts/ViolationPieChart.vue -->
<template>
  <div class="chart-panel">
    <div class="chart-header">
      <span>违规类型分布图</span>
      <span class="chart-info">{{ chartInfo }}</span>
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
      chartInfo: '--'
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

      if (this.violationsList.length === 0) {
        this.chart.setOption({
          title: {
            text: '暂无违规数据',
            left: 'center',
            top: 'middle',
            textStyle: { fontSize: 16, color: '#999' }
          }
        })
        this.chartInfo = '无数据'
        return
      }

      const data = this.violationsList.map(item => ({
        name: item.name,
        value: item.count
      }))

      const option = {
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
          }
        }]
      }

      this.chart.setOption(option, true)

      const totalViolations = data.reduce((sum, item) => sum + item.value, 0)
      this.chartInfo = `${totalViolations} 次违规`
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

.chart-info {
  font-size: 0.9em;
  opacity: 0.9;
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