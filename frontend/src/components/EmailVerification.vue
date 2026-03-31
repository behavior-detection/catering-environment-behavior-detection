<template>
  <div class="email-verification-container">
    <div class="verification-panel">
      <h2>{{ scenario === 'register' ? '邮箱验证' : '通过邮箱重置密码' }}</h2>
      <p class="subtitle">{{ subtitleText }}</p>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <!-- 成功提示 -->
      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>

      <!-- 邮箱输入 -->
      <div v-if="!emailVerified" class="form-group">
        <label>{{ scenario === 'register' ? '邮箱地址' : '注册邮箱' }}</label>
        <div class="input-with-button">
          <input
            v-model="email"
            type="email"
            placeholder="请输入您的注册邮箱"
            :disabled="isLoading"
            @keydown.enter="verifyEmail"
            :class="['form-input', {
              'error': showEmailError,
              'success': showEmailSuccess
            }]"
          >
          <button
            @click="verifyEmail"
            class="verify-btn"
            :disabled="isLoading || !email"
          >
            {{ isLoading ? '验证中...' : '验证邮箱' }}
          </button>
        </div>
      </div>

      <!-- 验证码输入 -->
      <div v-if="emailVerified && !codeVerified" class="form-group">
        <label>验证码</label>
        <p class="info-text">验证码已发送到：{{ maskedEmail }}</p>
        <div class="code-input-group">
          <input
            v-model="verificationCode"
            type="text"
            placeholder="请输入6位验证码"
            maxlength="6"
            :disabled="isVerifying"
            @keydown.enter="verifyCode"
            :class="['form-input', {
              'error': showCodeError
            }]"
          >
          <button
            v-if="countdown === 0"
            @click="resendCode"
            class="resend-btn"
            :disabled="isSendingCode"
          >
            重新发送
          </button>
          <span v-else class="countdown-text">
            {{ countdown }}秒后可重新发送
          </span>
        </div>

        <button
          @click="verifyCode"
          class="submit-btn"
          :disabled="isVerifying || !verificationCode"
        >
          {{ isVerifying ? '验证中...' : '提交验证码' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EmailVerification',
  props: {
    username: {
      type: String,
      default: ''
    },
    userType: {
      type: String,
      default: ''
    },
    // 新增：使用场景 - 'register' 或 'reset-password'
    scenario: {
      type: String,
      default: 'reset-password',
      validator: value => ['register', 'reset-password'].includes(value)
    }
  },
  data() {
    return {
      email: '',
      verificationCode: '',
      emailVerified: false,
      codeVerified: false,
      isLoading: false,
      isSendingCode: false,
      isVerifying: false,
      countdown: 0,
      countdownTimer: null,
      errorMessage: '',
      successMessage: '',
      showEmailError: false,
      showEmailSuccess: false,
      showCodeError: false
    }
  },
  computed: {
    // 显示邮箱地址
    maskedEmail() {
      if (!this.email) return '';
      const [localPart, domain] = this.email.split('@');
      if (localPart.length <= 3) {
        return `${localPart[0]}***@${domain}`;
      }
      return `${localPart.substring(0, 3)}***@${domain}`;
    },
    // 动态副标题文本
    subtitleText() {
      if (this.scenario === 'register') {
        return '请输入您的邮箱地址以接收验证码';
      }
      return '请输入您注册时使用的邮箱地址';
    }
  },
  methods: {
    // 验证邮箱是否与用户名匹配（仅在重置密码场景中）
    async verifyEmail() {
      if (!this.email) {
        this.errorMessage = '请输入邮箱地址';
        this.showEmailError = true;
        return;
      }

      // 验证邮箱格式
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.email)) {
        this.errorMessage = '请输入有效的邮箱地址';
        this.showEmailError = true;
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';
      this.successMessage = '';
      this.showEmailError = false;

      try {
        // 仅在重置密码场景下验证邮箱与用户名是否匹配
        if (this.scenario === 'reset-password' && this.username) {
          const verifyResponse = await fetch('/api/verify-user-email', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              username: this.username,
              email: this.email
            })
          });

          const verifyResult = await verifyResponse.json();

          if (!verifyResult.success) {
            this.errorMessage = verifyResult.message || '邮箱与用户名不匹配';
            this.showEmailError = true;
            return;
          }
        }

        // 发送验证码（注册或验证通过后）
        const sendResponse = await fetch('/api/send-verification-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: this.email })
        });

        const sendResult = await sendResponse.json();

        if (sendResult.success) {
          this.emailVerified = true;
          this.showEmailSuccess = true;
          this.successMessage = '验证码已发送到您的邮箱';
          this.startCountdown();
        } else {
          this.errorMessage = sendResult.message || '验证码发送失败';
        }
      } catch (error) {
        console.error('Error:', error);
        this.errorMessage = '网络错误，请稍后重试';
      } finally {
        this.isLoading = false;
      }
    },

    // 验证验证码
    async verifyCode() {
      if (!this.verificationCode || this.verificationCode.length !== 6) {
        this.errorMessage = '请输入6位验证码';
        this.showCodeError = true;
        return;
      }

      this.isVerifying = true;
      this.errorMessage = '';
      this.showCodeError = false;

      try {
        const response = await fetch('/api/verify-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.email,
            code: this.verificationCode
          })
        });

        const result = await response.json();

        if (result.success) {
          this.codeVerified = true;
          this.successMessage = '邮箱验证成功！';

          // 根据场景触发不同事件
          if (this.scenario === 'register') {
            // 注册场景：直接返回验证成功状态
            this.$emit('email-verified', {
              email: this.email,
              verified: true
            });
          } else {
            // 密码重置场景：跳转到密码重置页面
            setTimeout(() => {
              this.$emit('go-to-forgot-password', {
                step: 'reset-password',
                username: this.username,
                type: this.userType,
                verified: true,
                verificationMethod: 'email'
              });
            }, 1500);
          }
        } else {
          this.errorMessage = result.message || '验证码错误';
          this.showCodeError = true;
        }
      } catch (error) {
        console.error('Error:', error);
        this.errorMessage = '验证失败，请重试';
      } finally {
        this.isVerifying = false;
      }
    },

    // 重新发送验证码
    async resendCode() {
      this.isSendingCode = true;
      this.errorMessage = '';

      try {
        const response = await fetch('/api/send-verification-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: this.email })
        });

        const result = await response.json();

        if (result.success) {
          this.successMessage = '验证码已重新发送';
          this.startCountdown();
          this.verificationCode = ''; // 清空之前的验证码
        } else {
          this.errorMessage = result.message || '验证码发送失败';
        }
      } catch (error) {
        console.error('Error:', error);
        this.errorMessage = '网络错误，请稍后重试';
      } finally {
        this.isSendingCode = false;
      }
    },

    // 开始倒计时
    startCountdown() {
      this.countdown = 60;
      this.countdownTimer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(this.countdownTimer);
        }
      }, 1000);
    }
  },

  beforeDestroy() {
    // 清除倒计时
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  }
}
</script>

<style scoped>
.email-verification-container {
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
  margin-bottom: 8px;
  font-size: 20px;
}

.subtitle {
  color: #666;
  text-align: center;
  margin-bottom: 24px;
  font-size: 13px;
}

/* 消息提示 */
.error-message, .success-message {
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 16px;
  text-align: center;
  font-size: 13px;
}

.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
}

.success-message {
  background: #f0f9ff;
  border: 1px solid #91d5ff;
  color: #1890ff;
}

/* 表单样式 */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.info-text {
  color: #666;
  font-size: 13px;
  margin-bottom: 10px;
}

.input-with-button {
  display: flex;
  gap: 8px;
}

.form-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid #e6f2ff;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s;
}

.form-input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1);
}

.form-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.form-input.error {
  border-color: #ff4d4f;
}

.form-input.success {
  border-color: #52c41a;
}

/* 验证码输入组 */
.code-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.code-input-group .form-input {
  flex: 1;
}

/* 按钮样式 */
.verify-btn, .submit-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #87ceeb 0%, #4a90e2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
}

.submit-btn {
  width: 100%;
  padding: 12px;
}

.verify-btn:hover:not(:disabled),
.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25);
}

.verify-btn:disabled,
.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}

.resend-btn {
  padding: 6px 14px;
  background: white;
  color: #4a90e2;
  border: 2px solid #4a90e2;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
}

.resend-btn:hover:not(:disabled) {
  background: #4a90e2;
  color: white;
}

.resend-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.countdown-text {
  color: #666;
  font-size: 13px;
  white-space: nowrap;
}

/* 响应式设计 */
@media (max-width: 600px) {
  .verification-panel {
    padding: 32px 16px;
  }

  .input-with-button {
    flex-direction: column;
  }

  .verify-btn {
    width: 100%;
  }
}
</style>