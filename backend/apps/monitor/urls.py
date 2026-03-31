# backend/apps/monitor/urls.py

from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    # 页面路由 (如果Django也负责部分页面渲染)
    path('dashboard/', views.violations_dashboard, name='violations_dashboard'),

    # 设备仓库相关路由
    path('warehouses/', views.get_warehouses, name='get_warehouses'),
    path('warehouses/create/', views.create_warehouse, name='create_warehouse'),
    path('warehouses/<int:warehouse_id>/', views.get_warehouse_detail, name='get_warehouse_detail'),
    path('warehouses/<int:warehouse_id>/delete/', views.delete_warehouse, name='delete_warehouse'),
    path('warehouses/<int:warehouse_id>/files/', views.get_warehouse_files, name='get_warehouse_files'),
    path('warehouses/upload/', views.upload_files, name='upload_files'),
    path('files/<int:file_id>/content/', views.get_file_content, name='get_file_content'),
    path('files/<int:file_id>/delete/', views.delete_file, name='delete_file'),
    path('warehouses/<int:warehouse_id>/update-name/', views.update_warehouse_name, name='update_warehouse_name'),
    path('warehouses/by-eid/', views.get_warehouses_by_eid, name='get_warehouses_by_eid'),

    # 违规数据相关路由
    path('violations/by-eid/', views.get_violations_by_eid, name='violations_by_eid'),
    path('violations/analytics/', views.violations_analytics, name='violations_analytics'),
    path('violations/save/', views.save_violation_record, name='save_violation_record'),
    path('violations/list/', views.violations_list, name='violations_list'),
    path('violations/record/<int:record_id>/analyze/', views.analyze_violation_record, name='analyze_violation_record'),
    path('violations/stats/', views.violations_stats, name='violations_stats'),
    path('violations/clear/', views.clear_violations, name='clear_violations'),
    path('violations/batch-upload/', views.batch_upload_violations, name='batch_upload_violations'),
    path('violations/export/', views.export_violations_data, name='export_violations_data'),
    path('violations/trends/', views.get_violation_trends, name='get_violation_trends'),
    path('violations/unified/', views.get_unified_violations_data, name='unified_violations_data'),

    # AI查询相关
    path('ai-query/', views.ai_query, name='ai_query'),
    path('ai-query/history/', views.ai_query_history, name='ai_query_history'),

    # 系统相关
    path('health/', views.system_health, name='system_health'),
    path('status/', views.system_status, name='system_status'),

    # 权限申请相关路由
    path('permission/requests/', views.get_permission_requests, name='get_permission_requests'),
    path('permission/approve/', views.approve_permission_request, name='approve_permission_request'),
    path('submit-permission/', views.submit_permission_request, name='submit_permission_request'),
    path('check-file-exists/', views.check_file_exists, name='check_file_exists'),
    path('permission/my-requests/', views.get_my_permission_requests, name='get_my_permission_requests'),

    # WebRTC相关API
    path('permission/verify-token/', views.verify_access_token, name='verify_access_token'),
    path('online-status/', views.get_online_status, name='get_online_status'),
    path('online-users/', views.get_all_online_users, name='get_all_online_users'),

    # 日期文件访问相关
    path('permission/files-by-date/', views.get_files_by_date, name='get_files_by_date'),
    path('permission/available-dates/', views.get_available_dates, name='get_available_dates'),

    # employee历史数据分析
    path('visitor/authorized-data/', views.get_visitor_authorized_data, name='get_visitor_authorized_data'),

    # employee AI查询路由
    path('visitor/ai-query/', views.visitor_ai_query, name='visitor_ai_query'),

    # Admin令牌管理相关路由
    path('admin/generate-token/', views.admin_generate_token, name='admin_generate_token'),
    path('admin/list-tokens/', views.admin_list_tokens, name='admin_list_tokens'),
    path('admin/delete-token/', views.admin_delete_token, name='admin_delete_token'),
    path('admin/revoke-token/', views.admin_revoke_token, name='admin_revoke_token'),
]