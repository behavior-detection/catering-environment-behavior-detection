// services/auth.js - 修复版本

// 使用相对路径，让Vite代理处理
const API_BASE_URL = '';  // 留空，使用相对路径

// 统一的错误处理函数
const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.message || `HTTP error! status: ${response.status}`);
    error.response = {
      status: response.status,
      data: errorData
    };
    throw error;
  }
  return response.json();
};

export const authService = {
  // ==================== 登录相关API ====================

  // 管理员登录 - 修复：路径匹配后端
  async adminLogin(credentials) {
    const response = await fetch(`${API_BASE_URL}/admin_login`, {  // 注意：去掉了下划线
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials)
    });
    return handleResponse(response);
  },

  // 经理登录 - 修复：路径匹配后端
  async managerLogin(credentials) {
    const response = await fetch(`${API_BASE_URL}/manager_login`, {  // 注意：去掉了下划线
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials)
    });
    return handleResponse(response);
  },

  // 访客/员工登录 - 修复：路径匹配后端
  async visitorLogin(credentials) {
    const response = await fetch(`${API_BASE_URL}/visitor_login`, {  // 注意：去掉了下划线
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials)
    });
    return handleResponse(response);
  },
  // ==================== 注册相关API ====================

  // 发送验证码 - 修复：使用正确的端点
  async sendVerificationCode(email) {
    const response = await fetch(`${API_BASE_URL}/api/send-verification-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email })
    });
    return handleResponse(response);
  },

  // 验证邮箱验证码 - 修复：使用正确的端点
  async verifyCode(email, code) {
    const response = await fetch(`${API_BASE_URL}/api/verify-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, code })
    });
    return handleResponse(response);
  },

  // 检查用户名是否存在 - 修复：使用正确的端点
  async checkUsername(username) {
    const response = await fetch(`${API_BASE_URL}/api/check-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    return handleResponse(response);
  },

  // 注册访客 - 修复：使用正确的端点
  async registerVisitor(userData) {
    const response = await fetch(`${API_BASE_URL}/api/visitor-register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });
    return handleResponse(response);
  },

  // 注册用户（通用） - 修复：使用正确的端点
  async registerUser(userData) {
    const response = await fetch(`${API_BASE_URL}/api/user-register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });
    return handleResponse(response);
  },

  // ==================== 密码重置相关API ====================

  // 重置密码 - 修复：使用正确的参数名
  async resetPassword(username, userType, newPassword, verificationToken) {
    const response = await fetch(`${API_BASE_URL}/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        userType,        // 修复：使用userType而不是user_type
        newPassword,     // 修复：使用newPassword而不是new_password
        verificationToken
      })
    });
    return handleResponse(response);
  },

  // 通过邮箱重置密码 - 修复：使用正确的端点和参数
  async resetPasswordByEmail(email, code, newPassword) {
    const response = await fetch(`${API_BASE_URL}/reset-password-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        verification_code: code,
        new_password: newPassword
      })
    });
    return handleResponse(response);
  },

  // ==================== 其他业务API ====================

  // 检查企业是否存在 - 修复：参数名匹配后端
  async checkEnterprise(enterpriseName) {
    const response = await fetch(`${API_BASE_URL}/check-enterprise`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        enterpriseName    // 修复：使用enterpriseName而不是enterprise_name
      })
    });
    return handleResponse(response);
  },

  // OCR识别身份证 - 修复：字段名匹配后端
  async ocrIdCard(file) {
    const formData = new FormData();
    formData.append('idCard', file);  // 修复：使用idCard而不是image

    const response = await fetch(`${API_BASE_URL}/ocr-idcard`, {
      method: 'POST',
      body: formData
    });
    return handleResponse(response);
  },

  // 保存员工验证信息 - 修复：参数结构匹配后端
  async saveEmployeeVerification(verificationData) {
    if (verificationData.file) {
      // 如果有文件，使用FormData
      const formData = new FormData();
      formData.append('idCard', verificationData.file);      // 修复：字段名
      formData.append('userName', verificationData.userName);  // 修复：字段名
      formData.append('enterpriseName', verificationData.enterpriseName);
      formData.append('idNumber', verificationData.idNumber);

      const response = await fetch(`${API_BASE_URL}/save-employee-verification`, {
        method: 'POST',
        body: formData
      });
      return handleResponse(response);
    } else {
      // 如果没有文件，使用JSON
      const response = await fetch(`${API_BASE_URL}/save-employee-verification-data`, {  // 修复：端点名称
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          enterprise_name: verificationData.enterpriseName,
          employee_name: verificationData.employeeName,
          id_number: verificationData.idNumber,
          verification_status: verificationData.verificationStatus || 'pending'
        })
      });
      return handleResponse(response);
    }
  },

  // 保存营业执照文件 - 修复：字段名和端点
  async saveLicenseFile(licenseData) {
    const formData = new FormData();
    formData.append('license', licenseData.file);              // 修复：字段名
    formData.append('companyName', licenseData.enterpriseName); // 修复：字段名
    if (licenseData.creditCode) {
      formData.append('creditCode', licenseData.creditCode);   // 修复：字段名
    }

    const response = await fetch(`${API_BASE_URL}/save-license-file`, {
      method: 'POST',
      body: formData
    });
    return handleResponse(response);
  },

  // OCR营业执照 - 修复：新增缺失的方法
  async ocrBusinessLicense(file) {
    const formData = new FormData();
    formData.append('license', file);

    const response = await fetch(`${API_BASE_URL}/ocr-business-license`, {  // 修复：端点名称
      method: 'POST',
      body: formData
    });
    return handleResponse(response);
  },

  // 系统健康检查
  async systemHealth() {
    const response = await fetch(`${API_BASE_URL}/system/health`);
    return handleResponse(response);
  },

  // ==================== 密码重置流程API ====================

  // 获取安全问题
  async getSecurityQuestions(username) {
    const response = await fetch(`${API_BASE_URL}/get-security-questions?username=${encodeURIComponent(username)}`);
    return handleResponse(response);
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
    return handleResponse(response);
  },

  // ==================== 用户名验证API ====================

  // 验证用户邮箱匹配 - 修复：端点名称
  async verifyUserEmail(username, email) {
    const response = await fetch(`${API_BASE_URL}/verify-user-email`, {  // 修复：去掉/api前缀
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, email })
    });
    return handleResponse(response);
  },

  // 检查经理用户名 - 修复：端点名称
  async checkManagerUsername(username) {
    const response = await fetch(`${API_BASE_URL}/check-manager-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    return handleResponse(response);
  },

  // 检查访客用户名 - 修复：端点名称
  async checkVisitorUsername(username) {
    const response = await fetch(`${API_BASE_URL}/check-visitor-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    return handleResponse(response);
  },

  // 检查访客用户名 - 修复：端点名称
  async checkAdminUsername(username) {
    const response = await fetch(`${API_BASE_URL}/check-admin-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    return handleResponse(response);
  },

  // ==================== 企业相关API ====================

  // 创建企业档案 - 新增：前端调用但后端缺失的方法
  async createEnterpriseArchive(archiveData) {
    const response = await fetch(`${API_BASE_URL}/api/create-enterprise-archive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(archiveData)
    });
    return handleResponse(response);
  },

  // 保存法定代表人身份证 - 新增：前端调用但后端缺失的方法
  async saveLegalRepresentativeId(fileData) {
    const formData = new FormData();
    formData.append('idCard', fileData.file);
    formData.append('userName', fileData.userName);
    formData.append('enterpriseName', fileData.enterpriseName);
    formData.append('idNumber', fileData.idNumber);
    formData.append('creditCode', fileData.creditCode);

    const response = await fetch(`${API_BASE_URL}/api/save-legal-representative-id`, {
      method: 'POST',
      body: formData
    });
    return handleResponse(response);
  },

  // ==================== 人脸识别相关API ====================

  // 人脸识别验证
  async faceVerification(imageData, username, userType) {
    const response = await fetch(`${API_BASE_URL}/api/verify_face`, {  // 修复：端点路径
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: imageData,
        username: username,
        userType: userType
      })
    });
    return handleResponse(response);
  },

  // ==================== 辅助方法 ====================

  // 登出
  logout() {
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('userInfo');
    sessionStorage.removeItem('adminInfo');  // 添加管理员信息清理
  },

  // 检查是否已登录
  isAuthenticated() {
    return !!localStorage.getItem('authToken') ||
           !!sessionStorage.getItem('userInfo') ||
           !!sessionStorage.getItem('adminInfo');
  },

  // 获取当前用户信息
  getCurrentUser() {
    const userInfo = sessionStorage.getItem('userInfo');
    const adminInfo = sessionStorage.getItem('adminInfo');

    if (userInfo) {
      return JSON.parse(userInfo);
    } else if (adminInfo) {
      return JSON.parse(adminInfo);
    }
    return null;
  }
};