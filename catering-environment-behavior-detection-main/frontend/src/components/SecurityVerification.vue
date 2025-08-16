<template>
  <div class="security-verification-container">
    <div class="verification-panel">
      <h2>请回答安全问题</h2>

      <div v-if="questions.length > 0" class="questions-container">
        <div v-for="(question, index) in questions" :key="index" class="question-group">
          <p class="question-text">{{ question }}</p>
          <input v-model="answers[index]" type="text" placeholder="请输入答案">
        </div>

        <button @click="submitAnswers" class="submit-btn">提交答案</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SecurityVerification',
  props: ['username', 'userType'],
  data() {
    return {
      questions: ['您的出生地是？', '您母亲的姓名是？', '您的第一个宠物叫什么？'],
      answers: []
    }
  },
  mounted() {
    this.answers = new Array(this.questions.length).fill('');
  },
  methods: {
    async submitAnswers() {
      // 验证答案并触发事件
      this.$emit('go-to-forgot-password', {
        step: 'reset-password',
        username: this.username,
        type: this.userType,
        verified: 'true'
      });
    }
  }
}
</script>

<style scoped>
.security-verification-container {
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
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.verification-panel h2 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 40px;
}

.question-group {
  margin-bottom: 24px;
}

.question-text {
  font-size: 16px;
  margin-bottom: 12px;
  font-weight: 500;
  color: var(--color-text);
}

.question-group input {
  width: 100%;
  padding: 12px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
}

.question-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  margin-top: 30px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}
</style>