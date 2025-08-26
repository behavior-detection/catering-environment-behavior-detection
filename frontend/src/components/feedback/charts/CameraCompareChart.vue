<!-- components/feedback/charts/CameraCompareChart.vue -->
<template>
  <div class="chart-panel">
    <div class="chart-header">
      <span>摄像头违规分布图</span>
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
  name: 'CameraCompareChart',
  props: {
    camerasList: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      chart: null,
      chartInfo: '--'
    }
  },
  watch: {
    camerasList: {
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

      if (this.camerasList.length === 0) {
        this.chart.setOption({
          title: {
            text: '暂无摄像头数据',
            left: 'center',
            top: 'middle',
            textStyle: { fontSize: 16, color: '#999' }
          }
        })
        this.chartInfo = '无数据'
        return
      }

      const data = this.camerasList.slice(0, 10)

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
          top: '5%'
        },
        xAxis: {
          type: 'value',
          name: '违规次数'
        },
        yAxis: {
          type: 'category',
          data: data.map(item => item.camera_id),
          axisLabel: {
            interval: 0,
            fontSize: 12
          }
        },
        series: [{
          name: '违规次数',
          type: 'bar',
          data: data.map(item => item.violations),
          itemStyle: {
            color: '#667eea'
          }
        }]
      }

      this.chart.setOption(option, true)
      this.chartInfo = `${this.camerasList.length}个摄像头`
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