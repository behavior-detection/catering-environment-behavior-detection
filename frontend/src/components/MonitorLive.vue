<template>
  <div class="find-device-container">
    <!-- 子模块1：监控区域 -->
    <div class="monitor-panel">
      <video
        :src="sampleVideo"
        controls
        autoplay
        loop
        muted
        style="width: 100%; height: auto;"
      ></video>
    </div>
  </div>
</template>

<script>
import sampleVideo from '@/assets/D11_20240907170658.mp4'

export default {
  name: 'MonitorLive',
  data() {
    return {
      sampleVideo
    }
  }
}
</script>

<style scoped>
/* 外层容器：去掉多余的左边距，避免与 main-content 的 padding 叠加 */
.find-device-container {
  margin-top: 20px;
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.monitor-panel {
  width: 80%;
  max-width: 1280px;
  min-height: 560px;
  border: 1px dashed #aaa;
  border-radius: 6px;
  padding: 15px;
  background-color: #f9f9f9;
  color: #666;
  font-size: 14px;
  box-sizing: border-box;
}
</style>