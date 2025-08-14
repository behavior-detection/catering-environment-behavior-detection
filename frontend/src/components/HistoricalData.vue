<template>
  <div class="find-device-container">
    <!-- 子模块1：搜索区域 -->
    <div class="search-panel">
      <p>选择您要查看的时间段：</p>
      <select class=" time-select">
        <!-- 这里到时候要对接数据库，与后端交互，数据库中可选时间段就是这里的选项 -->
        <option value="">请选择</option>
        <option value="1st_period_of_time">6:00-8:00</option>
        <option value="2nd_period_of_time">8:00-10:00</option>
        <option value="3th_period_of_time">10:00-12:00</option>
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



/* 下拉框样式 */
.time-select {
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
