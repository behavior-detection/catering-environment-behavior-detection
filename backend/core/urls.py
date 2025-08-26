# backend/core/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/monitor/', include('apps.monitor.urls')),
    path('api/login/', include('apps.login.urls')),

    # Vue前端路由支持
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('monitor-live/', TemplateView.as_view(template_name='index.html'), name='monitor_live'),
    path('device-management/', TemplateView.as_view(template_name='index.html'), name='device_management'),
    path('find-device/', TemplateView.as_view(template_name='index.html'), name='find_device'),
    path('feedback-report/', TemplateView.as_view(template_name='index.html'), name='feedback_report'),
    path('historical-data/', TemplateView.as_view(template_name='index.html'), name='historical_data'),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)