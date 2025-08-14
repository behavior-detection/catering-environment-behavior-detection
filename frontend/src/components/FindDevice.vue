<template>
  <div class="find-device-container">
    <!-- 子模块1：搜索区域 -->
    <div class="search-panel">
      <input type="text" placeholder="请输入企业执照" class="search-input" />
      <select class="device-select">
        <option value="">请选择你要查看的监控</option>
        <option value="camera">摄像头</option>
        <option value="sensor">传感器</option>
        <option value="other">其他设备</option>
      </select>
    </div>

    <!-- 子模块2：监控区域 -->
    <div class="monitor-panel">
      <!-- 这里可以嵌入 iframe 或 canvas 等外部监控接口 -->
      <p>这里是监控接口区域，可嵌入外部视频或控制台。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FindDevice'
}
</script>

<style scoped>
/* 外层容器：设置与顶部/左侧导航栏间距 */
.find-device-container {
  margin-top: 20px;
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px; /* 子模块之间的间距 */
}

/* 子模块1：搜索与筛选区域 */
.search-panel {
  padding: 15px;
  border: 1px solid #cce7ff; /* 浅蓝色描边 */
  box-shadow: 0 4px 8px -2px #cce7ff; /* 同色系阴影 */
  border-radius: 8px;
  background-color: #ffffff;
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 输入框样式 */
.search-input {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  flex: 1;
}

/* 下拉框样式 */
.device-select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

/* 子模块2：监控接入区域 */
.monitor-panel {
  min-height: 200px;
  border: 1px dashed #aaa;
  border-radius: 6px;
  padding: 15px;
  background-color: #f9f9f9;
  color: #666;
  font-size: 14px;
}
</style>
