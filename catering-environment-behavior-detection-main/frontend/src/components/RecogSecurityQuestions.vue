<template>
  <div class="security-questions-container">
    <div class="loading-state" v-if="loading">
      <div class="loading-spinner"></div>
      <p>正在检查密保设置...</p>
    </div>

    <!-- 显示设置密保组件 -->
    <SetSecurityQuestion
      v-else-if="showSetSecurity"
      :userInfo="userInfo"
      @back="$emit('back')"
      @success="handleSetSuccess"
    />

    <!-- 显示重置密保组件 -->
    <ResetSecurityQuestion
      v-else-if="showResetSecurity"
      :userInfo="userInfo"
      :existingQuestions="existingQuestions"
      @back="$emit('back')"
      @success="handleResetSuccess"
    />
  </div>
</template>

<script>
import SetSecurityQuestion from './SetSecurityQuestion.vue'
import ResetSecurityQuestion from './ResetSecurityQuestion.vue'

export default {
  name: 'RecogSecurityQuestions',
  components: {
    SetSecurityQuestion,
    ResetSecurityQuestion
  },
  props: {
    userInfo: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      loading: true,
      showSetSecurity: false,
      showResetSecurity: false,
      existingQuestions: null
    }
  },
  mounted() {
    this.checkSecurityStatus()
  },
  methods: {
    async checkSecurityStatus() {
      this.loading = true
      try {
        const response = await fetch(`/api/check-security-status?username=${encodeURIComponent(this.userInfo.username)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        const data = await response.json()

        if (response.ok && data.success) {
          if (data.hasSecurityQuestions) {
            // 用户已设置密保，显示重置组件
            this.existingQuestions = data.questions
            this.showResetSecurity = true
          } else {
            // 用户未设置密保，显示设置组件
            this.showSetSecurity = true
          }
        } else {
          alert('检查密保状态失败：' + (data.message || '未知错误'))
          this.$emit('back')
        }
      } catch (error) {
        console.error('检查密保状态失败:', error)
        alert('网络错误，请稍后重试')
        this.$emit('back')
      } finally {
        this.loading = false
      }
    },

    handleSetSuccess() {
      alert('密保问题设置成功！')
      this.$emit('back')
    },

    handleResetSuccess() {
      alert('密保问题重置成功！')
      this.$emit('back')
    }
  }
}
</script>

<style scoped>
.security-questions-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>