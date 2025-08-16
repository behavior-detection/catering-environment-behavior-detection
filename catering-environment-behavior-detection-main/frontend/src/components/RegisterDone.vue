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
  padding: 20px;
}

.verification-panel {
  max-width: 600px;
  margin: 0 auto;
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.upload-area {
  border: 2px dashed #667eea;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  margin: 20px 0;
}

.user-info {
  background: #e8f5e9;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 18px;
  cursor: pointer;
}
</style>