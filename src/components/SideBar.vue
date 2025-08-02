<template>
  <div class="sidebar">
    <h2 class="sidebar-title">我的设备</h2>
    <div
      v-for="(item, index) in options"
      :key="index"
      class="sidebar-option"
      :class="{ active: activeIndex === index }"
      @click="selectOption(index, item.component)"
    >
      <i :class="item.icon" class="sidebar-icon"></i>
      <span class="sidebar-text">{{ item.label }}</span>
      <i :class="activeIndex === index ? 'fas fa-chevron-up' : 'fas fa-chevron-down'" class="sidebar-arrow"></i>
    </div>
    <img :src="ridebike" class="ridebike-image"/>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ridebike from '@/assets/ridebike.svg'

const emit = defineEmits(['select']) // 定义一个事件用于向父组件传递选中的组件名称,声明事件

const activeIndex = ref(null)
const options = [
  { label: '寻找设备', icon: 'fas fa-laptop', component: 'FindDevice' },
  { label: '实时监测', icon: 'fas fa-mobile-alt', component: 'MonitorLive' },
  { label: '历史视频与数据', icon: 'fas fa-tablet-alt', component: 'HistoricalData' },
  { label: '反馈报告', icon: 'fas fa-cogs', component: 'FeedbackReport' },
  { label: '设备管理', icon: 'fas fa-info-circle', component: 'DeviceManagement' }
]

function selectOption(index, componentName) {
  activeIndex.value = index
  emit('select', componentName)  //如果你需要向父组件通信
}
</script>



<style scoped>
.sidebar {
  width: 231px;
  background-color: #e6f4ff; /* 浅蓝色背景 */
  padding: 16px;
  box-sizing: border-box;
  height: calc(100vh - 60px); /* 减去顶部导航栏高度，填满剩余屏幕 */
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
  width: 80%;
  height: auto;
  margin: 230px auto 0 auto; /* 顶部 230px，左右居中 */
  display: block;
}
</style>


