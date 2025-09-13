<template>
  <div class="find-device-container">
    <div class="search-panel">
      <p>选择您要删除的设备：</p>
      <select v-model="selectedDevice" class="device-select">
        <option value="">请选择</option>
        <option value="1st_period_of_time">设备1</option>
        <option value="2nd_period_of_time">设备2</option>
        <option value="3th_period_of_time">设备3</option>
      </select>
      <button @click="handleConfirm">确认</button>
    </div>

    <!-- 添加设备面板（新增） -->
    <div class="search-panel">
      <p>输入您要添加的设备名称：</p>
      <input v-model="newDeviceName" class="device-input" placeholder="设备名称" />
      <button @click="handleAdd">添加设备</button>
    </div>

    <!-- 弹窗改成ref调用 -->
    <StateWindow ref="StateWindow" />
  </div>
</template>

<script>
import axios from 'axios';
import StateWindow from './StateWindow.vue';

export default {
  name: 'DeviceManagement',
  components: { StateWindow },
  data() {
    return {
      selectedDevice: '',
      newDeviceName: '',  //添加设备名称
      requestTimeout: 5000  // 请求超时时间，单位毫秒
    }
  },
  methods: {
    handleConfirm() { // 调用StateWindow组件封装的方法
      if (!this.selectedDevice) {
        this.$refs.StateWindow.show('未选择设备');
        return;
      }

      // 使用StateWindow组件弹出确认删除
      this.$refs.StateWindow.show('是否确认删除设备？', {
        confirm: true,
        onConfirm: this.deleteDevice
      });
    },
    async deleteDevice() { // 调用StateWindow组件显示结果!【与后端连接】
      try {
        const response = await Promise.race([
          axios.post('/api/delete-device', { deviceId: this.selectedDevice }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), this.requestTimeout))
        ]);

        if (response.data.success) {
          this.$refs.StateWindow.show('删除成功');
        } else {
          this.$refs.StateWindow.show('删除失败');
        }
      } catch (error) {
        console.error('删除请求失败:', error);
        this.$refs.StateWindow.show('删除失败');
      }
    },
    handleAdd() { // 添加设备逻辑
      if (!this.newDeviceName) {
        this.$refs.StateWindow.show('请输入设备名称');
        return;
      }

      // 使用StateWindow组件弹出添加结果
      this.$refs.StateWindow.show(`是否确认添加设备：${this.newDeviceName}？`, {
        confirm: true,
        onConfirm: this.addDevice
      });
    },
    async addDevice() { // 调用StateWindow组件显示结果!【与后端连接】
      try {
        const response = await Promise.race([
          axios.post('/api/add-device', { deviceName: this.newDeviceName }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), this.requestTimeout))
        ]);
        if (response.data.success) {
          this.$refs.StateWindow.show('添加成功');
        } else {
          this.$refs.StateWindow.show('添加失败');
        }
      } catch (error) {
        console.error('添加请求失败:', error);
        this.$refs.StateWindow.show('添加失败');
      }
    }
  }
}
</script>

<style scoped>
.find-device-container {
  margin-top: 20px;
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-panel {
  padding: 20px;
  border: 1px solid #cce7ff;
  box-shadow: 0 4px 8px -2px #cce7ff;
  border-radius: 8px;
  background-color: #fff;
  display: flex;
  gap: 30px;
  align-items: center;
}

.device-select {
  padding: 10px 30px; /*第一个数字是控制选项框宽度，第二个是控制内部文字与边框的距离*/
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  flex-grow: 1; /* 输入框占满剩余空间 */
}

.device-input {
  padding: 10px 30px; /*第一个数字是控制选项框宽度，第二个是控制内部文字与边框的距离*/
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  flex-grow: 1; /* 输入框占满剩余空间 */
}

button {
  padding: 10px 30px;
  border: none;
  background-color: #409eff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
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
