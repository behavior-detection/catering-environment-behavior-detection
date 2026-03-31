from django.urls import path
from . import views

# 这些路径不需要 /api/ 前缀
urlpatterns = [
    # 系统健康检查
    path('system/health', views.system_health, name='system_health'),

    # OCR相关 - 文件上传类接口
    path('ocr-idcard', views.ocr_idcard, name='ocr_idcard'),
    path('ocr-business-license', views.ocr_business_license, name='ocr_business_license'),

    # 企业相关检查
    path('check-enterprise', views.check_enterprise, name='check_enterprise'),

    # 文件保存相关 - 所有文件上传接口
    path('save-employee-verification', views.save_employee_verification, name='save_employee_verification'),
    path('save-license-file', views.save_license_file, name='save_license_file'),
    path('save-legal-representative-id', views.save_legal_representative_id, name='save_legal_representative_id'),
    path('save-employee-verification-data', views.save_employee_verification_data,
         name='save_employee_verification_data'),

    #  统一文件保存接口
    path('save-registration-file', views.save_registration_file, name='save_registration_file'),

    # 密码重置相关
    path('reset-password-email', views.reset_password_email, name='reset_password_email'),

    # 文件下载和预览
    path('download-registration-file', views.download_registration_file, name='download_registration_file'),
    path('preview-registration-file', views.preview_registration_file, name='preview_registration_file'),

    # 这些端点在前端直接调用时没有/api前缀的备用版本
    path('verify-user-email', views.verify_user_email, name='verify_user_email_no_prefix'),
    path('check-manager-username', views.check_manager_username, name='check_manager_username_no_prefix'),
    path('check-visitor-username', views.check_visitor_username, name='check_visitor_username_no_prefix'),
]