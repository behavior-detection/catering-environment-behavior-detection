<template>
  <main>
    <!-- 根据当前组件状态显示不同的组件 -->
    <component
      v-if="!isLoginComponent"
      :is="currentComponent"
      @go-to-login="handleGoToLogin"
      @go-to-register="handleGoToRegister"
      @go-to-forgot-password="handleGoToForgotPassword"
      @register-success="handleRegisterSuccess"
      @reset-success="handleResetSuccess"
      :user-type="userType"
      :username="username"
    />

    <!-- 登录组件单独处理 -->
    <BaseLogin
      v-else
      :user-type="userType"
      :greeting-text="loginGreetingText"
      :login-endpoint="loginEndpoint"
      :success-route="loginSuccessRoute"
      :show-signup="showSignup"
      @login-success="handleLoginSuccess"
      @go-to-forgot-password="handleGoToForgotPassword"
      @go-to-register="handleGoToRegister"
    />
  </main>
</template>

<script>
// 认证相关组件
import IdentityDivision from '../components/IdentityDivision.vue'
import BaseLogin from '../components/BaseLogin.vue'

// 注册相关组件
import RegisterChoice from '../components/RegisterChoice.vue'
import RegisterDone from '../components/RegisterDone.vue'
import RegisterYet from '../components/RegisterYet.vue'
import RegisterVisitor from '../components/RegisterVisitor.vue'
import RegisterUser from '../components/RegisterUser.vue'

// 账户管理相关组件
import VerifyUsername from '../components/VerifyUsername.vue'
import ResetOptions from '../components/ResetOptions.vue'
import SecurityVerification from '../components/SecurityVerification.vue'
import EmailVerification from '../components/EmailVerification.vue'
import FaceRecognition from '../components/FaceRecognition.vue'
import ResetPassword from '../components/ResetPassword.vue'

export default {
  name: 'Page1',
  components: {
    // 认证相关
    IdentityDivision,
    BaseLogin,

    // 注册相关
    RegisterChoice,
    RegisterDone,
    RegisterYet,
    RegisterVisitor,
    RegisterUser,

    // 账户管理相关
    VerifyUsername,
    ResetOptions,
    SecurityVerification,
    EmailVerification,
    FaceRecognition,
    ResetPassword
  },
  data() {
    return {
      currentComponent: 'IdentityDivision', // 默认显示身份选择组件
      userType: '', // 当前用户类型
      username: '', // 当前用户名
      previousComponent: null // 用于返回功能
    }
  },
  computed: {
    // 判断当前是否是登录组件
    isLoginComponent() {
      return this.currentComponent === 'Login'
    },

    // 根据用户类型返回登录欢迎语
    loginGreetingText() {
      const greetings = {
        'manager': '欢迎，经理！',
        'visitor': '欢迎，访客！'
      }
      return greetings[this.userType] || '欢迎！'
    },

    // 根据用户类型返回登录API端点
    loginEndpoint() {
      return `${this.userType}_login`
    },

    // 根据用户类型返回登录成功后的路由
    loginSuccessRoute() {
      return `/${this.userType}`
    },

    // 是否显示注册链接
    showSignup() {
      return true  // 所有用户类型都可以注册
    }
  },
  methods: {
    // 处理跳转到登录页面
    handleGoToLogin(type) {
      this.userType = type
      this.previousComponent = 'IdentityDivision'
      this.currentComponent = 'Login' // 统一使用Login标识
    },

    // 处理登录成功
    handleLoginSuccess(userData) {
      // 保存用户信息到 sessionStorage
      sessionStorage.setItem('userInfo', JSON.stringify({
        ...userData,
        userType: this.userType
      }))

      // 登录成功后可以跳转到 Page2 或显示其他内容
      alert(`${this.userType} 登录成功！`)

      // 如果需要跳转到其他页面
      // this.$router.push('/Page2')
    },

    // 处理跳转到注册页面
    handleGoToRegister(type) {
      this.previousComponent = this.currentComponent

      if (type === 'choice' || !type) {
        this.currentComponent = 'RegisterChoice'
      } else if (type === 'visitor') {
        this.currentComponent = 'RegisterVisitor'
      } else if (type === 'enterprise-employee') {
        this.currentComponent = 'RegisterDone'
      } else if (type === 'enterprise-new') {
        this.currentComponent = 'RegisterYet'
      } else if (type === 'complete') {
        this.currentComponent = 'RegisterUser'
      }
    },

    // 处理注册成功
    handleRegisterSuccess() {
      alert('注册成功！')
      this.currentComponent = 'IdentityDivision'
    },

    // 处理忘记密码
    handleGoToForgotPassword(data) {
      this.previousComponent = this.currentComponent

      // 如果从登录页面过来，需要保存用户类型
      if (this.isLoginComponent) {
        data = { type: this.userType, step: 'verify-username' }
      }

      this.userType = data.type
      this.username = data.username || ''

      if (data.step === 'verify-username' || !data.step) {
        this.currentComponent = 'VerifyUsername'
      } else if (data.step === 'reset-options') {
        this.currentComponent = 'ResetOptions'
      } else if (data.step === 'security-verification') {
        this.currentComponent = 'SecurityVerification'
      } else if (data.step === 'email-verification') {
        this.currentComponent = 'EmailVerification'
      } else if (data.step === 'face-recognition') {
        this.currentComponent = 'FaceRecognition'
      } else if (data.step === 'reset-password') {
        this.currentComponent = 'ResetPassword'
      }
    },

    // 处理密码重置成功
    handleResetSuccess() {
      alert('密码重置成功！')
      this.currentComponent = 'IdentityDivision'
    },

    // 返回上一个组件
    goBack() {
      if (this.previousComponent) {
        this.currentComponent = this.previousComponent
        this.previousComponent = null
      } else {
        this.currentComponent = 'IdentityDivision'
      }
    }
  }
}
</script>

<style scoped>
main {
  min-height: 100vh;
  width: 100%;
  overflow-x: hidden;
}
</style>