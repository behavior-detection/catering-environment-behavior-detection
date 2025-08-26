<!-- components/common/MessageToast.vue -->
<template>
  <div :class="['message', `message-${type}`]">
    <i class="icon">{{ getMessageIcon(type) }}</i>
    {{ text }}
  </div>
</template>

<script>
export default {
  name: 'MessageToast',
  props: {
    type: {
      type: String,
      default: 'info',
      validator: (value) => ['info', 'success', 'error', 'warning'].includes(value)
    },
    text: {
      type: String,
      required: true
    }
  },
  methods: {
    getMessageIcon(type) {
      const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
      }
      return icons[type] || 'ℹ️'
    }
  }
}
</script>

<style scoped>
.message {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 20px;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 1000;
  min-width: 300px;
  font-weight: 500;
}

.message-info {
  background: #d1ecf1;
  color: #0c5460;
  border-left: 4px solid #17a2b8;
}

.message-success {
  background: #d4edda;
  color: #155724;
  border-left: 4px solid #28a745;
}

.message-error {
  background: #f8d7da;
  color: #721c24;
  border-left: 4px solid #dc3545;
}

.message-warning {
  background: #fff3cd;
  color: #856404;
  border-left: 4px solid #ffc107;
}

.icon {
  font-size: 1.1em;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .message {
    right: 15px;
    left: 15px;
    min-width: auto;
  }
}
</style>