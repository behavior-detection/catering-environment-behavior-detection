<template>
  <div class="reset-password-container">
    <div class="reset-panel">
      <h2>重置密码</h2>
      <p>正在为用户 <strong>{{ username }}</strong> 重置密码</p>

      <!-- 密码要求提示 -->
      <div class="password-requirements">
        <h4>密码要求：</h4>
        <ul>
          <li :class="{valid: passwordChecks.length}">8-16个字符</li>
          <li :class="{valid: passwordChecks.letter}">至少包含一个字母</li>
          <li :class="{valid: passwordChecks.number}">至少包含一个数字</li>
          <li :class="{valid: passwordChecks.special}">至少包含一个特殊字符</li>
        </ul>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>新密码</label>
          <input v-model="formData.newPassword" type="password" @input="checkPasswordStrength">
        </div>

        <div class="form-group">
          <label>确认密码</label>
          <input v-model="formData.confirmPassword" type="password">
        </div>

        <button type="submit" class="submit-btn">确认修改</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResetPassword',
  props: ['username', 'userType'],
  data() {
    return {
      formData: {
        newPassword: '',
        confirmPassword: ''
      },
      passwordChecks: {
        length: false,
        letter: false,
        number: false,
        special: false
      }
    }
  },
  methods: {
    checkPasswordStrength() {
      const password = this.formData.newPassword;
      this.passwordChecks = {
        length: password.length >= 8 && password.length <= 16,
        letter: /[a-zA-Z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
      };
    },
    async handleSubmit() {
      // 提交密码重置
      if (this.formData.newPassword !== this.formData.confirmPassword) {
        alert('两次密码输入不一致');
        return;
      }

      alert('密码修改成功！');
      this.$emit('reset-success');
    }
  }
}
</script>

<style scoped>
.reset-password-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.reset-panel {
  background: white;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.reset-panel h2 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 10px;
}

.reset-panel > p {
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: 30px;
}

.password-requirements {
  background: var(--color-primary-lighter);
  padding: 20px;
  border-radius: var(--radius-md);
  margin: 20px 0;
  border: 1px solid var(--color-border);
}

.password-requirements h4 {
  margin-bottom: 15px;
  color: var(--color-text);
}

.password-requirements ul {
  list-style: none;
  padding: 0;
  text-align: left;
}

.password-requirements li {
  padding: 8px 0;
  color: var(--color-text-light);
  display: flex;
  align-items: center;
}

.password-requirements li.valid {
  color: var(--color-success);
}

.password-requirements li::before {
  content: '○';
  margin-right: 10px;
  font-size: 18px;
}

.password-requirements li.valid::before {
  content: '✓';
  color: var(--color-success);
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text);
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
}

.form-group input:focus {
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
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}
</style>