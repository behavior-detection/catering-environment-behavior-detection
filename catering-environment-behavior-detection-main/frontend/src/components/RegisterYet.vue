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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.qualification-panel {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.qualification-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
  font-size: 2.5rem;
}

.qualification-panel > p {
  color: var(--color-text-secondary);
  margin-bottom: 40px;
  font-size: 16px;
}

.upload-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 30px;
  margin: 40px 0;
  justify-items: center;
}

.upload-card {
  background: white;
  border: 2px dashed var(--color-primary-light);
  border-radius: var(--radius-lg);
  padding: 40px;
  text-align: center;
  width: 100%;
  max-width: 450px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-5px);
  box-shadow: var(--shadow-md);
}

.upload-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  display: block;
}

.upload-card h3 {
  color: var(--color-text);
  margin-bottom: 20px;
  font-size: 1.25rem;
}

.upload-card button {
  padding: 12px 32px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-card button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}

.result-section {
  background: var(--color-primary-lighter);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 30px;
  margin: 40px auto;
  max-width: 800px;
}

.submit-btn {
  padding: 16px 48px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 20px;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(135, 206, 235, 0.3);
}

@media (max-width: 768px) {
  .upload-section {
    grid-template-columns: 1fr;
  }

  .qualification-panel h1 {
    font-size: 2rem;
  }
}
</style>