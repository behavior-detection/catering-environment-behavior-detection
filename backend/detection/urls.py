# In backend/detection/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import StartDetectionAPI

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'video-sources', views.VideoSourceViewSet, basename='videosource')
router.register(r'roi-polygons', views.ROIPolygonViewSet, basename='roipolygon')
router.register(r'detection-settings', views.DetectionSettingViewSet, basename='detection-setting')
router.register(r'violation-events', views.ViolationEventViewSet, basename='violation-event')

urlpatterns = [
    path('', include(router.urls)),

    path('video-sources/<int:source_id>/start-detection/', StartDetectionAPI.as_view(), name='start-detection-api'),

    # JSON文件管理API
    path('json-files/<int:source_id>/', views.get_detection_json_files, name='get-json-files'),
    path('json-files/<int:source_id>/save/', views.save_selected_json_files, name='save-json-files'),
    path('json-files/<int:source_id>/delete-all/', views.delete_all_json_files, name='delete-all-json-files'),
]