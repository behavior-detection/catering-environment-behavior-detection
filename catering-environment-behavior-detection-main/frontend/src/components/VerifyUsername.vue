<template>
  <div class="verify-username-container">
    <div class="verify-panel">
      <h1>重置密码</h1>
      <p>请输入您的用户名</p>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            :disabled="isLoading"
            required
          >
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading || !username">
          {{ isLoading ? '验证中...' : '确认' }}
        </button>
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
      username: '',
      isLoading: false,
      errorMessage: ''
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.username.trim()) {
        this.errorMessage = '请输入用户名';
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';

      try {
        // 根据用户类型构建不同的验证URL
        let checkUrl = '';

        if (this.userType === 'manager') {
          checkUrl = '/api/check-manager-username';
        } else if (this.userType === 'visitor') {
          checkUrl = '/api/check-visitor-username';
        } else {
          checkUrl = '/api/check-admin-username';
        }

        // 验证用户名是否存在
        const response = await fetch(checkUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ username: this.username.trim() })
        });

        const result = await response.json();

        if (result.success && result.exists) {
          // 用户名存在，继续重置密码流程
          this.$emit('go-to-forgot-password', {
            step: 'reset-options',
            username: this.username.trim(),
            type: this.userType
          });
        } else {
          // 用户名不存在
          this.errorMessage = `该用户名在${this.userType === 'manager' ? '经理' : '访客'}系统中不存在`;
        }
      } catch (error) {
        console.error('Error checking username:', error);
        this.errorMessage = '网络错误，请稍后重试';
      } finally {
        this.isLoading = false;
      }
    }
  }
}
</script>

<style scoped>
.verify-username-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: var(--color-bg);
  padding: 120px 15px 15px; /* 添加顶部padding，让内容上移 */
}

.verify-panel {
  background: white;
  padding: 40px 32px; /* 从50px 40px缩小 */
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 360px; /* 从450px缩小 */
  text-align: center;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.verify-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 8px; /* 从10px缩小 */
  font-size: 1.5rem; /* 新增明确尺寸 */
}

.verify-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 24px; /* 从30px缩小 */
  font-size: 14px; /* 新增 */
}

/* 错误消息 */
.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 8px 12px; /* 从10px 14px缩小 */
  border-radius: 5px; /* 从6px缩小 */
  margin-bottom: 16px; /* 从20px缩小 */
  font-size: 13px; /* 从14px缩小 */
}

.form-group {
  margin: 24px 0; /* 从30px 0缩小 */
}

.form-group label {
  display: block;
  margin-bottom: 8px; /* 从10px缩小 */
  color: var(--color-text);
  font-weight: 500;
  font-size: 14px; /* 新增 */
}

.form-group input {
  width: 100%;
  padding: 12px; /* 从14px缩小 */
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px; /* 从16px缩小 */
  text-align: center;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1); /* 从4px缩小 */
}

.form-group input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.submit-btn {
  width: 100%;
  padding: 12px; /* 从14px缩小 */
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px; /* 从18px缩小 */
  cursor: pointer;
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25); /* 从6px 20px缩小 */
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}
</style>