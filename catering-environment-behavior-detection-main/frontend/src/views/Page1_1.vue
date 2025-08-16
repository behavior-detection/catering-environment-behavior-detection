<template>
  <div class="admin-login-container">
    <div class="admin-panel">
      <!-- Logo和标题区域 -->
      <div class="admin-header">
        <div class="admin-icon">
          <i class="icon-shield">🛡️</i>
        </div>
        <h1>系统管理员登录</h1>
        <p>请使用管理员账号登录系统后台</p>
      </div>

      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin" class="admin-form">
        <div class="form-group">
          <label class="form-label">
            <i class="icon-user">👤</i> 管理员账号
          </label>
          <input
            v-model="formData.username"
            type="text"
            class="form-input"
            placeholder="请输入管理员账号"
            required
            autocomplete="username"
          >
        </div>

        <div class="form-group">
          <label class="form-label">
            <i class="icon-lock">🔒</i> 密码
          </label>
          <input
            v-model="formData.password"
            type="password"
            class="form-input"
            placeholder="请输入密码"
            required
            autocomplete="current-password"
          >
        </div>

        <!-- 安全验证码（可选） -->
        <div class="form-group">
          <label class="form-label">
            <i class="icon-shield">🛡️</i> 验证码
          </label>
          <div class="captcha-group">
            <input
              v-model="formData.captcha"
              type="text"
              class="form-input captcha-input"
              placeholder="请输入验证码"
              maxlength="6"
              required
            >
            <div class="captcha-image" @click="refreshCaptcha">
              <span>{{ captchaText }}</span>
              <div class="refresh-icon">🔄</div>
            </div>
          </div>
        </div>

        <!-- 记住我 -->
        <div class="form-check">
          <input
            type="checkbox"
            id="rememberMe"
            v-model="formData.rememberMe"
          >
          <label for="rememberMe">记住我（30天）</label>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-alert">
          <i class="icon-error">⚠️</i> {{ errorMessage }}
        </div>

        <!-- 登录按钮 -->
        <button
          type="submit"
          class="login-btn"
          :disabled="isLoading"
        >
          <span v-if="!isLoading">
            <i class="icon-lock">🔐</i> 安全登录
          </span>
          <span v-else class="loading">
            <span class="spinner"></span> 登录中...
          </span>
        </button>
      </form>

      <!-- 底部链接 -->
      <div class="admin-footer">
        <a @click="goBack" href="javascript:void(0)" class="back-link">
          <i class="icon-arrow-left">←</i> 返回身份选择
        </a>
        <a @click="contactSupport" href="javascript:void(0)" class="support-link">
          <i class="icon-phone">📞</i> 联系技术支持
        </a>
      </div>

      <!-- 安全提示 -->
      <div class="security-notice">
        <i class="icon-info">ℹ️</i>
        <span>此为系统管理员专用入口，所有操作将被记录和审计</span>
      </div>
    </div>
  </div>
</template>

<script>
import { authService } from '@/services/auth';

export default {
  name: 'AdminLogin',
  data() {
    return {
      formData: {
        username: '',
        password: '',
        captcha: '',
        rememberMe: false
      },
      captchaText: '',
      errorMessage: '',
      isLoading: false,
      loginAttempts: 0
    }
  },
  mounted() {
    this.generateCaptcha();
    // 检查是否有记住的用户名
    const savedUsername = localStorage.getItem('adminUsername');
    if (savedUsername) {
      this.formData.username = savedUsername;
      this.formData.rememberMe = true;
    }
  },
  methods: {
    // 生成验证码
    generateCaptcha() {
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
      let captcha = '';
      for (let i = 0; i < 6; i++) {
        captcha += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      this.captchaText = captcha;
    },

    // 刷新验证码
    refreshCaptcha() {
      this.generateCaptcha();
      this.formData.captcha = '';
    },

    // 处理登录
    async handleLogin() {
      // 清除之前的错误
      this.errorMessage = '';

      // 验证验证码
      if (this.formData.captcha.toUpperCase() !== this.captchaText) {
        this.errorMessage = '验证码错误';
        this.refreshCaptcha();
        return;
      }

      this.isLoading = true;

      try {
        // 模拟API调用
        // const response = await authService.adminLogin({
        //   username: this.formData.username,
        //   password: this.formData.password
        // });

        // 模拟延迟
        await new Promise(resolve => setTimeout(resolve, 1500));

        // 模拟验证
        if (this.formData.username === 'admin' && this.formData.password === 'admin123') {
          // 处理记住我
          if (this.formData.rememberMe) {
            localStorage.setItem('adminUsername', this.formData.username);
          } else {
            localStorage.removeItem('adminUsername');
          }

          // 保存管理员信息
          sessionStorage.setItem('adminInfo', JSON.stringify({
            username: this.formData.username,
            role: 'admin',
            loginTime: new Date().toISOString()
          }));

          // 触发登录成功事件
          this.$emit('login-success', {
            username: this.formData.username,
            role: 'admin'
          });

          // 或者跳转到管理后台
          // this.$router.push('/admin/dashboard');
        } else {
          this.loginAttempts++;
          if (this.loginAttempts >= 3) {
            this.errorMessage = '登录失败次数过多，请联系技术支持';
          } else {
            this.errorMessage = '用户名或密码错误';
          }
          this.refreshCaptcha();
        }
      } catch (error) {
        this.errorMessage = '系统错误，请稍后重试';
        this.refreshCaptcha();
      } finally {
        this.isLoading = false;
      }
    },

    // 返回身份选择
    goBack() {
      this.$emit('go-back');
      // 或者使用路由
      // this.$router.push('/');
    },

    // 联系支持
    contactSupport() {
      alert('技术支持电话：400-888-8888\n邮箱：admin@system.com');
    }
  }
}
</script>

<style scoped>
.admin-login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
  position: relative;
}

.admin-login-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    repeating-linear-gradient(
      45deg,
      transparent,
      transparent 10px,
      rgba(255, 255, 255, 0.05) 10px,
      rgba(255, 255, 255, 0.05) 20px
    );
  pointer-events: none;
}

.admin-panel {
  background: white;
  padding: 60px 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 500px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--color-border);
  position: relative;
}

.admin-header {
  text-align: center;
  margin-bottom: 40px;
}

.admin-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  box-shadow: 0 8px 16px rgba(135, 206, 235, 0.2);
}

.admin-header h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
  font-size: 2rem;
}

.admin-header p {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.admin-form {
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 14px;
}

.form-label i {
  font-size: 1rem;
}

.captcha-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.captcha-input {
  flex: 1;
}

.captcha-image {
  background: var(--color-primary-lighter);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  user-select: none;
  transition: all 0.3s;
}

.captcha-image:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.captcha-image span {
  font-family: monospace;
  font-size: 20px;
  font-weight: bold;
  letter-spacing: 3px;
  color: var(--color-primary-dark);
}

.refresh-icon {
  font-size: 1rem;
  transition: transform 0.3s;
}

.captcha-image:hover .refresh-icon {
  transform: rotate(180deg);
}

.form-check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.form-check input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.form-check label {
  font-size: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.error-alert {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: var(--color-error);
  padding: 12px 16px;
  border-radius: var(--radius-md);
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  animation: shake 0.5s;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.login-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-primary-dark) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(70, 130, 180, 0.3);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.admin-footer {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.back-link,
.support-link {
  color: var(--color-primary);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s;
}

.back-link:hover,
.support-link:hover {
  color: var(--color-primary-dark);
  transform: translateX(-2px);
}

.security-notice {
  background: var(--color-primary-lighter);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 响应式设计 */
@media (max-width: 480px) {
  .admin-panel {
    padding: 40px 30px;
  }

  .admin-header h1 {
    font-size: 1.5rem;
  }

  .captcha-group {
    flex-direction: column;
  }

  .captcha-image {
    width: 100%;
    justify-content: center;
  }
}
</style>