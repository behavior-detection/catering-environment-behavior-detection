<template>
  <div class="find-device-container">
    <!-- 子模块1：监控区域 -->
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


/* 子模块1：监控接入区域 */
.monitor-panel {
  min-height: 680px;
  border: 1px dashed #aaa;
  border-radius: 6px;
  padding: 15px;
  background-color: #f9f9f9;
  color: #666;
  font-size: 14px;
}
</style>
