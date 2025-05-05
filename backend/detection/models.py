from django.db import models
import json
import uuid
import os


class VideoSource(models.Model):
    """Model to store video sources (cameras, RTSP, files)"""
    SOURCE_TYPES = (
        ('camera', 'USB/Built-in Camera'),
        ('rtsp', 'RTSP Stream'),
        ('file', 'Video File'),
    )

    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES)
    source_url = models.CharField(max_length=255, help_text="Camera index (0, 1), RTSP URL, or file path")
    active = models.BooleanField(default=False)
    resolution_width = models.IntegerField(default=640)
    resolution_height = models.IntegerField(default=480)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.source_type})"

    class Meta:
        verbose_name = "Video Source"
        verbose_name_plural = "Video Sources"


class ROIPolygon(models.Model):
    """Region of Interest polygon for detection"""
    video_source = models.ForeignKey(VideoSource, on_delete=models.CASCADE, related_name='roi_polygons')
    name = models.CharField(max_length=100)
    points = models.TextField(help_text="JSON string of points: [[x1,y1], [x2,y2], ...]")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.video_source.name}"

    def get_points(self):
        """Return the polygon points as a list of coordinate pairs"""
        try:
            return json.loads(self.points)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_points(self, points_list):
        """Set the polygon points from a list of coordinate pairs"""
        self.points = json.dumps(points_list)

    class Meta:
        verbose_name = "ROI Polygon"
        verbose_name_plural = "ROI Polygons"


class DetectionSetting(models.Model):
    """Settings for YOLO detection"""
    video_source = models.OneToOneField(VideoSource, on_delete=models.CASCADE, related_name='detection_setting')
    confidence_threshold = models.FloatField(default=0.5)
    iou_threshold = models.FloatField(default=0.45)
    target_classes = models.CharField(max_length=255, blank=True, help_text="Comma-separated class IDs (empty for all)")
    enable_tracking = models.BooleanField(default=True)
    save_snapshots = models.BooleanField(default=True)

    def __str__(self):
        return f"Settings for {self.video_source.name}"

    def get_target_classes(self):
        """Get list of target class IDs"""
        if not self.target_classes:
            return []
        return [int(cls.strip()) for cls in self.target_classes.split(',') if cls.strip().isdigit()]


def snapshot_upload_path(instance, filename):
    """Determine the path for violation snapshot uploads"""
    # Format: snapshots/source_id/YYYY-MM-DD/uuid_filename.jpg
    date_str = instance.timestamp.strftime('%Y-%m-%d')
    _, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('snapshots', str(instance.video_source.id), date_str, unique_filename)


class ViolationEvent(models.Model):
    """Record of a detected violation event"""
    STATUS_CHOICES = (
        ('detected', 'Initially Detected'),
        ('confirmed', 'Violation Confirmed'),
        ('false_alarm', 'False Alarm'),
        ('resolved', 'Resolved'),
    )

    video_source = models.ForeignKey(VideoSource, on_delete=models.CASCADE, related_name='violation_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    snapshot = models.ImageField(upload_to=snapshot_upload_path)
    zoomed_snapshot = models.ImageField(upload_to=snapshot_upload_path, null=True, blank=True)
    detection_data = models.TextField(help_text="JSON string of detection results")
    confidence = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='detected')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Violation on {self.timestamp} - {self.video_source.name}"

    def get_detection_data(self):
        """Return the detection data as a dictionary"""
        try:
            return json.loads(self.detection_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_detection_data(self, data_dict):
        """Set the detection data from a dictionary"""
        self.detection_data = json.dumps(data_dict)

    class Meta:
        verbose_name = "Violation Event"
        verbose_name_plural = "Violation Events"
        ordering = ['-timestamp']