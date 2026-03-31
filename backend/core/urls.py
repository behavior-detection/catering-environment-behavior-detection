"""
URL configuration for backend project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/monitor/', include('apps.monitor.urls')),

    #  实时检测API
    path('api/detection/', include('detection.urls')),

    # 认证相关路由
    path("", include("apps.login.authentication.urls")),

    # API路由
    path("api/", include("apps.login.api.urls")),  # 所有api.urls中的路径都会加上/api/前缀

    # 但是有些路径不需要/api/前缀，需要单独配置
    path("", include("apps.login.api.urls_no_prefix")),  # 创建一个新的urls文件用于不需要api前缀的路径

    # 人脸识别路由
    path("", include("apps.login.face_recognition.urls")),

    # Vue前端路由支持
    path('monitor-live/', TemplateView.as_view(template_name='index.html'), name='monitor_live'),
    path('device-management/', TemplateView.as_view(template_name='index.html'), name='device_management'),
    path('find-device/', TemplateView.as_view(template_name='index.html'), name='find_device'),
    path('feedback-report/', TemplateView.as_view(template_name='index.html'), name='feedback_report'),
    path('historical-data/', TemplateView.as_view(template_name='index.html'), name='historical_data'),
]

# 开发环境静态文件和媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # 添加企业档案目录服务
    urlpatterns += static('/enterprise_archives/', document_root=settings.ENTERPRISE_ARCHIVES_ROOT)

    # 如果有员工档案目录，也添加
    if hasattr(settings, 'EMPLOYEE_ARCHIVES_ROOT'):
        urlpatterns += static('/employee_archives/', document_root=settings.EMPLOYEE_ARCHIVES_ROOT)

    if hasattr(settings, 'FACE_IMAGES_ROOT'):
        urlpatterns += static('/face-images/', document_root=settings.FACE_IMAGES_ROOT)