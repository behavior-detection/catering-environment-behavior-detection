<template>
  <div class="feedback-report">
    <ChatInterface />

    <MessageToast
      v-if="message.show"
      :type="message.type"
      :text="message.text"
    />
  </div>
</template>

<script>
import ChatInterface from './feedback/ChatInterface.vue'
import MessageToast from './common/MessageToast.vue'

export default {
  name: 'FeedbackReport',
  components: {
    ChatInterface,
    MessageToast
  },
  data() {
    return {
      // 消息提示
      message: {
        show: false,
        type: 'info',
        text: ''
      }
    }
  },

  mounted() {
    // 可以在这里检查系统状态
    this.checkSystemStatus()
  },

  methods: {
    // 检查系统状态
    async checkSystemStatus() {
      try {
        // 这里可以检查Redis和AI服务状态
        // const response = await systemAPI.getChatStatus()
        // 根据需要显示状态提示
      } catch (error) {
        console.warn('系统状态检查失败:', error)
      }
    },

    // 显示消息
    showMessage(text, type = 'info') {
      this.message = {
        show: true,
        type,
        text
      }

      setTimeout(() => {
        this.message.show = false
      }, type === 'error' ? 5000 : 3000)
    }
  }
}
</script>

<style scoped>
/* 定义主题颜色变量 */
:root {
  --primary-color: #42A5F5;
  --primary-color-dark: #1976D2;
  --background-gradient: linear-gradient(180deg, #f0f8ff 0%, #f7fbff 100%);
  --text-color-primary: #111827;
  --text-color-secondary: #6B7280;
  --card-border-color: #E3F2FD;
  --card-background-color: #ffffff;
}

.feedback-report {
  padding: 0px;
  background: var(--background-gradient);
  height: 100%;
  color: var(--text-color-primary);
}

/* 确保聊天界面占据合适的高度 */
.feedback-report :deep(.chat-interface) {
  height: 100%;
}
</style>