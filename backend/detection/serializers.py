from rest_framework import serializers
from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent


class ROIPolygonSerializer(serializers.ModelSerializer):
    points_list = serializers.SerializerMethodField()

    class Meta:
        model = ROIPolygon
        fields = ['id', 'name', 'points', 'points_list', 'active']
        extra_kwargs = {
            'points': {'write_only': True}
        }

    def get_points_list(self, obj):
        return obj.get_points()

    def validate_points(self, value):
        """Validate that points is a properly formatted JSON string"""
        try:
            import json
            points = json.loads(value)
            if not isinstance(points, list):
                raise serializers.ValidationError("Points must be a list of coordinate pairs")
            for point in points:
                if not isinstance(point, list) or len(point) != 2:
                    raise serializers.ValidationError("Each point must be a list of [x, y]")
            return value
        except json.JSONDecodeError:
            raise serializers.ValidationError("Points must be a valid JSON string")


class DetectionSettingSerializer(serializers.ModelSerializer):
    target_classes_list = serializers.SerializerMethodField()

    class Meta:
        model = DetectionSetting
        fields = ['id', 'confidence_threshold', 'iou_threshold', 'target_classes',
                  'target_classes_list', 'enable_tracking', 'save_snapshots']
        extra_kwargs = {
            'target_classes': {'write_only': True}
        }

    def get_target_classes_list(self, obj):
        return obj.get_target_classes()


class VideoSourceSerializer(serializers.ModelSerializer):
    roi_polygons = ROIPolygonSerializer(many=True, read_only=True)
    detection_setting = DetectionSettingSerializer(read_only=True)

    class Meta:
        model = VideoSource
        fields = ['id', 'name', 'source_type', 'source_url', 'active',
                  'resolution_width', 'resolution_height', 'roi_polygons',
                  'detection_setting', 'created_at', 'updated_at']


class VideoSourceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating video sources with nested detection settings"""
    detection_setting = DetectionSettingSerializer(required=False)
    roi_polygons = ROIPolygonSerializer(many=True, required=False)

    class Meta:
        model = VideoSource
        fields = ['id', 'name', 'source_type', 'source_url', 'active',
                  'resolution_width', 'resolution_height', 'detection_setting',
                  'roi_polygons']

    def create(self, validated_data):
        detection_setting_data = validated_data.pop('detection_setting', None)
        roi_polygons_data = validated_data.pop('roi_polygons', None)

        video_source = VideoSource.objects.create(**validated_data)

        if detection_setting_data:
            DetectionSetting.objects.create(video_source=video_source, **detection_setting_data)
        else:
            DetectionSetting.objects.create(video_source=video_source)

        if roi_polygons_data:
            for roi_data in roi_polygons_data:
                ROIPolygon.objects.create(video_source=video_source, **roi_data)

        return video_source


class ViolationEventSerializer(serializers.ModelSerializer):
    detection_data_parsed = serializers.SerializerMethodField()
    video_source_name = serializers.StringRelatedField(source='video_source')

    class Meta:
        model = ViolationEvent
        fields = ['id', 'video_source', 'video_source_name', 'timestamp', 'snapshot',
                  'zoomed_snapshot', 'detection_data', 'detection_data_parsed',
                  'confidence', 'status', 'notes']
        extra_kwargs = {
            'detection_data': {'write_only': True}
        }

    def get_detection_data_parsed(self, obj):
        return obj.get_detection_data()