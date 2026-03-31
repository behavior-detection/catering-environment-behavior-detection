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

// ResetPassword.vue - Script部分的修改

<script>
import { authService } from '@/services/auth';

export default {
  name: 'ResetPassword',
  props: ['username', 'userType', 'verificationToken', 'email', 'verificationCode'],
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
      },
      isLoading: false,
      errorMessage: ''
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

    validatePassword() {
      const { length, letter, number, special } = this.passwordChecks;
      return length && letter && number && special;
    },

    async handleSubmit() {
      this.errorMessage = '';

      // 验证密码
      if (this.formData.newPassword !== this.formData.confirmPassword) {
        this.errorMessage = '两次密码输入不一致';
        return;
      }

      if (!this.validatePassword()) {
        this.errorMessage = '密码不符合要求，请检查密码强度提示';
        return;
      }

      this.isLoading = true;

      try {
        let result;

        // 根据验证方式选择不同的API
        if (this.email && this.verificationCode) {
          // 通过邮箱验证重置密码
          result = await authService.resetPasswordByEmail(
            this.email,
            this.verificationCode,
            this.formData.newPassword
          );
        } else {
          // 通过其他方式验证重置密码（安全问题、人脸识别等）
          result = await authService.resetPassword(
            this.username,
            this.userType,
            this.formData.newPassword,
            this.verificationToken
          );
        }

        if (result.success || result.status === 'success') {
          alert('密码修改成功！请使用新密码登录');
          this.$emit('reset-success', {
            username: this.username,
            userType: this.userType
          });
        } else {
          this.errorMessage = result.message || '密码修改失败';
        }
      } catch (error) {
        console.error('Reset password error:', error);

        if (error.response?.status === 400) {
          this.errorMessage = '验证信息已过期或无效，请重新开始密码重置流程';
        } else if (error.response?.status === 404) {
          this.errorMessage = '用户不存在';
        } else {
          this.errorMessage = error.response?.data?.message || '密码修改失败，请重试';
        }
      } finally {
        this.isLoading = false;
      }
    },

    // 清除密码输入
    clearPasswords() {
      this.formData.newPassword = '';
      this.formData.confirmPassword = '';
      this.checkPasswordStrength();
    },

    // 检查密码强度是否满足要求
    isPasswordValid() {
      return Object.values(this.passwordChecks).every(check => check);
    }
  },

  mounted() {
    // 检查必要的验证信息
    if (!this.username || !this.userType) {
      this.errorMessage = '缺少用户信息，请重新开始密码重置流程';
    }

    if (!this.verificationToken && !this.verificationCode) {
      this.errorMessage = '缺少验证信息，请重新验证身份';
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
  padding: 15px; /* 从20px缩小 */
}

.reset-panel {
  background: white;
  padding: 40px 32px; /* 从50px 40px缩小 */
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 400px; /* 从500px缩小 */
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.reset-panel h2 {
  color: var(--color-primary-dark);
  text-align: center;
  margin-bottom: 8px; /* 从10px缩小 */
  font-size: 1.25rem; /* 新增明确尺寸 */
}

.reset-panel > p {
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: 24px; /* 从30px缩小 */
  font-size: 14px; /* 新增明确尺寸 */
}

.password-requirements {
  background: var(--color-primary-lighter);
  padding: 16px; /* 从20px缩小 */
  border-radius: var(--radius-md);
  margin: 16px 0; /* 从20px 0缩小 */
  border: 1px solid var(--color-border);
}

.password-requirements h4 {
  margin-bottom: 12px; /* 从15px缩小 */
  color: var(--color-text);
  font-size: 14px; /* 新增 */
}

.password-requirements ul {
  list-style: none;
  padding: 0;
  text-align: left;
}

.password-requirements li {
  padding: 6px 0; /* 从8px 0缩小 */
  color: var(--color-text-light);
  display: flex;
  align-items: center;
  font-size: 13px; /* 新增 */
}

.password-requirements li.valid {
  color: var(--color-success);
}

.password-requirements li::before {
  content: '○';
  margin-right: 8px; /* 从10px缩小 */
  font-size: 15px; /* 从18px缩小 */
}

.password-requirements li.valid::before {
  content: '✓';
  color: var(--color-success);
}

.form-group {
  margin-bottom: 20px; /* 从24px缩小 */
}

.form-group label {
  display: block;
  margin-bottom: 6px; /* 从8px缩小 */
  color: var(--color-text);
  font-weight: 500;
  font-size: 14px; /* 新增 */
}

.form-group input {
  width: 100%;
  padding: 10px; /* 从12px缩小 */
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px; /* 从16px缩小 */
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1); /* 从4px缩小 */
}

.submit-btn {
  width: 100%;
  padding: 12px; /* 从14px缩小 */
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 14px; /* 从16px缩小 */
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25); /* 从6px 20px缩小 */
}
</style>