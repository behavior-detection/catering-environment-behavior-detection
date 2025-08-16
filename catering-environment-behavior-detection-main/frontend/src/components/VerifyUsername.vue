<template>
  <div class="verify-username-container">
    <div class="verify-panel">
      <h1>重置密码</h1>
      <p>请输入您的用户名</p>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" required>
        </div>

        <button type="submit" class="submit-btn">确认</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'VerifyUsername',
  props: ['userType'],
  data() {
    return {
      username: ''
    }
  },
  methods: {
    async handleSubmit() {
      // 验证用户名并触发事件
      this.$emit('go-to-forgot-password', {
        step: 'reset-options',
        username: this.username,
        type: this.userType
      });
    }
  }
}
</script>

<style scoped>
.verify-username-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.verify-panel {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 450px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.verify-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
}

.verify-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 30px;
}

.form-group {
  margin: 30px 0;
}

.form-group label {
  display: block;
  margin-bottom: 10px;
  color: var(--color-text);
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
  text-align: center;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}
</style>