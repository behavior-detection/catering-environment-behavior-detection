<template>
  <div class="edit-account-container">
    <!-- 输入框组 -->
    <div class="input-panel">
      <p>账号名字：</p>
      <input 
        v-model="form.username" 
        class="account-input" 
        :placeholder="originalData.username" 
      />
    </div>

    <div class="input-panel">
      <p>账号密码：</p>
      <input 
        v-model="form.password" 
        type="password"
        class="account-input" 
        :placeholder="originalData.password" 
      />
    </div>

    <div class="input-panel">
      <p>邮箱：</p>
      <input 
        v-model="form.email" 
        type="email"
        class="account-input" 
        :placeholder="originalData.email" 
      />
    </div>

    <!-- 确认按钮 -->
    <button @click="handleConfirm">确认修改</button>

    <!-- 状态弹窗 -->
    <StateWindow ref="StateWindow" />
  </div>
</template>

<script>
import axios from 'axios'
import StateWindow from './StateWindow.vue'

export default {
  name: 'EditAccount',
  components: { StateWindow },
  data() {
    return {
      // ✅ 模拟数据库拉取的数据（实际需要后端接口）
      originalData: {
        username: '当前账号名',   // 【TODO: 接入数据库】axios.get('/api/account-info')
        password: '当前密码',     // 【TODO: 接入数据库】axios.get('/api/account-info')
        email: '当前邮箱@example.com' // 【TODO: 接入数据库】axios.get('/api/account-info')
      },
      // 用户编辑的临时数据
      form: {
        username: '',
        password: '',
        email: ''
      },
      requestTimeout: 5000
    }
  },
  methods: {
    async handleConfirm() {
      // 组装需要提交的数据：如果用户没填，就保留原值
      const payload = {
        username: this.form.username || this.originalData.username,
        password: this.form.password || this.originalData.password,
        email: this.form.email || this.originalData.email
      }

      // 【TODO: 与后端连接】调用更新接口
      try {
        const response = await Promise.race([
          axios.post('/api/update-account', payload),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), this.requestTimeout))
        ])

        if (response.data.success) {
          this.$refs.StateWindow.show('账号信息修改成功')

          // 更新本地 originalData，保持预设文字和最新一致
          this.originalData = { ...payload }
          this.form = { username: '', password: '', email: '' } // 清空输入框
        } else {
          this.$refs.StateWindow.show('修改失败')
        }
      } catch (error) {
        console.error('修改请求失败:', error)
        this.$refs.StateWindow.show('修改失败')
      }
    }
  }
}
</script>

<style scoped>
.edit-account-container {
  margin-top: 20px;
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-panel {
  padding: 20px;
  border: 1px solid #cce7ff;
  box-shadow: 0 4px 8px -2px #cce7ff;
  border-radius: 8px;
  background-color: #fff;
  display: flex;
  gap: 30px;
  align-items: center;
}

.account-input {
  padding: 10px 30px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  flex-grow: 1;
}

button {
  padding: 10px 30px;
  border: none;
  background-color: #409eff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
}

button:hover {
  background-color: #66b1ff;
}

p {
  margin: 0;
  font-size: 17px;
  color: #333;
}
</style>
