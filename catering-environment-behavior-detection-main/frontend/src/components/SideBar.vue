<template>
  <div class="sidebar">
    <h2 class="sidebar-title">我的设备</h2>

    <!-- 主菜单选项 -->
    <div
      v-for="(item, index) in filteredOptions"
      :key="index"
      class="sidebar-option"
      :class="{ active: activeIndex === index }"
    >
      <!-- 如果有子菜单，处理下拉逻辑 -->
      <div v-if="item.children" class="dropdown-container">
        <div class="dropdown-header" @click="toggleDropdown(index)">
          <i :class="item.icon" class="sidebar-icon"></i>
          <span class="sidebar-text">{{ item.label }}</span>
          <i :class="expandedItems.includes(index) ? 'fas fa-chevron-up' : 'fas fa-chevron-down'" class="sidebar-arrow"></i>
        </div>

        <!-- 下拉菜单内容 -->
        <transition name="dropdown">
          <div v-show="expandedItems.includes(index)" class="dropdown-content">
            <div
              v-for="(child, childIndex) in item.children"
              :key="childIndex"
              class="dropdown-item"
              :class="{ active: activeChild === `${index}-${childIndex}` }"
              @click="selectChild(index, childIndex, child.component)"
            >
              <i :class="child.icon" class="dropdown-icon"></i>
              <span>{{ child.label }}</span>
            </div>
          </div>
        </transition>
      </div>

      <!-- 普通菜单项 -->
      <div v-else @click="selectOption(index, item.component)" class="normal-menu-item">
        <i :class="item.icon" class="sidebar-icon"></i>
        <span class="sidebar-text">{{ item.label }}</span>
        <i :class="activeIndex === index ? 'fas fa-chevron-up' : 'fas fa-chevron-down'" class="sidebar-arrow"></i>
      </div>
    </div>

    <img :src="ridebike" class="ridebike-image"/>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import ridebike from '@/assets/ridebike.svg'

const store = useStore()
const emit = defineEmits(['select'])

// 获取用户信息
const userInfo = ref(null)

// 状态管理
const activeIndex = ref(null)
const activeChild = ref(null)
const expandedItems = ref([])

// 所有可能的菜单选项
const allOptions = ref([
  { label: '寻找设备', icon: 'fas fa-laptop', component: 'FindDevice' },
  { label: '实时监测', icon: 'fas fa-mobile-alt', component: 'MonitorLive' },
  { label: '历史视频与数据', icon: 'fas fa-tablet-alt', component: 'HistoricalData' },
  { label: '反馈报告', icon: 'fas fa-cogs', component: 'FeedbackReport' },
  { label: '设备管理', icon: 'fas fa-info-circle', component: 'DeviceManagement' }
])

// 管理员和经理的授予权限子菜单
const grantPermissionMenu = {
  label: '授予权限',
  icon: 'fas fa-user-shield',
  children: [
    { label: '查看权限申请', icon: 'fas fa-eye', component: 'ViewPermissionRequests' },
  ]
}

// 访客的申请权限子菜单
const requestPermissionMenu = {
  label: '申请权限',
  icon: 'fas fa-hand-paper',
  children: [
    { label: '提交权限申请', icon: 'fas fa-plus-circle', component: 'SubmitPermissionRequest' },
    { label: '申请状态查询', icon: 'fas fa-search', component: 'CheckRequestStatus' }
  ]
}

const permissionManager = {
  label:"权限管理",
  icon:"fas fa-key stat-icon",
  children:[
      { label: '生成令牌', icon: 'fas fa-clock-o', component: 'GenerateToken' },
      {label:'令牌管理', icon: 'fas fa-exclamation-circle', component: 'TokenManager' },
  ]

}

// 根据用户类型过滤选项
const filteredOptions = computed(() => {
  if (!userInfo.value) return allOptions.value

  const userType = userInfo.value.userType
  let options = []

  switch(userType) {
    case 'visitor':
      options = allOptions.value.filter(item =>
        item.label !== '设备管理'
      )
      options.push(requestPermissionMenu)
      break

    case 'manager':
      options = allOptions.value.filter(item =>
        item.label !== '寻找设备'
      )
      options.push(grantPermissionMenu)
      break

    case 'admin':
      options = allOptions.value.filter(item =>
        item.label !== '设备管理'
      )
      options.push(permissionManager)
      break

    default:
      options = allOptions.value
  }

  return options
})

// 根据用户类型获取默认组件
function getDefaultComponent(userType) {
  switch(userType) {
    case 'manager':
    case 'admin':
      return 'MonitorLive'
    case 'visitor':
      return 'FindDevice'
    default:
      return 'FindDevice'
  }
}

// 组件挂载时获取用户信息并设置默认模块
onMounted(() => {
  const storedUserInfo = sessionStorage.getItem('userInfo')
  if (storedUserInfo) {
    userInfo.value = JSON.parse(storedUserInfo)
  }

  // 获取默认组件
  const defaultComponent = getDefaultComponent(userInfo.value?.userType)

  // 设置 Vuex 状态
  store.dispatch('navigation/setCurrentModule', defaultComponent)

  // 在 filteredOptions 中找到对应的索引并设置为激活状态
  const options = filteredOptions.value
  for (let i = 0; i < options.length; i++) {
    const option = options[i]

    // 如果是普通菜单项
    if (!option.children && option.component === defaultComponent) {
      activeIndex.value = i
      emit('select', defaultComponent)
      break
    }

    // 如果是下拉菜单项
    if (option.children) {
      const childIndex = option.children.findIndex(child => child.component === defaultComponent)
      if (childIndex > -1) {
        activeIndex.value = i
        activeChild.value = `${i}-${childIndex}`
        expandedItems.value.push(i) // 自动展开该下拉菜单
        emit('select', defaultComponent)
        break
      }
    }
  }
})

// 切换下拉菜单
function toggleDropdown(index) {
  const idx = expandedItems.value.indexOf(index)
  if (idx > -1) {
    expandedItems.value.splice(idx, 1)
  } else {
    expandedItems.value.push(index)
  }
}

// 选择普通选项
function selectOption(index, componentName) {
  activeIndex.value = index
  activeChild.value = null
  store.dispatch('navigation/setCurrentModule', componentName)
  emit('select', componentName)
}

// 选择子菜单项
function selectChild(parentIndex, childIndex, componentName) {
  activeIndex.value = parentIndex
  activeChild.value = `${parentIndex}-${childIndex}`
  store.dispatch('navigation/setCurrentModule', componentName)
  emit('select', componentName)
}
</script>


<style scoped>
.sidebar {
  width: 231px;
  background-color: #e6f4ff;
  padding: 16px;
  box-sizing: border-box;
  height: calc(100vh - 60px);
}

.sidebar-title {
  margin-bottom: 16px;
  font-size: 18px;
  color: #333;
}

/* 普通菜单项样式 */
.sidebar-option {
  margin-bottom: 8px;
}

.normal-menu-item {
  background-color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  cursor: pointer;
  border-radius: 4px;
  transition: 0.2s;
}

.normal-menu-item:hover {
  background-color: #f0f8ff;
}

/* 下拉容器样式 */
.dropdown-container {
  background-color: white;
  border-radius: 4px;
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  cursor: pointer;
  transition: 0.2s;
}

.dropdown-header:hover {
  background-color: #f0f8ff;
}

/* 下拉内容样式 */
.dropdown-content {
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.dropdown-item {
  display: flex;
  align-items: center;
  padding: 10px 10px 10px 30px;
  cursor: pointer;
  transition: 0.2s;
  color: rgba(0, 0, 0, 0.65);
  font-size: 14px;
}

.dropdown-item:hover {
  background-color: #e6f4ff;
}

.dropdown-item.active {
  background-color: #e6f4ff;
  color: #1890FF;
}

.dropdown-item.active .dropdown-icon {
  color: #1890FF;
}

.dropdown-icon {
  margin-right: 8px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  width: 16px;
  text-align: center;
}

/* 图标和文字样式 */
.sidebar-icon {
  margin-right: 8px;
  width: 20px;
  text-align: center;
}

.sidebar-option .sidebar-icon,
.sidebar-option .sidebar-text,
.sidebar-option .sidebar-arrow {
  color: rgba(0, 0, 0, 0.65);
}

.sidebar-option.active .normal-menu-item .sidebar-icon,
.sidebar-option.active .normal-menu-item .sidebar-text,
.sidebar-option.active .normal-menu-item .sidebar-arrow {
  color: #1890FF;
}

.sidebar-option.active .dropdown-header .sidebar-icon,
.sidebar-option.active .dropdown-header .sidebar-text,
.sidebar-option.active .dropdown-header .sidebar-arrow {
  color: #1890FF;
}

/* 下拉动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.3s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 底部图片 */
.ridebike-image {
  width: 80%;
  height: auto;
  margin: 20px auto 0 auto;
  display: block;
}

/* 响应式设计 */
@media (max-height: 700px) {
  .ridebike-image {
    margin-top: 10px;
    width: 60%;
  }
}
</style>