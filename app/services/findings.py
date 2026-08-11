import json

from sqlalchemy.orm import Session

from app.db.models import Finding
from app.services.conflicts import ConflictFinding


def save_conflicts(
    db: Session,
    document_id: int,
    conflicts: list[ConflictFinding],
) -> list[Finding]:
    findings = []

    for conflict in conflicts:
        finding = Finding(
            document_id=document_id,
            finding_type="conflict",
            description=(
                f"{conflict.fact}: "
                f"{', '.join(conflict.values)}"
            ),
            fact_ids=json.dumps(conflict.fact_ids),
            status="pending",
        )

        db.add(finding)
        findings.append(finding)

    db.commit()

    for finding in findings:
        db.refresh(finding)

    return findings