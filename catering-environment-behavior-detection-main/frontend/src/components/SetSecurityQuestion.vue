<template>
  <div class="set-security-container">
    <div class="form-card">
      <div class="form-header">
        <h2>设置密保问题</h2>
      </div>

      <div class="info-message">
        <p>请设置密保问题，用于找回密码或增强账户安全</p>
      </div>

      <form @submit.prevent="handleSetSecurity" class="security-form">
        <div class="question-group">
          <div class="question-label">
            <span class="question-number">1</span>
            <span class="question-text">您的出生城市是？</span>
          </div>
          <input
            v-model="answer1"
            type="text"
            placeholder="请输入答案"
            required
            :disabled="loading"
            maxlength="50"
          />
        </div>

        <div class="question-group">
          <div class="question-label">
            <span class="question-number">2</span>
            <span class="question-text">您最喜欢的颜色是？</span>
          </div>
          <input
            v-model="answer2"
            type="text"
            placeholder="请输入答案"
            required
            :disabled="loading"
            maxlength="50"
          />
        </div>

        <div class="tips">
          <ul>
            <li>请记住您设置的答案，用于后续验证</li>
            <li>答案区分大小写</li>
            <li>建议使用易记但他人难以猜测的答案</li>
          </ul>
        </div>

        <button type="submit" class="submit-btn" :disabled="loading || !isFormValid">
          <span v-if="loading">设置中...</span>
          <span v-else>确认设置</span>
        </button>
      </form>

      <!-- 错误消息 -->
      <div v-if="errorMessage" class="error-message">
        <span>✗</span> {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SetSecurityQuestion',
  props: {
    userInfo: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      answer1: '',
      answer2: '',
      loading: false,
      errorMessage: ''
    }
  },
  computed: {
    isFormValid() {
      return this.answer1.trim().length > 0 && this.answer2.trim().length > 0
    }
  },
  methods: {
    async handleSetSecurity() {
      if (!this.isFormValid) return

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await fetch('/api/set-security-questions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.userInfo.username,
            answer1: this.answer1.trim(),
            answer2: this.answer2.trim()
          })
        })

        const data = await response.json()

        if (response.ok && data.success) {
          this.$emit('success')
        } else {
          this.errorMessage = data.message || '设置失败，请稍后重试'
        }
      } catch (error) {
        console.error('设置密保问题失败:', error)
        this.errorMessage = '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.set-security-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.form-card {
  background: white;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}


.form-header h2 {
  margin: 0;
  color: #5BA0C3;
  font-size: 1.5rem;
  flex: 1;
  text-align: center;
}

.info-message {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.info-icon {
  font-size: 20px;
}

.info-message p {
  margin: 0;
  color: #5ba0c3;
  font-size: 14px;
}

.security-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.question-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-label {
  display: flex;
  align-items: center;
  gap: 12px;
}

.question-number {
  background: #5ba0c3;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.question-text {
  color: #1e293b;
  font-weight: 500;
  font-size: 16px;
}

.question-group input {
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.3s;
}

.question-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.question-group input:disabled {
  background: #f8fafc;
  cursor: not-allowed;
}

.tips {
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 16px;
  margin-top: 8px;
}

.tips p {
  margin: 0 0 8px 0;
  font-weight: 500;
  color: #92400e;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
  color: #92400e;
  font-size: 14px;
}

.tips li {
  margin-bottom: 4px;
}

.submit-btn {
  background: #3b82f6;
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
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.submit-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  margin-top: 24px;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
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

/* 响应式设计 */
@media (max-width: 640px) {
  .set-security-container {
    padding: 16px;
  }

  .form-card {
    padding: 24px 20px;
  }

  .question-text {
    font-size: 14px;
  }
}
</style>