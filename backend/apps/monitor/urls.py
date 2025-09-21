# apps/monitor/urls.py - 最终清理版

from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    # --- 新架构的核心接口 ---
    path('dashboard/', views.violations_dashboard, name='violations_dashboard'),
    path('ai-query/smart/', views.smart_ai_query, name='smart_ai_query'),
    path('ai-query/routing-status/', views.routing_system_status, name='routing_system_status'),

    # --- HistoricalData.vue 所需的数据API ---
    path('violations/analytics/', views.violations_analytics, name='violations_analytics'),
    path('violations/list/', views.violations_list, name='violations_list'),
    path('violations/stats/', views.violations_stats, name='violations_stats'),
    path('violations/trends/', views.get_violation_trends, name='get_violation_trends'),
    path('violations/clear/', views.clear_violations, name='clear_violations'),
    path('violations/record/<int:record_id>/analyze/', views.analyze_violation_record, name='analyze_violation_record'),
]