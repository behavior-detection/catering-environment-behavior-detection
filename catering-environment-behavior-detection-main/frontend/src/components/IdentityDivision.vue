<template>
  <div class="identity-container">
    <div class="identity-panel">
      <h1>请确认您的身份</h1>

      <div class="identity-options">
        <!-- Manager选项 -->
        <div class="identity-card" @click="goToLogin('manager')">
          <i class="fas fa-user-tie"></i>
          <h2>Manager</h2>
          <p>作为Manager，您可以访问系统的管理功能。</p>
        </div>

        <!-- Visitor选项 -->
        <div class="identity-card" @click="goToLogin('visitor')">
          <i class="fas fa-user"></i>
          <h2>Visitor</h2>
          <p>作为Visitor，您只能查看公共信息。</p>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'IdentityDivision',
  methods: {
    goToLogin(type) {
      // 如果type是'admin'，可以选择忽略或重定向到其他类型
      if (type === 'admin') {
        return; // 忽略admin登录请求
      }
      this.$emit('go-to-login', type);
    }
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
  padding: 20px;
}

.identity-panel {
  width: 100%;
  max-width: 900px;
  text-align: center;
}

.identity-panel h1 {
  color: var(--color-primary-dark);
  font-size: 2.5rem;
  margin-bottom: 60px;
}

.identity-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
  justify-content: center;
  margin-bottom: 40px;
}

.identity-card {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.identity-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-8px);
  box-shadow: var(--shadow-lg);
}

.identity-card i {
  font-size: 3rem;
  color: var(--color-primary);
  display: block;
  margin-bottom: 20px;
}

.identity-card h2 {
  color: var(--color-text);
  margin-bottom: 15px;
}

.identity-card p {
  color: var(--color-text-secondary);
}

.admin-link {
  margin-top: 40px;
}

.admin-link a {
  color: var(--color-primary);
  font-size: 1rem;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--radius-md);
  transition: all 0.3s;
  background: var(--color-primary-lighter);
}

.admin-link a:hover {
  background: var(--color-primary-light);
  transform: translateY(-2px);
}
</style>