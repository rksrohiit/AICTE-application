"""
geo_validator.py — Geotag & EXIF Metadata Verification Service
AICTE AI-Powered Application Validation Platform
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import ExifTags, Image


class GeoValidatorService:
    """Extracts EXIF metadata from campus infrastructure photographs and performs
    triangulation checks against registered institutional campus coordinates
    and live application submission coordinates.
    """

    EARTH_RADIUS_METERS = 6371000.0

    @staticmethod
    def haversine_distance_meters(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate the great-circle distance between two GPS coordinates in meters."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return GeoValidatorService.EARTH_RADIUS_METERS * c

    @staticmethod
    def _convert_dms_to_decimal(dms_tuple: tuple, ref: str) -> Optional[float]:
        """Convert GPS degrees/minutes/seconds rational tuple to decimal degrees."""
        try:
            d = float(dms_tuple[0])
            m = float(dms_tuple[1])
            s = float(dms_tuple[2])
            decimal = d + (m / 60.0) + (s / 3600.0)
            if ref in ("S", "W"):
                decimal = -decimal
            return round(decimal, 6)
        except Exception:
            return None

    def extract_exif_metadata(self, image_path: str | Path) -> Dict[str, Any]:
        """Extract camera hardware metadata and GPS positioning from image EXIF.

        Returns a dictionary with parsed latitude, longitude, altitude,
        timestamp, and camera device information.
        """
        metadata: Dict[str, Any] = {
            "has_exif": False,
            "has_gps": False,
            "latitude": None,
            "longitude": None,
            "altitude_meters": None,
            "timestamp": None,
            "camera_make": None,
            "camera_model": None,
            "raw_tags_count": 0,
        }

        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return metadata

                metadata["has_exif"] = True
                metadata["raw_tags_count"] = len(exif_data)

                # Map EXIF tag IDs to human-readable names
                labeled: Dict[str, Any] = {}
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    labeled[tag_name] = value

                metadata["camera_make"] = labeled.get("Make")
                metadata["camera_model"] = labeled.get("Model")
                metadata["timestamp"] = labeled.get("DateTimeOriginal") or labeled.get("DateTime")

                # Extract GPSInfo
                gps_info = labeled.get("GPSInfo")
                if gps_info and isinstance(gps_info, dict):
                    # Map GPS sub-tags
                    gps_labeled: Dict[str, Any] = {}
                    for k, v in gps_info.items():
                        sub_tag = ExifTags.GPSTAGS.get(k, str(k))
                        gps_labeled[sub_tag] = v

                    lat_tuple = gps_labeled.get("GPSLatitude")
                    lat_ref = gps_labeled.get("GPSLatitudeRef", "N")
                    lon_tuple = gps_labeled.get("GPSLongitude")
                    lon_ref = gps_labeled.get("GPSLongitudeRef", "E")

                    if lat_tuple and lon_tuple:
                        lat = self._convert_dms_to_decimal(lat_tuple, lat_ref)
                        lon = self._convert_dms_to_decimal(lon_tuple, lon_ref)
                        if lat is not None and lon is not None:
                            metadata["latitude"] = lat
                            metadata["longitude"] = lon
                            metadata["has_gps"] = True

                    alt = gps_labeled.get("GPSAltitude")
                    if alt is not None:
                        try:
                            metadata["altitude_meters"] = round(float(alt), 2)
                        except Exception:
                            pass

        except Exception as exc:
            metadata["error"] = str(exc)

        return metadata

    def verify_location_consistency(
        self,
        image_path: str | Path,
        campus_lat: float,
        campus_lon: float,
        live_lat: Optional[float] = None,
        live_lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive location consistency analysis:
        1. Compares photo EXIF GPS vs. AICTE registered campus location.
        2. Compares live submission GPS (from browser) vs. campus location.
        3. Compares photo EXIF GPS vs. live submission GPS.
        """
        exif = self.extract_exif_metadata(image_path)
        photo_has_gps = exif.get("has_gps", False)
        photo_lat = exif.get("latitude")
        photo_lon = exif.get("longitude")

        result: Dict[str, Any] = {
            "exif_metadata": exif,
            "campus_coordinates": {"latitude": campus_lat, "longitude": campus_lon},
            "live_submission_coordinates": (
                {"latitude": live_lat, "longitude": live_lon}
                if live_lat is not None and live_lon is not None
                else None
            ),
            "photo_to_campus_distance_meters": None,
            "live_to_campus_distance_meters": None,
            "photo_to_live_distance_meters": None,
            "status": "VERIFIED",
            "anomaly_flags": [],
            "risk_level": "LOW",  # LOW | MEDIUM | HIGH
            "summary": "",
        }

        # ── 1. Check if photo contains GPS metadata ───────────────────────────
        if not photo_has_gps:
            result["status"] = "METADATA_STRIPPED"
            result["risk_level"] = "HIGH"
            result["anomaly_flags"].append({
                "code": "EXIF_GPS_MISSING",
                "severity": "HIGH",
                "message": (
                    "Photo has no GPS tags. The image was either downloaded from the internet, "
                    "forwarded via messaging platforms (which strip EXIF), or modified."
                ),
            })
            result["summary"] = "Photo lacks embedded GPS coordinates. Physical inspection verification advised."
        else:
            # Calculate photo to registered campus distance
            d_photo_campus = self.haversine_distance_meters(
                photo_lat, photo_lon, campus_lat, campus_lon
            )
            result["photo_to_campus_distance_meters"] = round(d_photo_campus, 1)

            if d_photo_campus > 50000:  # > 50 km away
                result["status"] = "LOCATION_MISMATCH_CRITICAL"
                result["risk_level"] = "HIGH"
                result["anomaly_flags"].append({
                    "code": "PHOTO_LOCATION_MISMATCH",
                    "severity": "HIGH",
                    "distance_km": round(d_photo_campus / 1000.0, 2),
                    "message": (
                        f"Photo taken {round(d_photo_campus / 1000.0, 1)} km away from the "
                        f"institution's registered campus coordinates. Suspected stock/external photo."
                    ),
                })
            elif d_photo_campus > 1500:  # > 1.5 km away
                result["status"] = "LOCATION_MISMATCH_MODERATE"
                result["risk_level"] = "MEDIUM"
                result["anomaly_flags"].append({
                    "code": "PHOTO_CAMPUS_BOUNDARY_EXCEEDED",
                    "severity": "MEDIUM",
                    "distance_meters": round(d_photo_campus, 1),
                    "message": f"Photo taken {round(d_photo_campus, 1)} m away from campus boundary.",
                })
            else:
                result["status"] = "CAMPUS_COORDINATES_VERIFIED"

        # ── 2. Check live submission location if provided ─────────────────────
        if live_lat is not None and live_lon is not None:
            d_live_campus = self.haversine_distance_meters(
                live_lat, live_lon, campus_lat, campus_lon
            )
            result["live_to_campus_distance_meters"] = round(d_live_campus, 1)

            if d_live_campus > 100000:  # > 100 km away
                result["anomaly_flags"].append({
                    "code": "REMOTE_SUBMISSION_DETECTED",
                    "severity": "MEDIUM",
                    "message": (
                        f"Application submitted from a location {round(d_live_campus / 1000.0, 1)} km "
                        f"away from the institution campus. Applicant is not on-site."
                    ),
                })

            if photo_has_gps:
                d_photo_live = self.haversine_distance_meters(
                    photo_lat, photo_lon, live_lat, live_lon
                )
                result["photo_to_live_distance_meters"] = round(d_photo_live, 1)

        # Build concise summary
        if not result["anomaly_flags"]:
            result["summary"] = (
                f"Location Verified: Photo coordinates match campus boundary "
                f"({result.get('photo_to_campus_distance_meters')} m offset)."
            )
        elif not result["summary"]:
            flag_msgs = "; ".join(f["message"] for f in result["anomaly_flags"])
            result["summary"] = f"Flagged with {len(result['anomaly_flags'])} location anomalies: {flag_msgs}"

        return result
