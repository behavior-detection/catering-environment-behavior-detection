<template>
  <div class="page2-2-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <button @click="goBack" class="back-btn">
        <i class="icon-arrow-left">←</i> 返回设备列表
      </button>
      <h2>设备详情</h2>
    </div>

    <!-- 设备信息卡片 -->
    <div class="device-detail-card card">
      <div class="device-header">
        <div class="device-icon">
          <i class="icon-device">📱</i>
        </div>
        <div class="device-info">
          <h3>{{ deviceInfo.name }}</h3>
          <p class="device-id">设备ID: {{ deviceInfo.id }}</p>
          <span class="device-status" :class="deviceInfo.status">
            {{ deviceStatusText }}
          </span>
        </div>
      </div>

      <!-- 设备详细信息 -->
      <div class="detail-sections">
        <!-- 基本信息 -->
        <section class="detail-section">
          <h4>基本信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <label>设备型号</label>
              <span>{{ deviceInfo.model }}</span>
            </div>
            <div class="info-item">
              <label>所属部门</label>
              <span>{{ deviceInfo.department }}</span>
            </div>
            <div class="info-item">
              <label>负责人</label>
              <span>{{ deviceInfo.manager }}</span>
            </div>
            <div class="info-item">
              <label>添加时间</label>
              <span>{{ deviceInfo.addTime }}</span>
            </div>
          </div>
        </section>

        <!-- 运行状态 -->
        <section class="detail-section">
          <h4>运行状态</h4>
          <div class="status-grid">
            <div class="status-item">
              <label>运行时长</label>
              <span>{{ deviceInfo.runningTime }}</span>
            </div>
            <div class="status-item">
              <label>上次维护</label>
              <span>{{ deviceInfo.lastMaintenance }}</span>
            </div>
            <div class="status-item">
              <label>健康度</label>
              <div class="health-bar">
                <div class="health-progress" :style="{width: deviceInfo.health + '%'}"></div>
                <span class="health-text">{{ deviceInfo.health }}%</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 操作按钮 -->
        <section class="detail-section actions">
          <button class="btn btn-primary" @click="handleMonitor">
            <i class="icon-monitor">📊</i> 实时监控
          </button>
          <button class="btn btn-secondary" @click="handleHistory">
            <i class="icon-history">📈</i> 历史数据
          </button>
          <button class="btn btn-ghost" @click="handleMaintenance">
            <i class="icon-settings">⚙️</i> 维护管理
          </button>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
// 导入全局导航锁定管理器
import { navLockManager } from '@/services/NavLockManager'

export default {
  name: 'Page2_2',
  data() {
    return {
      // 模拟设备信息
      deviceInfo: {
        id: 'DEV-2024-001',
        name: '智能监控设备 A1',
        model: 'SM-2024-Pro',
        department: '生产一部',
        manager: '张三',
        addTime: '2024-01-15',
        status: 'online',
        runningTime: '1,234 小时',
        lastMaintenance: '2024-12-01',
        health: 85
      }
    }
  },
  computed: {
    deviceStatusText() {
      const statusMap = {
        online: '在线',
        offline: '离线',
        maintenance: '维护中',
        error: '故障'
      }
      return statusMap[this.deviceInfo.status] || '未知'
    }
  },
  mounted() {
    // 更新导航锁定状态（自动锁定"首页"，解锁"我的设备"和"账号管理"）
    navLockManager.updateLocksByRoute()

    // 检查登录状态
    this.checkLoginStatus()

    // 可以根据路由参数获取设备ID并加载对应数据
    // const deviceId = this.$route.params.deviceId
    // this.loadDeviceInfo(deviceId)
  },
  methods: {
    checkLoginStatus() {
      const userInfo = sessionStorage.getItem('userInfo')
      const adminInfo = sessionStorage.getItem('adminInfo')

      if (!userInfo && !adminInfo) {
        alert('请先登录！')
        this.$router.push('/')
      }
    },

    goBack() {
      // 返回设备列表页
      this.$router.push('/Page2')
    },

    handleMonitor() {
      alert('进入实时监控页面')
      // 可以跳转到监控页面
    },

    handleHistory() {
      alert('查看历史数据')
      // 可以跳转到历史数据页面
    },

    handleMaintenance() {
      alert('进入维护管理')
      // 可以跳转到维护管理页面
    }
  }
}
</script>

<style scoped>
.page2-2-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
  padding: 16px 24px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary-light);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary);
  transform: translateX(-2px);
}

.page-header h2 {
  flex: 1;
  margin: 0;
  font-size: 1.5rem;
  color: var(--color-text);
}

/* 设备详情卡片 */
.device-detail-card {
  max-width: 1000px;
  margin: 0 auto;
}

.device-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 32px;
}

.device-icon {
  width: 80px;
  height: 80px;
  background: var(--color-primary-lighter);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
}

.device-info {
  flex: 1;
}

.device-info h3 {
  margin-bottom: 8px;
  color: var(--color-text);
}

.device-id {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-bottom: 12px;
}

/* 设备状态标签 */
.device-status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.device-status.online {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.device-status.offline {
  background: #fff2e8;
  color: #fa8c16;
  border: 1px solid #ffd591;
}

.device-status.maintenance {
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.device-status.error {
  background: #fff1f0;
  color: #f5222d;
  border: 1px solid #ffa39e;
}

/* 详情区域 */
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.detail-section {
  background: var(--color-bg-light);
  padding: 24px;
  border-radius: 8px;
}

.detail-section h4 {
  margin-bottom: 20px;
  color: var(--color-text);
  font-size: 1.125rem;
}

/* 信息网格 */
.info-grid,
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.info-item,
.status-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label,
.status-item label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.info-item span,
.status-item span {
  font-size: 16px;
  color: var(--color-text);
  font-weight: 500;
}

/* 健康度进度条 */
.health-bar {
  position: relative;
  width: 100%;
  height: 24px;
  background: #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
}

.health-progress {
  height: 100%;
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
  transition: width 0.3s ease;
}

.health-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 600;
  color: white;
}

/* 操作按钮区域 */
.detail-section.actions {
  display: flex;
  gap: 16px;
  background: transparent;
  padding: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .device-header {
    flex-direction: column;
    text-align: center;
  }

  .info-grid,
  .status-grid {
    grid-template-columns: 1fr;
  }

  .detail-section.actions {
    flex-direction: column;
  }

  .detail-section.actions .btn {
    width: 100%;
  }
}
</style>