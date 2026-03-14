from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # 添加 views. 前缀
    path('visitor_login', views.visitor_login, name='visitor_login'),
    path('manager_login', views.manager_login, name='manager_login'),
    path('admin_login', views.admin_login, name='admin_login'),
    path('api/visitor-register', views.visitor_register, name='visitor_register'),
    path('api/send-verification-code', views.send_verification_code, name='send_verification_code'),
    path('api/verify-code', views.verify_code, name='verify_code'),
    path('get-security-questions', views.get_security_questions, name='get_security_questions'),
    path('verify-security-answers', views.verify_security_answers, name='verify_security_answers'),
    path('reset-password', views.reset_password, name='reset_password'),
    path('api/check-username', views.check_username, name='check_username'),
    path('api/verify-user-email', views.verify_user_email, name='verify_user_email'),
    path('api/check-visitor-username', views.check_visitor_username, name='check_visitor_username'),
    path('api/check-manager-username', views.check_manager_username, name='check_manager_username'),
    path('api/check-admin-username', views.check_admin_username, name='check_admin_username'),
    path('verify-security-answers', views.verify_security_answers, name='verify_security_answers'),
]