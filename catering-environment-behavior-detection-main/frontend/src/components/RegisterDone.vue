<template>
  <div class="register-done-container">
    <div class="verification-panel">
      <h1>企业员工注册</h1>
      <p>请按步骤完成企业员工身份验证和账户注册</p>

      <!-- 进度条 -->
      <div class="progress-bar">
        <div class="progress-fill" :style="{width: progressPercentage + '%'}"></div>
      </div>

      <!-- 步骤指示器 -->
      <div class="step-indicators">
        <div
          v-for="i in 5"
          :key="i"
          :class="['step-dot', {
            'active': i === currentStep,
            'completed': i < currentStep
          }]"
        >
          {{ i }}
        </div>
      </div>

      <!-- 状态消息 -->
      <div v-if="statusMessage" :class="['status-message', statusType]">
        {{ statusMessage }}
      </div>

      <!-- 步骤1：企业信息验证 -->
      <div v-show="currentStep === 1" class="step">
        <h2>验证企业信息</h2>
        <div class="form-group">
          <label>企业名称 *</label>
          <input
            v-model="formData.enterpriseName"
            type="text"
            placeholder="请输入您要加入的企业名称"
            @input="clearEnterpriseMessages"
            @blur="validateEnterprise"
            :class="['form-input', {
              'error': showEnterpriseError,
              'success': showEnterpriseSuccess
            }]"
            required
          >
          <div v-if="showEnterpriseError" class="error-message">{{ enterpriseError }}</div>
          <div v-if="showEnterpriseSuccess" class="success-message">{{ enterpriseSuccess }}</div>
        </div>

        <button
          class="btn btn-primary"
          @click="nextStep(1)"
          :disabled="!enterpriseValidated"
        >
          下一步
        </button>
      </div>

      <!-- 步骤2：身份证验证 -->
      <div v-show="currentStep === 2" class="step">
        <h2>上传身份证件</h2>
        <div
          class="upload-card"
          :class="{ uploaded: idUploaded, dragover: idDragover }"
          @dragover.prevent="idDragover = true"
          @dragleave="idDragover = false"
          @drop.prevent="handleIdDrop"
          @click="$refs.idInput.click()"
        >
          <div class="upload-icon">🆔</div>
          <h3>身份证正面照片</h3>
          <p class="upload-hint">点击或拖拽文件到此处</p>
          <button @click.stop="$refs.idInput.click()">选择文件</button>
          <input
            type="file"
            ref="idInput"
            @change="handleIdSelect"
            accept="image/jpeg,image/png,image/jpg"
            hidden
          >

          <!-- 进度条 -->
          <div v-if="idProgress > 0" class="progress-bar">
            <div class="progress-fill" :style="{ width: idProgress + '%' }"></div>
          </div>

          <!-- 预览 -->
          <div v-if="idPreview" class="preview">
            <img :src="idPreview" alt="身份证预览">
          </div>
        </div>

        <!-- 识别结果 -->
        <div v-if="idData" class="result-card">
          <h3>身份证信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <div class="info-label">姓名</div>
              <div class="info-value">{{ idData.name }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">身份证号</div>
              <div class="info-value">{{ maskIdNumber(idData.idNumber) }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">地址</div>
              <div class="info-value">{{ idData.address }}</div>
            </div>
          </div>
          <div :class="['validation-status', idData.isValid ? 'valid' : 'invalid']">
            {{ idData.isValid ? '✓ 身份证验证通过' : '✗ 身份证验证失败' }}
          </div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(2)">上一步</button>
          <button
            class="btn btn-primary"
            @click="nextStep(2)"
            :disabled="!idData || !idData.isValid"
          >
            下一步
          </button>
        </div>
      </div>

      <!-- 步骤3：邮箱验证 -->
      <div v-show="currentStep === 3" class="step">
        <h2>验证邮箱</h2>
        <div class="form-group">
          <label>邮箱地址</label>
          <div class="input-with-button">
            <input
              v-model="formData.email"
              @input="clearEmailMessages"
              @blur="validateEmail"
              :class="['form-input', {
                'error': showEmailError,
                'success': showEmailSuccess
              }]"
              type="email"
              placeholder="请输入邮箱地址"
            >
            <button
              class="send-code-btn"
              @click="sendVerificationCode"
              :disabled="isSendingCode || countdown > 0"
            >
              {{ sendCodeButtonText }}
            </button>
          </div>
          <div v-if="showEmailError" class="error-message">{{ emailError }}</div>
          <div v-if="showEmailSuccess" class="success-message">{{ emailSuccess }}</div>
          <div v-if="countdown > 0" class="countdown">{{ countdown }}秒后可重新发送</div>
        </div>

        <div class="form-group">
          <label>验证码</label>
          <input
            v-model="formData.emailCode"
            @input="clearCodeMessages"
            :class="['form-input', {
              'error': showCodeError,
              'success': showCodeSuccess
            }]"
            type="text"
            placeholder="请输入邮箱验证码"
            @keydown.enter="nextStep(3)"
          >
          <div v-if="showCodeError" class="error-message">{{ codeError }}</div>
          <div v-if="showCodeSuccess" class="success-message">{{ codeSuccess }}</div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(3)">上一步</button>
          <button class="btn btn-primary" @click="nextStep(3)">下一步</button>
        </div>
      </div>

      <!-- 步骤4：确认用户名 -->
      <div v-show="currentStep === 4" class="step">
        <h2>确认用户名</h2>
        <div class="user-info-card">
          <h3>用户信息确认</h3>
          <div class="info-grid">
            <div class="info-item">
              <div class="info-label">真实姓名</div>
              <div class="info-value">{{ idData?.name }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">系统用户名</div>
              <div class="info-value">{{ formData.username }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">企业名称</div>
              <div class="info-value">{{ formData.enterpriseName }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">职位</div>
              <div class="info-value">企业员工</div>
            </div>
          </div>

          <div class="username-note">
            <div class="note-content">
              <p><strong>用户名说明：</strong></p>
              <p>为保证实名制管理，系统将使用您的真实姓名作为用户名。该用户名不可修改，请确认信息无误后继续。</p>
            </div>
          </div>

          <div v-if="usernameValidationStatus" :class="['validation-status', usernameValidationStatus.type]">
            {{ usernameValidationStatus.message }}
          </div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(4)">上一步</button>
          <button
            class="btn btn-primary"
            @click="nextStep(4)"
            :disabled="!usernameValidationStatus || usernameValidationStatus.type !== 'valid'"
          >
            确认并继续
          </button>
        </div>
      </div>

      <!-- 步骤5：设置密码 -->
      <div v-show="currentStep === 5" class="step">
        <h2>设置密码</h2>
        <div class="form-group">
          <label>密码</label>
          <input
            v-model="formData.password"
            @input="validatePassword"
            :class="['form-input', {
              'error': showPasswordError,
              'success': passwordValid
            }]"
            type="password"
            placeholder="请输入密码"
          >
          <div v-if="showPasswordError" class="error-message">{{ passwordError }}</div>

          <!-- 密码要求提示 -->
          <div class="password-requirements">
            <div :class="['requirement', passwordRequirements.length ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.length ? '✓' : '✗' }}</span>
              8-16个字符
            </div>
            <div :class="['requirement', passwordRequirements.letter ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.letter ? '✓' : '✗' }}</span>
              包含字母
            </div>
            <div :class="['requirement', passwordRequirements.number ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.number ? '✓' : '✗' }}</span>
              包含数字
            </div>
            <div :class="['requirement', passwordRequirements.special ? 'valid' : '']">
              <span class="icon">{{ passwordRequirements.special ? '✓' : '✗' }}</span>
              包含特殊字符
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>确认密码</label>
          <input
            v-model="formData.confirmPassword"
            @input="validateConfirmPassword"
            :class="['form-input', {
              'error': showConfirmPasswordError,
              'success': showConfirmPasswordSuccess
            }]"
            type="password"
            placeholder="请再次输入密码"
            @keydown.enter="submitRegistration"
          >
          <div v-if="showConfirmPasswordError" class="error-message">{{ confirmPasswordError }}</div>
          <div v-if="showConfirmPasswordSuccess" class="success-message">{{ confirmPasswordSuccess }}</div>
        </div>

        <div class="button-group">
          <button class="btn btn-secondary" @click="prevStep(5)">上一步</button>
          <button
            class="btn btn-primary"
            @click="submitRegistration"
            :disabled="isSubmitting || !canSubmitFinal"
          >
            {{ isSubmitting ? '注册中...' : '提交注册申请' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterDone',
  data() {
    return {
      currentStep: 1,

      // 表单数据
      formData: {
        enterpriseName: '',
        username: '',
        email: '',
        emailCode: '',
        password: '',
        confirmPassword: ''
      },

      // 文件数据
      idFile: null,
      idData: null,

      // UI状态
      idUploaded: false,
      idDragover: false,
      idProgress: 0,
      idPreview: null,

      // 验证状态
      enterpriseValidated: false,
      emailVerified: false,
      countdown: 0,
      countdownTimer: null,
      isSendingCode: false,
      isSubmitting: false,

      // 用户名验证状态
      usernameValidationStatus: null,

      // 企业验证
      enterpriseError: '',
      enterpriseSuccess: '',
      showEnterpriseError: false,
      showEnterpriseSuccess: false,

      // 邮箱验证
      emailError: '',
      emailSuccess: '',
      showEmailError: false,
      showEmailSuccess: false,

      // 验证码
      codeError: '',
      codeSuccess: '',
      showCodeError: false,
      showCodeSuccess: false,

      // 密码验证
      passwordError: '',
      showPasswordError: false,
      passwordValid: false,
      confirmPasswordError: '',
      confirmPasswordSuccess: '',
      showConfirmPasswordError: false,
      showConfirmPasswordSuccess: false,

      // 密码要求
      passwordRequirements: {
        length: false,
        letter: false,
        number: false,
        special: false
      },

      // 状态消息
      statusMessage: '',
      statusType: 'info'
    }
  },
  computed: {
    progressPercentage() {
      return (this.currentStep / 5) * 100;
    },
    sendCodeButtonText() {
      if (this.isSendingCode) return '发送中...';
      if (this.countdown > 0) return '重新发送';
      return '发送验证码';
    },
    canSubmitFinal() {
      return this.passwordValid &&
             this.validateConfirmPassword() &&
             this.emailVerified &&
             this.usernameValidationStatus?.type === 'valid';
    }
  },
  methods: {
    // 清除企业消息
    clearEnterpriseMessages() {
      this.showEnterpriseError = false;
      this.showEnterpriseSuccess = false;
    },

    // 验证企业是否存在
    async validateEnterprise() {
      const enterpriseName = this.formData.enterpriseName.trim();

      if (!enterpriseName) {
        this.enterpriseError = '请输入企业名称';
        this.showEnterpriseError = true;
        this.enterpriseValidated = false;
        return false;
      }

      try {
        const response = await fetch('/check-enterprise', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ enterpriseName })
        });

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.message || '验证企业失败');
        }

        if (data.exists) {
          this.enterpriseSuccess = '企业验证通过';
          this.showEnterpriseSuccess = true;
          this.enterpriseValidated = true;
          return true;
        } else {
          this.enterpriseError = '企业未注册，请选择"还没有"选项进行企业注册';
          this.showEnterpriseError = true;
          this.enterpriseValidated = false;
          return false;
        }
      } catch (error) {
        console.error('验证企业失败:', error);
        this.enterpriseError = '验证企业时网络错误，请重试';
        this.showEnterpriseError = true;
        this.enterpriseValidated = false;
        return false;
      }
    },

    // 处理身份证拖拽
    handleIdDrop(e) {
      this.idDragover = false;
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        this.handleFile(files[0]);
      }
    },

    // 处理身份证选择
    handleIdSelect(e) {
      if (e.target.files.length > 0) {
        this.handleFile(e.target.files[0]);
      }
    },

    // 统一文件处理
    async handleFile(file) {
      console.log(`处理身份证文件:`, file.name, file.size, 'bytes');

      // 文件大小验证
      if (file.size > 10 * 1024 * 1024) {
        this.showStatus('文件大小不能超过10MB', 'error');
        return;
      }

      // 文件类型验证
      const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
      if (!allowedTypes.includes(file.type)) {
        this.showStatus('身份证文件格式不支持，请上传 JPG 或 PNG 格式', 'error');
        return;
      }

      // 保存文件
      this.idFile = file;
      this.idUploaded = true;
      this.showPreview(file);
      this.simulateProgress(() => this.performOCR(file));
    },

    // 显示预览
    showPreview(file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.idPreview = e.target.result;
      };
      reader.readAsDataURL(file);
    },

    // 模拟上传进度
    simulateProgress(callback) {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setTimeout(callback, 500);
        }
        this.idProgress = progress;
      }, 200);
    },

    // OCR识别
    async performOCR(file) {
      console.log('开始身份证OCR识别...');

      try {
        const result = await this.performIdCardOCR(file);

        if (!result.success) {
          throw new Error(result.message || '身份证识别失败');
        }

        if (!result.data?.name || !result.data?.idNumber) {
          throw new Error('身份证信息不完整，请确保上传的身份证正面图片清晰完整');
        }

        this.idData = {
          name: result.data.name,
          idNumber: result.data.idNumber,
          address: result.data.address || '未识别',
          isValid: true
        };

        // 自动设置用户名
        this.formData.username = this.idData.name;
        await this.autoValidateUsername();

        this.showStatus('✓ 身份证识别成功', 'success');

      } catch (error) {
        console.error('身份证识别失败:', error);

        let errorMessage = '';
        if (error.message.includes('OCR服务暂时不可用')) {
          errorMessage = 'OCR识别服务暂时不可用，请稍后再试';
        } else if (error.message.includes('超时')) {
          errorMessage = '识别超时，请尝试：\n1. 上传更小的图片（建议小于2MB）\n2. 确保图片清晰\n3. 检查网络连接';
        } else {
          errorMessage = `身份证识别失败，请确保：\n1. 图片清晰可见\n2. 证件完整无遮挡\n3. 光线充足无反光`;
        }

        this.showStatus(`✗ ${errorMessage}`, 'error');
        this.idData = null;
        this.idProgress = 0;
      }
    },

    // 身份证OCR识别
    async performIdCardOCR(file) {
      const formData = new FormData();
      formData.append('idCard', file);

      try {
        const response = await fetch('/ocr-idcard', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (!response.ok) {
          if (response.status === 503) {
            throw new Error('OCR服务暂时不可用，请稍后再试');
          } else if (response.status === 408) {
            throw new Error('识别超时，请上传更清晰或更小的图片');
          } else {
            throw new Error(data.message || '身份证识别失败');
          }
        }

        return data;
      } catch (error) {
        console.error('身份证OCR识别失败:', error);
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
          throw new Error('网络连接失败，请检查网络后重试');
        }
        throw error;
      }
    },

    // 自动验证用户名
    async autoValidateUsername() {
      if (!this.idData || !this.idData.name) {
        this.usernameValidationStatus = {
          type: 'invalid',
          message: '无法获取身份证姓名信息'
        };
        return false;
      }

      try {
        const response = await fetch('/api/check-visitor-username', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ username: this.formData.username })
        });

        const data = await response.json();

        if (data.exists) {
          this.usernameValidationStatus = {
            type: 'invalid',
            message: `用户名"${this.formData.username}"已存在，该姓名已被注册为员工账户。如果这是您的账户，请使用登录功能；如果您确认是本人首次注册，请联系客服处理。`
          };
          return false;
        } else {
          this.usernameValidationStatus = {
            type: 'valid',
            message: `用户名"${this.formData.username}"可用，系统将使用您的真实姓名作为登录用户名。`
          };
          return true;
        }
      } catch (error) {
        this.usernameValidationStatus = {
          type: 'invalid',
          message: '验证用户名时网络错误，请重试'
        };
        return false;
      }
    },

    // 清除邮箱消息
    clearEmailMessages() {
      this.showEmailError = false;
      this.showEmailSuccess = false;
    },

    // 清除验证码消息
    clearCodeMessages() {
      this.showCodeError = false;
      this.showCodeSuccess = false;
    },

    // 验证邮箱格式
    validateEmail() {
      const email = this.formData.email.trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!email) {
        this.emailError = '请输入邮箱地址';
        this.showEmailError = true;
        return false;
      }

      if (!emailRegex.test(email)) {
        this.emailError = '请输入有效的邮箱地址';
        this.showEmailError = true;
        return false;
      }

      this.showEmailError = false;
      return true;
    },

    // 发送验证码
    async sendVerificationCode() {
      if (!this.validateEmail()) return;

      this.isSendingCode = true;

      try {
        const response = await fetch('/api/send-verification-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email: this.formData.email.trim() })
        });

        const data = await response.json();

        if (data.success) {
          this.emailSuccess = '验证码已发送到您的邮箱';
          this.showEmailSuccess = true;
          this.startCountdown();
        } else {
          this.emailError = data.message || '验证码发送失败';
          this.showEmailError = true;
        }
      } catch (error) {
        this.emailError = '网络错误，请稍后重试';
        this.showEmailError = true;
      } finally {
        this.isSendingCode = false;
      }
    },

    // 开始倒计时
    startCountdown() {
      this.countdown = 60;
      this.countdownTimer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) {
          clearInterval(this.countdownTimer);
        }
      }, 1000);
    },

    // 验证邮箱验证码
    async verifyEmailCode() {
      const code = this.formData.emailCode.trim();

      if (!code) {
        this.codeError = '请输入验证码';
        this.showCodeError = true;
        return false;
      }

      try {
        const response = await fetch('/api/verify-code', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.formData.email.trim(),
            code
          })
        });

        const data = await response.json();

        if (data.success) {
          this.codeSuccess = '邮箱验证成功';
          this.showCodeSuccess = true;
          this.emailVerified = true;
          return true;
        } else {
          this.codeError = data.message || '验证码错误';
          this.showCodeError = true;
          return false;
        }
      } catch (error) {
        this.codeError = '验证失败，请重试';
        this.showCodeError = true;
        return false;
      }
    },

    // 验证密码强度
    validatePassword() {
      const password = this.formData.password;

      // 更新密码要求
      this.passwordRequirements = {
        length: password.length >= 8 && password.length <= 16,
        letter: /[a-zA-Z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
      };

      const allValid = Object.values(this.passwordRequirements).every(req => req);

      if (!password) {
        this.passwordError = '请输入密码';
        this.showPasswordError = true;
        this.passwordValid = false;
        return false;
      }

      if (!allValid) {
        this.passwordError = '密码不符合要求';
        this.showPasswordError = true;
        this.passwordValid = false;
        return false;
      }

      this.showPasswordError = false;
      this.passwordValid = true;
      return true;
    },

    // 验证确认密码
    validateConfirmPassword() {
      const password = this.formData.password;
      const confirmPassword = this.formData.confirmPassword;

      if (!confirmPassword) {
        this.showConfirmPasswordError = false;
        this.showConfirmPasswordSuccess = false;
        return false;
      }

      if (password !== confirmPassword) {
        this.confirmPasswordError = '两次输入的密码不一致';
        this.showConfirmPasswordError = true;
        this.showConfirmPasswordSuccess = false;
        return false;
      }

      if (!this.validatePassword()) {
        this.confirmPasswordError = '密码格式不符合要求';
        this.showConfirmPasswordError = true;
        this.showConfirmPasswordSuccess = false;
        return false;
      }

      this.confirmPasswordSuccess = '密码确认成功';
      this.showConfirmPasswordSuccess = true;
      this.showConfirmPasswordError = false;
      return true;
    },

    // 下一步
    async nextStep(step) {
      let canProceed = false;

      if (step === 1) {
        canProceed = await this.validateEnterprise();
      } else if (step === 2) {
        canProceed = this.idData && this.idData.isValid;
        if (!canProceed) {
          this.showStatus('请先上传并验证通过身份证', 'error');
          return;
        }
      } else if (step === 3) {
        canProceed = await this.verifyEmailCode();
      } else if (step === 4) {
        canProceed = await this.autoValidateUsername();
      }

      if (canProceed) {
        this.currentStep++;
      }
    },

    // 上一步
    prevStep(step) {
      this.currentStep--;
    },

    // 提交注册
    async submitRegistration() {
      console.log('=== 开始提交员工注册到缓存 ===');

      if (!this.canSubmitFinal) {
        this.showStatus('请确保所有步骤都已完成并验证通过', 'error');
        return;
      }

      this.isSubmitting = true;

      try {
        // 先保存文件到服务器
        const savedFiles = await this.saveFilesToServer();
        console.log('文件保存结果:', savedFiles);

        // 构建注册数据
        const registrationData = {
          // 企业信息
          enterpriseName: this.formData.enterpriseName.trim(),

          // 员工信息
          employeeName: this.idData.name,
          idNumber: this.idData.idNumber,

          // 用户账户信息
          username: this.formData.username.trim(),
          email: this.formData.email.trim(),
          password: this.formData.password,

          // 文件信息 - 使用实际保存的文件路径
          savedFiles: savedFiles,

          // 验证状态
          idVerified: this.idData.isValid,
          emailVerified: this.emailVerified,

          // 时间戳
          registrationTime: new Date().toISOString()
        };

        console.log('准备提交的员工注册数据:', registrationData);

        // 将注册数据保存到缓存
        const cacheResult = await this.saveRegistrationToCache(registrationData);

        if (cacheResult.success) {
          this.showStatus('✓ 员工注册申请已提交，等待企业管理员审核', 'success');

          // 🔧 修改：成功提交后直接跳转到身份选择页面
          setTimeout(() => {
            this.showStatus('员工注册申请已成功提交，正在返回身份选择页面...', 'success');

            setTimeout(() => {
              // 跳转到身份选择页面
              this.$router.push('/identity-division');
            }, 1500);
          }, 2000);

        } else {
          throw new Error(cacheResult.message || '注册信息保存失败');
        }

      } catch (error) {
        console.error('提交失败:', error);
        this.showStatus('✗ 提交失败: ' + error.message, 'error');
      } finally {
        this.isSubmitting = false;
      }
    },

    // 保存文件到服务器
    async saveFilesToServer() {
      const savedFiles = {};

      try {
        // 保存身份证
        if (this.idFile && this.idData) {
          const idFormData = new FormData();
          idFormData.append('idCard', this.idFile);
          idFormData.append('userName', this.idData.name);
          idFormData.append('enterpriseName', this.formData.enterpriseName);

          const idResponse = await fetch('/save-employee-verification', {
            method: 'POST',
            body: idFormData
          });

          const idResult = await idResponse.json();
          if (!idResult.success) {
            throw new Error('员工身份证保存失败: ' + idResult.message);
          }

          // 使用动态文件名作为键
          const idCardFileName = `${this.idData.name}-身份证.jpg`;
          savedFiles[idCardFileName] = idResult.data.fileName ?
            `/media/${idResult.data.fileName}` :
            idResult.data.path || `/media/${this.idData.name}-${this.formData.enterpriseName}.jpg`;
        }

        return savedFiles;
      } catch (error) {
        console.error('保存文件失败:', error);
        throw error;
      }
    },

    // 保存注册数据到缓存
    async saveRegistrationToCache(registrationData) {
      try {
        const response = await fetch('/api/save-employee-registration-cache', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(registrationData)
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.message || '保存到缓存失败');
        }

        return result;
      } catch (error) {
        console.error('保存员工注册数据到缓存失败:', error);
        throw error;
      }
    },

    // 重置表单
    resetForm() {
      // 重置步骤
      this.currentStep = 1;

      // 重置表单数据
      this.formData = {
        enterpriseName: '',
        username: '',
        email: '',
        emailCode: '',
        password: '',
        confirmPassword: ''
      };

      // 重置文件数据
      this.idFile = null;
      this.idData = null;

      // 重置UI状态
      this.idUploaded = false;
      this.idProgress = 0;
      this.idPreview = null;

      // 重置验证状态
      this.enterpriseValidated = false;
      this.emailVerified = false;
      this.isSubmitting = false;
      this.usernameValidationStatus = null;

      // 重置验证消息
      this.showEnterpriseError = false;
      this.showEnterpriseSuccess = false;
      this.showEmailError = false;
      this.showEmailSuccess = false;
      this.showCodeError = false;
      this.showCodeSuccess = false;
      this.showPasswordError = false;
      this.showConfirmPasswordError = false;
      this.showConfirmPasswordSuccess = false;
      this.passwordValid = false;

      // 重置密码要求
      this.passwordRequirements = {
        length: false,
        letter: false,
        number: false,
        special: false
      };

      // 重置文件输入
      if (this.$refs.idInput) this.$refs.idInput.value = '';

      this.showStatus('表单已重置，可以重新注册', 'info');
    },

    // 显示状态消息
    showStatus(message, type) {
      console.log('状态消息:', message, type);
      this.statusMessage = message;
      this.statusType = type;

      setTimeout(() => {
        this.statusMessage = '';
      }, 5000);
    },

    // 屏蔽身份证号
    maskIdNumber(idNumber) {
      if (!idNumber) return '';
      return idNumber.replace(/(\d{6})\d{8}(\d{4})/, '$1********$2');
    }
  },

  beforeDestroy() {
    // 清除倒计时
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  },

  mounted() {
    console.log('员工注册系统初始化完成');
    this.showStatus('请按步骤完成企业员工身份验证和账户注册', 'info');
  }
}
</script>

<style scoped>
.register-done-container {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: white;
  padding: 60px 15px 15px;
}

.verification-panel {
  background: white;
  padding: 32px;
  border-radius: 16px;
  width: 100%;
  max-width: 680px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  border: 1px solid #e6f2ff;
}

.verification-panel h1 {
  color: #5ba0c3;
  text-align: center;
  margin-bottom: 8px;
  font-size: 2rem;
}

.verification-panel > p {
  color: #64748b;
  margin-bottom: 32px;
  font-size: 14px;
  text-align: center;
}

.verification-panel h2 {
  color: #333;
  text-align: center;
  margin-bottom: 24px;
  font-size: 16px;
  font-weight: 500;
}

/* 进度条 */
.progress-bar {
  height: 5px;
  background: #e6f2ff;
  border-radius: 3px;
  margin: 24px 0 16px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #87ceeb 0%, #5ba0c3 100%);
  transition: width 0.3s ease;
}

/* 步骤指示器 */
.step-indicators {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 32px;
  gap: 24px;
}

.step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #e6f2ff;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  position: relative;
  transition: all 0.3s;
}

.step-dot.active {
  background: #5ba0c3;
  color: white;
  transform: scale(1.1);
}

.step-dot.completed {
  background: #5cb85c;
  color: white;
}

.step-dot.completed::after {
  content: '✓';
  position: absolute;
  font-size: 15px;
}

/* 状态消息 */
.status-message {
  padding: 10px 20px;
  border-radius: 6px;
  margin: 16px auto;
  max-width: 480px;
  font-weight: 500;
  font-size: 14px;
  animation: slideIn 0.3s ease;
  text-align: center;
}

.status-message.success {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.status-message.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.status-message.info {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

/* 步骤样式 */
.step {
  text-align: center;
}

/* 表单样式 */
.form-group {
  margin-bottom: 16px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 2px solid #e6f2ff;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s;
}

.form-input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(135, 206, 235, 0.1);
}

.form-input.error {
  border-color: #dc3545;
}

.form-input.success {
  border-color: #5cb85c;
}

/* 带按钮的输入框 */
.input-with-button {
  display: flex;
  gap: 8px;
}

.input-with-button .form-input {
  flex: 1;
}

.send-code-btn {
  padding: 12px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s;
}

.send-code-btn:hover:not(:disabled) {
  background: #357abd;
}

.send-code-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 错误和成功消息 */
.error-message {
  color: #dc3545;
  font-size: 13px;
  margin-top: 5px;
}

.success-message {
  color: #5cb85c;
  font-size: 13px;
  margin-top: 5px;
}

.countdown {
  color: #666;
  font-size: 13px;
  margin-top: 5px;
}

/* 密码要求 */
.password-requirements {
  margin-top: 10px;
  padding: 14px;
  background: #f8f9fa;
  border-radius: 6px;
}

.requirement {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  color: #666;
}

.requirement:last-child {
  margin-bottom: 0;
}

.requirement .icon {
  margin-right: 6px;
  font-weight: bold;
}

.requirement.valid {
  color: #5cb85c;
}

.requirement.valid .icon {
  color: #5cb85c;
}

/* 上传区域 */
.upload-card {
  background: #f8f9fa;
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  padding: 32px;
  text-align: center;
  width: 100%;
  max-width: 400px;
  margin: 0 auto 24px;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.upload-card:hover {
  border-color: #60a5fa;
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  background: #f1f3f4;
}

.upload-card.dragover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.upload-card.uploaded {
  border-color: #10b981;
  border-style: solid;
  background: #f0f9ff;
}

.upload-icon {
  font-size: 3.2rem;
  margin-bottom: 16px;
  display: block;
}

.upload-card h3 {
  color: #1e293b;
  margin-bottom: 8px;
  font-size: 1rem;
}

.upload-hint {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 16px;
}

.upload-card button {
  padding: 10px 26px;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-card button:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(59, 130, 246, 0.25);
}

/* 预览 */
.preview {
  margin-top: 16px;
  border-radius: 6px;
  overflow: hidden;
}

.preview img {
  max-width: 100%;
  max-height: 160px;
  object-fit: contain;
}

/* 用户信息确认卡片 */
.user-info-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 24px;
  margin: 0 auto 24px;
  max-width: 500px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.user-info-card h3 {
  color: #1e293b;
  margin-bottom: 20px;
  font-size: 1.1rem;
  text-align: center;
  border-bottom: 2px solid #e6f2ff;
  padding-bottom: 12px;
}

.username-note {
  display: flex;
  align-items: flex-start;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin: 20px 0;
  gap: 12px;
}

.note-content {
  flex: 1;
}

.note-content p {
  margin: 0 0 8px 0;
  font-size: 14px;
  line-height: 1.5;
}

.note-content p:last-child {
  margin-bottom: 0;
}

.note-content strong {
  color: #1e293b;
  font-weight: 600;
}

/* 结果卡片 */
.result-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 20px;
  margin: 16px auto 24px;
  max-width: 480px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.result-card h3 {
  color: #1e293b;
  margin-bottom: 16px;
  font-size: 1rem;
  text-align: left;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.info-item {
  text-align: left;
  padding: 10px;
  background: #f8fafc;
  border-radius: 5px;
}

.info-label {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 3px;
}

.info-value {
  color: #1e293b;
  font-size: 14px;
  font-weight: 500;
}

.validation-status {
  padding: 10px;
  border-radius: 5px;
  font-weight: 500;
  text-align: center;
  font-size: 14px;
}

.validation-status.valid {
  background: #d1fae5;
  color: #065f46;
}

.validation-status.invalid {
  background: #fee2e2;
  color: #991b1b;
}

/* 按钮 */
.btn {
  padding: 10px 32px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(135, 206, 235, 0.25);
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: #f8f9fa;
  color: #666;
  border: 2px solid #e6f2ff;
}

.btn-secondary:hover {
  background: #e6f2ff;
}

.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 24px;
}

@keyframes slideIn {
  from {
    transform: translateY(-8px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .verification-panel {
    padding: 24px 16px;
  }

  .step-indicators {
    gap: 16px;
  }

  .step-dot {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .button-group {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>