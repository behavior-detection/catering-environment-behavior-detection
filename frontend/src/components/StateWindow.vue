<template>
  <div v-if="visible" class="overlay"> <!-- 增加 v-if 控制显示 -->
    <div class="modal">
      <p>{{ message }}</p>
      <!-- 增加确认删除按钮逻辑 -->
      <div v-if="showConfirm">
        <button @click="confirm">确认</button>
        <button @click="close">取消</button>
      </div>
      <div v-else>
        <button @click="close">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'OperationSuccess',
  data() {   // 增加内部状态管理
    return {
      visible: false,
      message: '',
      showConfirm: false,
      confirmCallback: null,
    }
  },
  methods: {  // 封装弹窗接口
    show(message, options = {}) {
      this.message = message;
      this.visible = true;
      this.showConfirm = !!options.confirm;
      this.confirmCallback = options.onConfirm || null;
    },
    confirm() {
      this.visible = false;
      if (this.confirmCallback) this.confirmCallback();
    },
    close() {
      this.visible = false;
      this.confirmCallback = null;
      this.showConfirm = false;
    }
  }
}
</script>

<style scoped>
/* 样式保持不变 */
.overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}

.modal {
  background-color: #fff;
  padding: 20px 30px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

button {
  margin-top: 15px;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  background-color: #1890FF;
  color: #fff;
  cursor: pointer;
}

button:hover {
  background-color: #66b1ff;
}
</style>
