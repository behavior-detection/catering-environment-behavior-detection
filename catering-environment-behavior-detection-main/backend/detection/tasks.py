import os
import cv2
import time
import json
import base64
import logging
import numpy as np
from datetime import datetime
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
import redis
from django.core.cache import cache
from celery.result import AsyncResult

from .models import VideoSource, ROIPolygon, DetectionSetting, ViolationEvent
from .yolo.video_source import VideoSourceManager
from django.core.cache import cache

logger = logging.getLogger(__name__)

YOLO_MODEL = None

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', '127.0.0.1'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)


def get_yolo_model():
    global YOLO_MODEL
    if YOLO_MODEL is None:
        # Force project-local caches for reproducibility
        os.environ.setdefault('TORCH_HOME', str(settings.BASE_DIR / '.cache' / 'torch'))
        os.makedirs(os.environ['TORCH_HOME'], exist_ok=True)

        from ultralytics import YOLO
        model_path = settings.YOLO_MODEL_PATH
        YOLO_MODEL = YOLO(model_path)

        # Device from env, default cpu
        device = os.getenv('YOLO_DEVICE', 'cpu')
        try:
            YOLO_MODEL.to(device)
        except Exception:
            logger.warning(f"Could not move YOLO model to device '{device}', using default.")
    return YOLO_MODEL


CLASSES = ["person", "mask", "hat", "uniform", "mouse", "phone", "cigarette"]
PPE_CLASSES = {"mask", "hat", "uniform"}
OCCURRENCE_ONLY = {"mouse", "phone", "cigarette"}

# Color map (BGR) for drawing per class; fallback palette used if class missing
CLASS_COLOR_MAP = {
    "person": (0, 255, 0),  # green
    "mask": (255, 0, 0),  # blue
    "hat": (0, 165, 255),  # orange
    "uniform": (255, 0, 255),  # magenta
    "mouse": (128, 128, 128),  # gray
    "phone": (255, 255, 0),  # yellow (BGR)
    "cigarette": (0, 0, 255),  # red
}

COLOR_PALETTE = [
    (0, 255, 0), (255, 0, 0), (0, 165, 255), (255, 0, 255),
    (255, 255, 0), (255, 0, 127), (127, 255, 212), (0, 255, 255)
]


def _color_for_class(name, class_id=None):
    if name in CLASS_COLOR_MAP:
        return CLASS_COLOR_MAP[name]
    if class_id is not None:
        return COLOR_PALETTE[class_id % len(COLOR_PALETTE)]
    return (0, 255, 0)


os.makedirs(settings.DETECTION_JSON_DIR, exist_ok=True)


def _encode_bgr_to_base64(img_bgr):
    _, buffer = cv2.imencode(".jpg", img_bgr)
    return base64.b64encode(buffer).decode("utf-8")


def _build_json_from_result(res, camera_id, ts_str):
    class_numbers = {c: 0 for c in CLASSES}
    names = res.names
    if getattr(res, "boxes", None) is not None:
        for b in res.boxes:
            cls = int(b.cls.item())
            name = names.get(cls, str(cls)) if isinstance(names, dict) else str(cls)
            if name in class_numbers:
                class_numbers[name] += 1
    person_cnt = class_numbers["person"]
    violations = {}
    for cls in CLASSES:
        if cls == "person":
            violations[cls] = 0
        elif cls in PPE_CLASSES:
            violations[cls] = max(0, person_cnt - class_numbers[cls])
        else:
            violations[cls] = class_numbers[cls]
    return {
        "camera_id": camera_id,
        "timestamp": ts_str,
        "class_numbers": class_numbers,
        "violations": violations,
        "total_violations": int(sum(violations.values())),
    }


def _polys_to_pixel(polys, img_w, img_h):
    px_polys = []
    logger.debug(f"[ROI] Converting {len(polys or [])} polygons for image {img_w}x{img_h}")
    for i, poly in enumerate(polys or []):
        if not poly or len(poly) < 3:  # 忽略无效多边形
            continue

        # [修复] 强制转换为 float 列表，防止混入字符串
        try:
            clean_poly = [[float(p[0]), float(p[1])] for p in poly]
        except (ValueError, TypeError):
            logger.error(f"[ROI] Invalid coordinates in polygon {i}")
            continue

        # Check if coordinates are already in pixel format (>1.1)
        is_pixel = any(p[0] > 1.1 or p[1] > 1.1 for p in clean_poly)

        if is_pixel:
            # 如果是像素坐标，不做乘法
            px = np.array(clean_poly, dtype=np.float32)
        else:
            # 如果是归一化坐标，乘以宽高
            px = np.array([[p[0] * img_w, p[1] * img_h] for p in clean_poly], dtype=np.float32)

        # [修复] 转换为 int32 之前进行边界钳制 (Clamp)，防止越界导致 OpenCV 错误
        px[:, 0] = np.clip(px[:, 0], 0, img_w)  # 限制 x
        px[:, 1] = np.clip(px[:, 1], 0, img_h)  # 限制 y

        px_polys.append(px.astype(np.int32))
    return px_polys


def _filter_res_by_roi(res, roi_polygons, img_w, img_h):
    if not roi_polygons or getattr(res, "boxes", None) is None or len(res.boxes) == 0:
        logger.info(
            f"[ROI_FILTER] Skip filtering: roi_count={len(roi_polygons or [])}, boxes={len(res.boxes) if hasattr(res, 'boxes') and res.boxes is not None else 0}")
        return res

    data = res.boxes.data
    cx = (data[:, 0] + data[:, 2]) / 2
    cy = (data[:, 1] + data[:, 3]) / 2
    keep = np.zeros(len(data), dtype=bool)

    logger.debug(f"[ROI] Image size: {img_w}x{img_h}")
    logger.debug(f"[ROI] Detection bboxes (first 3): {data[:3, :4].tolist() if len(data) > 0 else 'none'}")
    logger.debug(
        f"[ROI] Detection centers (first 3): {list(zip(cx[:3].tolist(), cy[:3].tolist())) if len(cx) > 0 else 'none'}")
    logger.info(
        f"[ROI_FILTER] Processing {len(data)} detections against {len(roi_polygons)} ROIs. Image: {img_w}x{img_h}")

    for i, poly_px in enumerate(_polys_to_pixel(roi_polygons, img_w, img_h)):
        logger.debug(f"[ROI] Testing polygon {i} with pixel coords: {poly_px.tolist()}")
        inside_count = 0
        for j, (x, y) in enumerate(zip(cx, cy)):
            test_result = cv2.pointPolygonTest(poly_px, (float(x), float(y)), False)
            if test_result >= 0:
                inside_count += 1
                logger.debug(f"[ROI] Detection {j} center ({x:.1f},{y:.1f}) is INSIDE polygon {i}")
            else:
                logger.debug(f"[ROI] Detection {j} center ({x:.1f},{y:.1f}) is OUTSIDE polygon {i}")

        mask = [cv2.pointPolygonTest(poly_px, (float(x), float(y)), False) >= 0 for x, y in zip(cx, cy)]
        keep |= np.array(mask, dtype=bool)
        logger.info(f"[ROI] Polygon {i}: {inside_count} detections inside")

    # 打印最终结果
    logger.info(f"[ROI_FILTER] Final result: {len(data)} -> {np.sum(keep)} detections kept")
    res.boxes.data = data[keep]
    return res


# ---------- Unified helpers (ROI load & render) ----------
def _load_active_roi_polygons(source):
    try:
        # 强制刷新
        if hasattr(source, 'refresh_from_db'):
            source.refresh_from_db()

        polys = []
        rois = ROIPolygon.objects.filter(video_source=source, active=True)

        logger.info(f"[ROI_LOAD] Found {rois.count()} ROI records in DB")

        for r in rois:
            try:
                # 假设 get_points 返回的是 list，如果报错则捕获
                pts = r.get_points()

                # 增加数据校验
                if not isinstance(pts, list):
                    logger.warning(f"[ROI_LOAD] ROI {r.id} points is not a list: {type(pts)}")
                    continue

                if len(pts) >= 3:
                    polys.append(pts)
                else:
                    logger.warning(f"[ROI_LOAD] ROI {r.id} has insufficient points: {len(pts)}")

            except Exception as e:
                logger.error(f"[ROI_LOAD] Error parsing ROI {r.id}: {e}")
                continue

        return polys
    except Exception as e:
        logger.error(f"[ROI_LOAD_FATAL] Failed to load ROIs: {e}", exc_info=True)
        return []  # 即使出错也返回空列表，不要让任务崩溃


def _render_with_optional_roi(frame_bgr, res, use_roi, roi_polygons):
    """Apply ROI filter, draw detections, then (optionally) draw ROI outlines."""
    h, w = frame_bgr.shape[:2]
    if use_roi and roi_polygons:
        res = _filter_res_by_roi(res, roi_polygons, w, h)
    dets = _results_to_detections(res)
    vis = _draw_detections(frame_bgr, dets)
    if use_roi and roi_polygons:
        vis = _draw_roi_regions(vis, roi_polygons, w, h)
    return vis, dets, res


# --------------------------------------------------------


def _results_to_detections(res):
    dets = []
    names = res.names
    if getattr(res, "boxes", None) is not None:
        for b in res.boxes:
            dets.append({
                "bbox": b.xyxy[0].tolist(),
                "class_id": int(b.cls.item()),
                "class_name": names.get(int(b.cls.item()), str(int(b.cls.item()))) if isinstance(names, dict) else str(
                    int(b.cls.item())),
                "confidence": float(b.conf.item())
            })
    return dets


def _draw_detections(img_bgr, detections):
    vis = img_bgr.copy()

    # Calculate dynamic line width and font parameters based on image size
    img_height, img_width = img_bgr.shape[:2]
    base_size = (img_width + img_height) / 2

    # Dynamic line width (thinner than before)
    line_width = max(round(base_size * 0.002), 1)

    # Optimized font parameters for maximum clarity
    font_scale = max(base_size * 0.0003, 0.20)  # Smaller font
    font_thickness = 1  # Always use thickness 1 for maximum clarity

    for d in detections:
        x1, y1, x2, y2 = map(int, d["bbox"])
        color = _color_for_class(d.get("class_name"), d.get("class_id"))

        # Draw bounding box with dynamic line width
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, line_width, cv2.LINE_AA)

        # Prepare label text
        label = f'{d["class_name"]} {d["confidence"]:.2f}'
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Get text size with optimized parameters
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

        # Calculate text background position with minimal padding
        bg_x1 = x1
        bg_y1 = max(0, y1 - text_h - baseline - 1)  # Minimal padding
        bg_x2 = min(vis.shape[1] - 1, x1 + text_w + 4)  # Minimal padding
        bg_y2 = y1

        # Draw text background (filled rectangle)
        cv2.rectangle(vis, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1, cv2.LINE_AA)

        # Calculate text color based on background color for better contrast
        text_color = _get_text_color(color)

        # Draw text with optimized parameters for maximum clarity
        cv2.putText(
            vis,
            label,
            (bg_x1 + 2, bg_y2 - 1),
            font,
            font_scale,
            text_color,
            font_thickness,  # Always 1 for clarity
            cv2.LINE_AA
        )

    return vis


def _get_text_color(bg_color):
    """Calculate optimal text color based on background color for better readability"""
    # Calculate brightness using standard formula
    b, g, r = bg_color
    brightness = (0.299 * r + 0.587 * g + 0.114 * b)

    # Return white text for dark backgrounds, dark text for light backgrounds
    if brightness < 127:
        return (255, 255, 255)  # White text
    else:
        return (0, 0, 0)  # Black text


@shared_task
def process_frame(source_id, use_roi=False):
    try:
        try:
            source = VideoSource.objects.get(id=source_id, active=True)
        except VideoSource.DoesNotExist:
            logger.warning(f"Video source {source_id} not found or not active")
            return None

        manager = VideoSourceManager()
        video_source = manager.get_source(source_id)
        if not video_source or not video_source.is_running():
            video_source = manager.add_source(
                source_id=source_id,
                source_type=source.source_type,
                source_url=source.source_url,
                width=source.resolution_width,
                height=source.resolution_height,
                buffer_size=5,
                target_fps=settings.DETECTION_FRAME_RATE,
            )
            if not video_source or not video_source.is_running():
                logger.error(f"Failed to start video source {source_id}")
                return None

        # Load ROI polygons if enabled
        roi_polygons = _load_active_roi_polygons(source) if use_roi else []

        frame_info = video_source.get_frame(timeout=1.0)
        if frame_info is None:
            logger.warning(f"No frame received from source {source_id}")
            return None

        frame_bgr = cv2.cvtColor(frame_info["frame"], cv2.COLOR_RGB2BGR)

        res = get_yolo_model().predict(
            frame_bgr,
            conf=settings.DETECTION_CONFIDENCE_THRESHOLD,
            iou=settings.DETECTION_IOU_THRESHOLD,
            verbose=False
        )[0]

        # unified render
        vis, dets, res = _render_with_optional_roi(frame_bgr, res, use_roi, roi_polygons)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"video_{source_id}",
            {
                "type": "send_frame",
                "frame": _encode_bgr_to_base64(vis),
                "timestamp": frame_info["timestamp"],
                "source_id": source_id,
                "detections": dets,
            },
        )
        return {"source_id": source_id, "processed": True}
    except Exception as e:
        logger.error(f"Error processing frame for source {source_id}: {e}", exc_info=True)
        return None


# 辅助函数：使用 Redis 强制互斥
def _stop_existing_task(source_id):
    """使用 Redis 锁强制终止旧任务"""
    lock_key = f"task_lock_{source_id}"  # 专门的锁 Key
    old_task_id = redis_client.get(lock_key)  # 直接读 Redis

    if old_task_id:
        logger.info(f"[TASK_CONTROL] Found existing task {old_task_id} in Redis, killing it...")
        try:
            # 强行终止
            AsyncResult(old_task_id).revoke(terminate=True, signal='SIGKILL')
            # 此时不要急着删 key，让新任务去覆盖，或者等它自然过期
        except Exception as e:
            logger.error(f"[TASK_CONTROL] Failed to revoke task {old_task_id}: {e}")


@shared_task(bind=True)
def continuous_detection(self, source_id, duration=None, use_roi=False):
    # 互斥
    _stop_existing_task(source_id)

    # 抢占锁
    task_id = self.request.id
    lock_key = f"task_lock_{source_id}"
    redis_client.setex(lock_key, 86400, task_id)

    logger.info(f"[TASK_START] Started task {task_id}, acquired lock {lock_key}")

    manager = VideoSourceManager()
    try:

        # ========== 开始JSON文件追踪 ==========
        tracking_key = _start_json_tracking(source_id)
        logger.info(f"[JSON_TRACKING] Started tracking for source {source_id}: {tracking_key}")

        try:
            source = VideoSource.objects.get(id=source_id, active=True)
        except VideoSource.DoesNotExist:
            logger.warning(f"Video source {source_id} not found or not active")
            return None

        start_time = time.time()
        manager = VideoSourceManager()
        video_source = manager.add_source(
            source_id=source_id,
            source_type=source.source_type,
            source_url=source.source_url,
            width=source.resolution_width,
            height=source.resolution_height,
            buffer_size=5,
            target_fps=settings.DETECTION_FRAME_RATE,
        )

        if not video_source or not video_source.is_running():
            logger.error(f"Failed to start video source {source_id}")
            return None

        # 加载ROI多边形（如果启用）
        roi_polygons = _load_active_roi_polygons(source) if use_roi else []
        cache_key = f"roi_updated_{source_id}"
        last_roi_update_time = 0

        channel_layer = get_channel_layer()
        frame_count = 0

        # 主检测循环
        while source.active:
            current_lock = redis_client.get(lock_key)
            if current_lock and current_lock != task_id:
                logger.warning(f"[TASK_SUICIDE] Lock stolen by {current_lock}, task {task_id} exiting.")
                break

            if duration and (time.time() - start_time) > duration:
                break

            try:
                source.refresh_from_db()
                if not source.active:
                    break
            except VideoSource.DoesNotExist:
                break

            # 获取视频帧
            frame_info = video_source.get_frame(timeout=1.0)
            if frame_info is None:
                time.sleep(0.05)
                continue

            frame_rgb = frame_info["frame"]
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # 检查ROI是否有更新
            if use_roi:
                cached_val = redis_client.get(cache_key)
                current_update_time = float(cached_val) if cached_val else 0

                if current_update_time > last_roi_update_time:
                    logger.info(f"[ROI] Detected update! Reloading ROIs...")
                    # 重新从数据库加载
                    roi_polygons = _load_active_roi_polygons(source)
                    # 更新本地时间戳
                    last_roi_update_time = current_update_time

            # YOLO检测
            res = get_yolo_model().predict(
                frame_bgr,
                conf=settings.DETECTION_CONFIDENCE_THRESHOLD,
                iou=settings.DETECTION_IOU_THRESHOLD,
                verbose=False
            )[0]

            try:
                # 渲染检测结果（带ROI过滤）
                vis, dets, res = _render_with_optional_roi(frame_bgr, res, use_roi, roi_polygons)
            except Exception as e:
                logger.error(f"[RENDER_ERROR] Error rendering ROI/Detections: {e}")
                # 如果渲染失败，降级为显示原始画面，防止黑屏
                vis = frame_bgr
                dets = []
            # res 保持不变或设为空

            ts = frame_info["timestamp"]
            ts_str = time.strftime("%H:%M:%S", time.localtime(ts))

            # ========== 修改：保存JSON文件并追踪 ==========
            json_dir = os.path.join(settings.DETECTION_JSON_DIR, str(source.id))
            os.makedirs(json_dir, exist_ok=True)

            # 文件名格式：ts_时间戳.json
            json_filename = f"ts_{int(ts)}.json"
            json_filepath = os.path.join(json_dir, json_filename)

            # 保存JSON文件
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    _build_json_from_result(res, camera_id=source.name, ts_str=ts_str),
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            # 👉 新增：将文件路径添加到追踪列表
            _add_json_file(source_id, json_filepath)
            logger.debug(f"[JSON_TRACKING] Added file: {json_filename}")

            # 通过WebSocket发送检测帧
            async_to_sync(channel_layer.group_send)(
                f"video_{source_id}",
                {
                    "type": "send_frame",
                    "frame": _encode_bgr_to_base64(vis),
                    "timestamp": ts,
                    "source_id": source_id,
                    "detections": dets,
                },
            )

            frame_count += 1
            time.sleep(0.01)

        # 清理资源
        manager.remove_source(source_id)

        # ========== 返回追踪的文件信息 ==========
        tracked_files = _get_tracked_files(source_id)
        logger.info(
            f"[JSON_TRACKING] Continuous detection completed for source {source_id}. "
            f"Processed {frame_count} frames, generated {len(tracked_files)} JSON files."
        )

        # 通过 WebSocket 发送处理完成消息通知前端
        async_to_sync(channel_layer.group_send)(
            f"video_{source_id}",
            {
                "type": "send_processing_complete",  # 对应 consumers.py 中的处理函数
                "source_id": source_id,
                "processed_frames": frame_count,
                "violations_detected": 0,  # 如果有统计变量可填入
                "duration": time.time() - start_time,
                "json_files_count": len(tracked_files)
            },
        )

        return {"status": "completed", "frames": frame_count}

    except Exception as e:
        logger.error(f"Error in continuous detection for source {source_id}: {e}", exc_info=True)
        return None

    finally:
        logger.info(f"[TASK_CLEANUP] Task {task_id} finishing...")
        manager.remove_source(source_id)

        if redis_client.get(lock_key) == task_id:
            redis_client.delete(lock_key)
            logger.info(f"[TASK_UNLOCK] Released lock for {source_id}")


@shared_task(bind=True)
def process_video_detection(self, source_id, use_roi=False):
    print(f"============== DEBUG: 任务进入 Celery, ID: {source_id} ==============")
    # 1. 互斥检查
    _stop_existing_task(source_id)

    # 2. 注册新任务
    task_id = self.request.id
    cache.set(f"detection_task_{source_id}", task_id, timeout=86400)

    logger.info(f"[TASK_START] Started file detection task {task_id} for source {source_id}")

    try:
        # ========== 初始化阶段的保护 ==========
        try:
            _start_json_tracking(source_id)  # 启动JSON文件追踪会话（必须在主循环前调用）
            # 验证视频源
            source = VideoSource.objects.get(id=source_id)
            if source.source_type != "file":
                logger.error(f"Source {source_id} is not a file type")
                return None

            # 构建视频路径
            video_path = os.path.join(settings.MEDIA_ROOT, source.source_url)
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None

            # 打开视频
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return None

            # [关键点] 加载 ROI 数据 - 这里最容易崩
            roi_polygons = []
            if use_roi:
                logger.info(f"[DEBUG_INIT] Loading ROI polygons for source {source_id}...")
                roi_polygons = _load_active_roi_polygons(source)
                logger.info(f"[DEBUG_INIT] Loaded {len(roi_polygons)} polygons: {roi_polygons}")

            # 初始化其他变量
            roi_cache_key = f"roi_updated_{source_id}"
            cached_val = redis_client.get(roi_cache_key)
            last_roi_update_time = float(cached_val) if cached_val else 0

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if fps else 0
            channel_layer = get_channel_layer()
            frame_idx = 0

            logger.info("[DEBUG_INIT] Initialization successful, entering loop...")

        except Exception as e:
            logger.error(f"[CRITICAL_INIT_FAIL] Task died BEFORE loop: {e}", exc_info=True)
            return None  # 初始化失败直接退出

        # ========== 主循环 ==========
        while True:
            if cache.get(f"detection_task_{source_id}") != task_id:
                logger.warning(f"[TASK_ABORT] Task {task_id} superseded by new task, stopping.")
                break

            # 检查源是否被停用（允许用户中断处理）
            try:
                source.refresh_from_db()
                if not source.active:
                    logger.info(f"Source {source_id} deactivated, stopping video file processing.")
                    break
            except VideoSource.DoesNotExist:
                logger.warning(f"Source {source_id} was deleted, stopping processing.")
                break

            # 读取视频帧
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if frame_idx % 10 == 0:
                print(f"[DEBUG_TRACE] Processing frame {frame_idx}, use_roi={use_roi}")

            time.sleep(0.001)

            frame_idx += 1

            # 检查ROI是否有更新
            if use_roi:
                cached_val = redis_client.get(roi_cache_key)
                current_update_time = float(cached_val) if cached_val else 0

                logger.info(
                    f"Last update: {last_roi_update_time}, Current in cache: {current_update_time}"
                )

                if current_update_time > last_roi_update_time:
                    logger.info(
                        f"[ROI] Video file processing: Detected ROI update for source {source_id}. Reloading."
                    )
                    roi_polygons = _load_active_roi_polygons(source)
                    last_roi_update_time = current_update_time

            # YOLO检测
            try:
                # print(f"[DEBUG_TRACE] Frame {frame_idx}: Entering YOLO predict") # 调试用
                res = get_yolo_model().predict(
                    frame_bgr,
                    conf=settings.DETECTION_CONFIDENCE_THRESHOLD,
                    iou=settings.DETECTION_IOU_THRESHOLD,
                    verbose=False
                )[0]
            # print(f"[DEBUG_TRACE] Frame {frame_idx}: YOLO predict done") # 调试用
            except Exception as e:
                logger.error(f"[CRITICAL_FAIL] YOLO Predict Failed: {e}")
                continue

            try:
                h, w = frame_bgr.shape[:2]
                if use_roi:
                    # print(f"[DEBUG_TRACE] Frame {frame_idx}: Start Rendering with ROI. Img size: {w}x{h}")
                    # print(f"[DEBUG_TRACE] ROI Data: {roi_polygons}")
                    pass

                vis, dets, res = _render_with_optional_roi(frame_bgr, res, use_roi, roi_polygons)

            # print(f"[DEBUG_TRACE] Frame {frame_idx}: Rendering Success")
            except Exception as e:
                logger.error(f"[CRITICAL_FAIL] Render/ROI Failed at frame {frame_idx}: {e}", exc_info=True)
                # 降级处理：如果渲染挂了，至少把原图发回去，证明连接没断
                vis = frame_bgr
                dets = []

            # 计算时间戳字符串
            ts_str = f"{int((frame_idx / fps) // 60):02d}:{int((frame_idx / fps) % 60):02d}" if fps else time.strftime(
                "%H:%M:%S")

            # ========== 保存JSON文件并追踪 ==========
            json_dir = os.path.join(settings.DETECTION_JSON_DIR, str(source.id))
            os.makedirs(json_dir, exist_ok=True)

            # 文件名格式：frame_帧号.json
            json_filename = f"frame_{frame_idx:06d}.json"
            json_filepath = os.path.join(json_dir, json_filename)

            # 保存JSON文件
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    _build_json_from_result(res, camera_id=source.name, ts_str=ts_str),
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            # 将文件路径添加到追踪列表
            _add_json_file(source_id, json_filepath)
            if frame_idx % 100 == 0:  # 每100帧记录一次日志
                logger.debug(f"[JSON_TRACKING] Processed {frame_idx} frames, added {json_filename}")

            # 通过WebSocket发送检测帧和进度
            async_to_sync(channel_layer.group_send)(
                f"video_{source_id}",
                {
                    "type": "send_frame",
                    "frame": _encode_bgr_to_base64(vis),
                    "timestamp": time.time(),
                    "video_timestamp": frame_idx / fps if fps else 0,
                    "source_id": source_id,
                    "detections": dets,
                    "progress": round(100 * frame_idx / frame_count) if frame_count > 0 else 0,
                },
            )

        # 释放视频资源
        cap.release()

        # ========== 新增：获取追踪的文件信息并发送完成消息 ==========
        tracked_files = _get_tracked_files(source_id)
        logger.info(
            f"[JSON_TRACKING] Video file processing completed for source {source_id}. "
            f"Processed {frame_idx} frames, generated {len(tracked_files)} JSON files."
        )

        # 发送处理完成的消息
        async_to_sync(channel_layer.group_send)(
            f"video_{source_id}",
            {
                "type": "send_processing_complete",
                "source_id": source_id,
                "processed_frames": frame_idx,
                "violations_detected": 0,
                "duration": frame_idx / fps if fps else 0,
                "json_files_count": len(tracked_files)  # 返回JSON文件数量
            },
        )

        return {
            "source_id": source_id,
            "processed_frames": frame_idx,
            "json_files_count": len(tracked_files),
            # "tracking_key": tracking_key
        }

    except Exception as e:
        print(f"============== DEBUG: 任务崩溃: {e} ==============")
        logger.error(f"Error processing video detection for source {source_id}: {e}", exc_info=True)
        return None
    finally:
        # 3. 清理
        current_recorded_id = cache.get(f"detection_task_{source_id}")
        if current_recorded_id == task_id:
            cache.delete(f"detection_task_{source_id}")


def _draw_roi_regions(img_bgr, roi_polygons, img_w, img_h):
    """Draw ROI regions with clear, visible outlines"""
    vis = img_bgr.copy()

    # line width / font
    base_size = (img_w + img_h) / 2
    roi_line_width = max(round(base_size * 0.003), 2)
    roi_font_scale = max(base_size * 0.0008, 0.5)
    roi_font_thickness = 1
    roi_color = (255, 255, 0)  # keep your color

    # CRITICAL: use the same pixel-conversion as filtering
    for i, pts in enumerate(_polys_to_pixel(roi_polygons, img_w, img_h)):
        if pts is None or len(pts) < 3:
            continue

        # outline
        cv2.polylines(vis, [pts], True, roi_color, roi_line_width, cv2.LINE_AA)

        # corner dots
        for p in pts:
            cv2.circle(vis, tuple(p), max(2, roi_line_width), roi_color, -1, cv2.LINE_AA)

        # label
        center_x = int(np.mean(pts[:, 0]))
        center_y = int(np.mean(pts[:, 1]))
        roi_label = f"ROI-{i + 1}"
        (label_w, label_h), _ = cv2.getTextSize(
            roi_label, cv2.FONT_HERSHEY_SIMPLEX, roi_font_scale, roi_font_thickness
        )

        text_bg_x1 = center_x - label_w // 2 - 3
        text_bg_y1 = center_y - label_h // 2 - 3
        text_bg_x2 = center_x + label_w // 2 + 3
        text_bg_y2 = center_y + label_h // 2 + 3

        overlay = vis.copy()
        cv2.rectangle(overlay, (text_bg_x1, text_bg_y1), (text_bg_x2, text_bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(vis, 0.7, overlay, 0.3, 0, vis)

        cv2.putText(
            vis,
            roi_label,
            (center_x - label_w // 2, center_y + label_h // 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            roi_font_scale,
            (255, 255, 255),
            roi_font_thickness,
            cv2.LINE_AA,
        )

    return vis


# JSON文件追踪功能
def _get_json_tracking_key(source_id):
    """获取当前检测会话的JSON文件追踪键"""
    return f"json_files_{source_id}_{int(time.time())}"


def _start_json_tracking(source_id):
    """开始新的JSON文件追踪会话"""
    tracking_key = _get_json_tracking_key(source_id)
    redis_client.delete(tracking_key)  # 清除可能存在的旧数据
    redis_client.set(f"current_tracking_{source_id}", tracking_key, ex=3600)  # 1小时过期
    logger.info(f"[JSON_TRACKING] Started tracking session: {tracking_key}")
    return tracking_key


def _add_json_file(source_id, file_path):
    """添加JSON文件到当前追踪会话"""
    current_key = redis_client.get(f"current_tracking_{source_id}")
    if current_key:
        redis_client.rpush(current_key, file_path)
        logger.debug(f"[JSON_TRACKING] Added file: {file_path}")


def _get_tracked_files(source_id):
    """获取当前会话追踪的所有JSON文件"""
    current_key = redis_client.get(f"current_tracking_{source_id}")
    if current_key:
        files = redis_client.lrange(current_key, 0, -1)
        return [f.decode() if isinstance(f, bytes) else f for f in files]
    return []


def _cleanup_unselected_files(source_id, selected_files):
    """删除未被选中的JSON文件"""
    all_files = _get_tracked_files(source_id)
    deleted_count = 0

    for file_path in all_files:
        if file_path not in selected_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"[JSON_CLEANUP] Deleted: {file_path}")
            except Exception as e:
                logger.error(f"[JSON_CLEANUP] Error deleting {file_path}: {e}")

    # 清除追踪数据
    current_key = redis_client.get(f"current_tracking_{source_id}")
    if current_key:
        redis_client.delete(current_key)
    redis_client.delete(f"current_tracking_{source_id}")

    logger.info(f"[JSON_CLEANUP] Deleted {deleted_count} unselected files, kept {len(selected_files)} files")
    return deleted_count