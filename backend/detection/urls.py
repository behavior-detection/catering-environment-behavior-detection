from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'video-sources', views.VideoSourceViewSet)
router.register(r'roi-polygons', views.ROIPolygonViewSet)
router.register(r'detection-settings', views.DetectionSettingViewSet)
router.register(r'violation-events', views.ViolationEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
]