<template>
  <div class="login-container">
    <div class="login-panel">
      <h1>登录</h1>
      <p>{{ greetingText }}</p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="formData.username"
            type="text"
            required
            autocomplete="username"
            :disabled="isLoading"
          >
        </div>

        <div class="form-group">
          <label>密码</label>
          <input
            v-model="formData.password"
            type="password"
            required
            autocomplete="current-password"
            :disabled="isLoading"
          >
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button type="submit" class="login-btn" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>

        <div class="links" :class="{ 'links-center': userType === 'admin' }">
          <a @click="handleForgotPassword" href="javascript:void(0)">忘记密码？</a>
          <a v-if="showSignup && userType !== 'admin'" @click="handleGoToRegister" href="javascript:void(0)">注册账户</a>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { authService } from '@/services/auth';

export default {
  name: 'BaseLogin',
  props: {
    userType: {
      type: String,
      required: true
    },
    greetingText: {
      type: String,
      default: '欢迎登录'
    },
    loginEndpoint: {
      type: String,
      required: true
    },
    successRoute: {
      type: String,
      required: true
    },
    showSignup: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      formData: {
        username: '',
        password: '',
        rememberMe: false
      },
      errorMessage: '',
      isLoading: false
    }
  },
  mounted() {
    // 检查是否有记住的用户名
    const savedUsername = localStorage.getItem(`${this.userType}Username`);
    if (savedUsername) {
      this.formData.username = savedUsername;
      this.formData.rememberMe = true;
    }
  },
  methods: {
    async handleLogin() {
      this.errorMessage = '';
      this.isLoading = true;

      try {
        let response;

        // 根据用户类型调用不同的登录API
        switch (this.userType) {
          case 'manager':
            response = await authService.managerLogin(this.formData);
            break;
          case 'visitor':
            response = await authService.visitorLogin(this.formData);
            break;
          case 'admin':
            response = await authService.adminLogin(this.formData);
            break;
          default:
            throw new Error('未知的用户类型');
        }

        // 处理记住功能（基于是否填写了用户名）
        if (this.formData.username) {
          localStorage.setItem(`${this.userType}Username`, this.formData.username);
        }

        // 保存用户信息
        const userInfo = {
          username: this.formData.username,
          userType: this.userType,
          ...response.data  // 包含后端返回的其他用户信息
        };

        sessionStorage.setItem('userInfo', JSON.stringify(userInfo));

        // 触发登录成功事件
        this.$emit('login-success', userInfo);

      } catch (error) {
        console.error('Login error:', error);

        // 处理错误信息
        if (error.response) {
          // 后端返回的错误
          this.errorMessage = error.response.data.message || '用户名或密码错误';
        } else if (error.request) {
          // 网络错误
          this.errorMessage = '网络错误，请检查后端服务是否启动';
        } else {
          // 其他错误
          this.errorMessage = error.message || '登录失败，请稍后重试';
        }
      } finally {
        this.isLoading = false;
      }
    },

    handleForgotPassword() {
      this.$emit('go-to-forgot-password', {
        type: this.userType,
        step: 'verify-username'
      });
    },

    handleGoToRegister() {
      // 对于游客类型（员工也是游客类型），直接跳转到游客注册
      if (this.userType === 'visitor') {
        this.$emit('go-to-register', 'visitor');
      } else {
        this.$emit('go-to-register', 'choice');
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start; /* 改为flex-start */
  justify-content: center;
  background: var(--color-bg);
  padding: 80px 15px 15px; /* 增加顶部padding，减少底部padding */
}

.login-panel {
  background: white;
  padding: 40px 32px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 360px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  text-align: center;
}

.login-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.login-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 24px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  transition: all 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1);
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 8px 12px;
  border-radius: 5px;
  margin-bottom: 14px;
  font-size: 13px;
  text-align: left;
}

.login-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.links {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  font-size: 13px;
}

/* 当只有一个链接时居中显示 */
.links-center {
  justify-content: center;
}

.links a {
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.3s;
}

.links a:hover {
  text-decoration: underline;
  color: var(--color-primary-dark);
}

/* 响应式设计 */
@media (max-width: 480px) {
  .login-container {
    padding: 60px 15px 15px; /* 移动端减少顶部padding */
  }

  .login-panel {
    padding: 32px 24px;
  }

  .links {
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }

  /* 移动端即使是admin也保持垂直布局 */
  .links-center {
    justify-content: center;
  }
}
</style>