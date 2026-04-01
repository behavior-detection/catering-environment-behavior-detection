<template>
  <div class="logout-button-wrapper">
    <button @click="showConfirmDialog" class="logout-btn">退出账号</button>

    <!-- 确认弹窗 -->
    <Teleport to="body">
      <div v-if="showDialog" class="dialog-overlay" @click="cancelLogout">
        <div class="dialog-content" @click.stop>
          <div class="dialog-header">
            <h3>确认退出</h3>
          </div>
          <div class="dialog-body">
            <p>您确定要退出当前账号吗？</p>
            <p class="dialog-hint">退出后需要重新登录才能访问系统功能</p>
          </div>
          <div class="dialog-footer">
            <button @click="cancelLogout" class="btn btn-secondary">
              取消
            </button>
            <button @click="confirmLogout" class="btn btn-primary">
              确定退出
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
// 导入导航锁定管理器
import { navLockManager } from '@/services/NavLockManager'
import { ElMessage } from 'element-plus'

export default {
  name: 'LogoutButton',
  data() {
    return {
      showDialog: false
    }
  },
  methods: {
    // 显示确认弹窗
    showConfirmDialog() {
      this.showDialog = true
    },

    // 取消退出
    cancelLogout() {
      this.showDialog = false
    },

    // 确认退出
    confirmLogout() {
      // 清除 JWT Token
      localStorage.removeItem('authToken')

      // 清除所有用户信息
      sessionStorage.removeItem('userInfo')
      sessionStorage.removeItem('adminInfo')
      localStorage.removeItem('adminUsername')

      // 清除所有导航锁定
      navLockManager.clearAllLocks()

      // 关闭弹窗
      this.showDialog = false

      // 跳转到首页（Page1）
      this.$router.push('/')

      setTimeout(() => {
        ElMessage.success('已成功退出账号！')
      }, 100)
    }
  }
}
</script>

<style scoped>
/* 退出按钮样式 */
.logout-button-wrapper {
  display: inline-block;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: #fff;
  color: #ff4d4f;
  border: 2px solid #ff4d4f;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.logout-btn:hover {
  background: #ff4d4f;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 77, 79, 0.3);
}

.icon-logout {
  font-size: 18px;
}

/* 弹窗遮罩层 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}

/* 弹窗内容 */
.dialog-content {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  max-width: 400px;
  width: 90%;
  animation: slideIn 0.3s ease;
}

.dialog-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--color-border);
}

.dialog-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-text);
}

.dialog-body {
  padding: 24px;
}

.dialog-body p {
  margin: 0 0 12px;
  color: var(--color-text);
  font-size: 16px;
}

.dialog-hint {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 0;
}

.dialog-footer {
  padding: 16px 24px 24px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* 动画效果 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 480px) {
  .dialog-content {
    width: 95%;
    margin: 20px;
  }

  .dialog-footer {
    flex-direction: column-reverse;
  }

  .dialog-footer .btn {
    width: 100%;
  }
}
</style>