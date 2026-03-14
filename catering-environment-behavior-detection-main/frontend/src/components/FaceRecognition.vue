<template>
  <div class="face-recognition-container">
    <div class="recognition-panel">
      <h1>人脸识别</h1>
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
        type: 'waiting',
        message: '系统已准备就绪，请点击"开始身份验证"'
      },
      stream: null,
      detectionInterval: null,
      redirectTimer: null,
      successStartTime: null,
      countdown: 0,
      canvas: null,
      canvasCtx: null
    }
  },
  mounted() {
    this.initializeCanvas();
    this.initializeCamera();
  },
  beforeDestroy() {
    this.cleanup();
  },
  methods: {
    initializeCanvas() {
      this.canvas = document.createElement('canvas');
      this.canvasCtx = this.canvas.getContext('2d');
    },

    async initializeCamera() {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 }
          }
        });

        const video = this.$refs.video;
        video.srcObject = this.stream;

        video.addEventListener('loadedmetadata', () => {
          const overlay = this.$refs.overlay;
          overlay.width = video.videoWidth;
          overlay.height = video.videoHeight;
          this.canvas.width = video.videoWidth;
          this.canvas.height = video.videoHeight;
        });
      } catch (error) {
        console.error('摄像头访问失败:', error);
        this.updateStatus('failed', '⚠️ 无法访问摄像头，请检查浏览器权限');
      }
    },

    startVerification() {
      this.isRunning = true;
      this.showVideo = true;
      this.updateStatus('detecting', '🔍 正在检测人脸...');

      // 每秒进行一次人脸检测
      this.detectionInterval = setInterval(() => {
        this.performFaceDetection();
      }, 1000);
    },

    stopVerification() {
      this.isRunning = false;
      this.showVideo = false;

      if (this.detectionInterval) {
        clearInterval(this.detectionInterval);
        this.detectionInterval = null;
      }

      if (this.redirectTimer) {
        clearTimeout(this.redirectTimer);
        this.redirectTimer = null;
      }

      this.successStartTime = null;
      this.countdown = 0;
      this.clearOverlay();
      this.updateStatus('waiting', '验证已停止，可重新开始');
    },

    async performFaceDetection() {
      if (!this.isRunning) return;

      try {
        // 捕获当前帧
        const video = this.$refs.video;
        this.canvasCtx.drawImage(video, 0, 0, this.canvas.width, this.canvas.height);
        const imageData = this.canvas.toDataURL('image/jpeg', 0.8);

        // 发送到后端进行识别
        const response = await fetch('/api/verify_face', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            image: imageData
          })
        });

        const data = await response.json();

        if (data.success) {
          this.processDetectionResults(data.results);
        } else {
          this.updateStatus('failed', `❌ 检测失败: ${data.error}`);
        }

      } catch (error) {
        console.error('人脸检测失败:', error);
        this.updateStatus('failed', '❌ 无法连接到服务器');
      }
    },

    processDetectionResults(results) {
      this.clearOverlay();

      if (results.length === 0) {
        this.updateStatus('detecting', '🔍 正在检测人脸...');
        this.resetSuccessTimer();
        return;
      }

      let hasSuccess = false;

      for (const result of results) {
        // 检查用户身份是否匹配
        if (result.recognized_name && this.username) {
          const isCorrectUser = result.recognized_name.toLowerCase() === this.username.toLowerCase();

          if (!isCorrectUser) {
            result.status = 'wrong-user';
            this.drawFaceBox(result);
            this.updateStatus('wrong-user', `❌ 用户身份不匹配，请使用正确的账号`);
            this.resetSuccessTimer();
            continue;
          }
        }

        this.drawFaceBox(result);

        if (result.status === 'success') {
          hasSuccess = true;
          this.handleSuccessfulVerification(result.recognized_name);
        }
      }

      if (!hasSuccess && results.length > 0) {
        const result = results[0];
        if (result.status === 'fake') {
          this.updateStatus('fake', `⚠️ 检测到伪造：${result.recognized_name}`);
        } else if (result.status === 'wrong-user') {
          // 已经在上面处理过了
        } else {
          this.updateStatus('failed', '❌ 未识别的用户');
        }
        this.resetSuccessTimer();
      }
    },

    handleSuccessfulVerification(userName) {
      if (!this.successStartTime) {
        this.successStartTime = Date.now();
      }

      const elapsed = (Date.now() - this.successStartTime) / 1000;
      const remaining = Math.max(0, 2 - elapsed);

      if (remaining > 0) {
        this.updateStatus('success', `✅ 验证成功！欢迎回来，${userName}`);
        this.countdown = Math.ceil(remaining);

        if (!this.redirectTimer) {
          this.redirectTimer = setTimeout(() => {
            this.redirectToResetPassword();
          }, 2000);
        }
      } else {
        this.redirectToResetPassword();
      }
    },

    redirectToResetPassword() {
      console.log('跳转到密码重置页面...');
      this.updateStatus('success', '🔄 正在跳转到密码重置页面...');

      // 使用 Vue Router 进行跳转
      setTimeout(() => {
        this.$emit('go-to-forgot-password', {
          step: 'reset-password',
          username: this.username,
          type: this.userType,
          verified: 'true'
        });
      }, 1000);
    },

    drawFaceBox(result) {
      const overlay = this.$refs.overlay;
      const ctx = overlay.getContext('2d');
      const [x1, y1, x2, y2] = result.face_location;
      const width = x2 - x1;
      const height = y2 - y1;

      let strokeColor, label;

      switch (result.status) {
        case 'success':
          strokeColor = '#28a745';
          label = result.recognized_name;
          break;
        case 'fake':
          strokeColor = '#ff5722';
          label = `Fake ${result.recognized_name}`;
          break;
        case 'wrong-user':
          strokeColor = '#9c27b0';
          label = `Wrong User: ${result.recognized_name}`;
          break;
        default:
          strokeColor = '#dc3545';
          label = 'Undefined';
      }

      // 绘制人脸框
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 4;
      ctx.strokeRect(x1, y1, width, height);

      // 绘制标签背景
      ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
      ctx.fillRect(x1, y2 + 5, width, 35);

      // 绘制标签文字
      ctx.fillStyle = 'white';
      ctx.font = 'bold 18px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(label, x1 + width / 2, y2 + 28);
    },

    resetSuccessTimer() {
      this.successStartTime = null;
      this.countdown = 0;
      if (this.redirectTimer) {
        clearTimeout(this.redirectTimer);
        this.redirectTimer = null;
      }
    },

    clearOverlay() {
      const overlay = this.$refs.overlay;
      const ctx = overlay.getContext('2d');
      ctx.clearRect(0, 0, overlay.width, overlay.height);
    },

    updateStatus(type, message) {
      this.status = {
        type: type,
        message: message
      };
    },

    cleanup() {
      this.stopVerification();
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }
    }
  }
}
</script>

<style scoped>
.face-recognition-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: var(--color-bg);
  padding: 100px 15px 15px; /* 添加顶部padding，让内容上移 */
}

.recognition-panel {
  background: white;
  padding: 24px; /* 从32px减小到24px */
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 640px;
  text-align: center;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.recognition-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 4px; /* 从8px减小到4px */
  font-size: 1.5rem;
}

.recognition-panel p {
  color: var(--color-text-secondary);
  margin-bottom: 16px; /* 从24px减小到16px */
  font-size: 14px;
}

.camera-container {
  position: relative;
  width: 100%;
  max-width: 512px;
  height: 384px;
  margin: 16px auto; /* 从24px减小到16px */
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
  font-size: 3.2rem;
  color: var(--color-primary);
  margin-bottom: 12px; /* 从16px减小到12px */
}

.controls {
  display: flex;
  gap: 14px;
  justify-content: center;
  margin: 16px 0; /* 从24px减小到16px */
}

.controls button {
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
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
  padding: 10px; /* 从12px减小到10px */
  background: var(--color-primary-lighter);
  border-radius: var(--radius-md);
  margin-top: 10px; /* 从12px减小到10px */
  color: var(--color-text);
  font-size: 14px;
  border: 1px solid var(--color-border);
}
</style>