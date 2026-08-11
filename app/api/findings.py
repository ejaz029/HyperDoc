from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Finding


router = APIRouter(
    prefix="/findings",
    tags=["findings"],
)


class ReviewRequest(BaseModel):
    decision: str


@router.get("/{document_id}")
def get_findings(document_id: int):
    db = SessionLocal()

    try:
        findings = list(
            db.scalars(
                select(Finding)
                .where(Finding.document_id == document_id)
                .order_by(Finding.id)
            )
        )

        return [
            {
                "id": finding.id,
                "type": finding.finding_type,
                "description": finding.description,
                "fact_ids": finding.fact_ids,
                "status": finding.status,
            }
            for finding in findings
        ]

    finally:
        db.close()


@router.post("/{finding_id}/review")
def review_finding(
    finding_id: int,
    request: ReviewRequest,
):
    if request.decision not in {"accepted", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="decision must be accepted or rejected",
        )

    db = SessionLocal()

    try:
        finding = db.get(Finding, finding_id)

        if finding is None:
            raise HTTPException(
                status_code=404,
                detail="Finding not found",
            )

        finding.status = request.decision

        db.commit()
        db.refresh(finding)

        return {
            "id": finding.id,
            "status": finding.status,
        }

    finally:
        db.close()