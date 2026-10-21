"""
forensics.py — Image Tampering Forensics (Error Level Analysis & Copy-Move Detection)
AICTE AI-Powered Application Validation Platform
"""

from __future__ import annotations

import base64
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


class ImageForensicsService:
    """Detects digital alterations, photoshopped signs, modified dates/stamps,
    and copy-move (cloning) forgery on institutional photographs and certificates.
    """

    def __init__(self, quality_level: int = 90, scale_multiplier: int = 15):
        self.quality_level = quality_level
        self.scale_multiplier = scale_multiplier

    def compute_ela(
        self, image_path: str | Path
    ) -> Tuple[float, bool, str, Dict[str, Any]]:
        """Perform Error Level Analysis (ELA) on an image file.

        ELA highlights differences in compression error rates across an image.
        Original camera regions typically have consistent error distributions,
        while pasted, inserted, or cloned elements (such as photoshopped dates
        or altered building signs) have noticeably higher/different error levels.

        Returns:
            Tuple of:
            - tamper_score: float (0.0 to 100.0)
            - is_tampered: bool (True if score exceeds threshold)
            - heatmap_base64: str (data URI ready for direct <img> rendering)
            - stats: Dict with mean, max, and variance details
        """
        orig_img = Image.open(image_path).convert("RGB")

        # Save re-compressed copy in memory at target quality
        buffer = io.BytesIO()
        orig_img.save(buffer, format="JPEG", quality=self.quality_level)
        buffer.seek(0)
        recompressed_img = Image.open(buffer)

        # Compute absolute difference
        diff = ImageChops.difference(orig_img, recompressed_img)

        # Extract extreme values
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema]) if extrema else 1
        scale = 255.0 / max(max_diff, 1)

        # Scale difference to maximize visual contrast of errors
        enhancer = ImageEnhance.Brightness(diff)
        ela_img = enhancer.enhance(scale * (self.scale_multiplier / 10.0))

        # Convert to numpy array for statistical analysis & color mapping
        ela_np = np.array(ela_img)
        gray_ela = cv2.cvtColor(ela_np, cv2.COLOR_RGB2GRAY)

        mean_error = float(np.mean(gray_ela))
        std_error = float(np.std(gray_ela))
        max_error = float(np.max(gray_ela))

        # High error region ratio: pixels with error > (mean + 2.5 * std)
        high_threshold = mean_error + 2.5 * max(std_error, 1.0)
        high_error_count = int(np.sum(gray_ela > high_threshold))
        total_pixels = gray_ela.size
        high_error_ratio = (high_error_count / float(total_pixels)) * 100.0

        # Calculate a normalized tamper score (0 - 100)
        # Healthy camera images typically have tamper score < 22
        # Edited/pasted text or signs produce localized spikes boosting score > 35
        raw_score = (std_error * 1.5) + (high_error_ratio * 4.0) + (max_error * 0.15)
        tamper_score = round(min(max(raw_score, 0.0), 100.0), 2)
        is_tampered = tamper_score >= 38.0

        # Generate visual false-color JET heatmap using OpenCV
        normalized_gray = cv2.normalize(gray_ela, None, 0, 255, cv2.NORM_MINMAX)
        heatmap_cv = cv2.applyColorMap(normalized_gray, cv2.COLORMAP_JET)

        # Convert heatmap to JPEG Base64 for web display
        _, encoded_img = cv2.imencode(".jpg", heatmap_cv, [cv2.IMWRITE_JPEG_QUALITY, 85])
        heatmap_b64 = "data:image/jpeg;base64," + base64.b64encode(encoded_img).decode("utf-8")

        stats = {
            "mean_error": round(mean_error, 2),
            "std_error": round(std_error, 2),
            "max_error": round(max_error, 2),
            "high_error_ratio_percent": round(high_error_ratio, 3),
            "compression_quality_used": self.quality_level,
        }

        return tamper_score, is_tampered, heatmap_b64, stats

    def detect_copy_move_forgery(
        self, image_path: str | Path
    ) -> Tuple[bool, int, Optional[str]]:
        """Detect Copy-Move (Cloning) Forgery in an image.

        Identifies identical or near-identical image patches that have been copied
        and pasted within the same photograph (e.g. duplicating computer monitors
        or fire extinguishers to falsely inflate equipment counts).

        Returns:
            Tuple of:
            - is_cloned: bool
            - cluster_matches_count: int
            - annotated_preview_b64: Optional base64 preview of cloned connections
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return False, 0, None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Use ORB feature extractor
        orb = cv2.ORB_create(nfeatures=1200)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(descriptors) < 10:
            return False, 0, None

        # Match keypoints with other keypoints within the same image
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, descriptors, k=3)

        cloned_pairs: List[Tuple[cv2.KeyPoint, cv2.KeyPoint]] = []
        min_spatial_distance = 60.0  # ignore trivial self-matches of nearby pixels

        for m in matches:
            # m[0] is always the self-match (distance 0)
            if len(m) >= 2:
                best_other = m[1]
                if best_other.distance < 30:  # highly similar descriptor
                    kp1 = keypoints[best_other.queryIdx]
                    kp2 = keypoints[best_other.trainIdx]
                    spatial_dist = math.hypot(kp1.pt[0] - kp2.pt[0], kp1.pt[1] - kp2.pt[1])
                    if spatial_dist > min_spatial_distance:
                        cloned_pairs.append((kp1, kp2))

        # If significant number of distant identical feature pairs exist, flag cloning
        is_cloned = len(cloned_pairs) >= 12
        annotated_b64 = None

        if len(cloned_pairs) > 0:
            # Draw lines connecting cloned regions
            preview = img.copy()
            for kp1, kp2 in cloned_pairs[:40]:  # draw up to 40 connections
                pt1 = (int(kp1.pt[0]), int(kp1.pt[1]))
                pt2 = (int(kp2.pt[0]), int(kp2.pt[1]))
                cv2.circle(preview, pt1, 6, (0, 0, 255), -1)
                cv2.circle(preview, pt2, 6, (0, 255, 255), -1)
                cv2.line(preview, pt1, pt2, (0, 165, 255), 2)

            _, encoded_preview = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 85])
            annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(encoded_preview).decode("utf-8")

        return is_cloned, len(cloned_pairs), annotated_b64
