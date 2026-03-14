from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone
import cv2
from datetime import datetime
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
import os
import json
from django.conf import settings
import logging
import redis
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent
from .serializers import (VideoSourceSerializer, VideoSourceCreateSerializer,
                          ROIPolygonSerializer, DetectionSettingSerializer,
                          ViolationEventSerializer)
from .yolo.detector import YOLODetector
from .yolo.video_source import VideoSourceManager
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .tasks import process_video_detection, continuous_detection
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

class StartDetectionAPI(APIView):
    def post(self, request, source_id):
        video_source = get_object_or_404(VideoSource, id=source_id)

        if not video_source.active:
            return Response({"error": "视频源未激活"}, status=status.HTTP_400_BAD_REQUEST)

        use_roi = request.data.get('use_roi', False)
        duration = request.data.get('duration')  # 可选，针对文件

        if video_source.source_type == 'file':
            # 文件检测任务
            task = process_video_detection.apply_async(
                args=[source_id, use_roi],
                queue='celery'
            )
        else:
            # 实时流检测任务
            task = continuous_detection.apply_async(
                args=[source_id, duration, use_roi],
                queue='celery'
            )

        logger.info(f"检测任务已启动，任务ID: {task.id}, 源ID: {source_id}")
        return Response({
            "message": "检测已启动",
            "source_id": source_id,
            "task_id": task.id,
            "use_roi": use_roi
        }, status=status.HTTP_200_OK)
    
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', '127.0.0.1'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0, 
    decode_responses=True
)

@method_decorator(csrf_exempt, name='dispatch')
class VideoSourceViewSet(viewsets.ModelViewSet):
    """API endpoint for video sources (cameras, RTSP, files)"""
    queryset = VideoSource.objects.all()
    permission_classes = [AllowAny]
    csrf_exempt = True

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return VideoSourceCreateSerializer
        return VideoSourceSerializer

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a video source"""
        source = self.get_object()
        source.active = True
        source.save()
        logger.info(f"Video source {source.id} activated")
        return Response({'status': 'video source activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a video source"""
        source = self.get_object()
        source.active = False
        source.save()

        manager = VideoSourceManager()
        manager.remove_source(source.id)

        return Response({'status': 'video source deactivated'})

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current status of video source"""
        source = self.get_object()

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
        source = self.get_object()

        manager = VideoSourceManager()
        video_source = manager.get_source(source.id)

        if video_source and video_source.is_running():
            frame_info = video_source.get_frame(timeout=2.0)
            if frame_info is None:
                return Response({'error': 'Could not get frame from video source'},
                                status=status.HTTP_504_GATEWAY_TIMEOUT)
            frame_bgr = cv2.cvtColor(frame_info['frame'], cv2.COLOR_RGB2BGR)
        else:
            if source.source_type == 'file':
                absolute_path = os.path.join(settings.MEDIA_ROOT, source.source_url)

                if not os.path.exists(absolute_path):
                    return Response({'error': f'Video file not found at: {absolute_path}'},
                                    status=status.HTTP_404_NOT_FOUND)

                cap = cv2.VideoCapture(absolute_path)
                ok, frame_bgr = cap.read()
                cap.release()
                if not ok or frame_bgr is None:
                    return Response({'error': 'Could not read frame from video file'},
                                    status=status.HTTP_400_BAD_REQUEST)

            elif source.source_type in ('camera', 'rtsp'):
                cap = cv2.VideoCapture(source.source_url)
                ok, frame_bgr = cap.read()
                cap.release()
                if not ok or frame_bgr is None:
                    return Response({'error': 'Could not grab frame from camera/rtsp'},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Video source not running'},
                                status=status.HTTP_400_BAD_REQUEST)

        roi_polygons = []
        for roi in ROIPolygon.objects.filter(video_source=source, active=True):
            roi_polygons.append(roi.get_points())

        try:
            detection_setting = source.detection_setting
        except DetectionSetting.DoesNotExist:
            detection_setting = DetectionSetting.objects.create(video_source=source)

        detector = YOLODetector()
        detections = detector.detect(
            frame_bgr,
            confidence_threshold=detection_setting.confidence_threshold,
            iou_threshold=detection_setting.iou_threshold,
            roi_polygons=roi_polygons,
            target_classes=detection_setting.get_target_classes()
        )

        vis = detector.draw_detections(frame_bgr, detections)
        if roi_polygons:
            vis = detector.draw_roi_polygons(vis, roi_polygons)

        _, buffer = cv2.imencode('.jpg', vis)
        return HttpResponse(buffer.tobytes(), content_type='image/jpeg')

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

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{source.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_file.name}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        rel = os.path.relpath(filepath, settings.MEDIA_ROOT).replace('\\', '/')
        source.source_url = rel
        source.save()

        return Response({
            'status': 'video uploaded',
            'file_path': rel
        })


@method_decorator(csrf_exempt, name='dispatch')
class ROIPolygonViewSet(viewsets.ModelViewSet):
    """API endpoint for ROI polygons"""
    queryset = ROIPolygon.objects.all()
    serializer_class = ROIPolygonSerializer
    permission_classes = [AllowAny]
    csrf_exempt = True

    def get_queryset(self):
        queryset = ROIPolygon.objects.all()
        video_source_id = self.request.query_params.get('video_source', None)

        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        return queryset

    @action(detail=False, methods=['post'])
    def bulk_replace(self, request):
        video_source_id = request.data.get('video_source')
        polygons_data = request.data.get('polygons', [])

        logger.info(f"[ROI] ========== Bulk Replace Start ==========")
        logger.info(f"[ROI] video_source_id: {video_source_id}")
        logger.info(f"[ROI] polygons_data: {polygons_data}")

        if not video_source_id:
            logger.error(f"[ROI] Missing video_source parameter")
            return Response({'error': 'video_source is required'}, status=400)

        try:
            source = VideoSource.objects.get(id=video_source_id)
            logger.info(f"[ROI] Found video source: {source.name}")
        except VideoSource.DoesNotExist:
            logger.error(f"[ROI] Video source {video_source_id} not found")
            return Response({'error': 'Video source not found'}, status=404)

        if not polygons_data or len(polygons_data) == 0:
            logger.warning(f"[ROI] No polygons data provided")
            return Response({'error': 'No polygons data provided'}, status=400)

        try:
            with transaction.atomic():
                old_active = ROIPolygon.objects.filter(
                    video_source_id=video_source_id,
                    active=True
                )
                old_count = old_active.count()
                logger.info(f"[ROI] Found {old_count} active ROIs to deactivate")

                old_active.update(active=False)
                logger.info(f"[ROI] Deactivated {old_count} old ROIs")

                created_rois = []
                for idx, poly_data in enumerate(polygons_data):
                    points_data = poly_data.get('points')

                    if isinstance(points_data, list):
                        points_str = json.dumps(points_data)
                        logger.info(f"[ROI] Polygon {idx}: converted list to JSON string")
                    elif isinstance(points_data, str):
                        points_str = points_data
                        logger.info(f"[ROI] Polygon {idx}: using existing JSON string")
                    else:
                        logger.error(f"[ROI] Polygon {idx}: invalid points type: {type(points_data)}")
                        continue

                    try:
                        points_list = json.loads(points_str)
                        if not isinstance(points_list, list) or len(points_list) < 3:
                            logger.error(f"[ROI] Polygon {idx}: invalid points data (need at least 3 points)")
                            continue

                        valid_points = True

                        for p in points_list:
                            if not isinstance(p, list) or len(p) < 2:
                                valid_points = False
                                break
                            if not isinstance(p[0], (int, float)) or not isinstance(p[1], (int, float)):
                                valid_points = False
                                break

                        if not valid_points:
                            logger.error(f"[ROI] Polygon {idx}: invalid coordinate format")
                            continue
                        
                        logger.info(f"[ROI] Polygon {idx}: validated {len(points_list)} points")
                    except json.JSONDecodeError as e:
                        logger.error(f"[ROI] Polygon {idx}: JSON decode error: {e}")
                        continue

                    roi = ROIPolygon.objects.create(
                        video_source_id=video_source_id,
                        name=poly_data.get('name', f'ROI-{timezone.now().timestamp()}'),
                        points=points_str,
                        active=poly_data.get('active', True)
                    )
                    created_rois.append(roi)
                    logger.info(f"[ROI] Created ROI {roi.id}: {roi.name}, active={roi.active}")

                if len(created_rois) == 0:
                    logger.error(f"[ROI] No ROIs were created successfully")
                    raise Exception("Failed to create any ROI")

                logger.info(f"[ROI] Successfully created {len(created_rois)} ROIs")

                final_active = ROIPolygon.objects.filter(
                    video_source_id=video_source_id,
                    active=True
                )
                final_count = final_active.count()
                logger.info(f"[ROI] Final verification: {final_count} active ROIs")

                for roi in final_active:
                    logger.info(f"[ROI] Active ROI: id={roi.id}, name={roi.name}, points_count={len(roi.get_points())}")

                logger.info(f"[ROI] ========== Bulk Replace Success ==========")

            cache_key = f"roi_updated_{video_source_id}"
            current_time = time.time()
            redis_client.set(cache_key, current_time, ex=60)
            logger.info(f"[ROI] Set cache signal AFTER commit: {cache_key} = {current_time}")
            
            return Response({
                'success': True,
                'message': 'ROI polygons replaced successfully',
                'count': len(created_rois),
                'active_count': final_count
            })

        except Exception as e:
            logger.error(f"[ROI] ========== Bulk Replace Failed ==========")
            logger.error(f"[ROI] Error: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class DetectionSettingViewSet(viewsets.ModelViewSet):
    """API endpoint for detection settings"""
    queryset = DetectionSetting.objects.all()
    serializer_class = DetectionSettingSerializer
    permission_classes = [AllowAny]
    csrf_exempt = True

    def get_queryset(self):
        queryset = DetectionSetting.objects.all()
        video_source_id = self.request.query_params.get('video_source', None)

        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        return queryset


@method_decorator(csrf_exempt, name='dispatch')
class ViolationEventViewSet(viewsets.ModelViewSet):
    """API endpoint for violation events"""
    queryset = ViolationEvent.objects.all().order_by('-timestamp')
    serializer_class = ViolationEventSerializer
    permission_classes = [AllowAny]
    csrf_exempt = True

    def get_queryset(self):
        queryset = ViolationEvent.objects.all().order_by('-timestamp')

        video_source_id = self.request.query_params.get('video_source', None)
        if video_source_id is not None:
            queryset = queryset.filter(video_source_id=video_source_id)

        status_param = self.request.query_params.get('status', None)
        if status_param is not None:
            queryset = queryset.filter(status=status_param)

        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date is not None:
            queryset = queryset.filter(timestamp__gte=start_date)

        if end_date is not None:
            queryset = queryset.filter(timestamp__lte=end_date)

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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_detection_json_files(request, source_id):
    """获取某个视频源当前检测会话生成的所有JSON文件列表"""
    try:
        logger.info(f"[JSON_API] 🔍 Getting JSON files for source {source_id}")

        # 从Redis获取当前追踪会话的key
        current_key = redis_client.get(f"current_tracking_{source_id}")

        if not current_key:
            logger.warning(f"[JSON_API] ⚠️ No tracking session found for source {source_id}")

            # ✅ 即使没有会话，也返回 success: True，避免前端判断错误
            return Response({
                'success': True,
                'message': '没有正在追踪的检测会话',
                'files': [],
                'source_id': source_id,
                'total_count': 0
            })

        # 获取所有追踪的文件路径
        file_paths = redis_client.lrange(current_key, 0, -1)
        logger.info(f"[JSON_API] 📋 Found {len(file_paths)} tracked files in Redis")

        # 构建文件信息列表
        files_info = []
        for file_path in file_paths:
            if isinstance(file_path, bytes):
                file_path = file_path.decode('utf-8')

            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"[JSON_API] File not found: {file_path}")
                continue

            try:
                # 读取JSON文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                # 获取文件信息
                file_stat = os.stat(file_path)

                files_info.append({
                    'path': file_path,
                    'filename': os.path.basename(file_path),
                    'size': file_stat.st_size,
                    'timestamp': json_data.get('timestamp', 'Unknown'),
                    'total_violations': json_data.get('total_violations', 0),
                    'class_numbers': json_data.get('class_numbers', {}),
                    'violations': json_data.get('violations', {})
                })
            except Exception as e:
                logger.error(f"[JSON_API] Error reading file {file_path}: {e}")
                continue

        # ✅ 确保返回 Response
        return Response({
            'success': True,
            'files': files_info,
            'source_id': source_id,
            'total_count': len(files_info)
        })

    except Exception as e:
        logger.error(f"[JSON_API] Error getting JSON files for source {source_id}: {e}", exc_info=True)
        # ✅ 错误情况也要返回 Response
        return Response({
            'success': False,
            'error': str(e),
            'source_id': source_id
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def save_selected_json_files(request, source_id):
    """
    保存用户选择的JSON文件，删除未选择的文件

    参数:
        source_id: 视频源ID

    请求体:
        {
            "selected_files": ["/path/to/file1.json", "/path/to/file2.json"]
        }

    返回:
        {
            "success": true/false,
            "kept_count": 5,
            "deleted_count": 10,
            "errors": []
        }
    """
    try:
        logger.info(f"[JSON_API] Saving selected files for source {source_id}")

        # 获取用户选择的文件列表
        selected_files = request.data.get('selected_files', [])

        # 验证输入
        if not isinstance(selected_files, list):
            logger.error(f"[JSON_API] Invalid selected_files type: {type(selected_files)}")
            return Response({
                'success': False,
                'error': 'selected_files必须是数组'
            }, status=400)

        logger.info(f"[JSON_API] User selected {len(selected_files)} files")

        # 获取当前追踪会话的所有文件
        current_key = redis_client.get(f"current_tracking_{source_id}")

        if not current_key:
            logger.warning(f"[JSON_API] No tracking session found for source {source_id}")
            return Response({
                'success': False,
                'message': '没有正在追踪的检测会话'
            })

        # 获取所有追踪的文件
        all_files = redis_client.lrange(current_key, 0, -1)
        all_files = [f.decode('utf-8') if isinstance(f, bytes) else f for f in all_files]

        logger.info(f"[JSON_API] Total tracked files: {len(all_files)}")

        # 删除未被选中的文件
        deleted_count = 0
        kept_count = 0
        errors = []

        for file_path in all_files:
            if file_path not in selected_files:
                # 删除未选中的文件
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"[JSON_CLEANUP] Deleted unselected file: {os.path.basename(file_path)}")
                    else:
                        logger.warning(f"[JSON_CLEANUP] File not found for deletion: {file_path}")
                except PermissionError as e:
                    error_msg = f"权限不足，无法删除 {os.path.basename(file_path)}"
                    errors.append(error_msg)
                    logger.error(f"[JSON_CLEANUP] {error_msg}: {e}")
                except Exception as e:
                    error_msg = f"删除文件失败 {os.path.basename(file_path)}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[JSON_CLEANUP] {error_msg}")
            else:
                # 保留选中的文件
                kept_count += 1
                logger.debug(f"[JSON_CLEANUP] Kept selected file: {os.path.basename(file_path)}")

        # 清除Redis中的追踪数据
        try:
            redis_client.delete(current_key)
            redis_client.delete(f"current_tracking_{source_id}")
            logger.info(f"[JSON_CLEANUP] Cleared tracking data from Redis")
        except Exception as e:
            logger.error(f"[JSON_CLEANUP] Error clearing Redis data: {e}")
            errors.append(f"清除缓存失败: {str(e)}")

        logger.info(
            f"[JSON_CLEANUP] Source {source_id}: "
            f"Kept {kept_count} files, deleted {deleted_count} files, {len(errors)} errors"
        )

        return Response({
            'success': True,
            'source_id': source_id,
            'kept_count': kept_count,
            'deleted_count': deleted_count,
            'errors': errors
        })

    except KeyError as e:
        logger.error(f"[JSON_API] Missing required field: {e}")
        return Response({
            'success': False,
            'error': f'缺少必需字段: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"[JSON_API] Error saving selected JSON files for source {source_id}: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def delete_all_json_files(request, source_id):
    """
    删除某个视频源当前会话的所有JSON文件

    参数:
        source_id: 视频源ID

    返回:
        {
            "success": true/false,
            "deleted_count": 10,
            "errors": []
        }
    """
    try:
        logger.info(f"[JSON_API] Deleting all JSON files for source {source_id}")

        # 获取当前追踪会话
        current_key = redis_client.get(f"current_tracking_{source_id}")

        if not current_key:
            logger.warning(f"[JSON_API] No tracking session found for source {source_id}")
            return Response({
                'success': True,
                'message': '没有需要删除的文件',
                'deleted_count': 0,
                'errors': []
            })

        # 获取所有追踪的文件
        all_files = redis_client.lrange(current_key, 0, -1)
        all_files = [f.decode('utf-8') if isinstance(f, bytes) else f for f in all_files]

        logger.info(f"[JSON_API] Found {len(all_files)} files to delete")

        deleted_count = 0
        errors = []

        # 删除所有文件
        for file_path in all_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"[JSON_CLEANUP] Deleted file: {os.path.basename(file_path)}")
                else:
                    logger.warning(f"[JSON_CLEANUP] File not found: {file_path}")
            except PermissionError as e:
                error_msg = f"权限不足，无法删除 {os.path.basename(file_path)}"
                errors.append(error_msg)
                logger.error(f"[JSON_CLEANUP] {error_msg}: {e}")
            except Exception as e:
                error_msg = f"删除文件失败 {os.path.basename(file_path)}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[JSON_CLEANUP] {error_msg}")

        # 清除Redis中的追踪数据
        try:
            redis_client.delete(current_key)
            redis_client.delete(f"current_tracking_{source_id}")
            logger.info(f"[JSON_CLEANUP] Cleared tracking data from Redis")
        except Exception as e:
            logger.error(f"[JSON_CLEANUP] Error clearing Redis data: {e}")
            errors.append(f"清除缓存失败: {str(e)}")

        logger.info(
            f"[JSON_CLEANUP] Source {source_id}: "
            f"Deleted {deleted_count} files, {len(errors)} errors"
        )

        return Response({
            'success': True,
            'source_id': source_id,
            'deleted_count': deleted_count,
            'errors': errors
        })

    except Exception as e:
        logger.error(f"[JSON_API] Error deleting all JSON files for source {source_id}: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# ========== 辅助函数（可选） ==========

def cleanup_orphaned_json_files(source_id):
    """
    清理孤立的JSON文件（没有被追踪的旧文件）
    可以通过定时任务调用此函数

    参数:
        source_id: 视频源ID

    返回:
        删除的文件数量
    """
    try:
        json_dir = os.path.join(settings.DETECTION_JSON_DIR, str(source_id))

        if not os.path.exists(json_dir):
            logger.info(f"[JSON_CLEANUP] Directory not found: {json_dir}")
            return 0

        # 获取当前追踪的文件
        current_key = redis_client.get(f"current_tracking_{source_id}")
        tracked_files = set()

        if current_key:
            tracked_list = redis_client.lrange(current_key, 0, -1)
            tracked_files = {
                f.decode('utf-8') if isinstance(f, bytes) else f
                for f in tracked_list
            }

        # 遍历目录中的所有JSON文件
        deleted_count = 0
        for filename in os.listdir(json_dir):
            if not filename.endswith('.json'):
                continue

            file_path = os.path.join(json_dir, filename)

            # 如果文件不在追踪列表中，删除它
            if file_path not in tracked_files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"[JSON_CLEANUP] Removed orphaned file: {filename}")
                except Exception as e:
                    logger.error(f"[JSON_CLEANUP] Error removing {filename}: {e}")

        logger.info(f"[JSON_CLEANUP] Cleaned up {deleted_count} orphaned files for source {source_id}")
        return deleted_count

    except Exception as e:
        logger.error(f"[JSON_CLEANUP] Error in cleanup_orphaned_json_files: {e}", exc_info=True)
        return 0
