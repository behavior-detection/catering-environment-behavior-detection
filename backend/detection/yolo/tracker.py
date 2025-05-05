import numpy as np
import cv2
import uuid
import time
import logging
from scipy.optimize import linear_sum_assignment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleTracker:
    """
    Simple object tracker based on IoU matching between frames
    Tracks objects across consecutive frames to maintain identity and detect events
    """

    def __init__(self, max_disappeared=30, min_hit_streak=3, iou_threshold=0.3):
        """
        Initialize tracker

        Args:
            max_disappeared: Maximum number of frames an object can be missing before its track is deleted
            min_hit_streak: Minimum number of consecutive matches for a track to be considered confirmed
            iou_threshold: Minimum IoU for matching detections to tracks
        """
        self.next_track_id = 0
        self.tracks = {}  # Dictionary of active tracks
        self.max_disappeared = max_disappeared
        self.min_hit_streak = min_hit_streak
        self.iou_threshold = iou_threshold

    def _get_next_id(self):
        """Get next unique track ID"""
        track_id = self.next_track_id
        self.next_track_id += 1
        return track_id

    def _calculate_iou(self, boxA, boxB):
        """Calculate IoU between two bounding boxes"""
        # Format: [x1, y1, x2, y2]
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # Compute intersection area
        inter_area = max(0, xB - xA) * max(0, yB - yA)

        # Compute union area
        boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        union_area = boxA_area + boxB_area - inter_area

        # Compute IoU
        iou = inter_area / float(union_area) if union_area > 0 else 0

        return iou

    def _assign_detections_to_tracks(self, detections, tracks):
        """
        Match detections with existing tracks using IoU and Hungarian algorithm

        Args:
            detections: List of detection dictionaries with 'bbox' key
            tracks: Dictionary of track objects

        Returns:
            Tuple of (matches, unmatched_detections, unmatched_tracks)
        """
        if not tracks or not detections:
            return [], list(range(len(detections))), list(tracks.keys())

        track_ids = list(tracks.keys())

        # Build cost matrix based on IoU between all detections and tracks
        cost_matrix = np.zeros((len(detections), len(track_ids)))

        for d_idx, detection in enumerate(detections):
            for t_idx, track_id in enumerate(track_ids):
                track = tracks[track_id]
                # Cost is 1 - IoU (lower cost = better match)
                iou = self._calculate_iou(detection['bbox'], track['bbox'])
                cost_matrix[d_idx, t_idx] = 1.0 - iou

        # Use Hungarian algorithm for optimal assignment
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        # Filter matches with low IoU
        matches = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(tracks.keys())

        for row, col in zip(row_indices, col_indices):
            # If cost is too high (IoU too low), consider as unmatched
            if cost_matrix[row, col] > (1.0 - self.iou_threshold):
                continue

            track_id = track_ids[col]

            # Add to matches
            matches.append((row, track_id))

            # Remove from unmatched lists
            if row in unmatched_detections:
                unmatched_detections.remove(row)
            if track_id in unmatched_tracks:
                unmatched_tracks.remove(track_id)

        return matches, unmatched_detections, unmatched_tracks

    def update(self, detections, frame_timestamp):
        """
        Update tracker with new detections

        Args:
            detections: List of detection dictionaries with at least 'bbox' key
            frame_timestamp: Timestamp of the current frame

        Returns:
            List of tracked objects with additional tracking info
        """
        # If no tracks yet, initialize all detections as new tracks
        if not self.tracks:
            for i, detection in enumerate(detections):
                self._create_new_track(detection, frame_timestamp)
            return self._get_tracked_objects()

        # Match detections with existing tracks
        matches, unmatched_detections, unmatched_tracks = self._assign_detections_to_tracks(
            detections, self.tracks)

        # Update matched tracks
        for detection_idx, track_id in matches:
            self._update_track(track_id, detections[detection_idx], frame_timestamp)

        # Handle unmatched tracks (mark as disappeared)
        for track_id in unmatched_tracks:
            self._mark_track_disappeared(track_id)

        # Create new tracks for unmatched detections
        for detection_idx in unmatched_detections:
            self._create_new_track(detections[detection_idx], frame_timestamp)

        # Remove tracks that have disappeared for too long
        self._remove_expired_tracks()

        # Return current tracked objects
        return self._get_tracked_objects()

    def _create_new_track(self, detection, timestamp):
        """Create a new track from a detection"""
        track_id = self._get_next_id()

        self.tracks[track_id] = {
            'track_id': track_id,
            'bbox': detection['bbox'],
            'class_id': detection['class_id'],
            'class_name': detection['class_name'],
            'confidence': detection['confidence'],
            'first_seen': timestamp,
            'last_seen': timestamp,
            'disappeared': 0,
            'hit_streak': 1,
            'total_hits': 1,
            'detection_history': [detection],
            'is_confirmed': False,
            'state': 'tentative',  # 'tentative', 'confirmed', 'suspicious', 'violation'
            'velocity': [0, 0],  # [x, y] velocity in pixels/sec
        }

    def _update_track(self, track_id, detection, timestamp):
        """Update an existing track with new detection"""
        track = self.tracks[track_id]

        # Calculate time difference since last update
        time_diff = timestamp - track['last_seen']
        if time_diff > 0:
            # Calculate velocity (movement per second)
            old_center_x = (track['bbox'][0] + track['bbox'][2]) / 2
            old_center_y = (track['bbox'][1] + track['bbox'][3]) / 2

            new_center_x = (detection['bbox'][0] + detection['bbox'][2]) / 2
            new_center_y = (detection['bbox'][1] + detection['bbox'][3]) / 2

            velocity_x = (new_center_x - old_center_x) / time_diff
            velocity_y = (new_center_y - old_center_y) / time_diff

            # Update velocity with smoothing
            alpha = 0.7  # Smoothing factor
            track['velocity'][0] = alpha * velocity_x + (1 - alpha) * track['velocity'][0]
            track['velocity'][1] = alpha * velocity_y + (1 - alpha) * track['velocity'][1]

        # Update track info
        track['bbox'] = detection['bbox']
        track['class_id'] = detection['class_id']
        track['class_name'] = detection['class_name']
        track['confidence'] = detection['confidence']
        track['last_seen'] = timestamp
        track['disappeared'] = 0
        track['hit_streak'] += 1
        track['total_hits'] += 1
        track['detection_history'].append(detection)

        # Limit history size
        if len(track['detection_history']) > 30:
            track['detection_history'] = track['detection_history'][-30:]

        # Update track state
        if not track['is_confirmed'] and track['hit_streak'] >= self.min_hit_streak:
            track['is_confirmed'] = True
            track['state'] = 'confirmed'

    def _mark_track_disappeared(self, track_id):
        """Mark a track as disappeared (not detected in current frame)"""
        self.tracks[track_id]['disappeared'] += 1
        self.tracks[track_id]['hit_streak'] = 0

    def _remove_expired_tracks(self):
        """Remove tracks that have disappeared for too long"""
        track_ids_to_delete = []

        for track_id, track in self.tracks.items():
            if track['disappeared'] > self.max_disappeared:
                track_ids_to_delete.append(track_id)

        for track_id in track_ids_to_delete:
            del self.tracks[track_id]

    def _get_tracked_objects(self):
        """Get list of current tracked objects"""
        tracked_objects = []

        for track_id, track in self.tracks.items():
            # Only include confirmed tracks or those with minimum hits
            if track['is_confirmed'] or track['hit_streak'] >= self.min_hit_streak:
                tracked_objects.append({
                    'track_id': track['track_id'],
                    'bbox': track['bbox'],
                    'class_id': track['class_id'],
                    'class_name': track['class_name'],
                    'confidence': track['confidence'],
                    'first_seen': track['first_seen'],
                    'last_seen': track['last_seen'],
                    'age': track['last_seen'] - track['first_seen'],
                    'hit_streak': track['hit_streak'],
                    'total_hits': track['total_hits'],
                    'is_confirmed': track['is_confirmed'],
                    'state': track['state'],
                    'velocity': track['velocity'],
                })

        return tracked_objects

    def update_track_state(self, track_id, new_state):
        """Update the state of a track (normal, suspicious, violation)"""
        if track_id in self.tracks:
            self.tracks[track_id]['state'] = new_state
            return True
        return False

    def get_track_by_id(self, track_id):
        """Get track by ID"""
        return self.tracks.get(track_id)

    def draw_tracks(self, frame, color_by_state=True):
        """Draw tracking info on frame"""
        img = frame.copy()

        state_colors = {
            'tentative': (255, 255, 0),  # Yellow
            'confirmed': (0, 255, 0),  # Green
            'suspicious': (0, 165, 255),  # Orange
            'violation': (0, 0, 255)  # Red
        }

        for track_id, track in self.tracks.items():
            if not track['is_confirmed'] and track['hit_streak'] < self.min_hit_streak:
                continue  # Skip unstable tracks

            x1, y1, x2, y2 = map(int, track['bbox'])

            # Choose color based on state
            if color_by_state:
                color = state_colors.get(track['state'], (0, 255, 0))
            else:
                color = (0, 255, 0)  # Default green

            # Draw bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            # Draw ID and class
            label = f"ID:{track_id} {track['class_name']}"
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw movement vector (optional)
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Scale velocity to make the arrow visible
            vel_x = int(track['velocity'][0] * 0.5)
            vel_y = int(track['velocity'][1] * 0.5)

            if abs(vel_x) > 1 or abs(vel_y) > 1:
                cv2.arrowedLine(img, (center_x, center_y),
                                (center_x + vel_x, center_y + vel_y),
                                color, 2, tipLength=0.3)

        return img


class ViolationDetector:
    """Detect violations based on tracking information and rule-based logic"""

    def __init__(self, violation_classes=None, suspicious_duration=1.0, violation_duration=3.0):
        """
        Initialize violation detector

        Args:
            violation_classes: List of class IDs that can cause violations
            suspicious_duration: Time in seconds for an object to be considered suspicious
            violation_duration: Time in seconds for an object to be confirmed as violation
        """
        self.violation_classes = violation_classes or [0]  # Default to class 0 (person)
        self.suspicious_duration = suspicious_duration
        self.violation_duration = violation_duration
        self.suspicious_tracks = {}
        self.violation_tracks = {}

    def update(self, tracked_objects, frame_timestamp):
        """
        Update violation detection based on current tracked objects

        Args:
            tracked_objects: List of tracked objects from tracker
            frame_timestamp: Current frame timestamp

        Returns:
            Tuple of (updated tracked objects, violation events)
        """
        violation_events = []

        # Process each tracked object
        for track in tracked_objects:
            track_id = track['track_id']

            # Check if class is in violation classes
            if track['class_id'] in self.violation_classes:
                track_age = track['age']  # time since first detection

                # State machine: normal -> suspicious -> violation
                if track['state'] == 'confirmed':
                    if track_age >= self.suspicious_duration:
                        # Update to suspicious state
                        track['state'] = 'suspicious'
                        self.suspicious_tracks[track_id] = frame_timestamp

                elif track['state'] == 'suspicious':
                    suspicious_time = frame_timestamp - self.suspicious_tracks.get(track_id, frame_timestamp)

                    if suspicious_time >= self.violation_duration:
                        # Update to violation state
                        track['state'] = 'violation'
                        self.violation_tracks[track_id] = frame_timestamp

                        # Create violation event
                        violation_events.append({
                            'track_id': track_id,
                            'bbox': track['bbox'],
                            'class_id': track['class_id'],
                            'class_name': track['class_name'],
                            'confidence': track['confidence'],
                            'timestamp': frame_timestamp,
                            'duration': track_age
                        })

            # If class changed or not in violation classes, reset state
            elif track['state'] in ['suspicious', 'violation']:
                track['state'] = 'confirmed'
                if track_id in self.suspicious_tracks:
                    del self.suspicious_tracks[track_id]
                if track_id in self.violation_tracks:
                    del self.violation_tracks[track_id]

        # Clean up expired tracks
        self._clean_expired_tracks([t['track_id'] for t in tracked_objects])

        return tracked_objects, violation_events

    def _clean_expired_tracks(self, current_track_ids):
        """Remove expired tracks from internal dictionaries"""
        for track_dict in [self.suspicious_tracks, self.violation_tracks]:
            expired_ids = [track_id for track_id in list(track_dict.keys())
                           if track_id not in current_track_ids]

            for track_id in expired_ids:
                if track_id in track_dict:
                    del track_dict[track_id]