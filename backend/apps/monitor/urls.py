# backend/apps/monitor/urls.py

from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    # 页面路由 (如果Django也负责部分页面渲染)
    path('dashboard/', views.violations_dashboard, name='violations_dashboard'),

    path('violations/analytics/', views.violations_analytics, name='violations_analytics'),
    path('violations/save/', views.save_violation_record, name='save_violation_record'),
    path('violations/list/', views.violations_list, name='violations_list'),
    path('violations/record/<int:record_id>/analyze/', views.analyze_violation_record, name='analyze_violation_record'),
    path('violations/stats/', views.violations_stats, name='violations_stats'),
    path('violations/clear/', views.clear_violations, name='clear_violations'),
    path('violations/batch-upload/', views.batch_upload_violations, name='batch_upload_violations'),
    path('violations/export/', views.export_violations_data, name='export_violations_data'),
    path('violations/trends/', views.get_violation_trends, name='get_violation_trends'),

    # AI查询相关
    path('ai-query/', views.ai_query, name='ai_query'),
    path('ai-query/history/', views.ai_query_history, name='ai_query_history'),

    # 系统相关
    path('health/', views.system_health, name='system_health'),
    path('status/', views.system_status, name='system_status'),
]