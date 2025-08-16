<template>
  <div class="face-recognition-container">
    <div class="recognition-panel">
      <h1>🔐 密码找回验证</h1>
      <p>请通过人脸识别验证您的身份</p>

      <!-- 摄像头区域 -->
      <div class="camera-container">
        <video ref="video" v-show="showVideo" autoplay muted></video>
        <div v-show="!showVideo" class="camera-placeholder">
          <i class="fas fa-camera"></i>
          <p>点击开始验证以启动摄像头</p>
        </div>
        <canvas ref="overlay" class="overlay"></canvas>
      </div>

      <!-- 控制按钮 -->
      <div class="controls">
        <button @click="startVerification" :disabled="isRunning">开始身份验证</button>
        <button @click="stopVerification" :disabled="!isRunning">停止验证</button>
      </div>

      <!-- 状态显示 -->
      <div class="status">{{ status.message }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FaceRecognition',
  props: ['username', 'userType'],
  data() {
    return {
      showVideo: false,
      isRunning: false,
      status: {
        message: '系统已准备就绪，请点击"开始身份验证"'
      }
    }
  },
  mounted() {
    this.initializeCamera();
  },
  methods: {
    async initializeCamera() {
      // 初始化摄像头
    },
    startVerification() {
      this.isRunning = true;
      this.showVideo = true;
      this.status.message = '正在检测人脸...';

      // 模拟验证成功
      setTimeout(() => {
        this.$emit('go-to-forgot-password', {
          step: 'reset-password',
          username: this.username,
          type: this.userType,
          verified: 'true'
        });
      }, 3000);
    },
    stopVerification() {
      this.isRunning = false;
      this.showVideo = false;
      this.status.message = '验证已停止';
    }
  }
}
</script>

<style scoped>
.face-recognition-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.recognition-panel {
  background: white;
  padding: 40px;
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 800px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.recognition-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
}

.recognition-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 30px;
}

.camera-container {
  position: relative;
  width: 100%;
  max-width: 640px;
  height: 480px;
  margin: 30px auto;
  background: var(--color-bg-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 2px solid var(--color-border);
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
}

.camera-placeholder i {
  font-size: 4rem;
  color: var(--color-primary);
  margin-bottom: 20px;
}

.controls {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin: 30px 0;
}

.controls button {
  padding: 14px 28px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.controls button:first-child {
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
}

.controls button:last-child {
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
}

.controls button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status {
  padding: 16px;
  background: var(--color-primary-lighter);
  border-radius: var(--radius-md);
  margin-top: 20px;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
</style>