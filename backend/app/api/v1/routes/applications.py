"""
Application CRUD and action routes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_officer
from app.models.application import Application, ApplicationStatus
from app.models.user import User, UserRole
from app.models.validation import ValidationRun
from app.models.audit import AuditLog
from app.models.alert import ApplicationAlert
from app.schemas.application import ApplicationCreate, ApplicationListResponse, ApplicationResponse
from app.schemas.validation import ValidationFindingResponse, ValidationReportResponse, ValidationRunResponse
from app.schemas.audit import AuditLogResponse
from app.schemas.anomaly import AnomalyFlagResponse

router = APIRouter(prefix="/applications", tags=["applications"])


async def _get_application_or_404(
    app_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> Application:
    """Fetch an application by ID, respecting role-based visibility.

    Args:
        app_id:       UUID of the application.
        db:           Async database session.
        current_user: The authenticated user making the request.

    Returns:
        The :class:`Application` ORM instance.

    Raises:
        :class:`~fastapi.HTTPException` 404: If not found or not visible to the user.
    """
    stmt = select(Application).where(Application.id == app_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()

    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    if current_user.role == UserRole.INSTITUTION and app.institution_id != current_user.institution_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    return app


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new EOA application",
)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationResponse:
    """Create a new EOA application for the authenticated institution user.

    Args:
        payload:      Application creation payload.
        db:           Async database session.
        current_user: Authenticated user (any role may create, institution_id must be set).

    Returns:
        The newly created :class:`ApplicationResponse`.
    """
    if current_user.role == UserRole.INSTITUTION and current_user.institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not linked to an institution.",
        )

    institution_id = (
        current_user.institution_id
        if current_user.role == UserRole.INSTITUTION
        else uuid.uuid4()  # officers can create on behalf; provide real id in production
    )

    app = Application(
        institution_id=institution_id,
        institution_name=payload.institution_name,
        application_type=payload.application_type,
        status=ApplicationStatus.DRAFT,
        academic_year=payload.academic_year,
        programmes=payload.programmes,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)

    audit = AuditLog(
        actor=current_user.email,
        action="APPLICATION_CREATED",
        application_id=app.id,
        result="SUCCESS",
        notes=f"Application type: {app.application_type.value}",
    )
    db.add(audit)

    return ApplicationResponse.model_validate(app)


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List applications",
)
async def list_applications(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationListResponse:
    """List applications. Institutions see only their own; officers see all.

    Args:
        skip:         Pagination offset.
        limit:        Maximum number of results to return.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        A :class:`ApplicationListResponse` with total count and items.
    """
    stmt = select(Application)
    if current_user.role == UserRole.INSTITUTION:
        stmt = stmt.where(Application.institution_id == current_user.institution_id)

    stmt = stmt.order_by(Application.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    apps = result.scalars().all()

    count_stmt = select(Application)
    if current_user.role == UserRole.INSTITUTION:
        count_stmt = count_stmt.where(Application.institution_id == current_user.institution_id)
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    return ApplicationListResponse(
        total=total,
        items=[ApplicationResponse.model_validate(a) for a in apps],
    )


@router.get(
    "/{app_id}",
    response_model=ApplicationResponse,
    summary="Get a single application",
)
async def get_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationResponse:
    """Retrieve a single application by UUID.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        The :class:`ApplicationResponse` for the matching application.
    """
    app = await _get_application_or_404(app_id, db, current_user)
    return ApplicationResponse.model_validate(app)


@router.post(
    "/{app_id}/validate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous validation for an application",
)
async def trigger_validation(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Enqueue a Celery validation task for the given application.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        A dict with the task id and status message.
    """
    from app.tasks.validation_tasks import run_validation  # lazy import to avoid circular deps

    app = await _get_application_or_404(app_id, db, current_user)

    if app.status == ApplicationStatus.UNDER_VALIDATION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Validation is already running for this application.",
        )

    app.status = ApplicationStatus.UNDER_VALIDATION
    audit = AuditLog(
        actor=current_user.email,
        action="VALIDATION_TRIGGERED",
        application_id=app.id,
        result="QUEUED",
    )
    db.add(audit)
    await db.flush()

    task = run_validation.delay(str(app_id))

    return {
        "task_id": task.id,
        "application_id": str(app_id),
        "status": "QUEUED",
        "message": "Validation task successfully queued.",
    }


@router.get(
    "/{app_id}/validation-report",
    response_model=ValidationReportResponse,
    summary="Get the latest validation report for an application",
)
@router.get(
    "/{app_id}/report",
    response_model=ValidationReportResponse,
    summary="Get the latest validation report for an application (alias)",
)
async def get_validation_report(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationReportResponse:
    """Retrieve the most recent validation run and all its findings.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        A :class:`ValidationReportResponse` with run metadata and findings list.
    """
    from app.models.validation import ValidationFinding

    await _get_application_or_404(app_id, db, current_user)

    run_result = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.application_id == app_id)
        .order_by(ValidationRun.started_at.desc())
        .limit(1)
    )
    run = run_result.scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation run found for this application.",
        )

    findings_result = await db.execute(
        select(ValidationFinding).where(ValidationFinding.validation_run_id == run.id)
    )
    findings = findings_result.scalars().all()

    summary: Dict[str, Any] = {
        "total_findings": len(findings),
        "high": run.findings_count_high,
        "medium": run.findings_count_medium,
        "low": run.findings_count_low,
        "overall_score": run.overall_score,
        "status": run.status.value,
    }

    return ValidationReportResponse(
        run=ValidationRunResponse.model_validate(run),
        findings=[ValidationFindingResponse.model_validate(f) for f in findings],
        summary=summary,
    )


@router.get(
    "/{app_id}/alerts",
    response_model=List[Dict[str, Any]],
    summary="Get alerts for an application",
)
async def get_application_alerts(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all unresolved (and recently resolved) alerts for an application.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        A list of alert dicts.
    """
    await _get_application_or_404(app_id, db, current_user)

    result = await db.execute(
        select(ApplicationAlert)
        .where(ApplicationAlert.application_id == app_id)
        .order_by(ApplicationAlert.created_at.desc())
    )
    alerts = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at.isoformat(),
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in alerts
    ]


@router.get(
    "/{app_id}/audit",
    response_model=List[AuditLogResponse],
    summary="Get audit trail for an application",
)
async def get_application_audit(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AuditLogResponse]:
    """Return the full chronological audit trail for an application.

    Args:
        app_id:       Application UUID.
        db:           Async database session.
        current_user: Authenticated user.

    Returns:
        Ordered list of :class:`AuditLogResponse` entries.
    """
    await _get_application_or_404(app_id, db, current_user)

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.application_id == app_id)
        .order_by(AuditLog.timestamp.asc())
    )
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.post(
    "/{app_id}/actions",
    status_code=status.HTTP_200_OK,
    summary="Officer action on an application (approve / reject / escalate / rectify)",
    dependencies=[Depends(require_officer)],
)
@router.post(
    "/{app_id}/action",
    status_code=status.HTTP_200_OK,
    summary="Officer action on an application (alias)",
    dependencies=[Depends(require_officer)],
)
async def officer_action(
    app_id: uuid.UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Apply an officer action to transition an application's status.

    Expected payload keys:
    - ``action``: one of ``APPROVE``, ``REJECT``, ``ESCALATE``, ``SEND_FOR_RECTIFICATION``
    - ``notes``:  optional free-text reasoning

    Args:
        app_id:       Application UUID.
        payload:      Action payload dict.
        db:           Async database session.
        current_user: Authenticated officer.

    Returns:
        Updated application status dict.
    """
    from app.models.application import Application  # noqa: F811

    app = await _get_application_or_404(app_id, db, current_user)

    action: str = payload.get("action", "").upper()
    notes: str = payload.get("notes", "")

    action_status_map: Dict[str, ApplicationStatus] = {
        "APPROVE": ApplicationStatus.APPROVED_FOR_PROCESSING,
        "REJECT": ApplicationStatus.REJECTED,
        "ESCALATE": ApplicationStatus.ESCALATED,
        "SEND_FOR_RECTIFICATION": ApplicationStatus.SENT_FOR_RECTIFICATION,
        "START_REVIEW": ApplicationStatus.UNDER_REVIEW,
    }

    new_status = action_status_map.get(action)
    if new_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action '{action}'. Valid actions: {list(action_status_map.keys())}",
        )

    app.status = new_status
    app.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        actor=current_user.email,
        action=f"OFFICER_ACTION_{action}",
        application_id=app.id,
        result=new_status.value,
        notes=notes or None,
    )
    db.add(audit)
    await db.flush()

    return {
        "application_id": str(app_id),
        "new_status": new_status.value,
        "action": action,
        "applied_by": current_user.email,
        "message": f"Application status updated to {new_status.value}.",
    }


@router.get(
    "/{app_id}/generate-report",
    summary="Download PDF Validation Report",
)
async def generate_pdf_report(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and return a structured PDF validation report for the given application."""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from app.models.validation import ValidationFinding

    app = await _get_application_or_404(app_id, db, current_user)

    # Fetch latest validation run
    run_result = await db.execute(
        select(ValidationRun)
        .where(ValidationRun.application_id == app_id)
        .order_by(ValidationRun.started_at.desc())
        .limit(1)
    )
    run = run_result.scalar_one_or_none()

    findings: List[ValidationFinding] = []
    if run:
        f_result = await db.execute(
            select(ValidationFinding).where(ValidationFinding.validation_run_id == run.id)
        )
        findings = list(f_result.scalars().all())

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1,
    )
    sub_style = ParagraphStyle(
        'SubStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#4B5563'),
        alignment=1,
    )
    section_style = ParagraphStyle(
        'SecStyle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E3A8A'),
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
    )

    story = []
    story.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", header_style))
    story.append(Paragraph("AI-Powered Application Validation & Compliance Report", sub_style))
    story.append(Spacer(1, 15))

    score_val = run.overall_score if run else 0
    score_color = colors.HexColor('#16A34A') if score_val >= 70 else (colors.HexColor('#D97706') if score_val >= 40 else colors.HexColor('#DC2626'))

    meta_data = [
        [Paragraph("<b>Application ID:</b>", body_style), Paragraph(str(app.id), body_style), Paragraph("<b>Overall Score:</b>", body_style), Paragraph(f"<b>{score_val}/100</b>", ParagraphStyle('Score', parent=body_style, textColor=score_color, fontSize=11))],
        [Paragraph("<b>Institution Name:</b>", body_style), Paragraph(app.institution_name, body_style), Paragraph("<b>Status:</b>", body_style), Paragraph(app.status.value, body_style)],
        [Paragraph("<b>Academic Year:</b>", body_style), Paragraph(app.academic_year or "N/A", body_style), Paragraph("<b>Generated At:</b>", body_style), Paragraph(datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"), body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[100, 180, 100, 160])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Detailed Validation Findings", section_style))
    story.append(Spacer(1, 8))

    findings_table_data = [
        [Paragraph("<b>Rule ID</b>", body_style), Paragraph("<b>Severity</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Message & Evidence</b>", body_style)]
    ]

    if findings:
        for f in findings:
            findings_table_data.append([
                Paragraph(f.rule_id, body_style),
                Paragraph(f.severity.value, body_style),
                Paragraph(f.status.value, body_style),
                Paragraph(f"{f.message}<br/><font color='#6B7280'>Evidence: {f.evidence or 'None'}</font>", body_style)
            ])
    else:
        findings_table_data.append([
            Paragraph("N/A", body_style),
            Paragraph("INFO", body_style),
            Paragraph("PENDING", body_style),
            Paragraph("No validation run recorded yet for this application.", body_style)
        ])

    f_table = Table(findings_table_data, colWidths=[70, 60, 60, 350])
    f_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(f_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Regulatory Disclaimer:</b> AI-generated validation findings and flags are preliminary decision-support indicators. Statutory scrutiny and final decision-making remain strictly with the competent AICTE authorities.", ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#6B7280'), fontName='Helvetica-Oblique')))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=validation_report_{app_id}.pdf"},
    )

