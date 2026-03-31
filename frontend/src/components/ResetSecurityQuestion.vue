<template>
  <div class="reset-security-container">
    <div class="form-card">
      <div class="form-header">
        <h2>重置密保问题</h2>
      </div>

      <!-- 步骤指示器 -->
      <div class="steps-indicator">
        <div class="step" :class="{ active: currentStep === 1, completed: currentStep > 1 }">
          <span class="step-number">1</span>
          <span class="step-text">验证原答案</span>
        </div>
        <div class="step-line" :class="{ active: currentStep > 1 }"></div>
        <div class="step" :class="{ active: currentStep === 2 }">
          <span class="step-number">2</span>
          <span class="step-text">设置新答案</span>
        </div>
      </div>

      <!-- 第一步：验证原答案 -->
      <form v-if="currentStep === 1" @submit.prevent="handleVerifyAnswers" class="security-form">
        <div class="info-message">
          <p>请输入您之前设置的密保答案进行验证</p>
        </div>

        <div class="question-group">
          <div class="question-label">
            <span class="question-number">1</span>
            <span class="question-text">您的出生城市是？</span>
          </div>
          <input
            v-model="oldAnswer1"
            type="text"
            placeholder="请输入原答案"
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
            v-model="oldAnswer2"
            type="text"
            placeholder="请输入原答案"
            required
            :disabled="loading"
            maxlength="50"
          />
        </div>

        <button type="submit" class="submit-btn" :disabled="loading || !isStep1Valid">
          <span v-if="loading">验证中...</span>
          <span v-else>下一步</span>
        </button>
      </form>

      <!-- 第二步：设置新答案 -->
      <form v-else-if="currentStep === 2" @submit.prevent="handleSetNewAnswers" class="security-form">
        <div class="info-message success">
          <div class="info-icon">✅</div>
          <p>验证成功！请设置新的密保答案</p>
        </div>

        <div class="question-group">
          <div class="question-label">
            <span class="question-number">1</span>
            <span class="question-text">您的出生城市是？</span>
          </div>
          <input
            v-model="newAnswer1"
            type="text"
            placeholder="请输入新答案"
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
            v-model="newAnswer2"
            type="text"
            placeholder="请输入新答案"
            required
            :disabled="loading"
            maxlength="50"
          />
        </div>

        <div class="tips">
          <p>💡 提示：</p>
          <ul>
            <li>新答案不能与原答案相同</li>
            <li>请牢记新设置的答案</li>
          </ul>
        </div>

        <div class="form-actions">
          <button type="button" @click="currentStep = 1" class="secondary-btn" :disabled="loading">
            上一步
          </button>
          <button type="submit" class="submit-btn" :disabled="loading || !isStep2Valid">
            <span v-if="loading">更新中...</span>
            <span v-else>确认更新</span>
          </button>
        </div>
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
  name: 'ResetSecurityQuestion',
  props: {
    userInfo: {
      type: Object,
      required: true
    },
    existingQuestions: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      currentStep: 1,
      oldAnswer1: '',
      oldAnswer2: '',
      newAnswer1: '',
      newAnswer2: '',
      loading: false,
      errorMessage: ''
    }
  },
  computed: {
    isStep1Valid() {
      return this.oldAnswer1.trim().length > 0 && this.oldAnswer2.trim().length > 0
    },
    isStep2Valid() {
      const newAnswer1Trimmed = this.newAnswer1.trim()
      const newAnswer2Trimmed = this.newAnswer2.trim()
      const oldAnswer1Trimmed = this.oldAnswer1.trim()
      const oldAnswer2Trimmed = this.oldAnswer2.trim()

      return newAnswer1Trimmed.length > 0 &&
             newAnswer2Trimmed.length > 0 &&
             (newAnswer1Trimmed !== oldAnswer1Trimmed || newAnswer2Trimmed !== oldAnswer2Trimmed)
    }
  },
  methods: {
    async handleVerifyAnswers() {
      if (!this.isStep1Valid) return

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await fetch('/api/verify-security-answers', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.userInfo.username,
            answer1: this.oldAnswer1.trim(),
            answer2: this.oldAnswer2.trim()
          })
        })

        const data = await response.json()

        if (response.ok && data.success) {
          // 验证成功，进入第二步
          this.currentStep = 2
          this.errorMessage = ''
        } else {
          this.errorMessage = data.message || '答案验证失败，请检查后重试'
        }
      } catch (error) {
        console.error('验证答案失败:', error)
        this.errorMessage = '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    async handleSetNewAnswers() {
      if (!this.isStep2Valid) return

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await fetch('/api/reset-security-questions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.userInfo.username,
            oldAnswer1: this.oldAnswer1.trim(),
            oldAnswer2: this.oldAnswer2.trim(),
            newAnswer1: this.newAnswer1.trim(),
            newAnswer2: this.newAnswer2.trim()
          })
        })

        const data = await response.json()

        if (response.ok && data.success) {
          this.$emit('success')
        } else {
          this.errorMessage = data.message || '更新失败，请稍后重试'
        }
      } catch (error) {
        console.error('更新密保问题失败:', error)
        this.errorMessage = '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.reset-security-container {
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
  margin-bottom: 32px;
}

.form-header h2 {
  margin: 0;
  color: #5BA0C3;
  font-size: 1.5rem;
  flex: 1;
  text-align: center;
}

/* 步骤指示器 */
.steps-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.3s;
}

.step.active .step-number {
  background: #5ba0c3;
  color: white;
}

.step.completed .step-number {
  background: #10b981;
  color: white;
}

.step-text {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.step.active .step-text,
.step.completed .step-text {
  color: #1e293b;
}

.step-line {
  width: 60px;
  height: 2px;
  background: #e2e8f0;
  margin: 0 16px;
  transition: all 0.3s;
}

.step-line.active {
  background: #10b981;
}

/* 信息提示 */
.info-message {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.info-message.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.info-icon {
  font-size: 20px;
}

.info-message p {
  margin: 0;
  color: #5ba0c3;
  font-size: 14px;
}

.info-message.success p {
  color: #16a34a;
}

/* 表单样式 */
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

/* 提示信息 */
.tips {
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 16px;
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

/* 按钮样式 */
.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.submit-btn,
.secondary-btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
}

.submit-btn {
  background: #5ba0c3;
  color: white;
  flex: 1;
}

.submit-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.secondary-btn {
  background: #f1f5f9;
  color: #475569;
  min-width: 100px;
}

.secondary-btn:hover:not(:disabled) {
  background: #e2e8f0;
}

.submit-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 错误消息 */
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
  .reset-security-container {
    padding: 16px;
  }

  .form-card {
    padding: 24px 20px;
  }

  .steps-indicator {
    transform: scale(0.9);
  }

  .question-text {
    font-size: 14px;
  }

  .form-actions {
    flex-direction: column;
  }

  .secondary-btn {
    width: 100%;
  }
}
</style>