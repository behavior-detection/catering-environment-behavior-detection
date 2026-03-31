<template>
  <div class="placeholder-container">
    <h2>权限日志</h2>
    <div class="placeholder-content">
      <i class="fas fa-history"></i>
      <p>该功能正在开发中...</p>
      <p class="sub-text">PermissionLogs 组件即将上线</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PermissionLogs'
}
</script>

<style scoped>
.placeholder-container {
  text-align: center;
  padding: 40px;
}

.placeholder-container h2 {
  color: #333;
  margin-bottom: 30px;
}

.placeholder-content {
  background: white;
  border-radius: 8px;
  padding: 60px 40px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  max-width: 500px;
  margin: 0 auto;
}

.placeholder-content i {
  font-size: 48px;
  color: #1890ff;
  margin-bottom: 20px;
}

.placeholder-content p {
  color: #666;
  margin: 10px 0;
  font-size: 16px;
}

.placeholder-content .sub-text {
  font-size: 14px;
  color: #999;
}
</style>