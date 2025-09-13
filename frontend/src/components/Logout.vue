<template>
  <div class="logout-container">
    <div class="logout-panel">
      <p>当前账号：<span class="account-name">{{ accountName }}</span></p>
      <button class="logout-button" @click="handleLogout">退出登录</button>
    </div>

    <!-- 弹窗组件 -->
    <StateWindow ref="StateWindow" />
  </div>
</template>

<script>
import axios from 'axios';
import StateWindow from './StateWindow.vue';

export default {
  name: 'LogoutAccount',
  components: { StateWindow },
  data() {
    return {
      // ⚠️ 这里应该从数据库 / 会话中调出当前登录的账号名字
      // 例如：axios.get('/api/current-user') → response.data.username
      accountName: '账号名字xxx（应从数据库调出）',

      requestTimeout: 5000 // 请求超时时间，单位毫秒
    }
  },
  methods: {
    handleLogout() {
      // 调用 StateWindow 确认退出
      this.$refs.StateWindow.show('是否确认退出登录？', {
        confirm: true,
        onConfirm: this.logoutAccount
      });
    },
    async logoutAccount() {
      try {
        const response = await Promise.race([
          axios.post('/api/logout', { username: this.accountName }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), this.requestTimeout))
        ]);

        if (response.data.success) {
          // 清除前端会话（例如 token / localStorage）
          localStorage.removeItem('token');
          this.$refs.StateWindow.show('退出成功');

          // ⚠️ 退出后可跳转到登录页
          this.$router.push('/login');
        } else {
          this.$refs.StateWindow.show('退出失败');
        }
      } catch (error) {
        console.error('退出请求失败:', error);
        this.$refs.StateWindow.show('退出失败');
      }
    }
  }
}
</script>

<style scoped>
.logout-container {
  margin-top: 20px;
  margin-left: 20px;
}

.logout-panel {
  padding: 20px;
  border: 1px solid #ffcccc;
  box-shadow: 0 4px 8px -2px #ffcccc;
  border-radius: 8px;
  background-color: #fff;
  display: flex;
  gap: 30px;
  align-items: center;
}

.account-name {
  font-weight: bold;
  color: #333;
}

.logout-button {
  padding: 10px 30px;
  border: none;
  background-color: #ff4d4f; /* 红色按钮 */
  color: white;
  border-radius: 4px;
  cursor: pointer;
}

.logout-button:hover {
  background-color: #ff7875;
}

p {
  margin: 0;
  font-size: 17px;
  color: #333;
}
</style>
