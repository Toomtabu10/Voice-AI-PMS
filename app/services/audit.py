from sqlalchemy.orm import Session
from app.models import AuditLog
from typing import Any, Optional
from datetime import datetime


def log_change(
    db: Session,
    table_name: str,
    record_id: int,
    action: str,
    field_name: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    changed_by: str = "user",
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Write an audit log entry."""
    entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        changed_by=changed_by,
        changed_at=datetime.utcnow(),
        reason=reason,
        ip_address=ip_address,
    )
    db.add(entry)
    # Caller should commit


def audit_model_update(
    db: Session,
    table_name: str,
    record_id: int,
    old_obj: Any,
    update_data: dict,
    changed_by: str = "user",
    reason: Optional[str] = None,
):
    """Compare old object fields vs update_data and log each changed field."""
    for field, new_val in update_data.items():
        if new_val is None:
            continue
        old_val = getattr(old_obj, field, None)
        if str(old_val) != str(new_val):
            log_change(
                db,
                table_name=table_name,
                record_id=record_id,
                action="update",
                field_name=field,
                old_value=old_val,
                new_value=new_val,
                changed_by=changed_by,
                reason=reason,
            )
