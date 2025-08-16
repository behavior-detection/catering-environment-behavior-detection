<template>
  <div class="reset-options-container">
    <div class="options-panel">
      <h2>您想如何重置 {{ username }} 的密码？</h2>

      <div class="options-grid">
        <!-- 安全问题 -->
        <div class="option-card" @click="selectOption('security')">
          <i class="fas fa-shield-alt"></i>
          <h3>安全问题</h3>
          <p>通过回答预设的安全问题验证身份</p>
        </div>

        <!-- 邮箱验证 -->
        <div class="option-card" @click="selectOption('email')">
          <i class="fas fa-envelope"></i>
          <h3>邮箱验证</h3>
          <p>向您的注册邮箱发送验证码</p>
        </div>

        <!-- 人脸识别 -->
        <div v-if="userType !== 'visitor'" class="option-card" @click="selectOption('face')">
          <i class="fas fa-camera"></i>
          <h3>人脸识别</h3>
          <p>通过人脸识别技术验证身份</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResetOptions',
  props: ['username', 'userType'],
  methods: {
    selectOption(option) {
      const stepMap = {
        'security': 'security-verification',
        'email': 'email-verification',
        'face': 'face-recognition'
      };

      this.$emit('go-to-forgot-password', {
        step: stepMap[option],
        username: this.username,
        type: this.userType
      });
    }
  }
}
</script>

<style scoped>
.reset-options-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.options-panel {
  width: 100%;
  max-width: 900px;
  text-align: center;
}

.options-panel h2 {
  color: var(--color-primary-dark);
  margin-bottom: 40px;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  justify-content: center;
}

.option-card {
  background: white;
  padding: 40px 30px;
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.option-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-5px);
  box-shadow: var(--shadow-lg);
}

.option-card i {
  font-size: 3rem;
  color: var(--color-primary);
  margin-bottom: 20px;
  display: block;
}

.option-card h3 {
  color: var(--color-text);
  margin-bottom: 15px;
}

.option-card p {
  color: var(--color-text-secondary);
  font-size: 14px;
}
</style>