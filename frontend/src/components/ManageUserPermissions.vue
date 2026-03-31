<template>
  <div class="placeholder-container">
    <h2>管理用户权限</h2>
    <div class="placeholder-content">
      <i class="fas fa-users-cog"></i>
      <p>该功能正在开发中...</p>
      <p class="sub-text">ManageUserPermissions 组件即将上线</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ManageUserPermissions'
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