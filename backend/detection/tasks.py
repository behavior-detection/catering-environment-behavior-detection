import cv2
import os
import time
import numpy as np
import uuid
import json
import logging
from celery import shared_task
from django.conf import settings
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent
from .yolo.detector import YOLODetector
from .yolo.preprocessor import FramePreprocessor
from .yolo.tracker import SimpleTracker, ViolationDetector
from .yolo.video_source import VideoSourceManager

# Configure logging
logger = logging.getLogger(__name__)


@shared_task
def process_frame(source_id):
    """
    Process a single frame from a video source
    This task is designed to be called repeatedly by a scheduler
    """
    try:
        # Get video source
        try:
            source = VideoSource.objects.get(id=source_id, active=True)
        except VideoSource.DoesNotExist:
            logger.warning(f"Video source {source_id} not found or not active")
            return None

        # Get source manager and check if source is running
        manager = VideoSourceManager()
        video_source = manager.get_source(source_id)

        if not video_source or not video_source.is_running():
            # Start source if not running
            video_source = manager.add_source(
                source_id=source_id,
                source_type=source.source_type,
                source_url=source.source_url,
                width=source.resolution_width,
                height=source.resolution_height,
                auto_start=True
            )

            if not video_source or not video_source.is_running():
                logger.error(f"Failed to start video source {source_id}")
                return None

        # Get frame from source
        frame_info = video_source.get_frame(timeout=1.0)
        if frame_info is None:
            logger.warning(f"No frame received from source {source_id}")
            return None

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

        # Initialize detection components
        detector = YOLODetector()
        preprocessor = FramePreprocessor(
            target_width=source.resolution_width,
            target_height=source.resolution_height
        )

        # Process frame
        processed_frame = preprocessor.process_frame(
            frame,
            roi_polygons=roi_polygons,
            enhance=True
        )

        # Run detection
        detections = detector.detect(
            processed_frame,
            confidence_threshold=detection_setting.confidence_threshold,
            iou_threshold=detection_setting.iou_threshold,
            roi_polygons=roi_polygons,
            target_classes=detection_setting.get_target_classes()
        )

        # Draw detections and ROI on the frame
        result_frame = detector.draw_detections(frame, detections)
        if roi_polygons:
            result_frame = detector.draw_roi_polygons(result_frame, roi_polygons)

        # Convert result frame to base64 for WebSocket
        _, buffer = cv2.imencode('.jpg', result_frame)
        encoded_frame = base64.b64encode(buffer).decode('utf-8')

        # Get channel layer and send frame to WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"video_{source_id}",
            {
                'type': 'send_frame',
                'frame': encoded_frame,
                'timestamp': time.time(),
                'source_id': source_id,
                'detections': detections
            }
        )

        return {
            'source_id': source_id,
            'processed': True,
            'detection_count': len(detections)
        }

    except Exception as e:
        logger.error(f"Error processing frame for source {source_id}: {e}", exc_info=True)
        return None


@shared_task
def continuous_detection(source_id, duration=None):
    """
    Run continuous detection on a video source for a specified duration
    If duration is None, it will run until the source is deactivated
    """
    try:
        # Get video source
        try:
            source = VideoSource.objects.get(id=source_id, active=True)
        except VideoSource.DoesNotExist:
            logger.warning(f"Video source {source_id} not found or not active")
            return None

        # Start time for duration tracking
        start_time = time.time()

        # Get source manager and start the source
        manager = VideoSourceManager()
        video_source = manager.add_source(
            source_id=source_id,
            source_type=source.source_type,
            source_url=source.source_url,
            width=source.resolution_width,
            height=source.resolution_height,
            buffer_size=5,  # Use smaller buffer for real-time processing
            target_fps=settings.DETECTION_FRAME_RATE
        )

        if not video_source or not video_source.is_running():
            logger.error(f"Failed to start video source {source_id}")
            return None

        # Get ROI polygons for this source
        roi_polygons = []
        for roi in ROIPolygon.objects.filter(video_source=source, active=True):
            roi_polygons.append(roi.get_points())

        # Get detection settings
        try:
            detection_setting = source.detection_setting
        except DetectionSetting.DoesNotExist:
            detection_setting = DetectionSetting.objects.create(video_source=source)

        # Initialize detection components
        detector = YOLODetector()
        preprocessor = FramePreprocessor(
            target_width=source.resolution_width,
            target_height=source.resolution_height
        )

        # Initialize tracker if enabled
        tracker = None
        violation_detector = None
        if detection_setting.enable_tracking:
            tracker = SimpleTracker(
                max_disappeared=30,
                min_hit_streak=3,
                iou_threshold=0.3
            )
            violation_detector = ViolationDetector(
                violation_classes=[0],  # Person class
                suspicious_duration=2.0,
                violation_duration=5.0
            )

        # Get channel layer for WebSocket communication
        channel_layer = get_channel_layer()

        # Main detection loop
        frame_count = 0
        violation_count = 0

        while source.active:
            # Check duration if specified
            if duration and (time.time() - start_time) > duration:
                break

            # Check if source still active in database
            try:
                source.refresh_from_db()
                if not source.active:
                    break
            except VideoSource.DoesNotExist:
                break

            # Get frame from source
            frame_info = video_source.get_frame(timeout=1.0)
            if frame_info is None:
                logger.warning(f"No frame received from source {source_id}")
                time.sleep(0.1)  # Short sleep to avoid busy waiting
                continue

            # Extract frame and metadata
            frame = frame_info['frame']  # RGB format
            frame_timestamp = frame_info['timestamp']

            # Convert to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Process frame
            processed_frame = preprocessor.process_frame(
                frame_bgr,
                roi_polygons=roi_polygons,
                enhance=True
            )

            # Run detection
            detections = detector.detect(
                processed_frame,
                confidence_threshold=detection_setting.confidence_threshold,
                iou_threshold=detection_setting.iou_threshold,
                roi_polygons=roi_polygons,
                target_classes=detection_setting.get_target_classes()
            )

            # Update tracker if enabled
            tracked_objects = detections
            violation_events = []

            if tracker and len(detections) > 0:
                tracked_objects = tracker.update(detections, frame_timestamp)

                if violation_detector:
                    tracked_objects, violation_events = violation_detector.update(
                        tracked_objects, frame_timestamp)

            # Process violation events
            for event in violation_events:
                # Create snapshot for the violation
                bbox = event['bbox']
                x1, y1, x2, y2 = map(int, bbox)

                # Ensure coordinates are within frame bounds
                height, width = frame_bgr.shape[:2]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(width, x2)
                y2 = min(height, y2)

                # Extract region for snapshot
                snapshot_region = frame_bgr[y1:y2, x1:x2]

                if snapshot_region.size > 0:
                    # Create zoomed snapshot
                    zoomed_snapshot = detector.extract_snapshot(frame_bgr, event, zoom_factor=2.0)

                    # Save snapshots to files
                    snapshot_dir = os.path.join(settings.VIOLATION_SNAPSHOT_DIR, str(source.id))
                    os.makedirs(snapshot_dir, exist_ok=True)

                    timestamp_str = datetime.fromtimestamp(event['timestamp']).strftime('%Y%m%d_%H%M%S')
                    snapshot_filename = f"violation_{timestamp_str}_{uuid.uuid4().hex[:8]}.jpg"
                    zoomed_filename = f"violation_{timestamp_str}_{uuid.uuid4().hex[:8]}_zoomed.jpg"

                    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                    zoomed_path = os.path.join(snapshot_dir, zoomed_filename)

                    cv2.imwrite(snapshot_path, snapshot_region)

                    if zoomed_snapshot is not None:
                        cv2.imwrite(zoomed_path, zoomed_snapshot)

                    # Create ViolationEvent record
                    if detection_setting.save_snapshots:
                        violation = ViolationEvent(
                            video_source=source,
                            timestamp=datetime.fromtimestamp(event['timestamp']),
                            snapshot=os.path.join('snapshots', str(source.id), snapshot_filename),
                            confidence=event['confidence'],
                            status='detected'
                        )

                        # Save zoomed snapshot if available
                        if zoomed_snapshot is not None:
                            violation.zoomed_snapshot = os.path.join('snapshots', str(source.id), zoomed_filename)

                        # Save detection data
                        violation.set_detection_data(event)
                        violation.save()

                        violation_count += 1

                        # Send notification via WebSocket
                        async_to_sync(channel_layer.group_send)(
                            f"violations_{source_id}",
                            {
                                'type': 'send_violation',
                                'violation_id': violation.id,
                                'timestamp': event['timestamp'],
                                'source_id': source_id,
                                'snapshot_url': violation.snapshot.url,
                                'zoomed_snapshot_url': violation.zoomed_snapshot.url if violation.zoomed_snapshot else None,
                                'confidence': event['confidence'],
                                'class_name': event['class_name']
                            }
                        )

            # Draw detections/tracking on frame
            result_frame = frame_bgr.copy()

            if tracker:
                result_frame = tracker.draw_tracks(result_frame, color_by_state=True)
            else:
                result_frame = detector.draw_detections(result_frame, tracked_objects)

            if roi_polygons:
                result_frame = detector.draw_roi_polygons(result_frame, roi_polygons)

            # Encode frame for WebSocket
            _, buffer = cv2.imencode('.jpg', result_frame)
            encoded_frame = base64.b64encode(buffer).decode('utf-8')

            # Send frame via WebSocket
            async_to_sync(channel_layer.group_send)(
                f"video_{source_id}",
                {
                    'type': 'send_frame',
                    'frame': encoded_frame,
                    'timestamp': frame_timestamp,
                    'source_id': source_id,
                    'detections': [
                        {
                            'bbox': list(obj['bbox']),
                            'class_id': obj['class_id'],
                            'class_name': obj['class_name'],
                            'confidence': obj['confidence'],
                            'track_id': obj.get('track_id'),
                            'state': obj.get('state')
                        } for obj in tracked_objects
                    ]
                }
            )

            frame_count += 1

            # Short sleep to control CPU usage
            time.sleep(0.01)

        # Cleanup
        manager.remove_source(source_id)

        return {
            'source_id': source_id,
            'frames_processed': frame_count,
            'violations_detected': violation_count,
            'duration': time.time() - start_time
        }

    except Exception as e:
        logger.error(f"Error in continuous detection for source {source_id}: {e}", exc_info=True)
        return None


@shared_task
def process_video_detection(source_id):
    """Process a video file for detection"""
    try:
        # Get video source
        try:
            source = VideoSource.objects.get(id=source_id)
            if source.source_type != 'file':
                logger.error(f"Source {source_id} is not a file type")
                return None
        except VideoSource.DoesNotExist:
            logger.error(f"Video source {source_id} not found")
            return None

        # Check if file exists
        if not os.path.exists(source.source_url):
            logger.error(f"Video file not found: {source.source_url}")
            return None

        # Get ROI polygons for this source
        roi_polygons = []
        for roi in ROIPolygon.objects.filter(video_source=source, active=True):
            roi_polygons.append(roi.get_points())

        # Get detection settings
        try:
            detection_setting = source.detection_setting
        except DetectionSetting.DoesNotExist:
            detection_setting = DetectionSetting.objects.create(video_source=source)

        # Initialize detection components
        detector = YOLODetector()
        preprocessor = FramePreprocessor(
            target_width=source.resolution_width,
            target_height=source.resolution_height
        )

        # Initialize tracker if enabled
        tracker = None
        violation_detector = None
        if detection_setting.enable_tracking:
            tracker = SimpleTracker(
                max_disappeared=30,
                min_hit_streak=3,
                iou_threshold=0.3
            )
            violation_detector = ViolationDetector(
                violation_classes=[0],  # Person class
                suspicious_duration=2.0,
                violation_duration=5.0
            )

        # Open video file
        cap = cv2.VideoCapture(source.source_url)
        if not cap.isOpened():
            logger.error(f"Could not open video file: {source.source_url}")
            return None

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        # Get channel layer for WebSocket communication
        channel_layer = get_channel_layer()

        # Process every Nth frame to reduce workload
        process_every_n_frames = max(1, int(fps / settings.DETECTION_FRAME_RATE))

        # Main processing loop
        processed_frames = 0
        violation_count = 0
        frame_idx = 0

        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Skip frames based on target frame rate
            if (frame_idx - 1) % process_every_n_frames != 0:
                continue

            # Calculate current timestamp in video
            frame_timestamp = frame_idx / fps

            # Process frame
            processed_frame = preprocessor.process_frame(
                frame,
                roi_polygons=roi_polygons,
                enhance=True
            )

            # Run detection
            detections = detector.detect(
                processed_frame,
                confidence_threshold=detection_setting.confidence_threshold,
                iou_threshold=detection_setting.iou_threshold,
                roi_polygons=roi_polygons,
                target_classes=detection_setting.get_target_classes()
            )

            # Update tracker if enabled
            tracked_objects = detections
            violation_events = []

            if tracker and len(detections) > 0:
                tracked_objects = tracker.update(detections, frame_timestamp)

                if violation_detector:
                    tracked_objects, violation_events = violation_detector.update(
                        tracked_objects, frame_timestamp)

            # Process violation events
            for event in violation_events:
                # Create snapshot for the violation
                bbox = event['bbox']
                x1, y1, x2, y2 = map(int, bbox)

                # Ensure coordinates are within frame bounds
                height, width = frame.shape[:2]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(width, x2)
                y2 = min(height, y2)

                # Extract region for snapshot
                snapshot_region = frame[y1:y2, x1:x2]

                if snapshot_region.size > 0:
                    # Create zoomed snapshot
                    zoomed_snapshot = detector.extract_snapshot(frame, event, zoom_factor=2.0)

                    # Save snapshots to files
                    snapshot_dir = os.path.join(settings.VIOLATION_SNAPSHOT_DIR, str(source.id))
                    os.makedirs(snapshot_dir, exist_ok=True)

                    time_obj = datetime.fromtimestamp(time.time())
                    timestamp_str = time_obj.strftime('%Y%m%d_%H%M%S')
                    video_time_str = f"{int(frame_timestamp // 60):02d}_{int(frame_timestamp % 60):02d}"

                    snapshot_filename = f"violation_{timestamp_str}_{video_time_str}_{uuid.uuid4().hex[:8]}.jpg"
                    zoomed_filename = f"violation_{timestamp_str}_{video_time_str}_{uuid.uuid4().hex[:8]}_zoomed.jpg"

                    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                    zoomed_path = os.path.join(snapshot_dir, zoomed_filename)

                    cv2.imwrite(snapshot_path, snapshot_region)

                    if zoomed_snapshot is not None:
                        cv2.imwrite(zoomed_path, zoomed_snapshot)

                    # Create ViolationEvent record
                    if detection_setting.save_snapshots:
                        violation = ViolationEvent(
                            video_source=source,
                            timestamp=time_obj,
                            snapshot=os.path.join('snapshots', str(source.id), snapshot_filename),
                            confidence=event['confidence'],
                            status='detected'
                        )

                        # Save zoomed snapshot if available
                        if zoomed_snapshot is not None:
                            violation.zoomed_snapshot = os.path.join('snapshots', str(source.id), zoomed_filename)

                        # Save detection data with video timestamp
                        event_data = event.copy()
                        event_data['video_timestamp'] = frame_timestamp
                        violation.set_detection_data(event_data)
                        violation.save()

                        violation_count += 1

                        # Send notification via WebSocket
                        async_to_sync(channel_layer.group_send)(
                            f"violations_{source_id}",
                            {
                                'type': 'send_violation',
                                'violation_id': violation.id,
                                'timestamp': time.time(),
                                'video_timestamp': frame_timestamp,
                                'source_id': source_id,
                                'snapshot_url': violation.snapshot.url,
                                'zoomed_snapshot_url': violation.zoomed_snapshot.url if violation.zoomed_snapshot else None,
                                'confidence': event['confidence'],
                                'class_name': event['class_name']
                            }
                        )

            # Draw detections/tracking on frame for preview
            result_frame = frame.copy()

            if tracker:
                result_frame = tracker.draw_tracks(result_frame, color_by_state=True)
            else:
                result_frame = detector.draw_detections(result_frame, tracked_objects)

            if roi_polygons:
                result_frame = detector.draw_roi_polygons(result_frame, roi_polygons)

            # Add timestamp to frame
            minutes = int(frame_timestamp // 60)
            seconds = int(frame_timestamp % 60)
            timestamp_text = f"{minutes:02d}:{seconds:02d}"
            cv2.putText(result_frame, timestamp_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Encode frame for WebSocket
            _, buffer = cv2.imencode('.jpg', result_frame)
            encoded_frame = base64.b64encode(buffer).decode('utf-8')

            # Send frame via WebSocket for preview
            async_to_sync(channel_layer.group_send)(
                f"video_{source_id}",
                {
                    'type': 'send_frame',
                    'frame': encoded_frame,
                    'timestamp': time.time(),
                    'video_timestamp': frame_timestamp,
                    'source_id': source_id,
                    'progress': round(100 * frame_idx / frame_count) if frame_count > 0 else 0,
                    'detections': [
                        {
                            'bbox': list(obj['bbox']),
                            'class_id': obj['class_id'],
                            'class_name': obj['class_name'],
                            'confidence': obj['confidence'],
                            'track_id': obj.get('track_id'),
                            'state': obj.get('state')
                        } for obj in tracked_objects
                    ]
                }
            )

            processed_frames += 1

        # Close video file
        cap.release()

        # Send completion notification
        async_to_sync(channel_layer.group_send)(
            f"video_{source_id}",
            {
                'type': 'send_processing_complete',
                'source_id': source_id,
                'processed_frames': processed_frames,
                'violations_detected': violation_count,
                'duration': duration
            }
        )

        return {
            'source_id': source_id,
            'processed_frames': processed_frames,
            'violations_detected': violation_count,
            'video_duration': duration
        }

    except Exception as e:
        logger.error(f"Error processing video detection for source {source_id}: {e}", exc_info=True)
        return None


# Helper function to encode frame to base64
def encode_frame_to_base64(frame):
    """Convert OpenCV frame to base64 encoded JPEG"""
    import base64
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')