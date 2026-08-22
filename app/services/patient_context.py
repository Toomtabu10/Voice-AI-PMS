"""
Build a rich textual / dict representation of a patient for LLM prompts.
"""
from sqlalchemy.orm import Session
from app.models import (
    Patient, Allergy, Medication, Condition, VitalSign,
    LabResult, Encounter, ClinicalNote, Document, Communication
)
from typing import Dict, Any, List
from datetime import datetime


def build_patient_dict(db: Session, patient_id: int) -> Dict[str, Any]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {}

    allergies = [
        {
            "allergen": a.allergen,
            "reaction": a.reaction,
            "severity": a.severity,
            "start_date": str(a.start_date) if a.start_date else None,
            "end_date": str(a.end_date) if a.end_date else None,
            "status": a.status,
        }
        for a in patient.allergies
    ]
    medications = [
        {
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "route": m.route,
            "start_date": str(m.start_date) if m.start_date else None,
            "end_date": str(m.end_date) if m.end_date else None,
            "status": m.status,
            "indication": m.indication,
        }
        for m in patient.medications if m.status == "active"
    ]
    conditions = [
        {
            "name": c.name,
            "icd_code": c.icd_code,
            "status": c.status,
            "start_date": str(c.start_date) if c.start_date else None,
            "end_date": str(c.end_date) if c.end_date else None,
        }
        for c in patient.conditions
    ]
    # Latest vitals (last 5)
    vitals = (
        db.query(VitalSign)
        .filter(VitalSign.patient_id == patient_id)
        .order_by(VitalSign.recorded_at.desc())
        .limit(5)
        .all()
    )
    vitals_list = [
        {
            "recorded_at": str(v.recorded_at),
            "bp": f"{v.bp_systolic}/{v.bp_diastolic}" if v.bp_systolic else None,
            "hr": v.heart_rate,
            "temp_c": v.temperature_c,
            "spo2": v.spo2,
            "weight_kg": v.weight_kg,
            "bmi": v.bmi,
        }
        for v in vitals
    ]
    # Recent labs (last 20)
    labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == patient_id)
        .order_by(LabResult.resulted_at.desc())
        .limit(20)
        .all()
    )
    labs_list = [
        {
            "test": l.test_name,
            "value": l.value or (str(l.numeric_value) if l.numeric_value is not None else None),
            "unit": l.unit,
            "flag": l.flag,
            "date": str(l.resulted_at) if l.resulted_at else None,
            "category": l.category,
        }
        for l in labs
    ]
    encounters = (
        db.query(Encounter)
        .filter(Encounter.patient_id == patient_id)
        .order_by(Encounter.date.desc())
        .limit(5)
        .all()
    )
    enc_list = [
        {
            "date": str(e.date),
            "type": e.encounter_type,
            "provider": e.provider,
            "chief_complaint": e.chief_complaint,
            "assessment": e.assessment,
        }
        for e in encounters
    ]
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.patient_id == patient_id)
        .order_by(ClinicalNote.created_at.desc())
        .limit(5)
        .all()
    )
    notes_list = [
        {"date": str(n.created_at), "type": n.note_type, "title": n.title, "content": n.content[:500]}
        for n in notes
    ]

    return {
        "id": patient.id,
        "mrn": patient.mrn,
        "name": f"{patient.first_name} {patient.last_name}",
        "dob": str(patient.date_of_birth),
        "gender": patient.gender,
        "blood_type": patient.blood_type,
        "status": patient.status,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "allergies": allergies,
        "medications": medications,
        "conditions": conditions,
        "recent_vitals": vitals_list,
        "recent_labs": labs_list,
        "recent_encounters": enc_list,
        "recent_notes": notes_list,
    }


def build_patient_context_text(db: Session, patient_id: int) -> str:
    data = build_patient_dict(db, patient_id)
    if not data:
        return "No patient data found."
    import json
    return json.dumps(data, indent=2, default=str)


def get_conversation_history(db: Session, patient_id: int | None, limit: int = 20) -> List[Dict[str, str]]:
    import re
    q = db.query(Communication).order_by(Communication.created_at.desc())
    if patient_id is not None:
        q = q.filter(Communication.patient_id == patient_id)
    else:
        q = q.filter(Communication.patient_id.is_(None))
    rows = q.limit(limit).all()
    # reverse to chronological
    rows = list(reversed(rows))

    def clean(content: str) -> str:
        # Aggressively remove checkmark / warning confirmation lines
        # so the LLM never sees or comments on them
        content = re.sub(r"[✅✔☑✓]", "", content)
        content = re.sub(r"[⚠️⚠]", "", content)
        content = re.sub(r"(?i)\b(check\s*mark|tick\s*mark|checkmarked)\b", "", content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        return content

    return [{"role": r.role, "content": clean(r.content)} for r in rows]
