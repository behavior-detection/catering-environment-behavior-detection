<template>
  <div class="register-choice-container">
    <div class="choice-panel">
      <h1>您所在的企业是否已在该平台注册？</h1>
      <div class="button-group">
        <button class="btn btn-yes" @click="goToRegisteredPage">
          <span class="icon">✓</span> 是的
        </button>
        <button class="btn btn-no" @click="goToNotRegisteredPage">
          <span class="icon">+</span> 还没有
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterChoice',
  methods: {
    goToRegisteredPage() {
      this.$emit('go-to-register', 'enterprise-employee');
    },
    goToNotRegisteredPage() {
      this.$emit('go-to-register', 'enterprise-new');
    }
  }
}
</script>

<style scoped>
.register-choice-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.choice-panel {
  background: white;
  padding: 60px 40px;
  border-radius: var(--radius-xl);
  text-align: center;
  max-width: 600px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.choice-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 40px;
}

.button-group {
  display: flex;
  gap: 30px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: 20px 50px;
  font-size: 20px;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.3s;
}

.btn-yes {
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
}

.btn-no {
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
}

.btn:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
</style>