<template>
  <div class="register-visitor-container">
    <div class="registration-panel">
      <h1>访客注册</h1>

      <!-- 进度条 -->
      <div class="progress-bar">
        <div class="progress-fill" :style="{width: progressPercentage + '%'}"></div>
      </div>

      <!-- 步骤1：用户名 -->
      <div v-if="currentStep === 1" class="step">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="formData.username" type="text" placeholder="请输入用户名（3-20个字符）">
        </div>
        <button @click="nextStep(1)">下一步</button>
      </div>

      <!-- 步骤2：邮箱验证 -->
      <div v-if="currentStep === 2" class="step">
        <div class="form-group">
          <label>邮箱地址</label>
          <input v-model="formData.email" type="email" placeholder="请输入邮箱地址">
          <button @click="sendVerificationCode">发送验证码</button>
        </div>
        <div class="form-group">
          <label>验证码</label>
          <input v-model="formData.emailCode" type="text" placeholder="请输入邮箱验证码">
        </div>
        <button @click="nextStep(2)">下一步</button>
      </div>

      <!-- 步骤3：密码设置 -->
      <div v-if="currentStep === 3" class="step">
        <div class="form-group">
          <label>密码</label>
          <input v-model="formData.password" type="password" placeholder="请设置密码">
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <input v-model="formData.confirmPassword" type="password" placeholder="请再次输入密码">
        </div>
        <button @click="submitRegistration">完成注册</button>
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
      }
    }
  },
  computed: {
    progressPercentage() {
      return (this.currentStep / 3) * 100;
    }
  },
  methods: {
    nextStep(step) {
      if (step < 3) this.currentStep++;
    },
    sendVerificationCode() {
      // 发送验证码
    },
    submitRegistration() {
      // 提交注册
    }
  }
}
</script>

<style scoped>
.register-visitor-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.registration-panel {
  background: white;
  padding: 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 600px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.registration-panel h1 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 20px;
}

.progress-bar {
  height: 6px;
  background: var(--color-border);
  border-radius: 3px;
  margin: 30px 0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  transition: width 0.3s ease;
}

.step {
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--color-text);
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
  text-align: center;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.step button {
  padding: 12px 40px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  cursor: pointer;
  margin-top: 20px;
  transition: all 0.3s;
}

.step button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}
</style>