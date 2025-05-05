import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import VideoSource, ViolationEvent
from django.conf import settings
from datetime import datetime
import asyncio
import time

# Configure logging
logger = logging.getLogger(__name__)


class VideoStreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time video streaming"""

    async def connect(self):
        """Handle connection - get parameters and join appropriate group"""
        # Get source ID from URL route
        self.source_id = self.scope['url_route']['kwargs']['source_id']
        self.group_name = f'video_{self.source_id}'

        # Check if source exists
        source_exists = await self.check_source_exists(self.source_id)
        if not source_exists:
            await self.close(code=4004)
            return

        # Join the group for this video source
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial metadata
        metadata = await self.get_source_metadata(self.source_id)
        await self.send(text_data=json.dumps({
            'type': 'metadata',
            'source_id': self.source_id,
            'metadata': metadata
        }))

    async def disconnect(self, close_code):
        """Leave group on disconnect"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            command = data.get('command', '')

            if command == 'start_detection':
                # Import here to avoid circular dependency
                from .tasks import continuous_detection, process_video_detection

                # Get duration if specified
                duration = data.get('duration')

                # Check source type and start appropriate task
                source = await self.get_source(self.source_id)
                if source and source['active']:
                    if source['source_type'] == 'file':
                        # Process video file
                        task = process_video_detection.delay(self.source_id)
                    else:
                        # Start continuous detection for camera/RTSP
                        task = continuous_detection.delay(self.source_id, duration)

                    await self.send(text_data=json.dumps({
                        'type': 'task_started',
                        'task_id': task.id,
                        'source_id': self.source_id
                    }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Video source not active or not found'
                    }))

            elif command == 'stop_detection':
                # Set source to inactive to stop continuous processing
                success = await self.deactivate_source(self.source_id)
                await self.send(text_data=json.dumps({
                    'type': 'detection_stopped',
                    'success': success,
                    'source_id': self.source_id
                }))

            elif command == 'get_status':
                # Get current status
                status = await self.get_source_status(self.source_id)
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'status': status,
                    'source_id': self.source_id
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def send_frame(self, event):
        """Send frame to WebSocket client"""
        # Forward the frame event to the client
        await self.send(text_data=json.dumps({
            'type': 'frame',
            'frame': event['frame'],
            'timestamp': event['timestamp'],
            'source_id': event['source_id'],
            'detections': event.get('detections', []),
            'progress': event.get('progress')
        }))

    async def send_processing_complete(self, event):
        """Send processing complete notification"""
        await self.send(text_data=json.dumps({
            'type': 'processing_complete',
            'source_id': event['source_id'],
            'processed_frames': event['processed_frames'],
            'violations_detected': event['violations_detected'],
            'duration': event['duration']
        }))

    @database_sync_to_async
    def check_source_exists(self, source_id):
        """Check if the video source exists"""
        try:
            return VideoSource.objects.filter(id=source_id).exists()
        except Exception:
            return False

    @database_sync_to_async
    def get_source(self, source_id):
        """Get source information"""
        try:
            source = VideoSource.objects.get(id=source_id)
            return {
                'id': source.id,
                'name': source.name,
                'source_type': source.source_type,
                'source_url': source.source_url,
                'active': source.active,
                'resolution_width': source.resolution_width,
                'resolution_height': source.resolution_height
            }
        except VideoSource.DoesNotExist:
            return None

    @database_sync_to_async
    def get_source_metadata(self, source_id):
        """Get metadata for a video source"""
        try:
            source = VideoSource.objects.get(id=source_id)

            # Get ROI data
            roi_polygons = []
            for roi in source.roi_polygons.filter(active=True):
                roi_polygons.append({
                    'id': roi.id,
                    'name': roi.name,
                    'points': roi.get_points()
                })

            # Get detection settings
            try:
                settings = source.detection_setting
                detection_settings = {
                    'confidence_threshold': settings.confidence_threshold,
                    'iou_threshold': settings.iou_threshold,
                    'target_classes': settings.get_target_classes(),
                    'enable_tracking': settings.enable_tracking,
                    'save_snapshots': settings.save_snapshots
                }
            except:
                detection_settings = {
                    'confidence_threshold': 0.5,
                    'iou_threshold': 0.45,
                    'target_classes': [],
                    'enable_tracking': True,
                    'save_snapshots': True
                }

            return {
                'name': source.name,
                'source_type': source.source_type,
                'resolution': f"{source.resolution_width}x{source.resolution_height}",
                'active': source.active,
                'roi_polygons': roi_polygons,
                'detection_settings': detection_settings
            }
        except VideoSource.DoesNotExist:
            return {}

    @database_sync_to_async
    def get_source_status(self, source_id):
        """Get current status of a video source"""
        try:
            source = VideoSource.objects.get(id=source_id)

            # Get recent violations
            recent_violations = ViolationEvent.objects.filter(
                video_source_id=source_id
            ).order_by('-timestamp')[:5]

            violations = []
            for violation in recent_violations:
                violations.append({
                    'id': violation.id,
                    'timestamp': violation.timestamp.isoformat(),
                    'snapshot_url': violation.snapshot.url if violation.snapshot else None,
                    'zoomed_snapshot_url': violation.zoomed_snapshot.url if violation.zoomed_snapshot else None,
                    'confidence': violation.confidence,
                    'status': violation.status
                })

            return {
                'id': source.id,
                'name': source.name,
                'active': source.active,
                'recent_violations': violations
            }
        except VideoSource.DoesNotExist:
            return {'error': 'Source not found'}

    @database_sync_to_async
    def deactivate_source(self, source_id):
        """Deactivate a video source to stop processing"""
        try:
            source = VideoSource.objects.get(id=source_id)
            source.active = False
            source.save()
            return True
        except VideoSource.DoesNotExist:
            return False


class ViolationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time violation notifications"""

    async def connect(self):
        """Handle connection - join appropriate group(s)"""
        # Get source ID from URL route or 'all' for all sources
        self.source_id = self.scope['url_route']['kwargs'].get('source_id', 'all')

        if self.source_id == 'all':
            self.group_name = 'violations_all'
        else:
            # Check if specific source exists
            source_exists = await self.check_source_exists(self.source_id)
            if not source_exists:
                await self.close(code=4004)
                return
            self.group_name = f'violations_{self.source_id}'

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send recent violations on connect
        recent_violations = await self.get_recent_violations(self.source_id)
        await self.send(text_data=json.dumps({
            'type': 'recent_violations',
            'violations': recent_violations
        }))

    async def disconnect(self, close_code):
        """Leave group on disconnect"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming commands"""
        try:
            data = json.loads(text_data)
            command = data.get('command', '')

            if command == 'mark_status':
                violation_id = data.get('violation_id')
                new_status = data.get('status')

                if violation_id and new_status:
                    success = await self.update_violation_status(violation_id, new_status)
                    await self.send(text_data=json.dumps({
                        'type': 'status_updated',
                        'violation_id': violation_id,
                        'status': new_status if success else 'error',
                        'success': success
                    }))

            elif command == 'get_violations':
                # Get violations with optional filters
                limit = data.get('limit', 20)
                status = data.get('status')
                source_id = data.get('source_id', self.source_id)

                violations = await self.get_filtered_violations(source_id, status, limit)
                await self.send(text_data=json.dumps({
                    'type': 'violation_list',
                    'violations': violations
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def send_violation(self, event):
        """Send violation notification to connected client"""
        # If this is the 'all' group, forward all violations
        if self.source_id == 'all' or str(event['source_id']) == self.source_id:
            await self.send(text_data=json.dumps({
                'type': 'new_violation',
                'violation_id': event['violation_id'],
                'timestamp': event['timestamp'],
                'source_id': event['source_id'],
                'snapshot_url': event['snapshot_url'],
                'zoomed_snapshot_url': event['zoomed_snapshot_url'],
                'confidence': event['confidence'],
                'class_name': event['class_name'],
                'video_timestamp': event.get('video_timestamp')  # For video file violations
            }))

    @database_sync_to_async
    def check_source_exists(self, source_id):
        """Check if the video source exists"""
        if source_id == 'all':
            return True
        try:
            return VideoSource.objects.filter(id=source_id).exists()
        except Exception:
            return False

    @database_sync_to_async
    def get_recent_violations(self, source_id, limit=10):
        """Get recent violations for a source or all sources"""
        try:
            query = ViolationEvent.objects.all().order_by('-timestamp')

            if source_id != 'all':
                query = query.filter(video_source_id=source_id)

            recent = query[:limit]

            violations = []
            for violation in recent:
                violations.append({
                    'id': violation.id,
                    'source_id': violation.video_source_id,
                    'source_name': violation.video_source.name,
                    'timestamp': violation.timestamp.isoformat(),
                    'snapshot_url': violation.snapshot.url if violation.snapshot else None,
                    'zoomed_snapshot_url': violation.zoomed_snapshot.url if violation.zoomed_snapshot else None,
                    'confidence': violation.confidence,
                    'status': violation.status,
                    'detection_data': violation.get_detection_data()
                })

            return violations
        except Exception as e:
            logger.error(f"Error getting recent violations: {e}", exc_info=True)
            return []

    @database_sync_to_async
    def update_violation_status(self, violation_id, new_status):
        """Update the status of a violation event"""
        try:
            valid_statuses = ['detected', 'confirmed', 'false_alarm', 'resolved']
            if new_status not in valid_statuses:
                return False

            violation = ViolationEvent.objects.get(id=violation_id)
            violation.status = new_status
            violation.save()
            return True
        except ViolationEvent.DoesNotExist:
            return False
        except Exception:
            return False

    @database_sync_to_async
    def get_filtered_violations(self, source_id, status=None, limit=20):
        """Get violations with optional filtering"""
        try:
            query = ViolationEvent.objects.all().order_by('-timestamp')

            if source_id != 'all':
                query = query.filter(video_source_id=source_id)

            if status:
                query = query.filter(status=status)

            filtered = query[:limit]

            violations = []
            for violation in filtered:
                violations.append({
                    'id': violation.id,
                    'source_id': violation.video_source_id,
                    'source_name': violation.video_source.name,
                    'timestamp': violation.timestamp.isoformat(),
                    'snapshot_url': violation.snapshot.url if violation.snapshot else None,
                    'zoomed_snapshot_url': violation.zoomed_snapshot.url if violation.zoomed_snapshot else None,
                    'confidence': violation.confidence,
                    'status': violation.status,
                    'notes': violation.notes,
                    'detection_data': violation.get_detection_data()
                })

            return violations
        except Exception as e:
            logger.error(f"Error getting filtered violations: {e}", exc_info=True)
            return []