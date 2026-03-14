import os
import sys
# LOCAL_ULTRALYTICS = r"C:\Users\86151\Desktop\ultralytics-main"
# if os.path.isdir(LOCAL_ULTRALYTICS) and LOCAL_ULTRALYTICS not in sys.path:
#     sys.path.insert(0, LOCAL_ULTRALYTICS)
import cv2
import numpy as np
import time
import torch
from django.conf import settings
from pathlib import Path
import threading
import logging
# from ultralytics import YOLO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class YOLODetector:
    """
    YOLO object detection class that handles model loading and inference.
    Supports CPU, CUDA, and TensorRT acceleration.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one model is loaded in memory"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(YOLODetector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, model_path=None, device='cuda' if torch.cuda.is_available() else 'cpu'):
        """Initialize the YOLO detector with specified model path and device"""
        if self._initialized:
            return

        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.device = device
        self.model = None
        self.class_names = []
        self.load_model()
        self._initialized = True

    def load_model(self):
        try:
            from django.conf import settings
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.conf_thres = settings.DETECTION_CONFIDENCE_THRESHOLD
            self.iou_thres = settings.DETECTION_IOU_THRESHOLD

            self.class_names = getattr(self.model.model, 'names', None) or getattr(self.model, 'names', {})
        except Exception as e:
            logger.error(f"Error loading YOLO model: {e}")
            raise

    def preprocess_frame(self, frame):
        """Preprocess frame before inference (resize, normalize, etc.)"""
        return frame  # YOLOv8 handles preprocessing internally

    def is_point_in_polygon(self, point, polygon):
        """Check if a point is inside a polygon using ray casting algorithm"""
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def filter_detections_by_roi(self, detections, roi_polygons, img_width, img_height):
        """Filter detections to only include those within ROI polygons"""
        if not roi_polygons:
            return detections  # No ROI specified, return all detections

        if img_width == 0 or img_height == 0:
            logger.error(f"[DETECTOR_ERROR] Invalid image size: {img_width}x{img_height}")
            return detections
        
        # Convert normalized coordinates to absolute pixel coordinates
        roi_polygons_absolute = []
        for polygon in roi_polygons:
            absolute_polygon = []
            
            # [修复开始] 检查坐标是否已经是绝对像素值，防止二次相乘导致的数值爆炸
            # 判断逻辑：如果多边形中任何一个点的坐标 > 1.0，则认为是绝对坐标
            is_absolute = False
            for point in polygon:
                # 确保点是数字类型
                if not isinstance(point[0], (int, float)) or not isinstance(point[1], (int, float)):
                    logger.error(f"[ROI_DATA_ERR] Invalid point type in poly {i}: {point}")
                    continue

                if point[0] > 1.1 or point[1] > 1.1: # 使用 1.1 作为容错阈值
                    is_absolute = True
                    break
            
            for point in polygon:
                # 判断是否为归一化坐标 (0.0 ~ 1.1)
                # 我们之前写的 > 1.1 判断逻辑在这里非常关键
                if point[0] > 1.1 or point[1] > 1.1:
                    # 如果收到的是像素值，直接用
                    x_abs = int(point[0])
                    y_abs = int(point[1])
                else:
                    # 收到的是归一化值，乘以视频真实分辨率
                    x_abs = int(point[0] * img_width)
                    y_abs = int(point[1] * img_height)
                
                # 钳制边界，防止崩盘
                x_abs = max(0, min(img_width, x_abs))
                y_abs = max(0, min(img_height, y_abs))
                
                absolute_polygon.append((x_abs, y_abs))
            
            roi_polygons_absolute.append(absolute_polygon)

        filtered_detections = []

        for detection in detections:
            # Get bounding box center point
            x1, y1, x2, y2 = map(int, detection['bbox'])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Check if center point is inside any ROI polygon
            for polygon in roi_polygons_absolute:
                if self.is_point_in_polygon((center_x, center_y), polygon):
                    filtered_detections.append(detection)
                    break

        return filtered_detections
    
    def detect(self, frame, confidence_threshold=None, iou_threshold=None, roi_polygons=None, target_classes=None):
        """
        Perform detection on a frame

        Args:
            frame: Input image frame (numpy array)
            confidence_threshold: Detection confidence threshold (0-1)
            iou_threshold: IoU threshold for NMS (0-1)
            roi_polygons: List of ROI polygons to filter detections
            target_classes: List of class IDs to detect (None for all)

        Returns:
            List of detection dictionaries with bbox, class_id, class_name, confidence
        """
        if self.model is None:
            logger.error("Model not loaded")
            return []

        conf = confidence_threshold if confidence_threshold is not None else getattr(self, 'conf_thres', 0.5)
        iou = iou_threshold if iou_threshold is not None else getattr(self, 'iou_thres', 0.45)

        try:
            results = self.model.predict(frame, conf=conf, iou=iou, verbose=False, classes=target_classes)
            res = results[0]
            detections = []
            names = self.class_names or res.names


            if hasattr(res, 'boxes') and res.boxes is not None:
                for b in res.boxes:
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    conf_ = float(b.conf.item())
                    cls = int(b.cls.item())
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'class_id': cls,
                        'class_name': names.get(cls, f"Class {cls}") if isinstance(names, dict) else str(cls),
                        'confidence': conf_
                    })


            if roi_polygons:
                detections = self.filter_detections_by_roi(detections, roi_polygons, frame.shape[1], frame.shape[0])

            return detections
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return []

    def draw_detections(self, frame, detections, draw_labels=True, thickness=2):
        """Draw detection boxes and labels on the frame"""
        img = frame.copy()

        for detection in detections:
            # Extract information
            x1, y1, x2, y2 = map(int, detection['bbox'])
            class_name = detection['class_name']
            confidence = detection['confidence']

            # Draw bounding box
            color = (0, 255, 0)  # Green box for detected objects
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

            # Draw label
            if draw_labels:
                label = f"{class_name}: {confidence:.2f}"
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(img, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
                cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        return img

    def draw_roi_polygons(self, frame, roi_polygons):
        """Draw ROI polygons on the frame with bright red outlines"""
        img = frame.copy()
        height, width = img.shape[:2]
        
        for i, polygon in enumerate(roi_polygons):
            points = []
            for point in polygon:
                x = int(point[0] * width)
                y = int(point[1] * height)
                points.append((x, y))

            if len(points) >= 3:  # Valid polygon
                points_array = np.array(points, np.int32)
                points_array = points_array.reshape((-1, 1, 2))
                
                # Draw thick red outline
                cv2.polylines(img, [points_array], True, (0, 0, 255), 5)  # BGR red, thick
                
                # Add ROI label
                center_x = int(np.mean([p[0] for p in points]))
                center_y = int(np.mean([p[1] for p in points]))
                cv2.putText(img, f"ROI-{i+1}", (center_x-30, center_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return img

    def extract_snapshot(self, frame, detection, zoom_factor=2.0):
        """Extract and zoom a snapshot of the detected object"""
        x1, y1, x2, y2 = map(int, detection['bbox'])

        # Ensure coordinates are within frame bounds
        height, width = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)

        # Extract region
        object_region = frame[y1:y2, x1:x2]

        if object_region.size == 0:
            return None  # Empty region

        # Calculate new dimensions
        new_height = int((y2 - y1) * zoom_factor)
        new_width = int((x2 - x1) * zoom_factor)

        # Resize using bilinear interpolation
        zoomed = cv2.resize(object_region, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        return zoomed