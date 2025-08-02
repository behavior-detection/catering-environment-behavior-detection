<template>
  <div class="find-device-container">
    <!-- 子模块1：搜索区域 -->
    <div class="search-panel">
      <input type="text" placeholder="请根据今天的数据，着重关注锚点和关键指标，分析后续我应该如何运营店铺" class="search-input" />

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



</style>
