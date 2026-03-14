<template>
  <div class="identity-container">
    <div class="identity-panel">
      <h1>请确认您的身份</h1>

      <div class="identity-options">
        <!-- Manager选项 -->
        <div class="identity-card" @click="goToLogin('manager')">
          <i class="fas fa-user-tie"></i>
          <h2>经理</h2>
          <p>作为经理，您可以访问系统的管理功能。</p>
        </div>

        <!-- Visitor选项 -->
        <div class="identity-card" @click="goToLogin('visitor')">
          <i class="fas fa-user"></i>
          <h2>员工</h2>
          <p>作为员工，您只能查看所属公司的信息。</p>
        </div>
      </div>

      <!-- 系统管理员登录入口 -->
      <div class="admin-link" @click="goToLogin('admin')">
        <a href="#" @click.prevent="goToAdminLogin">
          <i class="fas fa-shield-alt"></i>
          系统管理员登录入口
        </a>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'IdentityDivision',
  methods: {
    goToLogin(type) {
      this.$emit('go-to-login', type);
    },
  }
}
</script>

<style scoped>
.identity-container {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 15px; /* 从20px缩小 */
}

.identity-panel {
  width: 100%;
  max-width: 720px; /* 从900px缩小 */
  text-align: center;
}

.identity-panel h1 {
  color: var(--color-primary-dark);
  font-size: 2rem; /* 从2.5rem缩小 */
  margin-bottom: 48px; /* 从60px缩小 */
}

.identity-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* 从300px缩小 */
  gap: 32px; /* 从40px缩小 */
  justify-content: center;
  margin-bottom: 32px; /* 从40px缩小 */
}

.identity-card {
  background: white;
  padding: 40px 32px; /* 从50px 40px缩小 */
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.identity-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-6px); /* 从-8px缩小 */
  box-shadow: var(--shadow-lg);
}

.identity-card i {
  font-size: 2.4rem; /* 从3rem缩小 */
  color: var(--color-primary);
  display: block;
  margin-bottom: 16px; /* 从20px缩小 */
}

.identity-card h2 {
  color: var(--color-text);
  margin-bottom: 12px; /* 从15px缩小 */
  font-size: 1.1rem; /* 新增明确尺寸 */
}

.identity-card p {
  color: var(--color-text-secondary);
  font-size: 14px; /* 新增 */
}

.admin-link {
  margin-top: 32px; /* 从40px缩小 */
}

.admin-link a {
  color: var(--color-primary);
  font-size: 0.9rem; /* 从1rem缩小 */
  display: inline-flex;
  align-items: center;
  gap: 6px; /* 从8px缩小 */
  padding: 10px 20px; /* 从12px 24px缩小 */
  border-radius: var(--radius-md);
  transition: all 0.3s;
  background: var(--color-primary-lighter);
}

.admin-link a:hover {
  background: var(--color-primary-light);
  transform: translateY(-2px);
}
</style>