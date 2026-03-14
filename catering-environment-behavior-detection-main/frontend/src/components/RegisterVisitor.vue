<template>
  <div class="register-visitor-container">
    <div class="registration-panel">
      <h1>员工注册</h1>

      <!-- 进度条 -->
      <div class="progress-bar">
        <div class="progress-fill" :style="{width: progressPercentage + '%'}"></div>
      </div>

      <!-- 步骤指示器 -->
      <div class="step-indicators">
        <div
          v-for="i in 3"
          :key="i"
          :class="['step-dot', {
            'active': i === currentStep,
            'completed': i < currentStep
          }]"
        >
          {{ i }}
        </div>
      </div>

      <!-- 步骤1：用户名 -->
      <div v-show="currentStep === 1" class="step">
        <h2>设置用户名</h2>
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="formData.username"
            @input="clearUsernameMessages"
            @blur="validateUsername"
            :class="['form-input', {
              'error': showUsernameError,
              'success': showUsernameSuccess
            }]"
            type="text"
            placeholder="请输入用户名（3-20个字符）"
            @keydown.enter="nextStep(1)"
          >
          <div v-if="showUsernameError" class="error-message">{{ usernameError }}</div>
          <div v-if="showUsernameSuccess" class="success-message">{{ usernameSuccess }}</div>
        </div>
        <button class="btn btn-primary" @click="nextStep(1)">下一步</button>
      </div>

      <!-- 步骤2：邮箱验证 -->
      <div v-show="currentStep === 2" class="step">
        <h2>验证邮箱</h2>
        <div class="form-group">
          <label>邮箱地址</label>
          <div class="input-with-button">
            <input
              v-model="formData.email"
              @input="clearEmailMessages"
              @blur="validateEmail"
              :class="['form-input', {
                'error': showEmailError,
                'success': showEmailSuccess
              }]"
              type="email"
              placeholder="请输入邮箱地址"
            >
            <button
              class="send-code-btn"
              @click="sendVerificationCode"
              :disabled="isSendingCode || countdown > 0"
            >
              {{ sendCodeButtonText }}
            </button>
          </div>
          <div v-if="showEmailError" class="error-message">{{ emailError }}</div>
          <div v-if="showEmailSuccess" class="success-message">{{ emailSuccess }}</div>
          <div v-if="countdown > 0" class="countdown">{{ countdown }}秒后可重新发送</div>
        </div>

        <div class="form-group">
          <label>验证码</label>
          <input
            v-model="formData.emailCode"
            @input="clearCodeMessages"
            :class="['form-input', {
              'error': showCodeError,
              'success': showCodeSuccess
            }]"
            type="text"
            placeholder="请输入邮箱验证码"
            @keydown.enter="nextStep(2)"
          >
          <div v-if="showCodeError" class="error-message">{{ codeError }}</div>
          <div v-if="showCodeSuccess" class="success-message">{{ codeSuccess }}</div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(2)">上一步</button>
          <button class="btn btn-primary" @click="nextStep(2)">下一步</button>
        </div>
      </div>

      <!-- 步骤3：密码设置 -->
      <div v-show="currentStep === 3" class="step">
        <h2>设置密码</h2>
        <div class="form-group">
          <label>密码</label>
          <input
            v-model="formData.password"
            @input="validatePassword"
            :class="['form-input', {
              'error': showPasswordError,
              'success': passwordValid
            }]"
            type="password"
            placeholder="请输入密码"
          >
          <div v-if="showPasswordError" class="error-message">{{ passwordError }}</div>

          <!-- 密码要求提示 -->
          <div class="password-requirements">
            <div :class="['requirement', passwordRequirements.length ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.length ? '✓' : '✗' }}</span>
              8-16个字符
            </div>
            <div :class="['requirement', passwordRequirements.letter ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.letter ? '✓' : '✗' }}</span>
              包含字母
            </div>
            <div :class="['requirement', passwordRequirements.number ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.number ? '✓' : '✗' }}</span>
              包含数字
            </div>
            <div :class="['requirement', passwordRequirements.special ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.special ? '✓' : '✗' }}</span>
              包含特殊字符
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>确认密码</label>
          <input
            v-model="formData.confirmPassword"
            @input="validateConfirmPassword"
            :class="['form-input', {
              'error': showConfirmPasswordError,
              'success': showConfirmPasswordSuccess
            }]"
            type="password"
            placeholder="请再次输入密码"
            @keydown.enter="submitRegistration"
          >
          <div v-if="showConfirmPasswordError" class="error-message">{{ confirmPasswordError }}</div>
          <div v-if="showConfirmPasswordSuccess" class="success-message">{{ confirmPasswordSuccess }}</div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(3)">上一步</button>
          <button
            class="btn btn-primary"
            @click="submitRegistration"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? '注册中...' : '完成注册' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterVisitor',
  data() {
    return {
      currentStep: 1,
      formData: {
        username: '',
        email: '',
        emailCode: '',
        password: '',
        confirmPassword: ''
      },
      // 验证状态
      emailVerified: false,
      countdown: 0,
      countdownTimer: null,
      isSendingCode: false,
      isSubmitting: false,
      // 用户名验证
      usernameError: '',
      usernameSuccess: '',
      showUsernameError: false,
      showUsernameSuccess: false,
      // 邮箱验证
      emailError: '',
      emailSuccess: '',
      showEmailError: false,
      showEmailSuccess: false,
      // 验证码
      codeError: '',
      codeSuccess: '',
      showCodeError: false,
      showCodeSuccess: false,
      // 密码验证
      passwordError: '',
      showPasswordError: false,
      passwordValid: false,
      confirmPasswordError: '',
      confirmPasswordSuccess: '',
      showConfirmPasswordError: false,
      showConfirmPasswordSuccess: false,
      // 密码要求
      passwordRequirements: {
        length: false,
        letter: false,
        number: false,
        special: false
      }
    }
  },
  computed: {
    progressPercentage() {
      return (this.currentStep / 3) * 100;
    },
    sendCodeButtonText() {
      if (this.isSendingCode) return '发送中...';
      if (this.countdown > 0) return '重新发送';
      return '发送验证码';
    }
  },
  methods: {
    // 清除用户名消息
    clearUsernameMessages() {
      this.showUsernameError = false;
      this.showUsernameSuccess = false;
    },

    // 清除邮箱消息
    clearEmailMessages() {
      this.showEmailError = false;
      this.showEmailSuccess = false;
    },

    // 清除验证码消息
    clearCodeMessages() {
      this.showCodeError = false;
      this.showCodeSuccess = false;
    },

    // 验证用户名
    async validateUsername() {
      const username = this.formData.username.trim();

      if (!username) {
        this.usernameError = '请输入用户名';
        this.showUsernameError = true;
        return false;
      }

      if (username.length < 3 || username.length > 20) {
        this.usernameError = '用户名长度应在3-20个字符之间';
        this.showUsernameError = true;
        return false;
      }

      try {
        const response = await fetch('/api/check-username', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ username })
        });

        const data = await response.json();

        if (data.exists) {
          this.usernameError = '用户名已存在，请选择其他用户名';
          this.showUsernameError = true;
          return false;
        } else {
          this.usernameSuccess = '用户名可用';
          this.showUsernameSuccess = true;
          return true;
        }
      } catch (error) {
        this.usernameError = '验证用户名失败，请重试';
        this.showUsernameError = true;
        return false;
      }
    },

    // 验证邮箱格式
    validateEmail() {
      const email = this.formData.email.trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!email) {
        this.emailError = '请输入邮箱地址';
        this.showEmailError = true;
        return false;
      }

      if (!emailRegex.test(email)) {
        this.emailError = '请输入有效的邮箱地址';
        this.showEmailError = true;
        return false;
      }

      this.showEmailError = false;
      return true;
    },

    // 发送验证码
    async sendVerificationCode() {
      if (!this.validateEmail()) return;

      this.isSendingCode = true;

      try {
        const response = await fetch('/api/send-verification-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: this.formData.email.trim() })
        });

        const data = await response.json();

        if (data.success) {
          this.emailSuccess = '验证码已发送到您的邮箱';
          this.showEmailSuccess = true;
          this.startCountdown();
        } else {
          this.emailError = data.message || '验证码发送失败';
          this.showEmailError = true;
        }
      } catch (error) {
        this.emailError = '网络错误，请稍后重试';
        this.showEmailError = true;
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
    },

    // 验证邮箱验证码
    async verifyEmailCode() {
      const code = this.formData.emailCode.trim();

      if (!code) {
        this.codeError = '请输入验证码';
        this.showCodeError = true;
        return false;
      }

      try {
        const response = await fetch('/api/verify-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.formData.email.trim(),
            code
          })
        });

        const data = await response.json();

        if (data.success) {
          this.codeSuccess = '邮箱验证成功';
          this.showCodeSuccess = true;
          this.emailVerified = true;
          return true;
        } else {
          this.codeError = data.message || '验证码错误';
          this.showCodeError = true;
          return false;
        }
      } catch (error) {
        this.codeError = '验证失败，请重试';
        this.showCodeError = true;
        return false;
      }
    },

    // 验证密码强度
    validatePassword() {
      const password = this.formData.password;

      // 更新密码要求
      this.passwordRequirements = {
        length: password.length >= 8 && password.length <= 16,
        letter: /[a-zA-Z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
      };

      const allValid = Object.values(this.passwordRequirements).every(req => req);

      if (!password) {
        this.passwordError = '请输入密码';
        this.showPasswordError = true;
        this.passwordValid = false;
        return false;
      }

      if (!allValid) {
        this.passwordError = '密码不符合要求';
        this.showPasswordError = true;
        this.passwordValid = false;
        return false;
      }

      this.showPasswordError = false;
      this.passwordValid = true;
      return true;
    },

    // 验证确认密码
    validateConfirmPassword() {
      const password = this.formData.password;
      const confirmPassword = this.formData.confirmPassword;

      if (!confirmPassword) {
        // 如果确认密码为空，不显示错误，让用户继续输入
        this.showConfirmPasswordError = false;
        this.showConfirmPasswordSuccess = false;
        return false;
      }

      if (password !== confirmPassword) {
        this.confirmPasswordError = '两次输入的密码不一致';
        this.showConfirmPasswordError = true;
        this.showConfirmPasswordSuccess = false;
        // 移除 clearPasswordFields() 调用
        return false;
      }

      // 再次验证密码格式
      if (!this.validatePassword()) {
        this.confirmPasswordError = '密码格式不符合要求';
        this.showConfirmPasswordError = true;
        this.showConfirmPasswordSuccess = false;
        // 移除 clearPasswordFields() 调用
        return false;
      }

      this.confirmPasswordSuccess = '密码确认成功';
      this.showConfirmPasswordSuccess = true;
      this.showConfirmPasswordError = false;
      return true;
    },

    // 清空密码输入框
    clearPasswordFields() {
      this.formData.password = '';
      this.formData.confirmPassword = '';
      this.passwordValid = false;
      this.showPasswordError = false;
      this.showConfirmPasswordError = false;
      this.showConfirmPasswordSuccess = false;

      // 重置密码要求
      this.passwordRequirements = {
        length: false,
        letter: false,
        number: false,
        special: false
      };
    },

    // 下一步
    async nextStep(step) {
      let canProceed = false;

      if (step === 1) {
        canProceed = await this.validateUsername();
      } else if (step === 2) {
        canProceed = await this.verifyEmailCode();
      }

      if (canProceed) {
        this.currentStep++;
      }
    },

    // 上一步
    prevStep(step) {
      this.currentStep--;
    },

    // 提交注册
    async submitRegistration() {
      if (!this.validatePassword() || !this.validateConfirmPassword()) {
        return;
      }

      this.isSubmitting = true;

      try {
        const response = await fetch('/api/visitor-register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.formData.username.trim(),
            email: this.formData.email.trim(),
            password: this.formData.password
          })
        });

        const data = await response.json();

        if (data.success) {
          alert('注册成功！将跳转到身份选择页面...');
          this.$emit('register-success');
        } else {
          if (data.message.includes('用户名')) {
            // 跳回第一步
            this.currentStep = 1;
            this.usernameError = data.message;
            this.showUsernameError = true;
          } else if (data.message.includes('邮箱')) {
            // 跳回第二步
            this.currentStep = 2;
            this.emailError = data.message;
            this.showEmailError = true;
          } else {
            this.confirmPasswordError = data.message;
            this.showConfirmPasswordError = true;
            // 只在注册失败时清空密码
            this.clearPasswordFields();
          }
        }
      } catch (error) {
        this.confirmPasswordError = '注册失败，请重试';
        this.showConfirmPasswordError = true;
        // 只在出错时清空密码
        this.clearPasswordFields();
      } finally {
        this.isSubmitting = false;
      }
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
.register-visitor-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: white; /* 改为白色背景 */
  padding: 80px 15px 15px; /* 添加顶部padding，让内容上移 */
}

.registration-panel {
  background: white;
  padding: 32px;
  border-radius: 16px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  border: 1px solid #e6f2ff;
}

.registration-panel h1 {
  color: #5ba0c3;
  text-align: center;
  margin-bottom: 16px;
  font-size: 22px;
}

.registration-panel h2 {
  color: #333;
  text-align: center;
  margin-bottom: 24px;
  font-size: 16px;
  font-weight: 500;
}

/* 进度条 */
.progress-bar {
  height: 5px;
  background: #e6f2ff;
  border-radius: 3px;
  margin: 24px 0 16px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #87ceeb 0%, #5ba0c3 100%);
  transition: width 0.3s ease;
}

/* 步骤指示器 */
.step-indicators {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 32px;
  gap: 32px;
}

.step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #e6f2ff;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  position: relative;
  transition: all 0.3s;
}

.step-dot.active {
  background: #5ba0c3;
  color: white;
  transform: scale(1.1);
}

.step-dot.completed {
  background: #5cb85c;
  color: white;
}

.step-dot.completed::after {
  content: '✓';
  position: absolute;
  font-size: 15px;
}

/* 表单样式 */
.step {
  text-align: center;
}

.form-group {
  margin-bottom: 16px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.form-input {
  width: 100%;
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

.form-input.error {
  border-color: #dc3545;
}

.form-input.success {
  border-color: #5cb85c;
}

/* 带按钮的输入框 */
.input-with-button {
  display: flex;
  gap: 8px;
}

.input-with-button .form-input {
  flex: 1;
}

.send-code-btn {
  padding: 12px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s;
}

.send-code-btn:hover:not(:disabled) {
  background: #357abd;
}

.send-code-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 错误和成功消息 */
.error-message {
  color: #dc3545;
  font-size: 13px;
  margin-top: 5px;
}

.success-message {
  color: #5cb85c;
  font-size: 13px;
  margin-top: 5px;
}

.countdown {
  color: #666;
  font-size: 13px;
  margin-top: 5px;
}

/* 密码要求 */
.password-requirements {
  margin-top: 10px;
  padding: 14px;
  background: #f8f9fa;
  border-radius: 6px;
}

.requirement {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  color: #666;
}

.requirement:last-child {
  margin-bottom: 0;
}

.requirement .icon {
  margin-right: 6px;
  font-weight: bold;
}

.requirement.valid {
  color: #5cb85c;
}

.requirement.valid .icon {
  color: #5cb85c;
}

/* 按钮 */
.btn {
  padding: 10px 32px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25);
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: #f8f9fa;
  color: #666;
  border: 2px solid #e6f2ff;
}

.btn-secondary:hover {
  background: #e6f2ff;
}

.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 24px;
}

/* 响应式设计 */
@media (max-width: 600px) {
  .registration-panel {
    padding: 24px 16px;
  }

  .step-indicators {
    gap: 24px;
  }

  .step-dot {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .button-group {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>