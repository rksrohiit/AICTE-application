"""
campus_geo.py — API Routes for Plot Boundary Area Calculation & Geo-Verification
AICTE AI-Powered Application Validation Platform
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.anomaly import AnomalyFlag
from app.models.application import Application
from app.models.institution import InstitutionRecord
from app.models.user import User
from app.services.audit_chain import append_chained_audit_log
from app.services.campus_geo import CampusGeoService

router = APIRouter(prefix="/applications/{app_id}/geo", tags=["campus-geo"])


class VerifyPlotRequest(BaseModel):
    polygon_coordinates: List[List[float]] = Field(
        ...,
        description="List of [latitude, longitude] pairs defining plot boundary (min 3 vertices)",
        min_length=3,
    )
    claimed_acres: Optional[float] = Field(
        None, description="Land area claimed in institution deed (Acres)"
    )
    location_category: str = Field(
        "RURAL", description="Location classification: RURAL | URBAN | METRO"
    )


@router.get("/plot-summary")
async def get_campus_plot_summary(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve registered campus location, claimed land area, and initial plot reference."""
    app_res = await db.execute(select(Application).where(Application.id == app_id))
    app = app_res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    claimed_acres = 5.25  # Standard default demo claim
    campus_lat = 18.520430
    campus_lon = 73.856744
    location_category = "RURAL"

    if app.institution_id:
        inst_res = await db.execute(
            select(InstitutionRecord).where(InstitutionRecord.id == app.institution_id)
        )
        inst = inst_res.scalar_one_or_none()
        if inst:
            if getattr(inst, "latitude", None) and getattr(inst, "longitude", None):
                campus_lat = float(inst.latitude)
                campus_lon = float(inst.longitude)
            if getattr(inst, "land_area_acres", None):
                claimed_acres = float(inst.land_area_acres)
            if getattr(inst, "location_category", None):
                location_category = inst.location_category

    # Generate a realistic initial 4-point bounding perimeter around the campus coordinates
    # (roughly ~5 acres) so the user gets an immediate visual plot on the map to drag/edit!
    delta_lat = 0.0013
    delta_lon = 0.0014
    sample_polygon = [
        [round(campus_lat - delta_lat, 6), round(campus_lon - delta_lon, 6)],
        [round(campus_lat - delta_lat, 6), round(campus_lon + delta_lon, 6)],
        [round(campus_lat + delta_lat, 6), round(campus_lon + delta_lon, 6)],
        [round(campus_lat + delta_lat, 6), round(campus_lon - delta_lon, 6)],
    ]

    return {
        "application_id": str(app.id),
        "institution_name": app.institution_name,
        "registered_campus_center": {"latitude": campus_lat, "longitude": campus_lon},
        "claimed_land_acres": claimed_acres,
        "location_category": location_category,
        "sample_initial_polygon": sample_polygon,
    }


@router.post("/verify-plot")
async def verify_campus_plot(
    app_id: uuid.UUID,
    payload: VerifyPlotRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Calculate geodesic area of drawn plot boundary, verify against claimed deed,

    query OpenStreetMap Overpass connectivity, and obtain Sentinel-2 10m multispectral context.
    """
    app_res = await db.execute(select(Application).where(Application.id == app_id))
    app = app_res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    claimed_acres = payload.claimed_acres if payload.claimed_acres is not None else 5.25

    # 1. Geodesic area calculation
    geo_svc = CampusGeoService()
    try:
        area_calc = geo_svc.calculate_polygon_geodesic(payload.polygon_coordinates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Evaluate claim against AICTE APH regulations
    measured_acres = area_calc["area_acres"]
    claim_eval = geo_svc.evaluate_land_claim(
        measured_acres=measured_acres,
        claimed_acres=claimed_acres,
        location_category=payload.location_category,
    )

    # 3. OpenStreetMap Overpass spatial query
    centroid_lat = area_calc["centroid"]["latitude"]
    centroid_lon = area_calc["centroid"]["longitude"]
    osm_context = await geo_svc.query_osm_overpass_context(centroid_lat, centroid_lon)

    # 4. Sentinel-2 10m multispectral satellite context
    sentinel2_context = geo_svc.get_sentinel2_satellite_context(centroid_lat, centroid_lon)

    # 5. Record anomaly flag if land claim is significantly deficient
    now = datetime.now(timezone.utc)
    has_anomaly = claim_eval["discrepancy_level"] == "SIGNIFICANT_DEFICIT"

    if has_anomaly:
        anom = AnomalyFlag(
            id=uuid.uuid4(),
            application_id=app.id,
            check_type="LAND_AREA_POLYGON_DEFICIT",
            severity="HIGH",
            confidence=0.95,
            evidence=claim_eval["explanation"],
            advisory_note="Require certified revenue survey map / cadastral land deed verification.",
            created_at=now,
            is_reviewed=False,
        )
        db.add(anom)

    # 6. Append to cryptographic hash-chained audit trail
    verdict_summary = (
        f"Plot Area: {measured_acres:.2f} Acres (Claimed: {claimed_acres:.2f} Acres) | "
        f"Status: {claim_eval['claim_status']} | OSM Access: {osm_context['has_road_connectivity']}"
    )

    await append_chained_audit_log(
        db=db,
        actor=current_user.email,
        action="CAMPUS_PLOT_GEO_VERIFICATION",
        application_id=app.id,
        result="PASS" if not has_anomaly else "DEFICIT_FLAGGED",
        notes=verdict_summary,
    )

    await db.commit()

    return {
        "application_id": str(app.id),
        "area_metrics": area_calc,
        "land_claim_evaluation": claim_eval,
        "osm_spatial_context": osm_context,
        "sentinel2_satellite_context": sentinel2_context,
        "has_deficit_anomaly": has_anomaly,
        "verified_at": now.isoformat(),
    }
