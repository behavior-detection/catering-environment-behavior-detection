<template>
  <div class="register-user-container">
    <div class="register-panel">
      <h1>完成用户注册</h1>

      <form @submit.prevent="handleSubmit">
        <!-- 邮箱地址 -->
        <div class="form-group">
          <label>邮箱地址</label>
          <div class="email-group">
            <input
              v-model="formData.email"
              type="email"
              placeholder="请输入您的邮箱地址"
              required
            >
            <button
              type="button"
              @click="sendCode"
              :disabled="isCountingDown"
            >
              {{ sendCodeBtnText }}
            </button>
          </div>
        </div>

        <!-- 验证码 -->
        <div class="form-group">
          <label>验证码</label>
          <input
            v-model="formData.verificationCode"
            type="text"
            placeholder="请输入6位验证码"
            maxlength="6"
            required
          >
        </div>

        <!-- 密码 -->
        <div class="form-group">
          <label>密码</label>
          <input
            v-model="formData.password"
            type="password"
            placeholder="请输入8-16位密码"
            required
            @input="checkPasswordStrength"
          >
          <!-- 密码强度提示 -->
          <div class="password-strength" v-if="formData.password">
            <div :class="{valid: passwordChecks.length}">8-16个字符</div>
            <div :class="{valid: passwordChecks.letter}">至少包含一个字母</div>
            <div :class="{valid: passwordChecks.number}">至少包含一个数字</div>
            <div :class="{valid: passwordChecks.special}">至少包含一个特殊字符</div>
          </div>
        </div>

        <!-- 确认密码 -->
        <div class="form-group">
          <label>确认密码</label>
          <input
            v-model="formData.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            required
          >
        </div>

        <button type="submit" class="submit-btn">完成注册</button>
      </form>
    </div>
  </div>
</template>



<script>
import { authService } from '@/services/auth';

export default {
  name: 'RegisterUser',
  data() {
    return {
      formData: {
        email: '',
        verificationCode: '',
        password: '',
        confirmPassword: ''
      },
      isCountingDown: false,
      countdown: 0,
      passwordChecks: {
        length: false,
        letter: false,
        number: false,
        special: false
      },
      isLoading: false,
      errorMessage: ''
    }
  },
  computed: {
    sendCodeBtnText() {
      return this.isCountingDown ? `${this.countdown}s` : '发送验证码';
    }
  },
  methods: {
    async sendCode() {
      if (!this.formData.email) {
        this.errorMessage = '请输入邮箱地址';
        return;
      }

      // 验证邮箱格式
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.formData.email)) {
        this.errorMessage = '请输入有效的邮箱地址';
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';

      try {
        const result = await authService.sendVerificationCode(this.formData.email);

        if (result.success || result.status === 'success') {
          this.startCountdown();
          alert('验证码已发送到您的邮箱');
        } else {
          this.errorMessage = result.message || '发送验证码失败';
        }
      } catch (error) {
        console.error('Send verification code error:', error);
        this.errorMessage = error.response?.data?.message || '发送失败，请重试';
      } finally {
        this.isLoading = false;
      }
    },

    startCountdown() {
      this.isCountingDown = true;
      this.countdown = 60;
      const timer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(timer);
          this.isCountingDown = false;
        }
      }, 1000);
    },

    checkPasswordStrength() {
      const password = this.formData.password;
      this.passwordChecks = {
        length: password.length >= 8 && password.length <= 16,
        letter: /[a-zA-Z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
      };
    },

    validatePassword() {
      const { length, letter, number, special } = this.passwordChecks;
      return length && letter && number && special;
    },

    async handleSubmit() {
      this.errorMessage = '';

      // 验证密码
      if (this.formData.password !== this.formData.confirmPassword) {
        this.errorMessage = '两次密码输入不一致';
        return;
      }

      if (!this.validatePassword()) {
        this.errorMessage = '密码不符合要求，请检查密码强度提示';
        return;
      }

      if (!this.formData.verificationCode) {
        this.errorMessage = '请输入验证码';
        return;
      }

      this.isLoading = true;

      try {
        // 首先验证验证码
        const codeVerification = await authService.verifyCode(
          this.formData.email,
          this.formData.verificationCode
        );

        if (!codeVerification.success && codeVerification.status !== 'success') {
          this.errorMessage = '验证码错误或已过期';
          return;
        }

        // 获取之前保存的验证数据（如果有的话）
        const verificationData = JSON.parse(sessionStorage.getItem('verificationData') || '{}');

        const submitData = {
          ...verificationData,
          email: this.formData.email,
          verificationCode: this.formData.verificationCode,
          password: this.formData.password,
          userType: 'employee' // 或者根据实际情况设置
        };

        const result = await authService.registerUser(submitData);

        if (result.success || result.status === 'success') {
          sessionStorage.removeItem('verificationData');
          alert('注册成功！请使用您的账号登录');
          this.$emit('register-success', result);
        } else {
          this.errorMessage = result.message || '注册失败';
        }
      } catch (error) {
        console.error('Registration error:', error);
        this.errorMessage = error.response?.data?.message || '注册失败，请重试';
      } finally {
        this.isLoading = false;
      }
    }
  }
}
</script>

<style scoped>
.register-user-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 15px; /* 从20px缩小 */
}

.register-panel {
  background: white;
  padding: 35px 30px; /* 从50px 40px缩小 */
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 400px; /* 从500px缩小 */
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.register-panel h1 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 30px; /* 从40px缩小 */
  font-size: 1.6rem; /* 从2rem缩小 */
}

.form-group {
  margin-bottom: 18px; /* 从24px缩小 */
}

.form-group label {
  display: block;
  margin-bottom: 6px; /* 从8px缩小 */
  font-weight: 500;
  color: var(--color-text);
  font-size: 13px; /* 从14px缩小 */
}

.form-group input {
  width: 100%;
  padding: 10px 14px; /* 从12px 16px缩小 */
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px; /* 从16px缩小 */
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1); /* 从4px缩小 */
}

.email-group {
  display: flex;
  gap: 8px; /* 从10px缩小 */
}

.email-group input {
  flex: 1;
}

.email-group button {
  padding: 10px 16px; /* 从12px 20px缩小 */
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  white-space: nowrap;
  font-weight: 500;
  font-size: 14px; /* 新增 */
  transition: all 0.3s ease;
}

.email-group button:hover:not(:disabled) {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary-dark);
}

.email-group button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.password-strength {
  margin-top: 10px; /* 从12px缩小 */
  background: var(--color-primary-lighter);
  padding: 10px; /* 从12px缩小 */
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.password-strength div {
  color: var(--color-text-light);
  padding: 3px 0; /* 从4px 0缩小 */
  font-size: 12px; /* 从13px缩小 */
  display: flex;
  align-items: center;
}

.password-strength div::before {
  content: '○';
  margin-right: 6px; /* 从8px缩小 */
  font-size: 12px; /* 从14px缩小 */
}

.password-strength div.valid {
  color: var(--color-success);
}

.password-strength div.valid::before {
  content: '✓';
  color: var(--color-success);
}

.submit-btn {
  width: 100%;
  padding: 12px; /* 从14px缩小 */
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px; /* 从16px缩小 */
  font-weight: 600;
  cursor: pointer;
  margin-top: 25px; /* 从30px缩小 */
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(135, 206, 235, 0.25); /* 从6px 20px缩小 */
}

@media (max-width: 480px) {
  .register-panel {
    padding: 30px 25px; /* 从40px 30px缩小 */
  }

  .register-panel h1 {
    font-size: 1.3rem; /* 从1.5rem缩小 */
  }

  .email-group {
    flex-direction: column;
  }

  .email-group button {
    width: 100%;
  }
}
</style>