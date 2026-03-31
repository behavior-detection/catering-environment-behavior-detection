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
  align-items: flex-start;
  justify-content: center;
  background: var(--color-bg);
  padding: 100px 15px 15px; /* 添加顶部padding，让内容上移 */
}

.options-panel {
  width: 100%;
  max-width: 720px; /* 从900px缩小 */
  text-align: center;
}

.options-panel h2 {
  color: var(--color-primary-dark);
  margin-bottom: 32px; /* 从40px缩小 */
  font-size: 1.25rem; /* 新增明确尺寸 */
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); /* 从250px缩小 */
  gap: 24px; /* 从30px缩小 */
  justify-content: center;
}

.option-card {
  background: white;
  padding: 32px 24px; /* 从40px 30px缩小 */
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.option-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-4px); /* 从-5px缩小 */
  box-shadow: var(--shadow-lg);
}

.option-card i {
  font-size: 2.4rem; /* 从3rem缩小 */
  color: var(--color-primary);
  margin-bottom: 16px; /* 从20px缩小 */
  display: block;
}

.option-card h3 {
  color: var(--color-text);
  margin-bottom: 12px; /* 从15px缩小 */
  font-size: 1.1rem; /* 新增明确尺寸 */
}

.option-card p {
  color: var(--color-text-secondary);
  font-size: 13px; /* 从14px缩小 */
}
</style>