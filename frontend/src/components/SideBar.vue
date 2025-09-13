<template>
  <div class="sidebar">
    <!-- 根据路由动态显示标题 -->
    <h2 class="sidebar-title">{{ sidebarTitle }}</h2>

    <div
      v-for="(item, index) in options"
      :key="index"
      class="sidebar-option"
      :class="{ active: activeIndex === index }"
      @click="selectOption(index, item.component)"
    >
      <i :class="item.icon" class="sidebar-icon"></i>
      <span class="sidebar-text">{{ item.label }}</span>
      <i
        :class="activeIndex === index ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"
        class="sidebar-arrow"
      ></i>
    </div>

    <!-- 保留原本的图片，不动 -->
    <img :src="ridebike" class="ridebike-image" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import ridebike from '@/assets/ridebike.svg'

const emit = defineEmits(['select'])
const activeIndex = ref(null)
const route = useRoute()

// 定义两组不同的选项
const deviceOptions = [
  { label: '寻找设备', icon: 'fas fa-laptop', component: 'FindDevice' },
  { label: '实时监测', icon: 'fas fa-mobile-alt', component: 'MonitorLive' },
  { label: '历史视频与数据', icon: 'fas fa-tablet-alt', component: 'HistoricalData' },
  { label: '反馈报告', icon: 'fas fa-cogs', component: 'FeedbackReport' },
  { label: '设备管理', icon: 'fas fa-info-circle', component: 'DeviceManagement' }
]

const accountOptions = [
  { label: '修改账号信息', icon: 'fas fa-user-edit', component: 'EditAccount' },
  { label: '退出登录', icon: 'fas fa-sign-out-alt', component: 'Logout' }
]

// 根据当前路由动态选择 options
const options = computed(() => {
  if (route.path === '/page3') {
    return accountOptions
  }
  return deviceOptions
})

// 根据路由动态切换标题
const sidebarTitle = computed(() => {
  return route.path === '/page3' ? '账号管理' : '我的设备'
})

function selectOption(index, componentName) {
  activeIndex.value = index
  emit('select', componentName)
}
</script>




<style scoped>
.sidebar {
  position: relative;       /* 父容器设为相对定位 */
  width: 231px;
  background-color: #e6f4ff;
  padding: 16px;
  box-sizing: border-box;
  height: calc(100vh - 60px); /* 保持全高 */
}

.sidebar-title {
  margin-bottom: 16px;
  font-size: 18px;
}

.sidebar-option {
  background-color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: 0.2s;
}

.sidebar-option .sidebar-icon,
.sidebar-option .sidebar-text,
.sidebar-option .sidebar-arrow {
  color: rgba(0, 0, 0, 0.65);
}

.sidebar-option.active .sidebar-icon,
.sidebar-option.active .sidebar-text,
.sidebar-option.active .sidebar-arrow {
  color: #1890FF; /* 蓝色 */
}

.ridebike-image {
  position: absolute;  /* 绝对定位 */
  bottom: 40px;        /* 距离底部 20px，可自行调整 */
  left: 50%;           /* 水平居中 */
  transform: translateX(-50%);
  width: 80%;
  height: auto;
}
</style>


