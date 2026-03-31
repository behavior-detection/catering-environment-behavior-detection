from django.urls import path
from apps.login.authentication import views as auth_views
from apps.login.api import views as api_views
from apps.login.face_recognition import views as face_views

urlpatterns = [
    # ===================== 页面入口 =====================
    path('', auth_views.index, name='index'),

    # ===================== 登录 =====================
    path('visitor_login', auth_views.visitor_login, name='visitor_login'),
    path('manager_login', auth_views.manager_login, name='manager_login'),
    path('admin_login', auth_views.admin_login, name='admin_login'),

    # ===================== 邮箱验证 =====================
    path('api/send-verification-code', auth_views.send_verification_code, name='send_verification_code'),
    path('api/verify-code', auth_views.verify_code, name='verify_code'),
    path('api/verify-user-email', auth_views.verify_user_email, name='verify_user_email'),

    # ===================== 用户名检查 =====================
    path('api/check-username', auth_views.check_username, name='check_username'),
    path('api/check-manager-username', auth_views.check_manager_username, name='check_manager_username'),
    path('api/check-visitor-username', auth_views.check_visitor_username, name='check_visitor_username'),
    path('api/check-admin-username', auth_views.check_admin_username, name='check_admin_username'),

    # ===================== 注册 =====================
    path('api/visitor-register', auth_views.visitor_register, name='visitor_register'),
    path('api/user-register', api_views.user_register, name='user_register'),

    # ===================== 企业注册管理 =====================
    path('api/save-manager-registration-cache', api_views.save_manager_registration_cache,
         name='save_manager_registration_cache'),
    path('api/get-pending-manager-registrations', api_views.get_pending_manager_registrations,
         name='get_pending_manager_registrations'),
    path('api/approve-manager-registration', api_views.approve_manager_registration,
         name='approve_manager_registration'),
    path('api/create-enterprise-archive', api_views.create_enterprise_archive,
         name='create_enterprise_archive'),

    # ===================== 员工注册管理 =====================
    path('api/save-employee-registration-cache', api_views.save_employee_registration_cache,
         name='save_employee_registration_cache'),
    path('api/approve-employee-registration', api_views.approve_employee_registration,
         name='approve_employee_registration'),

    # ===================== 通知管理 =====================
    path('api/get-admin-notifications', api_views.get_admin_notifications, name='get_admin_notifications'),
    path('api/clear-admin-notifications', api_views.clear_admin_notifications, name='clear_admin_notifications'),
    path('api/clear-specific-notification', api_views.clear_specific_notification,
         name='clear_specific_notification'),
    path('api/get-manager-notifications', api_views.get_manager_notifications, name='get_manager_notifications'),
    path('api/clear-manager-notifications', api_views.clear_manager_notifications,
         name='clear_manager_notifications'),
    path('api/clear-specific-manager-notification', api_views.clear_specific_manager_notification,
         name='clear_specific_manager_notification'),

    # ===================== 密码与密保 (Page3 账号管理) =====================
    path('api/change-password', api_views.change_password, name='change_password'),
    path('api/check-security-status', api_views.check_security_status, name='check_security_status'),
    path('api/set-security-questions', api_views.set_security_questions, name='set_security_questions'),
    path('api/verify-security-answers', api_views.verify_security_answers, name='api_verify_security_answers'),
    path('api/reset-security-questions', api_views.reset_security_questions, name='reset_security_questions'),

    # ===================== 密码重置流程 (Page1 忘记密码) =====================
    path('get-security-questions', auth_views.get_security_questions, name='get_security_questions'),
    path('verify-security-answers', auth_views.verify_security_answers, name='verify_security_answers'),
    path('reset-password', auth_views.reset_password, name='reset_password'),
    path('reset-password-email', api_views.reset_password_email, name='reset_password_email'),

    # ===================== OCR =====================
    path('ocr-idcard', api_views.ocr_idcard, name='ocr_idcard'),
    path('ocr-business-license', api_views.ocr_business_license, name='ocr_business_license'),

    # ===================== 企业检查 =====================
    path('check-enterprise', api_views.check_enterprise, name='check_enterprise'),

    # ===================== 系统健康 =====================
    path('system/health', api_views.system_health, name='system_health'),

    # ===================== 文件保存 =====================
    path('save-employee-verification', api_views.save_employee_verification, name='save_employee_verification'),
    path('save-license-file', api_views.save_license_file, name='save_license_file'),
    path('save-legal-representative-id', api_views.save_legal_representative_id,
         name='save_legal_representative_id'),
    path('save-employee-verification-data', api_views.save_employee_verification_data,
         name='save_employee_verification_data'),
    path('save-registration-file', api_views.save_registration_file, name='save_registration_file'),

    # ===================== 文件下载与预览 =====================
    path('download-registration-file', api_views.download_registration_file, name='download_registration_file'),
    path('preview-registration-file', api_views.preview_registration_file, name='preview_registration_file'),

    # ===================== 人脸识别 =====================
    path('api/verify_face', face_views.verify_face, name='verify_face'),
    path('api/registered_users', face_views.get_registered_users, name='get_registered_users'),
    path('api/reload_database', face_views.reload_database, name='reload_database'),

    # ===================== 无前缀备用路由 =====================
    path('verify-user-email', api_views.verify_user_email, name='verify_user_email_no_prefix'),
    path('check-manager-username', api_views.check_manager_username, name='check_manager_username_no_prefix'),
    path('check-visitor-username', api_views.check_visitor_username, name='check_visitor_username_no_prefix'),
]