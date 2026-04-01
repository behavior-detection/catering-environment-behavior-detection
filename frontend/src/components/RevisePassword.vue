<template>
  <main>
  <div class="revise-password-container">
    <!-- 全局返回按钮 -->
    <div v-if="showBackButton" class="back-button-wrapper">
      <button @click="goBack" class="global-back-btn">
        返回
      </button>
    </div>

    <div class="form-card">
      <div class="form-header">
        <h2>更改密码</h2>
      </div>

      <form @submit.prevent="handlePasswordChange" class="password-form">
        <div class="form-group">
          <label for="oldPassword">当前密码</label>
          <input
            id="oldPassword"
            v-model="oldPassword"
            type="password"
            placeholder="请输入当前密码"
            required
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="newPassword">新密码</label>
          <input
            id="newPassword"
            v-model="newPassword"
            type="password"
            placeholder="请输入新密码"
            required
            :disabled="loading"
            @input="validatePassword"
          />
          <div v-if="passwordError" class="error-text">{{ passwordError }}</div>
        </div>

        <div class="form-group">
          <label for="confirmPassword">确认新密码</label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            required
            :disabled="loading"
            @input="validatePasswordMatch"
          />
          <div v-if="confirmError" class="error-text">{{ confirmError }}</div>
        </div>

        <button type="submit" class="submit-btn" :disabled="loading || !isFormValid">
          <span v-if="loading">更新中...</span>
          <span v-else>更新密码</span>
        </button>
      </form>

      <!-- 成功消息 -->
      <div v-if="successMessage" class="success-message">
        <span>✓</span> {{ successMessage }}
      </div>

      <!-- 错误消息 -->
      <div v-if="errorMessage" class="error-message">
        <span>✗</span> {{ errorMessage }}
      </div>
    </div>
  </div>
  </main>
</template>

<script>
export default {
  name: 'RevisePassword',
  props: {
    userInfo: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
      loading: false,
      successMessage: '',
      errorMessage: '',
      passwordError: '',
      confirmError: ''
    }
  },
  computed: {
    isFormValid() {
      return this.oldPassword &&
             this.newPassword &&
             this.confirmPassword &&
             this.newPassword === this.confirmPassword &&
             this.newPassword.length >= 6
    }
  },
  methods: {
    validatePassword() {
      if (this.newPassword.length < 6) {
        this.passwordError = '密码长度至少为6位'
      } else if (this.newPassword === this.oldPassword) {
        this.passwordError = '新密码不能与旧密码相同'
      } else {
        this.passwordError = ''
      }
      this.validatePasswordMatch()
    },

    validatePasswordMatch() {
      if (this.confirmPassword && this.newPassword !== this.confirmPassword) {
        this.confirmError = '两次输入的密码不一致'
      } else {
        this.confirmError = ''
      }
    },

    async handlePasswordChange() {
      if (!this.isFormValid) return

      this.loading = true
      this.successMessage = ''
      this.errorMessage = ''

      try {
        const token = localStorage.getItem('authToken')
        const response = await fetch('/api/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            username: this.userInfo.username,
            userType: this.userInfo.userType,
            oldPassword: this.oldPassword,
            newPassword: this.newPassword
          })
        })

        const data = await response.json()

        if (response.ok && data.success) {
          this.successMessage = '密码更新成功！'
          // 清空表单
          this.oldPassword = ''
          this.newPassword = ''
          this.confirmPassword = ''

          // 3秒后返回
          setTimeout(() => {
            this.$emit('back')
          }, 3000)
        } else {
          this.errorMessage = data.message || '密码更新失败'
        }
      } catch (error) {
        console.error('更新密码失败:', error)
        this.errorMessage = '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
main {
  min-height: 100vh;
  width: 100%;
  overflow-x: hidden;
  position: relative;
}

/* 返回按钮样式 - 改为相对定位 */
.back-button-wrapper {
  position: relative;
  margin: 20px 0 -10px 20px; /* 向上挪动通过负margin实现 */
  z-index: 999;
  display: inline-block;
}

.global-back-btn {
  padding: 12px 28px;
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary-light);
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.global-back-btn:hover {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 添加进入动画 */
.back-button-wrapper {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .back-button-wrapper {
    margin: 15px 0 -8px 10px;
  }

  .global-back-btn {
    padding: 10px 20px;
    font-size: 14px;
  }
}

/* 小屏幕优化 */
@media (max-width: 480px) {
  .back-button-wrapper {
    margin: 10px 0 -5px 10px;
  }

  .global-back-btn {
    padding: 8px 16px;
    font-size: 13px;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.form-card {
  max-width: 500px;
  margin: 20px auto;
  background: white;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.form-header {
  margin-bottom: 32px;
}

.form-header h2 {
  margin: 0;
  color: #5BA0C3;
  font-size: 1.5rem;
  text-align: center;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 500;
  color: #5BA0C3;
  font-size: 14px;
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid #5BA0C333;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #5BA0C3;
  box-shadow: 0 0 0 3px #5BA0C31A;
}

.form-group input:disabled {
  background: #f8fafc;
  cursor: not-allowed;
}

.error-text {
  color: #ef4444;
  font-size: 12px;
  margin-top: 4px;
}

.submit-btn {
  background: #5BA0C3;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background: #4A8FB2;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(91, 160, 195, 0.2);
}

.submit-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  transform: none;
}

.success-message,
.error-message {
  margin-top: 24px;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.success-message {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.success-message span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: #16a34a;
  color: white;
  border-radius: 50%;
  font-size: 12px;
}

.error-message {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.error-message span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: #dc2626;
  color: white;
  border-radius: 50%;
  font-size: 12px;
}


</style>