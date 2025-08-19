<template>
  <div class="register-done-container">
    <div class="verification-panel">
      <h1>企业员工证件验证系统</h1>
      <p>请填写企业信息并上传有效身份证件</p>

      <form @submit.prevent="handleSubmit">
        <!-- 企业名称输入 -->
        <div class="form-group">
          <label>企业名称 *</label>
          <input v-model="formData.enterpriseName" type="text" required>
        </div>

        <!-- 文件上传区域 -->
        <div class="upload-area" @click="$refs.fileInput.click()">
          <input type="file" ref="fileInput" @change="handleFileSelect" hidden>
          <span class="upload-icon">📄</span>
          <p>点击上传或拖拽文件到此处</p>
        </div>

        <!-- OCR识别结果 -->
        <div v-if="extractedUserInfo" class="user-info">
          <h4>身份信息识别结果：</h4>
          <p>姓名：{{ extractedUserInfo.name }}</p>
          <p>身份证号：{{ maskIdNumber(extractedUserInfo.idNumber) }}</p>
        </div>

        <button type="submit" class="submit-btn">提交验证</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterDone',
  data() {
    return {
      formData: {
        enterpriseName: ''
      },
      extractedUserInfo: null
    }
  },
  methods: {
    handleFileSelect(e) {
      // 处理文件上传和OCR识别
    },
    handleSubmit() {
      // 提交表单验证
    },
    maskIdNumber(idNumber) {
      return idNumber ? idNumber.replace(/(\d{6})\d{8}(\d{4})/, '$1********$2') : '';
    }
  }
}
</script>

<style scoped>
.register-done-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 20px;
}

.verification-panel {
  background: white;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  padding: 50px 40px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  text-align: center;
}

.verification-panel h1 {
  color: var(--color-primary-dark);
  margin-bottom: 10px;
  font-size: 2rem;
}

.verification-panel > p {
  color: var(--color-text-secondary);
  margin-bottom: 40px;
  font-size: 16px;
}

.form-group {
  margin-bottom: 24px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 16px;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(135, 206, 235, 0.1);
}

.upload-area {
  border: 2px dashed var(--color-primary-light);
  border-radius: var(--radius-lg);
  padding: 40px;
  text-align: center;
  cursor: pointer;
  margin: 30px 0;
  background: var(--color-primary-lighter);
  transition: all 0.3s ease;
}

.upload-area:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-hover);
  transform: translateY(-2px);
}

.upload-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 15px;
}

.upload-area p {
  color: var(--color-text-secondary);
  margin: 0;
}

.user-info {
  background: var(--color-primary-lighter);
  padding: 20px;
  border-radius: var(--radius-md);
  margin: 20px 0;
  border: 1px solid var(--color-border);
  text-align: left;
}

.user-info h4 {
  color: var(--color-text);
  margin-bottom: 15px;
  font-size: 16px;
}

.user-info p {
  color: var(--color-text-secondary);
  margin: 8px 0;
  font-size: 14px;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 20px;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(135, 206, 235, 0.25);
}

@media (max-width: 480px) {
  .verification-panel {
    padding: 40px 30px;
  }

  .verification-panel h1 {
    font-size: 1.5rem;
  }
}
</style>