<template>
  <div class="login-container">
    <div class="login-panel">
      <h1>登录</h1>
      <p>{{ greetingText }}</p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="formData.username" type="text" required>
        </div>

        <div class="form-group">
          <label>密码</label>
          <input v-model="formData.password" type="password" required>
        </div>

        <button type="submit" class="login-btn">登录</button>

        <div class="links">
          <a @click="goToForgotPassword" href="javascript:void(0)">忘记密码？</a>
          <a v-if="showSignup" @click="goToRegister" href="javascript:void(0)">注册账号</a>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BaseLogin',
  props: {
    userType: String,
    greetingText: String,
    loginEndpoint: String,
    successRoute: String,
    showSignup: Boolean
  },
  data() {
    return {
      formData: {
        username: '',
        password: ''
      }
    }
  },
  methods: {
    async handleLogin() {
      // 处理登录逻辑
      try {
        // 模拟API调用
        console.log('登录中...', this.loginEndpoint)

        // 触发登录成功事件
        this.$emit('login-success', {
          username: this.formData.username
        })
      } catch (error) {
        console.error('登录失败:', error)
      }
    },

    goToForgotPassword() {
      // 触发忘记密码事件
      this.$emit('go-to-forgot-password', {
        type: this.userType,
        step: 'verify-username'
      })
    },

    goToRegister() {
      // 根据用户类型决定注册流程
      if (this.userType === 'visitor') {
        this.$emit('go-to-register', 'visitor')
      } else {
        this.$emit('go-to-register', 'choice')
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.login-panel {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 450px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  text-align: center;
}

.login-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
}

.login-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 24px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text);
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
  transition: all 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.login-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}

.links {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  font-size: 14px;
}

.links a {
  color: var(--color-primary);
  cursor: pointer;
}

.links a:hover {
  text-decoration: underline;
}
</style>