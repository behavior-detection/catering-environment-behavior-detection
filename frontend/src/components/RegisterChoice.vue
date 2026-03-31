<template>
  <div class="register-choice-container">
    <div class="choice-panel">
      <h1>您所在的企业是否已在该平台注册？</h1>
      <div class="button-group">
        <button class="btn btn-yes" @click="goToRegisteredPage">
          是的
        </button>
        <button class="btn btn-no" @click="goToNotRegisteredPage">
          还没有
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
  align-items: flex-start; /* 改为flex-start */
  justify-content: center;
  background: var(--color-bg);
  padding: 80px 15px 15px; /* 增加顶部padding，减少底部padding */
}

.choice-panel {
  background: white;
  padding: 48px 32px;
  border-radius: var(--radius-xl);
  text-align: center;
  max-width: 480px;
  width: 100%;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.choice-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 32px;
  font-size: 1.5rem;
}

.button-group {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: 16px 40px;
  font-size: 16px;
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
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* 响应式设计 */
@media (max-width: 480px) {
  .register-choice-container {
    padding: 60px 15px 15px; /* 移动端减少顶部padding */
  }

  .button-group {
    flex-direction: column;
    gap: 16px;
  }

  .btn {
    width: 100%;
  }
}
</style>