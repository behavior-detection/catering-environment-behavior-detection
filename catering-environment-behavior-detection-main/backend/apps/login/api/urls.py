from django.urls import path
from . import views

urlpatterns = [
    path('system/health', views.system_health, name='system_health'),
    path('ocr-idcard', views.ocr_idcard, name='ocr_idcard'),
    path('check-enterprise', views.check_enterprise, name='check_enterprise'),
    path('save-employee-verification', views.save_employee_verification, name='save_employee_verification'),
    path('save-license-file', views.save_license_file, name='save_license_file'),
]