<template>
  <div class="email-verification-container">
    <div class="verification-panel">
      <h2>邮箱验证</h2>

      <!-- 步骤1：输入邮箱 -->
      <div v-if="currentStep === 1" class="step-content">
        <p>请输入您注册时使用的邮箱地址</p>
        <div class="form-group">
          <input v-model="email" type="email" placeholder="请输入邮箱">
        </div>
        <button @click="checkEmail" class="next-btn">下一步</button>
      </div>

      <!-- 步骤2：输入验证码 -->
      <div v-if="currentStep === 2" class="step-content">
        <p>验证码已发送到 {{ maskedEmail }}</p>
        <div class="form-group">
          <input v-model="verificationCode" type="text" placeholder="请输入6位验证码" maxlength="6">
          <button @click="resendCode" :disabled="countdown > 0">
            {{ countdown > 0 ? `重新发送(${countdown}s)` : '重新发送' }}
          </button>
        </div>
        <button @click="verifyCode" class="verify-btn">验证并继续</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EmailVerification',
  props: ['username', 'userType'],
  data() {
    return {
      currentStep: 1,
      email: '',
      verificationCode: '',
      countdown: 0
    }
  },
  computed: {
    maskedEmail() {
      if (!this.email) return '';
      const [user, domain] = this.email.split('@');
      return user.substring(0, 3) + '****@' + domain;
    }
  },
  methods: {
    async checkEmail() {
      // 验证邮箱并发送验证码
      this.currentStep = 2;
      this.startCountdown();
    },
    async verifyCode() {
      // 验证验证码并触发事件
      this.$emit('go-to-forgot-password', {
        step: 'reset-password',
        username: this.username,
        type: this.userType,
        verified: 'true'
      });
    },
    resendCode() {
      this.startCountdown();
    },
    startCountdown() {
      this.countdown = 60;
      const timer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) clearInterval(timer);
      }, 1000);
    }
  }
}
</script>

<style scoped>
.email-verification-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.verification-panel {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 600px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.verification-panel h2 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 30px;
}

.step-content {
  text-align: center;
}

.step-content p {
  color: var(--color-text-secondary);
  margin-bottom: 30px;
}

.form-group {
  margin: 30px 0;
}

.form-group input {
  width: 100%;
  padding: 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  font-size: 16px;
  text-align: center;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.form-group button {
  padding: 12px 20px;
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 14px;
}

.form-group button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.next-btn, .verify-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.next-btn:hover, .verify-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}
</style>