"""
URL configuration for backend project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/monitor/', include('apps.monitor.urls')),
    path('api/detection/', include('detection.urls')),
    path("", include("apps.login.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static('/enterprise_archives/', document_root=settings.ENTERPRISE_ARCHIVES_ROOT)

    if hasattr(settings, 'EMPLOYEE_ARCHIVES_ROOT'):
        urlpatterns += static('/employee_archives/', document_root=settings.EMPLOYEE_ARCHIVES_ROOT)

    if hasattr(settings, 'FACE_IMAGES_ROOT'):
        urlpatterns += static('/face-images/', document_root=settings.FACE_IMAGES_ROOT)