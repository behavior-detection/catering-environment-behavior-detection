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
      }
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
        alert('请输入邮箱地址');
        return;
      }

      try {
        const result = await authService.sendVerificationCode(this.formData.email);
        if (result.success) {
          this.startCountdown();
          alert('验证码已发送');
        }
      } catch (error) {
        alert('发送失败，请重试');
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

    async handleSubmit() {
      // 验证密码
      if (this.formData.password !== this.formData.confirmPassword) {
        alert('两次密码输入不一致');
        return;
      }

      // 获取之前保存的验证数据
      const verificationData = JSON.parse(sessionStorage.getItem('verificationData') || '{}');

      const submitData = {
        ...verificationData,
        email: this.formData.email,
        verificationCode: this.formData.verificationCode,
        password: this.formData.password
      };

      try {
        const result = await authService.registerUser(submitData);
        if (result.success) {
          sessionStorage.removeItem('verificationData');
          this.$emit('register-success');
        } else {
          alert(result.message || '注册失败');
        }
      } catch (error) {
        alert('注册失败，请重试');
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
  padding: 20px;
}

.register-panel {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.register-panel h1 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 40px;
  font-size: 2rem;
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--color-text);
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.email-group {
  display: flex;
  gap: 10px;
}

.email-group input {
  flex: 1;
}

.email-group button {
  padding: 12px 20px;
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  white-space: nowrap;
  font-weight: 500;
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
  margin-top: 12px;
  background: var(--color-primary-lighter);
  padding: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.password-strength div {
  color: var(--color-text-light);
  padding: 4px 0;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.password-strength div::before {
  content: '○';
  margin-right: 8px;
  font-size: 14px;
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
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 30px;
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}

@media (max-width: 480px) {
  .register-panel {
    padding: 40px 30px;
  }

  .register-panel h1 {
    font-size: 1.5rem;
  }

  .email-group {
    flex-direction: column;
  }

  .email-group button {
    width: 100%;
  }
}
</style>