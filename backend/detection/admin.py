from django.contrib import admin
from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent

@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'source_url', 'active', 'created_at')
    list_filter = ('source_type', 'active')
    search_fields = ('name', 'source_url')

@admin.register(ROIPolygon)
class ROIPolygonAdmin(admin.ModelAdmin):
    list_display = ('name', 'video_source', 'active')
    list_filter = ('active', 'video_source')
    search_fields = ('name',)

@admin.register(DetectionSetting)
class DetectionSettingAdmin(admin.ModelAdmin):
    list_display = ('video_source', 'confidence_threshold', 'iou_threshold', 'enable_tracking')
    search_fields = ('video_source__name',) # 用于通过 video_source 的 name 进行搜索

@admin.register(ViolationEvent)
class ViolationEventAdmin(admin.ModelAdmin):
    list_display = ('video_source', 'timestamp', 'status', 'confidence')
    list_filter = ('status', 'video_source')
    search_fields = ('video_source__name', 'status')