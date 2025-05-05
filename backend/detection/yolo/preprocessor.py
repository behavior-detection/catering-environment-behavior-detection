import cv2
import numpy as np
import logging
from shapely.geometry import Point, Polygon

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FramePreprocessor:
    """
    Frame preprocessing for object detection:
    - Resize to standard resolution
    - Color space conversion
    - ROI masking
    - Image enhancement
    """

    def __init__(self, target_width=640, target_height=480):
        """Initialize with target resolution"""
        self.target_width = target_width
        self.target_height = target_height

    def resize(self, frame, width=None, height=None):
        """Resize frame to target dimensions"""
        if width is None:
            width = self.target_width
        if height is None:
            height = self.target_height

        # Skip if already the desired size
        if frame.shape[1] == width and frame.shape[0] == height:
            return frame

        return cv2.resize(frame, (width, height))

    def convert_color(self, frame, src_format='BGR', dst_format='RGB'):
        """Convert between color spaces"""
        if src_format == dst_format:
            return frame

        conversions = {
            'BGR2RGB': cv2.COLOR_BGR2RGB,
            'RGB2BGR': cv2.COLOR_RGB2BGR,
            'BGR2GRAY': cv2.COLOR_BGR2GRAY,
            'RGB2GRAY': cv2.COLOR_RGB2GRAY,
            'GRAY2BGR': cv2.COLOR_GRAY2BGR,
            'GRAY2RGB': cv2.COLOR_GRAY2RGB
        }

        conversion_code = conversions.get(f"{src_format}2{dst_format}")
        if conversion_code is not None:
            return cv2.cvtColor(frame, conversion_code)
        else:
            logger.warning(f"Unsupported color conversion: {src_format} to {dst_format}")
            return frame

    def apply_roi_mask(self, frame, roi_polygons):
        """
        Apply ROI mask to focus detection only in specific regions

        Args:
            frame: Input image
            roi_polygons: List of polygons, where each polygon is a list of [x, y] coordinates
                          (normalized between 0-1)

        Returns:
            Masked image where only ROI regions are visible (rest is black)
        """
        if not roi_polygons:
            return frame  # No ROIs defined, return original frame

        # Create a black mask
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)

        height, width = frame.shape[:2]

        # Draw ROI polygons on the mask
        for polygon in roi_polygons:
            points = []
            for point in polygon:
                # Convert normalized coordinates to absolute
                x = int(point[0] * width)
                y = int(point[1] * height)
                points.append((x, y))

            # Convert points to numpy array
            points = np.array(points, np.int32)
            points = points.reshape((-1, 1, 2))

            # Draw filled polygon on mask
            cv2.fillPoly(mask, [points], 255)

        # Apply mask to image
        masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
        return masked_frame

    def enhance_contrast(self, frame, clip_limit=2.0, tile_grid_size=(8, 8)):
        """Enhance contrast using CLAHE"""
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

        # Split into L, A, B channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l)

        # Merge enhanced L channel with original A and B channels
        limg = cv2.merge((cl, a, b))

        # Convert back to BGR color space
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return enhanced

    def denoise(self, frame, h=10, template_window_size=7, search_window_size=21):
        """Apply denoising to improve detection in low light or noisy conditions"""
        return cv2.fastNlMeansDenoisingColored(
            frame,
            None,
            h=h,
            hColor=h,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size
        )

    def is_point_in_any_roi(self, point, roi_polygons, img_width, img_height):
        """Check if a point is inside any of the ROI polygons"""
        if not roi_polygons:
            return True  # No ROIs defined, accept all points

        x, y = point

        for polygon in roi_polygons:
            # Convert normalized coordinates to absolute
            abs_polygon = []
            for p in polygon:
                abs_polygon.append((p[0] * img_width, p[1] * img_height))

            # Create Shapely polygon and point
            poly = Polygon(abs_polygon)
            pt = Point(x, y)

            if poly.contains(pt):
                return True

        return False

    def process_frame(self, frame, roi_polygons=None, enhance=False, denoise_frame=False):
        """
        Process frame with all necessary preprocessing steps

        Args:
            frame: Input frame
            roi_polygons: List of ROI polygons
            enhance: Whether to enhance contrast
            denoise_frame: Whether to apply denoising

        Returns:
            Processed frame
        """
        # Resize to standard resolution if needed
        frame = self.resize(frame)

        # Optional enhancements
        if enhance:
            frame = self.enhance_contrast(frame)

        if denoise_frame:
            frame = self.denoise(frame)

        # Apply ROI mask if specified
        if roi_polygons:
            frame = self.apply_roi_mask(frame, roi_polygons)

        # Ensure proper color format for the model (RGB)
        frame = self.convert_color(frame, 'BGR', 'RGB')

        return frame