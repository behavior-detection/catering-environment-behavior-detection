const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export const authService = {
  // 检查企业是否存在
  async checkEnterpriseExists(enterpriseName) {
    const response = await fetch(`${API_BASE_URL}/api/check-enterprise`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ enterpriseName })
    });
    return response.json();
  },

  // OCR识别身份证
  async ocrIdCard(file) {
    const formData = new FormData();
    formData.append('idCard', file);

    const response = await fetch(`${API_BASE_URL}/api/ocr-idcard`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // OCR识别营业执照
  async ocrBusinessLicense(file) {
    const formData = new FormData();
    formData.append('license', file);

    const response = await fetch(`${API_BASE_URL}/api/ocr/business-license`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // 发送验证码
  async sendVerificationCode(email) {
    const response = await fetch(`${API_BASE_URL}/api/send-verification-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email })
    });
    return response.json();
  },

  // 验证邮箱验证码
  async verifyCode(email, code) {
    const response = await fetch(`${API_BASE_URL}/api/verify-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, code })
    });
    return response.json();
  },

  // 检查用户名是否存在
  async checkUsername(username) {
    const response = await fetch(`${API_BASE_URL}/api/check-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    return response.json();
  },

  // 注册访客
  async registerVisitor(userData) {
    const response = await fetch(`${API_BASE_URL}/api/visitor-register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });
    return response.json();
  },

  // 注册用户
  async registerUser(userData) {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });
    return response.json();
  },

  // 保存员工验证信息
  async saveEmployeeVerification(file, userName, enterpriseName, idNumber) {
    const formData = new FormData();
    formData.append('idCard', file);
    formData.append('userName', userName);
    formData.append('enterpriseName', enterpriseName);
    formData.append('idNumber', idNumber);

    const response = await fetch(`${API_BASE_URL}/api/save-employee-verification`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // 保存营业执照文件
  async saveLicenseFile(file, companyName, creditCode) {
    const formData = new FormData();
    formData.append('license', file);
    formData.append('companyName', companyName);
    formData.append('creditCode', creditCode);

    const response = await fetch(`${API_BASE_URL}/api/save-license-file`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // 保存法定代表人身份证
  async saveLegalRepresentativeId(file, userName, enterpriseName, idNumber, creditCode) {
    const formData = new FormData();
    formData.append('idCard', file);
    formData.append('userName', userName);
    formData.append('enterpriseName', enterpriseName);
    formData.append('idNumber', idNumber);
    formData.append('creditCode', creditCode);

    const response = await fetch(`${API_BASE_URL}/api/save-legal-representative-id`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // 创建企业档案
  async createEnterpriseArchive(archiveData) {
    const response = await fetch(`${API_BASE_URL}/api/create-enterprise-archive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(archiveData)
    });
    return response.json();
  },

  // 获取安全问题
  async getSecurityQuestions(username) {
    const response = await fetch(`${API_BASE_URL}/get-security-questions?username=${encodeURIComponent(username)}`);
    return response.json();
  },

  // 验证安全答案
  async verifySecurityAnswers(data) {
    const response = await fetch(`${API_BASE_URL}/verify-security-answers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    return response.json();
  }
};