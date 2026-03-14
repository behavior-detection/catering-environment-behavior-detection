<template>
  <div class="page3-container">
    <!-- 全局返回按钮 -->
    <div v-if="showBackButton" class="back-button-wrapper">
      <button @click="goBack" class="global-back-btn">
        返回
      </button>
    </div>

    <!-- 显示更改密码组件 -->
    <RevisePassword
      v-if="showChangePassword"
      :userInfo="userInfo"
      @back="handleBackToMain"
    />

    <!-- 显示密保设置组件 -->
    <RecogSecurityQuestions
      v-else-if="showSecuritySettings"
      :userInfo="userInfo"
      @back="handleBackToMain"
    />

    <!-- 主页面内容 -->
    <template v-else>
      <!-- 页面头部 -->
      <div class="page-header">
        <h1>账号管理</h1>
        <LogoutButton />
      </div>

      <!-- 页面主体内容 -->
      <div class="page-content">
        <!-- 用户信息和账号设置容器 -->
        <div class="info-settings-container">
          <!-- 用户信息卡片 -->
          <div class="user-info-card card">
            <h2>用户信息</h2>
            <div class="info-list">
              <div class="info-item">
                <label>用户名：</label>
                <span>{{ userInfo.username || '未知用户' }}</span>
              </div>
              <div class="info-item">
                <label>用户类型：</label>
                <span>{{ userTypeText }}</span>
              </div>
              <div class="info-item">
                <label>登录时间：</label>
                <span>{{ loginTime }}</span>
              </div>
            </div>
          </div>

          <!-- 账号设置卡片 -->
          <div class="settings-card card">
            <h2>账号设置</h2>
            <div class="settings-options">
              <button @click="showPasswordChange" class="setting-btn">
                <div class="setting-info">
                  <h3>更改密码</h3>
                  <p>修改您的账号密码</p>
                </div>
              </button>
              <button @click="showSecurityQuestions" class="setting-btn">
                <div class="setting-info">
                  <h3>设置密保</h3>
                  <p>设置或修改密保问题</p>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- Admin专用：企业注册管理 -->
        <div v-if="isAdmin" class="registration-management-card card">
          <div class="card-header">
            <h2>企业注册管理</h2>
            <div class="notification-badge" v-if="adminPendingCount > 0">
              {{ adminPendingCount }}
            </div>
            <div class="header-actions">
              <button @click="refreshAdminNotifications" class="refresh-btn" :disabled="loading">
                <span v-if="loading">刷新中...</span>
                <span v-else>刷新</span>
              </button>
              <button @click="clearAllAdminNotifications" class="clear-btn" :disabled="loading">
                <span v-if="loading">处理中...</span>
                <span v-else>清理全部</span>
              </button>
            </div>
          </div>

          <!-- 待审核的企业申请列表 -->
          <div v-if="adminNotifications.length > 0" class="notifications-list">
            <div
              v-for="notification in adminNotifications"
              :key="notification.id"
              class="notification-item enterprise-notification"
              :class="{
                'pending': notification.type === 'registration_request' && notification.data.approvalStatus === 'pending_approval',
                'result': notification.type === 'registration_result',
                'result-approved': notification.type === 'registration_result' && notification.data.decision === 'approve',
                'result-rejected': notification.type === 'registration_result' && notification.data.decision === 'reject'
              }"
            >
              <div class="notification-header">
                <div class="company-name">{{ notification.data.companyName }}</div>
                <div class="notification-time">{{ formatTime(notification.timestamp) }}</div>
                <div class="notification-actions">
                  <div class="status-badge" :class="getStatusClass(notification)">
                    {{ getStatusText(notification) }}
                  </div>
                  <button @click="deleteAdminNotification(notification.id)" class="delete-btn" :disabled="loading">
                    删除
                  </button>
                </div>
              </div>

              <div class="notification-details">
                <div class="detail-row" v-if="notification.data.legalRepresentative">
                  <span class="label">法定代表人：</span>
                  <span class="value">{{ notification.data.legalRepresentative }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.username">
                  <span class="label">用户名：</span>
                  <span class="value">{{ notification.data.username }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.email">
                  <span class="label">邮箱：</span>
                  <span class="value">{{ notification.data.email }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.unifiedSocialCreditCode">
                  <span class="label">统一社会信用代码：</span>
                  <span class="value">{{ notification.data.unifiedSocialCreditCode }}</span>
                </div>
              </div>

              <!-- 文件部分单独显示 -->
              <div v-if="notification.data.files && notification.data.files.length > 0" class="files-section">
                <div class="files-header">上传文件</div>
                <div class="files-list">
                  <div v-for="file in notification.data.files" :key="file.filename" class="file-item-compact">
                    <div class="file-info-compact">
                      <span class="file-name">{{ file.filename }}</span>
                      <span class="file-type-tag">{{ getFileTypeText(file.type) }}</span>
                    </div>
                    <div class="file-actions-compact">
                      <button @click="downloadFile(file)" class="action-btn download" :disabled="downloading[file.filename]">
                        {{ downloading[file.filename] ? '下载中...' : '下载' }}
                      </button>
                      <button @click="previewFile(file)" class="action-btn preview" v-if="isImageFile(file.filename)">
                        预览
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 企业注册审核操作按钮 -->
              <div v-if="notification.type === 'registration_request' && notification.data.approvalStatus === 'pending_approval'" class="approval-actions">
                <div class="comment-section">
                  <textarea
                    v-model="adminReviewComments[notification.id]"
                    placeholder="审核意见（可选）"
                    class="review-comment"
                    rows="2"
                  ></textarea>
                </div>
                <div class="action-buttons">
                  <button
                    @click="approveEnterpriseRegistration(notification.id, 'approve')"
                    class="btn btn-approve"
                    :disabled="adminProcessing[notification.id]"
                  >
                    <span v-if="adminProcessing[notification.id]">处理中...</span>
                    <span v-else>通过</span>
                  </button>
                  <button
                    @click="approveEnterpriseRegistration(notification.id, 'reject')"
                    class="btn btn-reject"
                    :disabled="adminProcessing[notification.id]"
                  >
                    <span v-if="adminProcessing[notification.id]">处理中...</span>
                    <span v-else>拒绝</span>
                  </button>
                </div>
              </div>

              <!-- 已审核的结果显示 -->
              <div v-else-if="notification.type === 'registration_result'" class="review-result">
                <div class="result-message">
                  <strong>审核结果：</strong>{{ notification.data.decision === 'approve' ? '已通过' : '已拒绝' }}
                </div>
                <div v-if="notification.data.reviewComments" class="review-comments">
                  <strong>审核意见：</strong>{{ notification.data.reviewComments }}
                </div>
              </div>
            </div>
          </div>

          <!-- 无企业注册申请时的提示 -->
          <div v-else-if="!loading" class="no-notifications">
            <p>暂无企业注册申请</p>
          </div>
        </div>

        <!-- Manager专用：员工注册管理 -->
        <div v-if="isManager" class="employee-management-card card">
          <div class="card-header">
            <h2>员工注册管理</h2>
            <div class="notification-badge" v-if="managerPendingCount > 0">
              {{ managerPendingCount }}
            </div>
            <div class="header-actions">
              <button @click="refreshManagerNotifications" class="refresh-btn" :disabled="loading">
                <span v-if="loading">刷新中...</span>
                <span v-else>刷新</span>
              </button>
              <button @click="clearAllManagerNotifications" class="clear-btn" :disabled="loading">
                <span v-if="loading">处理中...</span>
                <span v-else>清理全部</span>
              </button>
            </div>
          </div>

          <!-- 待审核的员工申请列表 -->
          <div v-if="managerNotifications.length > 0" class="notifications-list">
            <div
              v-for="notification in managerNotifications"
              :key="notification.id"
              class="notification-item employee-notification"
              :class="{
                'pending': notification.type === 'employee_registration_request' && notification.data.approvalStatus === 'pending_approval',
                'result': notification.type === 'employee_registration_result',
                'result-approved': notification.type === 'employee_registration_result' && notification.data.decision === 'approve',
                'result-rejected': notification.type === 'employee_registration_result' && notification.data.decision === 'reject'
              }"
            >
              <div class="notification-header">
                <div class="employee-name">{{ notification.data.employeeName }}</div>
                <div class="notification-time">{{ formatTime(notification.timestamp) }}</div>
                <div class="notification-actions">
                  <div class="status-badge" :class="getStatusClass(notification)">
                    {{ getEmployeeStatusText(notification) }}
                  </div>
                  <button @click="deleteManagerNotification(notification.id)" class="delete-btn" :disabled="loading">
                    删除
                  </button>
                </div>
              </div>

              <div class="notification-details">
                <div class="detail-row">
                  <span class="label">申请人：</span>
                  <span class="value">{{ notification.data.employeeName }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.username">
                  <span class="label">用户名：</span>
                  <span class="value">{{ notification.data.username }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.email">
                  <span class="label">邮箱：</span>
                  <span class="value">{{ notification.data.email }}</span>
                </div>
                <div class="detail-row" v-if="notification.data.enterpriseName">
                  <span class="label">申请加入：</span>
                  <span class="value">{{ notification.data.enterpriseName }}</span>
                </div>
              </div>

              <!-- 员工注册的文件部分 -->
              <div v-if="notification.data.files && notification.data.files.length > 0" class="files-section">
                <div class="files-header">上传文件</div>
                <div class="files-list">
                  <div v-for="file in notification.data.files" :key="file.filename" class="file-item-compact">
                    <div class="file-info-compact">
                      <span class="file-name">{{ file.filename }}</span>
                      <span class="file-type-tag">{{ getFileTypeText(file.type) }}</span>
                    </div>
                    <div class="file-actions-compact">
                      <button @click="downloadFile(file)" class="action-btn download" :disabled="downloading[file.filename]">
                        {{ downloading[file.filename] ? '下载中...' : '下载' }}
                      </button>
                      <button @click="previewFile(file)" class="action-btn preview" v-if="isImageFile(file.filename)">
                        预览
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 员工注册审核操作按钮 -->
              <div v-if="notification.type === 'employee_registration_request' && notification.data.approvalStatus === 'pending_approval'" class="approval-actions">
                <div class="comment-section">
                  <textarea
                    v-model="managerReviewComments[notification.id]"
                    placeholder="审核意见（可选）"
                    class="review-comment"
                    rows="2"
                  ></textarea>
                </div>
                <div class="action-buttons">
                  <button
                    @click="approveEmployeeRegistration(notification.id, 'approve')"
                    class="btn btn-approve"
                    :disabled="managerProcessing[notification.id]"
                  >
                    <span v-if="managerProcessing[notification.id]">处理中...</span>
                    <span v-else>通过</span>
                  </button>
                  <button
                    @click="approveEmployeeRegistration(notification.id, 'reject')"
                    class="btn btn-reject"
                    :disabled="managerProcessing[notification.id]"
                  >
                    <span v-if="managerProcessing[notification.id]">处理中...</span>
                    <span v-else>拒绝</span>
                  </button>
                </div>
              </div>

              <!-- 已审核的结果显示 -->
              <div v-else-if="notification.type === 'employee_registration_result'" class="review-result">
                <div class="result-message">
                  <strong>审核结果：</strong>{{ notification.data.decision === 'approve' ? '已通过' : '已拒绝' }}
                </div>
                <div v-if="notification.data.reviewComments" class="review-comments">
                  <strong>审核意见：</strong>{{ notification.data.reviewComments }}
                </div>
              </div>
            </div>
          </div>

          <!-- 无员工注册申请时的提示 -->
          <div v-else-if="!loading && isManager" class="no-notifications">
            <p>暂无员工注册申请</p>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>

        <!-- 错误提示 -->
        <div v-if="error" class="error-message">
          <p>{{ error }}</p>
          <button @click="refreshNotifications" class="retry-btn">重试</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
// 导入全局导航锁定管理器
import { navLockManager } from '@/services/NavLockManager'
// 导入退出按钮组件
import LogoutButton from '@/components/LogoutButton.vue'
// 导入账号设置相关组件
import RevisePassword from '@/components/RevisePassword.vue'
import RecogSecurityQuestions from '@/components/RecogSecurityQuestions.vue'

export default {
  name: 'Page3',
  components: {
    LogoutButton,
    RevisePassword,
    RecogSecurityQuestions
  },
  data() {
    return {
      userInfo: {},
      showChangePassword: false,
      showSecuritySettings: false,

      // Admin相关数据
      adminNotifications: [],
      adminReviewComments: {},
      adminProcessing: {},

      // Manager相关数据
      managerNotifications: [],
      managerReviewComments: {},
      managerProcessing: {},

      downloading: {},

      loading: false,
      error: null,
      refreshInterval: null
    }
  },
  computed: {
    userTypeText() {
      const typeMap = {
        'manager': '经理',
        'visitor': '员工',
        'admin': '管理员'
      }
      return typeMap[this.userInfo.userType] || '普通用户'
    },
    loginTime() {
      if (this.userInfo.loginTime) {
        return new Date(this.userInfo.loginTime).toLocaleString('zh-CN')
      }
      return '未知'
    },
    isAdmin() {
      return this.userInfo.userType === 'admin'
    },
    isManager() {
      return this.userInfo.userType === 'manager'
    },
    adminPendingCount() {
      return this.adminNotifications.filter(n => {
        return n.type === 'registration_request' &&
               n.data.approvalStatus === 'pending_approval'
      }).length
    },
    managerPendingCount() {
      return this.managerNotifications.filter(n => {
        return n.type === 'employee_registration_request' &&
               n.data.approvalStatus === 'pending_approval'
      }).length
    },
    // 是否显示返回按钮
    showBackButton() {
      // 只在RevisePassword或RecogSecurityQuestions页面显示返回按钮
      return this.showChangePassword || this.showSecuritySettings
    }
  },
  mounted() {
    // 更新导航锁定状态
    navLockManager.updateLocksByRoute()

    // 获取用户信息
    this.getUserInfo()

    // 根据用户类型获取通知并设置自动刷新
    if (this.isAdmin) {
      this.refreshAdminNotifications()
      this.startAutoRefresh('admin')
    } else if (this.isManager) {
      this.refreshManagerNotifications()
      this.startAutoRefresh('manager')
    }
  },
  beforeDestroy() {
    // 清除自动刷新定时器
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    getUserInfo() {
      // 获取用户信息
      const userInfoStr = sessionStorage.getItem('userInfo')
      const adminInfoStr = sessionStorage.getItem('adminInfo')

      if (userInfoStr) {
        this.userInfo = JSON.parse(userInfoStr)
      } else if (adminInfoStr) {
        this.userInfo = {
          ...JSON.parse(adminInfoStr),
          userType: 'admin'
        }
      } else {
        // 未登录，跳转到首页
        alert('请先登录！')
        this.$router.push('/')
      }
    },

    showPasswordChange() {
      this.showChangePassword = true
      this.showSecuritySettings = false
    },

    showSecurityQuestions() {
      this.showSecuritySettings = true
      this.showChangePassword = false
    },

    handleBackToMain() {
      this.showChangePassword = false
      this.showSecuritySettings = false
    },

    // 返回上一个组件（类似Page1.vue的goBack方法）
    goBack() {
      this.showChangePassword = false
      this.showSecuritySettings = false
    },

    // 获取文件类型显示文本
    getFileTypeText(fileType) {
      const typeMap = {
        'license': '营业执照',
        'idCard': '身份证',
        'businessLicense': '营业执照'
      }
      return typeMap[fileType] || '其他文件'
    },

    // Admin通知相关方法
    async refreshAdminNotifications() {
      if (!this.isAdmin) return

      this.loading = true
      this.error = null

      try {
        const response = await fetch(`/api/get-admin-notifications?admin_name=${encodeURIComponent(this.userInfo.username)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '获取通知失败')
        }

        if (data.success) {
          const allNotifications = data.data.notifications || []

          // 处理Admin通知逻辑（与原代码相同）
          const completedRegistrationIds = new Set()
          const pendingNotifications = []
          const resultNotifications = []

          allNotifications.forEach(notification => {
            if (notification.type === 'registration_result') {
              completedRegistrationIds.add(notification.id)
              resultNotifications.push(notification)
            } else if (notification.type === 'registration_request') {
              if (notification.data.approvalStatus === 'pending_approval') {
                pendingNotifications.push(notification)
              }
            }
          })

          const finalPendingNotifications = pendingNotifications.filter(notification => {
            return !completedRegistrationIds.has(notification.id)
          })

          this.adminNotifications = [
            ...finalPendingNotifications,
            ...resultNotifications.map(notification => ({
              ...notification,
              id: notification.id + '_result'
            }))
          ]

          // 初始化处理状态和评论
          this.adminNotifications.forEach(notification => {
            if (!this.adminProcessing[notification.id]) {
              this.adminProcessing[notification.id] = false
            }
            if (!this.adminReviewComments[notification.id]) {
              this.adminReviewComments[notification.id] = ''
            }
          })

        } else {
          throw new Error(data.message || '获取通知失败')
        }

      } catch (error) {
        console.error('获取管理员通知失败:', error)
        this.error = error.message || '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    async approveEnterpriseRegistration(registrationId, decision) {
      const actualRegistrationId = registrationId.replace('_result', '')
      this.adminProcessing[registrationId] = true

      try {
        const reviewComments = this.adminReviewComments[registrationId] || ''

        const response = await fetch('/api/approve-manager-registration', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            registrationId: actualRegistrationId,
            decision,
            reviewComments,
            reviewedBy: this.userInfo.username
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '审核操作失败')
        }

        if (data.success) {
          const actionText = decision === 'approve' ? '通过' : '拒绝'
          alert(`企业注册申请已${actionText}`)

          // 刷新通知列表
          await this.refreshAdminNotifications()

          // 清空该申请的评论
          this.adminReviewComments[registrationId] = ''
        } else {
          throw new Error(data.message || '审核操作失败')
        }

      } catch (error) {
        console.error('审核操作失败:', error)
        alert('审核操作失败: ' + error.message)
      } finally {
        this.adminProcessing[registrationId] = false
      }
    },

    async clearAllAdminNotifications() {
      if (!confirm('确定要清理所有通知吗？此操作不可恢复。')) {
        return
      }

      this.loading = true

      try {
        const response = await fetch('/api/clear-admin-notifications', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            admin_name: this.userInfo.username
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '清理失败')
        }

        if (data.success) {
          alert('所有通知已清理')
          this.adminNotifications = []
        } else {
          throw new Error(data.message || '清理失败')
        }

      } catch (error) {
        console.error('清理通知失败:', error)
        alert('清理失败: ' + error.message)
      } finally {
        this.loading = false
      }
    },

    async deleteAdminNotification(notificationId) {
      if (!confirm('确定要删除这条通知吗？')) {
        return
      }

      this.loading = true

      try {
        const response = await fetch('/api/clear-specific-notification', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            admin_name: this.userInfo.username,
            notification_id: notificationId
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '删除失败')
        }

        if (data.success) {
          alert('通知已删除')
          await this.refreshAdminNotifications()
        } else {
          throw new Error(data.message || '删除失败')
        }

      } catch (error) {
        console.error('删除通知失败:', error)
        alert('删除失败: ' + error.message)
      } finally {
        this.loading = false
      }
    },

    // Manager通知相关方法
    async refreshManagerNotifications() {
      if (!this.isManager) return

      this.loading = true
      this.error = null

      try {
        const response = await fetch(`/api/get-manager-notifications?manager_name=${encodeURIComponent(this.userInfo.username)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '获取员工注册通知失败')
        }

        if (data.success) {
          const allNotifications = data.data.notifications || []

          // 处理Manager通知逻辑
          const completedRegistrationIds = new Set()
          const pendingNotifications = []
          const resultNotifications = []

          allNotifications.forEach(notification => {
            if (notification.type === 'employee_registration_result') {
              completedRegistrationIds.add(notification.id)
              resultNotifications.push(notification)
            } else if (notification.type === 'employee_registration_request') {
              if (notification.data.approvalStatus === 'pending_approval') {
                pendingNotifications.push(notification)
              }
            }
          })

          const finalPendingNotifications = pendingNotifications.filter(notification => {
            return !completedRegistrationIds.has(notification.id)
          })

          this.managerNotifications = [
            ...finalPendingNotifications,
            ...resultNotifications.map(notification => ({
              ...notification,
              id: notification.id + '_result'
            }))
          ]

          // 初始化处理状态和评论
          this.managerNotifications.forEach(notification => {
            if (!this.managerProcessing[notification.id]) {
              this.managerProcessing[notification.id] = false
            }
            if (!this.managerReviewComments[notification.id]) {
              this.managerReviewComments[notification.id] = ''
            }
          })

        } else {
          throw new Error(data.message || '获取员工注册通知失败')
        }

      } catch (error) {
        console.error('获取Manager通知失败:', error)
        this.error = error.message || '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    async approveEmployeeRegistration(registrationId, decision) {
      const actualRegistrationId = registrationId.replace('_result', '')
      this.managerProcessing[registrationId] = true

      try {
        const reviewComments = this.managerReviewComments[registrationId] || ''

        const response = await fetch('/api/approve-employee-registration', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            registrationId: actualRegistrationId,
            decision,
            reviewComments,
            reviewedBy: this.userInfo.username
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '审核操作失败')
        }

        if (data.success) {
          const actionText = decision === 'approve' ? '通过' : '拒绝'
          alert(`员工注册申请已${actionText}`)

          // 刷新通知列表
          await this.refreshManagerNotifications()

          // 清空该申请的评论
          this.managerReviewComments[registrationId] = ''
        } else {
          throw new Error(data.message || '审核操作失败')
        }

      } catch (error) {
        console.error('审核操作失败:', error)
        alert('审核操作失败: ' + error.message)
      } finally {
        this.managerProcessing[registrationId] = false
      }
    },

    async clearAllManagerNotifications() {
      if (!confirm('确定要清理所有员工注册通知吗？此操作不可恢复。')) {
        return
      }

      this.loading = true

      try {
        const response = await fetch('/api/clear-manager-notifications', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            manager_name: this.userInfo.username
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '清理失败')
        }

        if (data.success) {
          alert('所有员工注册通知已清理')
          this.managerNotifications = []
        } else {
          throw new Error(data.message || '清理失败')
        }

      } catch (error) {
        console.error('清理通知失败:', error)
        alert('清理失败: ' + error.message)
      } finally {
        this.loading = false
      }
    },

    async deleteManagerNotification(notificationId) {
      if (!confirm('确定要删除这条员工注册通知吗？')) {
        return
      }

      this.loading = true

      try {
        const response = await fetch('/api/clear-specific-manager-notification', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            manager_name: this.userInfo.username,
            notification_id: notificationId
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || '删除失败')
        }

        if (data.success) {
          alert('员工注册通知已删除')
          await this.refreshManagerNotifications()
        } else {
          throw new Error(data.message || '删除失败')
        }

      } catch (error) {
        console.error('删除通知失败:', error)
        alert('删除失败: ' + error.message)
      } finally {
        this.loading = false
      }
    },

    // 通用方法
    refreshNotifications() {
      if (this.isAdmin) {
        this.refreshAdminNotifications()
      } else if (this.isManager) {
        this.refreshManagerNotifications()
      }
    },

    startAutoRefresh(userType) {
      // 每30秒自动刷新一次通知
      this.refreshInterval = setInterval(() => {
        if (userType === 'admin') {
          this.refreshAdminNotifications()
        } else if (userType === 'manager') {
          this.refreshManagerNotifications()
        }
      }, 30000)
    },

    formatTime(timestamp) {
      try {
        return new Date(timestamp).toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch {
        return '未知时间'
      }
    },

    getStatusClass(notification) {
      if (notification.type === 'registration_request' || notification.type === 'employee_registration_request') {
        return notification.data.approvalStatus || 'pending_approval'
      } else if (notification.type === 'registration_result' || notification.type === 'employee_registration_result') {
        return notification.data.decision === 'approve' ? 'approved' : 'rejected'
      }
      return 'unknown'
    },

    getStatusText(notification) {
      if (notification.type === 'registration_request') {
        const statusMap = {
          'pending_approval': '待审核',
          'approved': '已通过',
          'rejected': '已拒绝'
        }
        return statusMap[notification.data.approvalStatus] || '未知状态'
      } else if (notification.type === 'registration_result') {
        return notification.data.decision === 'approve' ? '已通过' : '已拒绝'
      }
      return '未知状态'
    },

    getEmployeeStatusText(notification) {
      if (notification.type === 'employee_registration_request') {
        const statusMap = {
          'pending_approval': '待审核',
          'approved': '已通过',
          'rejected': '已拒绝'
        }
        return statusMap[notification.data.approvalStatus] || '未知状态'
      } else if (notification.type === 'employee_registration_result') {
        return notification.data.decision === 'approve' ? '已通过' : '已拒绝'
      }
      return '未知状态'
    },

    async downloadFile(file) {
      if (!file || !file.filename || !file.path) {
        alert('文件信息不完整')
        return
      }

      // 设置下载状态
      this.downloading[file.filename] = true

      try {
        console.log('开始下载文件:', {
          filename: file.filename,
          path: file.path,
          userType: this.userInfo.userType,
          username: this.userInfo.username
        })

        const params = new URLSearchParams({
          file_path: file.path,
          file_name: file.filename,
          user_type: this.userInfo.userType,
          username: this.userInfo.username
        })

        const response = await fetch(`/download-registration-file?${params}`, {
          method: 'GET'
        })

        console.log('下载响应状态:', response.status)

        if (!response.ok) {
          let errorMessage = '下载失败'
          try {
            const errorData = await response.json()
            errorMessage = errorData.message || errorMessage
          } catch (e) {
            errorMessage = `HTTP错误: ${response.status}`
          }
          throw new Error(errorMessage)
        }

        // 创建下载链接
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = file.filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)

        console.log('文件下载成功:', file.filename)

      } catch (error) {
        console.error('下载文件失败:', error)
        alert('下载失败: ' + error.message)
      } finally {
        this.downloading[file.filename] = false
      }
    },

    // === 修复后的图片预览方法 ===

    // 验证图片URL是否有效
    validateImageUrl(url) {
      return new Promise((resolve) => {
        const img = new Image()

        img.onload = () => {
          console.log('图片加载成功')
          resolve(true)
        }

        img.onerror = () => {
          console.error('图片加载失败:', url)
          resolve(false)
        }

        // 设置超时
        setTimeout(() => {
          console.error('图片加载超时:', url)
          resolve(false)
        }, 10000) // 10秒超时

        img.src = url
      })
    },

    // 显示图片预览模态框
    async showImagePreviewModal(imageUrl, filename) {
      try {
        // 先测试图片是否能正确加载
        const isValidImage = await this.validateImageUrl(imageUrl)

        if (!isValidImage) {
          throw new Error('图片加载失败，请检查文件是否存在或网络连接')
        }

        // 创建模态框HTML
        const modalHtml = `
          <div id="imagePreviewModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            cursor: pointer;
          " onclick="this.remove()">
            <div style="
              max-width: 90vw;
              max-height: 90vh;
              background: white;
              border-radius: 8px;
              padding: 20px;
              position: relative;
              cursor: default;
            " onclick="event.stopPropagation()">
              <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
              ">
                <h3 style="margin: 0; color: #333;">${filename}</h3>
                <button onclick="document.getElementById('imagePreviewModal').remove()" style="
                  background: #ff4757;
                  color: white;
                  border: none;
                  border-radius: 4px;
                  padding: 5px 10px;
                  cursor: pointer;
                  font-size: 14px;
                ">关闭</button>
              </div>
              <div style="text-align: center;">
                <img src="${imageUrl}" style="
                  max-width: 100%;
                  max-height: 70vh;
                  object-fit: contain;
                  border-radius: 4px;
                  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                " alt="图片预览" />
              </div>
            </div>
          </div>
        `

        // 移除已存在的模态框
        const existingModal = document.getElementById('imagePreviewModal')
        if (existingModal) {
          existingModal.remove()
        }

        // 添加模态框到页面
        document.body.insertAdjacentHTML('beforeend', modalHtml)

      } catch (error) {
        console.error('显示预览模态框失败:', error)
        alert('图片预览失败: ' + error.message)
      }
    },

    // 使用fetch获取图片数据然后显示（更可靠的方法）
    async showImagePreviewWithFetch(file) {
      try {
        const params = new URLSearchParams({
          file_path: file.path,
          file_name: file.filename,
          user_type: this.userInfo.userType,
          username: this.userInfo.username,
          timestamp: Date.now() // 防止缓存
        })

        console.log('开始获取图片数据...')
        console.log('请求URL:', `/preview-registration-file?${params}`)

        const response = await fetch(`/preview-registration-file?${params}`)

        console.log('响应状态:', response.status)
        console.log('响应头Content-Type:', response.headers.get('Content-Type'))

        if (!response.ok) {
          let errorMessage = '获取图片失败'
          try {
            const errorData = await response.json()
            errorMessage = errorData.message || errorMessage
          } catch (e) {
            errorMessage = `HTTP错误: ${response.status}`
          }
          throw new Error(errorMessage)
        }

        const blob = await response.blob()
        console.log('Blob大小:', blob.size, 'bytes')
        console.log('Blob类型:', blob.type)

        if (blob.size === 0) {
          throw new Error('图片文件为空')
        }

        // 检查MIME类型
        if (!blob.type.startsWith('image/')) {
          throw new Error('返回的不是图片文件，类型: ' + blob.type)
        }

        // 创建blob URL并显示
        const blobUrl = URL.createObjectURL(blob)
        console.log('创建Blob URL:', blobUrl)

        // 使用模态框显示
        await this.showImagePreviewModal(blobUrl, file.filename)

        // 清理blob URL（延迟清理给图片足够时间加载）
        setTimeout(() => {
          URL.revokeObjectURL(blobUrl)
          console.log('Blob URL已清理')
        }, 60000) // 1分钟后清理

      } catch (error) {
        console.error('获取图片数据失败:', error)
        alert('图片预览失败: ' + error.message)
      }
    },

    // 主要的预览文件入口函数（完全替换原来的方法）
    async previewFile(file) {
      if (!file || !file.filename || !file.path) {
        alert('文件信息不完整')
        return
      }

      if (!this.isImageFile(file.filename)) {
        alert('只支持预览图片文件')
        return
      }

      console.log('=== 开始图片预览 ===')
      console.log('文件信息:', {
        filename: file.filename,
        path: file.path,
        userType: this.userInfo.userType,
        username: this.userInfo.username
      })

      // 使用更可靠的fetch方式获取并预览图片
      await this.showImagePreviewWithFetch(file)
    },

    isImageFile(filename) {
      if (!filename) return false
      const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
      const extension = filename.toLowerCase()
      return imageExtensions.some(ext => extension.endsWith(ext))
    },

    // 调试方法：打印文件信息
    debugFileInfo(file) {
      console.log('文件调试信息:', {
        filename: file.filename,
        path: file.path,
        type: file.type,
        userInfo: this.userInfo
      })
    }
  }
}
</script>

<style scoped>
.page3-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

/* 返回按钮样式 - 改为相对定位 */
.back-button-wrapper {
  position: relative;
  margin: 20px 0 -10px 20px; /* 向上挪动通过负margin实现 */
  z-index: 999;
  display: inline-block;
}

.global-back-btn {
  padding: 12px 28px;
  background: white;
  color: var(--color-primary);
  border: 2px solid var(--color-primary-light);
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.global-back-btn:hover {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 添加进入动画 */
.back-button-wrapper {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding: 24px 32px;
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.page-header h1 {
  margin: 0;
  color: var(--color-text);
  font-size: 2rem;
}

/* 页面内容 */
.page-content {
  max-width: 1200px;
  margin: 0 auto;
}

/* 用户信息和账号设置容器 */
.info-settings-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

/* 通用卡片样式 */
.card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

/* 用户信息卡片 */
.user-info-card h2,
.settings-card h2 {
  margin-bottom: 24px;
  color: var(--color-text);
  font-size: 1.5rem;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}

.info-item:last-child {
  border-bottom: none;
}

.info-item label {
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-right: 16px;
  min-width: 100px;
}

.info-item span {
  color: var(--color-text);
  font-size: 16px;
}

/* 设置卡片 */
.settings-card {
  display: flex;
  flex-direction: column;
}

.settings-card h2 {
  margin-bottom: 24px;
}

.settings-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-btn {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: left;
  width: 100%;
}

.setting-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
  transform: translateX(2px);
}

.setting-icon {
  font-size: 32px;
  min-width: 48px;
  text-align: center;
}

.setting-info {
  flex: 1;
}

.setting-info h3 {
  margin: 0 0 4px 0;
  color: #1e293b;
  font-size: 16px;
  font-weight: 600;
}

.setting-info p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.arrow {
  color: #94a3b8;
  font-size: 20px;
  font-weight: bold;
}

/* 注册管理卡片 */
.registration-management-card,
.employee-management-card {
  margin-top: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e6f2ff;
}

.card-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  gap: 12px;
}

.notification-badge {
  background: #ef4444;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.refresh-btn, .clear-btn {
  padding: 8px 16px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.clear-btn {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

.refresh-btn:hover:not(:disabled) {
  background: #e2e8f0;
}

.clear-btn:hover:not(:disabled) {
  background: #fecaca;
}

.refresh-btn:disabled, .clear-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 通知列表 */
.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.notification-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s;
}

.notification-item.pending {
  border-left: 4px solid #3b82f6;
  background: #f0f9ff;
}

.notification-item.result {
  border-left: 4px solid #10b981;
  background: #f0fdf4;
}

.notification-item.result-rejected {
  border-left-color: #ef4444;
  background: #fef2f2;
}

/* 企业通知特殊样式 */
.enterprise-notification.pending {
  border-left-color: #8b5cf6;
  background: #faf5ff;
}

/* 员工通知特殊样式 */
.employee-notification.pending {
  border-left-color: #06b6d4;
  background: #ecfeff;
}

.notification-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.notification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.company-name, .employee-name {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.notification-time {
  font-size: 12px;
  color: #64748b;
}

.notification-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.pending_approval {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.approved {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.rejected {
  background: #fee2e2;
  color: #991b1b;
}

.delete-btn {
  padding: 4px 8px;
  background: #fee2e2;
  color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.delete-btn:hover:not(:disabled) {
  background: #fecaca;
}

.delete-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.notification-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-row .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.detail-row .value {
  font-size: 14px;
  color: #1e293b;
  word-break: break-all;
}

/* 新的文件显示样式 - 更紧凑 */
.files-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.files-header {
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 6px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.file-item-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.file-item-compact:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.file-info-compact {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.file-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.file-name {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.file-type-tag {
  font-size: 11px;
  color: #0369a1;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 12px;
  flex-shrink: 0;
}

.file-actions-compact {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.action-btn {
  padding: 3px 10px;
  border: none;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn.download {
  background: #e0f2fe;
  color: #0369a1;
}

.action-btn.download:hover:not(:disabled) {
  background: #bae6fd;
}

.action-btn.preview {
  background: #dcfce7;
  color: #047857;
}

.action-btn.preview:hover {
  background: #bbf7d0;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 审核操作 */
.approval-actions {
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
}

.comment-section {
  margin-bottom: 12px;
}

.review-comment {
  width: 100%;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
  min-height: 60px;
}

.review-comment:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-approve {
  background: #10b981;
  color: white;
}

.btn-approve:hover:not(:disabled) {
  background: #059669;
}

.btn-reject {
  background: #ef4444;
  color: white;
}

.btn-reject:hover:not(:disabled) {
  background: #dc2626;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 审核结果 */
.review-result {
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
}

.result-message {
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 8px;
}

.review-comments {
  font-size: 14px;
  color: #64748b;
  font-style: italic;
  margin-bottom: 8px;
}

/* 空状态 */
.no-notifications {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: #64748b;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 错误状态 */
.error-message {
  text-align: center;
  padding: 20px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 6px;
  margin: 16px 0;
}

.retry-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-btn:hover {
  background: #b91c1c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .back-button-wrapper {
    margin: 15px 0 -8px 10px;
  }

  .global-back-btn {
    padding: 10px 20px;
    font-size: 14px;
  }

  .page-header {
    flex-direction: column;
    gap: 20px;
    padding: 20px;
    text-align: center;
  }

  .page-header h1 {
    font-size: 1.5rem;
  }

  /* 在小屏幕上，用户信息和账号设置垂直排列 */
  .info-settings-container {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .notification-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .notification-actions {
    width: 100%;
    justify-content: space-between;
  }

  .notification-details {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }

  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .info-item label {
    margin-bottom: 8px;
  }

  /* 移动端文件显示适配 */
  .file-item-compact {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 10px;
  }

  .file-info-compact {
    width: 100%;
  }

  .file-name {
    max-width: none;
    flex: 1;
  }

  .file-actions-compact {
    width: 100%;
    display: flex;
    gap: 8px;
  }

  .action-btn {
    flex: 1;
  }
}

/* 小屏幕优化 */
@media (max-width: 480px) {
  .back-button-wrapper {
    margin: 10px 0 -5px 10px;
  }

  .global-back-btn {
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>

<!-- 全局样式，用于导航锁定效果 -->
<style>
/* 全局导航锁定样式 */
.nav-locked-element {
  background: transparent !important;
  transform: none !important;
  box-shadow: none !important;
}

.nav-locked-element:hover {
  background: transparent !important;
  color: #ccc !important;
  transform: none !important;
  text-decoration: none !important;
}

/* 确保锁定图标显示 */
.lock-icon {
  pointer-events: none !important;
  user-select: none !important;
}
</style>