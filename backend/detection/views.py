from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
import os
import json
import cv2
import numpy as np
import base64
from datetime import datetime
import time

from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent
from .serializers import (VideoSourceSerializer, VideoSourceCreateSerializer,
                          ROIPolygonSerializer, DetectionSettingSerializer,
                          ViolationEventSerializer)
from .yolo.detector import YOLODetector
from .yolo.video_source import VideoSourceManager
from .yolo.preprocessor import FramePreprocessor
from .yolo.tracker import SimpleTracker, ViolationDetector
from .tasks import process_video_detection


class VideoSourceViewSet(viewsets.ModelViewSet):
    """API endpoint for video sources (cameras, RTSP, files)"""
    queryset = VideoSource.objects.all()

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return VideoSourceCreateSerializer
        return VideoSourceSerializer

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a video source"""
        source = self.get_object()
        source.active = True
        source.save()

        # Start video capture in the manager
        manager = VideoSourceManager()
        manager.add_source(
            source_id=source.id,
            source_type=source.source_type,
            source_url=source.source_url,
            width=source.resolution_width,
            height=source.resolution_height,
            auto_start=True
        )

        return Response({'status': 'video source activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a video source"""
        source = self.get_object()
        source.active = False
        source.save()

        # Stop video capture in the manager
        manager = VideoSourceManager()
        manager.remove_source(source.id)

        return Response({'status': 'video source deactivated'})

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current status of video source"""
        source = self.get_object()

        # Check if source is running in manager
        manager = VideoSourceManager()
        video_source = manager.get_source(source.id)

        if video_source and video_source.is_running():
            metrics = video_source.get_metrics()
            return Response({
                'id': source.id,
                'name': source.name,
                'active': True,
                'running': True,
                'metrics': metrics
            })
        else:
            return Response({
                'id': source.id,
                'name': source.name,
                'active': source.active,
                'running': False
            })

    @action(detail=True, methods=['get'])
    def snapshot(self, request, pk=None):
        """Get a snapshot from the video source"""
        source = self.get_object()

        # Check if source is running in manager
        manager = VideoSourceManager()
        video_source = manager.get_source(source.id)

        if not video_source or not video_source.is_running():
            return Response(
                {'error': 'Video source not running'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get a frame from the source
        frame_info = video_source.get_frame(timeout=2.0)
        if frame_info is None:
            return Response(
                {'error': 'Could not get frame from video source'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )

        # Convert to BGR for OpenCV
        frame = cv2.cvtColor(frame_info['frame'], cv2.COLOR_RGB2BGR)

        # Get ROI polygons for this source
        roi_polygons = []
        for roi in ROIPolygon.objects.filter(video_source=source, active=True):
            roi_polygons.append(roi.get_points())

        # Get detection settings
        try:
            detection_setting = source.detection_setting
        except DetectionSetting.DoesNotExist:
            detection_setting = DetectionSetting.objects.create(video_source=source)

        # Initialize YOLO detector
        detector = YOLODetector()

        # Process frame with detection
        detections = detector.detect(
            frame,
            confidence_threshold=detection_setting.confidence_threshold,
            iou_threshold=detection_setting.iou_threshold,
            roi_polygons=roi_polygons,
            target_classes=detection_setting.get_target_classes()
        )

        # Draw detections and ROI on the frame
        result_frame = detector.draw_detections(frame, detections)
        if roi_polygons:
            result_frame = detector.draw_roi_polygons(result_frame, roi_polygons)

        # Convert to JPEG bytes
        _, buffer = cv2.imencode('.jpg', result_frame)
        jpg_bytes = buffer.tobytes()

        # Return image/jpeg response
        return HttpResponse(
            jpg_bytes,
            content_type='image/jpeg'
        )

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_video(self, request, pk=None):
        """Upload a video file for the source"""
        source = self.get_object()

        if source.source_type != 'file':
            return Response(
                {'error': 'Only file-type sources can have videos uploaded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']

        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
        os.makedirs(upload_dir, exist_ok=True)

        # Save the file
        filename = f"{source.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Update source URL
        source.source_url = filepath
        source.save()

        # Start processing
        process_task = process_video_detection.delay(source.id)

        return Response({
            'status': 'video uploaded',
            'file_path': filepath,
            'task_id': process_task.id
        })


class ROIPolygonViewSet(viewsets.ModelViewSet):
    """API endpoint for ROI polygons"""
    queryset = ROIPolygon.objects.all()
    serializer_class = ROIPolygonSerializer

    def get_queryset(self):
        """Optionally filter by video source"""
        queryset = ROIPolygon.objects.all()
        video_source_id = self.request.query_params.get('video_source', None)

        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        return queryset


class DetectionSettingViewSet(viewsets.ModelViewSet):
    """API endpoint for detection settings"""
    queryset = DetectionSetting.objects.all()
    serializer_class = DetectionSettingSerializer

    def get_queryset(self):
        """Optionally filter by video source"""
        queryset = DetectionSetting.objects.all()
        video_source_id = self.request.query_params.get('video_source', None)

        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        return queryset


class ViolationEventViewSet(viewsets.ModelViewSet):
    """API endpoint for violation events"""
    queryset = ViolationEvent.objects.all().order_by('-timestamp')
    serializer_class = ViolationEventSerializer

    def get_queryset(self):
        """Filter by various parameters"""
        queryset = ViolationEvent.objects.all().order_by('-timestamp')

        # Filter by video source
        video_source_id = self.request.query_params.get('video_source', None)
        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param is not None:
            queryset = queryset.filter(status=status_param)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date is not None:
            queryset = queryset.filter(timestamp__gte=start_date)

        if end_date is not None:
            queryset = queryset.filter(timestamp__lte=end_date)

        # Limit the number of results
        limit = self.request.query_params.get('limit', None)
        if limit is not None:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass

        return queryset

    @action(detail=True, methods=['post'])
    def mark_false_alarm(self, request, pk=None):
        """Mark violation as false alarm"""
        violation = self.get_object()
        violation.status = 'false_alarm'
        violation.save()

        return Response({'status': 'marked as false alarm'})

    @action(detail=True, methods=['post'])
    def mark_resolved(self, request, pk=None):
        """Mark violation as resolved"""
        violation = self.get_object()
        violation.status = 'resolved'
        violation.save()

        return Response({'status': 'marked as resolved'})