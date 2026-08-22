from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, Dict, Any

from app.database import get_db
from app import models, schemas
from app.services.patient_context import (
    build_patient_context_text,
    get_conversation_history,
)
from app.services.llm import answer_with_context
from app.services.audit import log_change, audit_model_update

router = APIRouter(prefix="/chat", tags=["chat"])


def _parse_date(value):
    """Convert string YYYY-MM-DD (or date/datetime) to Python date, or return None."""
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _execute_action(db: Session, patient_id: int, action: Dict[str, Any]) -> str:
    """Execute a structured action returned by the LLM. Returns a short status message."""
    act = action.get("action")

    if act == "update_patient":
        fields = action.get("fields") or {}
        if not fields:
            return "No fields provided to update."
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            return "Patient not found."
        # Only allow safe demographic fields
        allowed = {
            "first_name", "last_name", "middle_name", "gender", "sex_at_birth",
            "blood_type", "phone_primary", "phone_secondary", "email",
            "address_line1", "address_line2", "city", "state", "zip_code",
            "height_cm", "weight_kg", "primary_care_provider", "notes",
            "emergency_contact_name", "emergency_contact_phone",
            "marital_status", "preferred_language",
        }
        update_data = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not update_data:
            return "No valid fields to update."
        audit_model_update(db, "patients", patient_id, patient, update_data, changed_by="voice/ai")
        for k, v in update_data.items():
            setattr(patient, k, v)
        patient.updated_at = datetime.utcnow()
        db.commit()
        changed = ", ".join(f"{k}={v}" for k, v in update_data.items())
        return f"Updated: {changed}"

    elif act == "add_allergy":
        allergen = action.get("allergen")
        if not allergen:
            return "Allergen name is required."
        allergy = models.Allergy(
            patient_id=patient_id,
            allergen=allergen,
            reaction=action.get("reaction"),
            severity=action.get("severity"),
            start_date=_parse_date(action.get("start_date")),
            end_date=_parse_date(action.get("end_date")),
            status=action.get("status", "active"),
            source="voice/ai",
        )
        db.add(allergy)
        db.commit()
        db.refresh(allergy)
        log_change(db, "allergies", allergy.id, "create", changed_by="voice/ai")
        db.commit()
        return f"Added allergy: {allergen}"

    elif act == "add_medication":
        name = action.get("name")
        if not name:
            return "Medication name is required."
        med = models.Medication(
            patient_id=patient_id,
            name=name,
            dosage=action.get("dosage"),
            frequency=action.get("frequency"),
            route=action.get("route"),
            start_date=_parse_date(action.get("start_date")),
            end_date=_parse_date(action.get("end_date")),
            status=action.get("status", "active"),
            prescribed_by=action.get("prescribed_by"),
            indication=action.get("indication"),
            notes=action.get("notes"),
            source="voice/ai",
        )
        db.add(med)
        db.commit()
        db.refresh(med)
        log_change(db, "medications", med.id, "create", changed_by="voice/ai")
        db.commit()
        return f"Added medication: {name}"

    elif act == "update_medication":
        # Find medication by name (prefer most recent)
        med_name = action.get("medication_name") or action.get("name")
        med_id = action.get("medication_id") or action.get("id")
        if not med_name and not med_id:
            return "Medication name or id is required to update."

        q = db.query(models.Medication).filter(models.Medication.patient_id == patient_id)
        if med_id:
            med = q.filter(models.Medication.id == med_id).first()
        else:
            med = (
                q.filter(models.Medication.name.ilike(med_name))
                .order_by(models.Medication.recorded_at.desc())
                .first()
            )
        if not med:
            return f"No medication named '{med_name or med_id}' found for this patient."

        # All updatable fields
        update_data = {}
        string_fields = ["name", "dosage", "frequency", "route", "status",
                         "prescribed_by", "indication", "notes"]
        for f in string_fields:
            if f in action and action[f] is not None:
                update_data[f] = action[f]

        if "start_date" in action:
            update_data["start_date"] = _parse_date(action.get("start_date"))
        if "end_date" in action:
            update_data["end_date"] = _parse_date(action.get("end_date"))

        if not update_data:
            return "No fields provided to update."

        # If marking inactive and no end_date given, default to today
        if update_data.get("status") == "inactive" and "end_date" not in update_data:
            update_data["end_date"] = date.today()

        audit_model_update(db, "medications", med.id, med, update_data, changed_by="voice/ai")
        for k, v in update_data.items():
            setattr(med, k, v)
        db.commit()
        db.refresh(med)
        changed = ", ".join(f"{k}={v}" for k, v in update_data.items())
        return f"Updated medication {med.name}: {changed}"

    elif act == "add_condition":
        name = action.get("name")
        if not name:
            return "Condition name is required."
        cond = models.Condition(
            patient_id=patient_id,
            name=name,
            icd_code=action.get("icd_code"),
            status=action.get("status", "active"),
            start_date=_parse_date(action.get("start_date")),
            end_date=_parse_date(action.get("end_date")),
            source="voice/ai",
        )
        db.add(cond)
        db.commit()
        db.refresh(cond)
        log_change(db, "conditions", cond.id, "create", changed_by="voice/ai")
        db.commit()
        return f"Added condition: {name}"

    elif act == "add_vitals":
        data = {k: action.get(k) for k in [
            "temperature_c", "heart_rate", "respiratory_rate",
            "bp_systolic", "bp_diastolic", "spo2", "weight_kg",
            "height_cm", "bmi", "pain_score", "blood_glucose"
        ] if action.get(k) is not None}
        if not data:
            return "No vital values provided."
        # Auto BMI
        if data.get("weight_kg") and data.get("height_cm") and not data.get("bmi"):
            h_m = data["height_cm"] / 100
            data["bmi"] = round(data["weight_kg"] / (h_m * h_m), 1)
        vital = models.VitalSign(patient_id=patient_id, source="voice/ai", **data)
        db.add(vital)
        # Also update latest height/weight on patient
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if patient:
            if data.get("weight_kg"):
                patient.weight_kg = data["weight_kg"]
            if data.get("height_cm"):
                patient.height_cm = data["height_cm"]
        db.commit()
        db.refresh(vital)
        log_change(db, "vital_signs", vital.id, "create", changed_by="voice/ai")
        db.commit()
        return "Vitals recorded."

    else:
        return f"Unknown action: {act}"


@router.post("/", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    patient_context = ""
    if payload.patient_id:
        patient = db.query(models.Patient).filter(models.Patient.id == payload.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        patient_context = build_patient_context_text(db, payload.patient_id)

    history = []
    if payload.include_history:
        history = get_conversation_history(db, payload.patient_id)

    # Store user message
    user_comm = models.Communication(
        patient_id=payload.patient_id,
        role="user",
        content=payload.message,
        modality=payload.modality or "text",
    )
    db.add(user_comm)
    db.commit()
    db.refresh(user_comm)

    # Get AI reply (+ optional structured action)
    action_status = None
    try:
        reply, action = answer_with_context(
            payload.message,
            patient_context,
            history,
            patient_id=payload.patient_id,
        )
        # Execute action if present and we have a patient
        if action and payload.patient_id:
            try:
                action_status = _execute_action(db, payload.patient_id, action)
                # Plain text only — no emoji (prevents LLM commenting on checkmarks)
                reply = f"Done. {action_status}"
            except Exception as e:
                reply = f"Could not apply change: {str(e)}"
    except Exception as e:
        reply = f"Sorry, I could not reach the language model. Error: {str(e)}"

    # Store assistant reply
    asst_comm = models.Communication(
        patient_id=payload.patient_id,
        role="assistant",
        content=reply,
        modality=payload.modality or "text",
    )
    db.add(asst_comm)
    db.commit()
    db.refresh(asst_comm)

    return schemas.ChatResponse(reply=reply, communication_id=asst_comm.id)


@router.get("/history")
def get_history(
    patient_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(models.Communication).order_by(models.Communication.created_at.desc())
    if patient_id is not None:
        q = q.filter(models.Communication.patient_id == patient_id)
    rows = q.limit(limit).all()
    return list(reversed(rows))
