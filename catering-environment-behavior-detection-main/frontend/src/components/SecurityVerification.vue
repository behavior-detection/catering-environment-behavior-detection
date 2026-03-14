<template>
  <div class="security-verification-container">
    <div class="verification-panel">
      <h2>请回答安全问题</h2>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- 问题列表 -->
      <div v-else-if="questions.length > 0" class="questions-container">
        <div v-for="(question, index) in questions" :key="index" class="question-group">
          <p class="question-text">{{ question }}</p>
          <input
            v-model="answers[index]"
            type="text"
            placeholder="请输入答案"
            :disabled="isSubmitting"
            @keydown.enter="submitAnswers"
          >
        </div>

        <button
          @click="submitAnswers"
          class="submit-btn"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? '验证中...' : '提交答案' }}
        </button>
      </div>

      <!-- 无安全问题提示 -->
      <div v-else-if="!isLoading && questions.length === 0" class="no-questions">
        <p>该用户未设置安全问题</p>
        <button @click="goBack" class="secondary-btn">选择其他验证方式</button>
      </div>
    </div>
  </div>
</template>

<script>
import { authService } from '@/services/auth';

export default {
  name: 'SecurityVerification',
  props: {
    username: {
      type: String,
      required: true
    },
    userType: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      questions: [],
      answers: [],
      isLoading: false,
      isSubmitting: false,
      errorMessage: ''
    }
  },
  async mounted() {
    await this.loadSecurityQuestions();
  },
  methods: {
    async loadSecurityQuestions() {
      // 验证必需参数
      if (!this.username) {
        this.errorMessage = '用户名缺失，请返回重试';
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';

      try {
        const response = await fetch(`/get-security-questions?username=${encodeURIComponent(this.username)}`);

        // 检查响应是否为JSON
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("服务器返回了非JSON响应");
        }

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
          this.questions = result.questions || [];
          // 初始化答案数组
          this.answers = new Array(this.questions.length).fill('');

          if (this.questions.length === 0) {
            this.errorMessage = '该用户未设置安全问题，请选择其他验证方式';
          }
        } else {
          this.errorMessage = result.message || '无法加载安全问题';
        }
      } catch (error) {
        console.error('Error loading security questions:', error);
        this.errorMessage = '加载安全问题时发生错误，请重试';
      } finally {
        this.isLoading = false;
      }
    },

    async submitAnswers() {
      // 验证必需参数
      if (!this.username) {
        this.errorMessage = '用户名缺失，请返回重试';
        return;
      }

      // 检查是否所有问题都已回答
      const validAnswers = this.answers.filter(answer => answer && answer.trim());
      if (validAnswers.length === 0) {
        this.errorMessage = '请至少回答一个问题';
        return;
      }

      this.isSubmitting = true;
      this.errorMessage = '';

      try {
        const response = await fetch('/verify-security-answers', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.username,
            answers: validAnswers
          })
        });

        // 检查响应是否为JSON
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("服务器返回了非JSON响应");
        }

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
          alert('安全问题验证成功！');

          // 跳转到密码重置页面
          this.$emit('go-to-forgot-password', {
            step: 'reset-password',
            username: this.username,
            type: this.userType,
            verified: true
          });
        } else {
          this.errorMessage = result.message || '答案错误，请重试';
        }
      } catch (error) {
        console.error('Error verifying answers:', error);
        this.errorMessage = '验证答案时发生错误，请重试';
      } finally {
        this.isSubmitting = false;
      }
    },

    // 返回上一页
    goBack() {
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
.security-verification-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: white; /* 改为白色背景 */
  padding: 100px 15px 15px; /* 添加顶部padding，让内容上移 */
}

.verification-panel {
  background: white;
  padding: 40px 32px;
  border-radius: 16px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  border: 1px solid #e6f2ff;
}

.verification-panel h2 {
  color: #5ba0c3;
  text-align: center;
  margin-bottom: 24px;
  font-size: 20px;
}

/* 错误消息 */
.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 16px;
  text-align: center;
  font-size: 13px;
}

/* 加载状态 */
.loading-container {
  text-align: center;
  padding: 32px 0;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 14px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4a90e2;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-container p {
  color: #666;
  font-size: 13px;
}

/* 问题容器 */
.questions-container {
  margin-top: 16px;
}

.question-group {
  margin-bottom: 20px;
}

.question-text {
  font-size: 14px;
  margin-bottom: 10px;
  font-weight: 500;
  color: #333;
  line-height: 1.5;
}

.question-group input {
  width: 100%;
  padding: 10px 14px;
  border: 2px solid #e6f2ff;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s;
}

.question-group input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1);
}

.question-group input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

/* 按钮样式 */
.submit-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  margin-top: 24px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25);
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}

.secondary-btn {
  padding: 10px 24px;
  background: #f8f9fa;
  color: #4a90e2;
  border: 2px solid #e6f2ff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
  margin-top: 16px;
}

.secondary-btn:hover {
  background: #e6f2ff;
  border-color: #4a90e2;
}

/* 无安全问题提示 */
.no-questions {
  text-align: center;
  padding: 32px 0;
}

.no-questions p {
  color: #666;
  font-size: 14px;
  margin-bottom: 16px;
}

/* 响应式设计 */
@media (max-width: 600px) {
  .verification-panel {
    padding: 32px 16px;
  }

  .verification-panel h2 {
    font-size: 18px;
  }

  .question-text {
    font-size: 13px;
  }

  .question-group input {
    font-size: 13px;
    padding: 8px 12px;
  }
}
</style>