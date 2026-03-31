<!-- components/feedback/charts/CameraCompareChart.vue -->
<template>
  <div class="chart-panel">
    <div class="chart-header">
      <span>摄像头违规统计</span>
      <div class="header-actions">
        <span class="chart-info">{{ chartInfo }}</span>
        <button class="download-btn" @click="downloadChart" title="下载图表">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
          </svg>
        </button>
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

      // 清除之前的配置 - 这很重要！
      this.chart.clear()

      if (this.camerasList.length === 0) {
        this.chart.setOption({
          title: {
            text: '暂无摄像头数据',
            left: 'center',
            top: 'middle',
            textStyle: { fontSize: 16, color: '#999' }
          },
          // 明确设置空的坐标轴和系列，避免残留配置
          xAxis: null,
          yAxis: null,
          series: []
        })
        this.chartInfo = '无数据'
        return
      }

      const data = this.camerasList.slice(0, 10)

      const option = {
        // 清除 title 配置，避免与数据展示冲突
        title: null,
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
          name: '违规次数',
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
          data: data.map(item => item.camera_id),
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
          data: data.map(item => item.violations),
          // 确保使用正确的坐标系
          coordinateSystem: 'cartesian2d',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' }
            ])
          },
          label: {
            show: true,
            position: 'right',
            formatter: '{c}',
            fontSize: 12
          }
        }]
      }

      // 使用 notMerge: true 确保完全替换配置
      this.chart.setOption(option, { notMerge: true })
      this.chartInfo = `${this.camerasList.length}个摄像头`
    },
    downloadChart() {
      if (!this.chart) {
        this.$message.warning('图表未加载完成')
        return
      }

      if (this.camerasList.length === 0) {
        this.$message.warning('暂无数据可下载')
        return
      }

      try {
        // 获取图表的base64图片数据
        const url = this.chart.getDataURL({
          type: 'png',
          pixelRatio: 2, // 提高分辨率
          backgroundColor: '#fff'
        })

        // 创建下载链接
        const link = document.createElement('a')
        link.href = url

        // 生成文件名（包含时间戳）
        const timestamp = new Date().toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }).replace(/[/:]/g, '-').replace(/\s/g, '_')

        link.download = `摄像头违规统计_${timestamp}.png`

        // 触发下载
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        this.$message.success('图表下载成功')
      } catch (error) {
        console.error('下载图表失败:', error)
        this.$message.error('下载图表失败，请重试')
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

.download-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.download-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.download-btn:active {
  transform: translateY(0);
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