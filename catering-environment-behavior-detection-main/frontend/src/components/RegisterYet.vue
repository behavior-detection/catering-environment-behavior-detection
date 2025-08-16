<template>
  <div class="register-yet-container">
    <div class="qualification-panel">
      <h1>🏢 企业资质验证系统</h1>
      <p>上传营业执照和法定代表人身份证，自动识别并验证信息有效性</p>

      <div class="upload-section">
        <!-- 营业执照上传 -->
        <div class="upload-card">
          <div class="upload-icon">📄</div>
          <h3>营业执照</h3>
          <button @click="$refs.licenseInput.click()">选择文件</button>
          <input type="file" ref="licenseInput" @change="handleLicenseSelect" hidden>
        </div>

        <!-- 身份证上传 -->
        <div class="upload-card">
          <div class="upload-icon">🆔</div>
          <h3>法定代表人身份证</h3>
          <button @click="$refs.idInput.click()">选择文件</button>
          <input type="file" ref="idInput" @change="handleIdSelect" hidden>
        </div>
      </div>

      <!-- 识别结果 -->
      <div v-if="licenseData || idData" class="result-section">
        <!-- 显示识别结果 -->
      </div>

      <button class="submit-btn" @click="handleSubmit">提交并创建档案</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterYet',
  data() {
    return {
      licenseData: null,
      idData: null
    }
  },
  methods: {
    handleLicenseSelect(e) {
      // 处理营业执照上传
    },
    handleIdSelect(e) {
      // 处理身份证上传
    },
    handleSubmit() {
      // 提交创建企业档案
    }
  }
}
</script>

<style scoped>
.register-yet-container {
  padding: 20px;
}

.qualification-panel {
  max-width: 1200px;
  margin: 0 auto;
}

.upload-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 30px;
  margin: 40px 0;
}

.upload-card {
  background: white;
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
}

.submit-btn {
  padding: 16px 48px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 18px;
  cursor: pointer;
}
</style>