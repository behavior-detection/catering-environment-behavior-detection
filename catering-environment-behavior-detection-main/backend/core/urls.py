"""
URL configuration for backend project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # 应用路由
    path("api/monitor/", include("monitor.urls")),           # 原有应用路由
    path("", include("authentication.urls")),                # 认证路由
    path("face/", include("face_recognition.urls")),         # 人脸识别路由
    path("api/", include("api.urls")),                      # API路由
]

# 开发环境静态文件和媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # 人脸图片特殊路由
    if hasattr(settings, 'FACE_IMAGES_ROOT'):
        urlpatterns += static('/face-images/', document_root=settings.FACE_IMAGES_ROOT)