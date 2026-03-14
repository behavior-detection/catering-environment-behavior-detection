from django.urls import path
from . import views

# 这些路径会自动加上 /api/ 前缀
urlpatterns = [
    # 邮箱验证相关
    path('send-verification-code', views.send_verification_code, name='api_send_verification_code'),
    path('verify-code', views.verify_code, name='api_verify_code'),

    # 用户名检查
    path('check-username', views.check_username, name='api_check_username'),
    path('check-manager-username', views.check_manager_username, name='api_check_manager_username'),
    path('check-visitor-username', views.check_visitor_username, name='api_check_visitor_username'),

    # 用户注册
    path('visitor-register', views.visitor_register, name='api_visitor_register'),
    path('user-register', views.user_register, name='api_user_register'),

    # 企业注册管理
    path('save-manager-registration-cache', views.save_manager_registration_cache,
         name='save_manager_registration_cache'),
    path('get-pending-manager-registrations', views.get_pending_manager_registrations,
         name='get_pending_manager_registrations'),
    path('approve-manager-registration', views.approve_manager_registration, name='approve_manager_registration'),

    # 管理员通知
    path('get-admin-notifications', views.get_admin_notifications, name='get_admin_notifications'),

    # 企业档案创建
    path('create-enterprise-archive', views.create_enterprise_archive, name='create_enterprise_archive'),

    # 邮箱验证
    path('verify-user-email', views.verify_user_email, name='api_verify_user_email'),

    # 非企业代表人经理注册
    path('save-employee-registration-cache', views.save_employee_registration_cache,
         name='save_employee_registration_cache'),
    path('approve-employee-registration', views.approve_employee_registration, name='approve_employee_registration'),

    # 企业管理员通知管理
    path('get-manager-notifications', views.get_manager_notifications, name='get_manager_notifications'),
    path('clear-manager-notifications', views.clear_manager_notifications, name='clear_manager_notifications'),
    path('clear-specific-manager-notification', views.clear_specific_manager_notification,
         name='clear_specific_manager_notification'),

    # 密码和密保相关
    path('change-password', views.change_password, name='change_password'),
    path('check-security-status', views.check_security_status, name='check_security_status'),
    path('set-security-questions', views.set_security_questions, name='set_security_questions'),
    path('verify-security-answers', views.verify_security_answers, name='verify_security_answers'),
    path('reset-security-questions', views.reset_security_questions, name='reset_security_questions'),

    # 清理多余的通知
    path('clear-admin-notifications', views.clear_admin_notifications, name='clear_admin_notifications'),
    path('clear-specific-notification', views.clear_specific_notification, name='clear_specific_notification'),
]