import cv2
import numpy as np
import threading
import time
import queue
import logging
import os
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VideoSource:
    """
    Video source manager that handles camera/RTSP/file streams
    and provides frames for processing in an asynchronous way
    """

    def __init__(self, source_id, source_type, source_url,
                 width=640, height=480, buffer_size=30, target_fps=15):
        """
        Initialize the video source

        Args:
            source_id: Unique identifier for this source
            source_type: Type of source ('camera', 'rtsp', 'file')
            source_url: URL or index for the source
            width: Target width for frames
            height: Target height for frames
            buffer_size: Number of frames to buffer
            target_fps: Target frame rate for processing
        """
        self.source_id = source_id
        self.source_type = source_type
        self.source_url = source_url
        self.width = width
        self.height = height
        self.buffer_size = buffer_size
        self.target_fps = target_fps

        # Video capture object
        self.cap = None
        self.frame_count = 0
        self.fps = 0

        # Threading and synchronization
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.lock = threading.Lock()
        self.capture_thread = None

        # Metrics
        self.last_frame_time = 0
        self.current_fps = 0
        self.frames_processed = 0
        self.recent_latencies = deque(maxlen=100)  # Store last 100 frame latencies

    def open(self):
        """Open the video source"""
        try:
            if self.source_type == 'camera':
                # Camera index could be an integer or a string
                try:
                    source_index = int(self.source_url)
                except ValueError:
                    source_index = self.source_url
                self.cap = cv2.VideoCapture(source_index)
            elif self.source_type == 'rtsp':
                # Set buffer size for RTSP stream to reduce latency
                self.cap = cv2.VideoCapture(self.source_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time
            elif self.source_type == 'file':
                if not os.path.exists(self.source_url):
                    raise FileNotFoundError(f"Video file not found: {self.source_url}")
                self.cap = cv2.VideoCapture(self.source_url)
            else:
                raise ValueError(f"Unsupported source type: {self.source_type}")

            # Check if camera opened successfully
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open video source: {self.source_url}")

            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # Get actual resolution and FPS
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)

            # For video files, get frame count
            if self.source_type == 'file':
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            logger.info(f"Opened {self.source_type} source: {self.source_url}, "
                        f"Resolution: {self.width}x{self.height}, FPS: {self.fps}")

            return True

        except Exception as e:
            logger.error(f"Error opening video source: {e}")
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            return False

    def start(self):
        """Start capturing frames in a separate thread"""
        if self.cap is None and not self.open():
            return False

        with self.lock:
            if self.running:
                return True  # Already running

            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            logger.info(f"Started capture thread for source {self.source_id}")
            return True

    def stop(self):
        """Stop capturing frames"""
        with self.lock:
            self.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
            self.capture_thread = None

        if self.cap:
            self.cap.release()
            self.cap = None

        # Clear the queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        logger.info(f"Stopped capture for source {self.source_id}")
        return True

    def _capture_loop(self):
        """Main capture loop that runs in a separate thread"""
        last_capture_time = time.time()
        frame_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0

        while self.running:
            try:
                # Throttle capture to target FPS
                elapsed = time.time() - last_capture_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)

                # Capture frame
                capture_timestamp = time.time()
                ret, frame = self.cap.read()

                if not ret:
                    if self.source_type == 'file':
                        # Restart video file if it's finished
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        # Camera or stream might be temporarily unavailable
                        logger.warning(f"Failed to read frame from source {self.source_id}")
                        time.sleep(1.0)  # Avoid busy waiting
                        continue

                # Resize frame if necessary
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Calculate latency and FPS
                now = time.time()
                latency = (now - capture_timestamp) * 1000  # ms
                self.recent_latencies.append(latency)

                if now - self.last_frame_time >= 1.0:  # Update FPS every second
                    self.current_fps = self.frames_processed
                    self.frames_processed = 0
                    self.last_frame_time = now

                self.frames_processed += 1

                # Create frame info dictionary
                frame_info = {
                    'frame': frame_rgb,
                    'timestamp': capture_timestamp,
                    'frame_id': self.frames_processed,
                    'source_id': self.source_id,
                    'latency': latency,
                }

                # Try to put in queue, skip if full (to avoid blocking)
                try:
                    self.frame_queue.put(frame_info, block=False)
                    last_capture_time = time.time()
                except queue.Full:
                    # Queue is full, skip this frame to maintain real-time
                    pass

            except Exception as e:
                logger.error(f"Error in capture loop for source {self.source_id}: {e}")
                time.sleep(1.0)  # Avoid busy waiting on error

    def get_frame(self, timeout=1.0):
        """Get a frame from the queue with timeout"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_metrics(self):
        """Get current performance metrics"""
        avg_latency = sum(self.recent_latencies) / len(self.recent_latencies) if self.recent_latencies else 0
        return {
            'source_id': self.source_id,
            'current_fps': self.current_fps,
            'queue_size': self.frame_queue.qsize(),
            'avg_latency_ms': avg_latency,
            'resolution': f"{self.width}x{self.height}"
        }

    def is_running(self):
        """Check if capture is running"""
        with self.lock:
            return self.running and (self.cap is not None) and self.cap.isOpened()


class VideoSourceManager:
    """Manager for multiple video sources"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VideoSourceManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the manager"""
        if self._initialized:
            return

        self.sources = {}
        self.lock = threading.Lock()
        self._initialized = True

    def add_source(self, source_id, source_type, source_url,
                   width=640, height=480, buffer_size=30, target_fps=15,
                   auto_start=True):
        """Add a new video source"""
        with self.lock:
            if source_id in self.sources:
                logger.warning(f"Video source with ID {source_id} already exists. Stopping it first.")
                self.remove_source(source_id)

            source = VideoSource(
                source_id=source_id,
                source_type=source_type,
                source_url=source_url,
                width=width,
                height=height,
                buffer_size=buffer_size,
                target_fps=target_fps
            )

            self.sources[source_id] = source

            if auto_start:
                source.start()

            return source

    def get_source(self, source_id):
        """Get a video source by ID"""
        with self.lock:
            return self.sources.get(source_id)

    def remove_source(self, source_id):
        """Remove and stop a video source"""
        with self.lock:
            source = self.sources.pop(source_id, None)
            if source:
                source.stop()
                return True
            return False

    def get_all_sources(self):
        """Get a list of all video sources"""
        with self.lock:
            return list(self.sources.values())

    def shutdown(self):
        """Shutdown all video sources"""
        with self.lock:
            for source_id in list(self.sources.keys()):
                self.remove_source(source_id)