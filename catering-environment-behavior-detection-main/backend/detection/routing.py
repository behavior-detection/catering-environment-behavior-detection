from django.urls import re_path
from . import consumers
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

websocket_urlpatterns = [
    re_path(r'ws/video/(?P<source_id>\w+)/$', consumers.VideoStreamConsumer.as_asgi()),
    re_path(r'ws/violations/(?P<source_id>\w+)/$', consumers.ViolationConsumer.as_asgi()),
    re_path(r'ws/violations/$', consumers.ViolationConsumer.as_asgi()),
]

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'video-sources', views.VideoSourceViewSet, basename='videosource')
router.register(r'roi-polygons', views.ROIPolygonViewSet, basename='roipolygon')
router.register(r'detection-settings', views.DetectionSettingViewSet, basename='detection-setting')
router.register(r'violation-events', views.ViolationEventViewSet, basename='violation-event')

urlpatterns = [
    path('', include(router.urls)),

    # ========== 新增：JSON文件管理API ==========
    # 获取某个视频源的JSON文件列表
    path('json-files/<str:source_id>/',
         views.get_detection_json_files,
         name='get-json-files'),

    # 保存选中的JSON文件（删除未选中的）
    path('json-files/<str:source_id>/save/',
         views.save_selected_json_files,
         name='save-json-files'),

    # 删除所有JSON文件
    path('json-files/<str:source_id>/delete-all/',
         views.delete_all_json_files,
         name='delete-all-json'),
]