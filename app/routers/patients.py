from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas
from app.services.audit import log_change, audit_model_update
from app.services.patient_context import build_patient_dict
from app.services.llm import generate_patient_summary

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/", response_model=schemas.PatientOut)
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Patient).filter(models.Patient.mrn == payload.mrn).first()
    if existing:
        raise HTTPException(status_code=400, detail="MRN already exists")
    patient = models.Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    log_change(db, "patients", patient.id, "create", changed_by="user")
    db.commit()
    return patient


@router.get("/", response_model=List[schemas.PatientOut])
def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Patient)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Patient.first_name.ilike(like))
            | (models.Patient.last_name.ilike(like))
            | (models.Patient.mrn.ilike(like))
        )
    return q.order_by(models.Patient.last_name).offset(skip).limit(limit).all()


@router.get("/{patient_id}", response_model=schemas.PatientDetail)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Attach related for detail view
    detail = schemas.PatientDetail.model_validate(patient)
    detail.allergies = patient.allergies
    detail.medications = patient.medications
    detail.conditions = patient.conditions
    detail.recent_vitals = (
        db.query(models.VitalSign)
        .filter(models.VitalSign.patient_id == patient_id)
        .order_by(models.VitalSign.recorded_at.desc())
        .limit(10)
        .all()
    )
    detail.recent_labs = (
        db.query(models.LabResult)
        .filter(models.LabResult.patient_id == patient_id)
        .order_by(models.LabResult.resulted_at.desc())
        .limit(20)
        .all()
    )
    for lab in detail.recent_labs:
        if getattr(lab, "document_id", None):
            doc = db.query(models.Document).filter(models.Document.id == lab.document_id).first()
            if doc:
                lab.original_filename = doc.original_filename or doc.filename
    detail.encounters = (
        db.query(models.Encounter)
        .filter(models.Encounter.patient_id == patient_id)
        .order_by(models.Encounter.date.desc())
        .limit(10)
        .all()
    )
    detail.documents = patient.documents
    return detail


@router.patch("/{patient_id}", response_model=schemas.PatientOut)
def update_patient(
    patient_id: int,
    payload: schemas.PatientUpdate,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    update_data = payload.model_dump(exclude_unset=True)
    audit_model_update(db, "patients", patient_id, patient, update_data, reason=reason)
    for k, v in update_data.items():
        setattr(patient, k, v)
    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    log_change(db, "patients", patient_id, "delete", changed_by="user")
    db.delete(patient)
    db.commit()
    return {"ok": True}


# ---- Sub-resources ----

@router.post("/{patient_id}/allergies", response_model=schemas.AllergyOut)
def add_allergy(patient_id: int, payload: schemas.AllergyBase, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    allergy = models.Allergy(patient_id=patient_id, **payload.model_dump())
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    log_change(db, "allergies", allergy.id, "create", changed_by="user")
    db.commit()
    return allergy


@router.patch("/allergies/{allergy_id}", response_model=schemas.AllergyOut)
def update_allergy(
    allergy_id: int,
    payload: schemas.AllergyUpdate,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    allergy = db.query(models.Allergy).filter(models.Allergy.id == allergy_id).first()
    if not allergy:
        raise HTTPException(status_code=404, detail="Allergy not found")
    update_data = payload.model_dump(exclude_unset=True)
    audit_model_update(db, "allergies", allergy_id, allergy, update_data, reason=reason)
    for k, v in update_data.items():
        setattr(allergy, k, v)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.post("/{patient_id}/medications", response_model=schemas.MedicationOut)
def add_medication(patient_id: int, payload: schemas.MedicationBase, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    med = models.Medication(patient_id=patient_id, **payload.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    log_change(db, "medications", med.id, "create", changed_by="user")
    db.commit()
    return med


@router.patch("/medications/{med_id}", response_model=schemas.MedicationOut)
def update_medication(
    med_id: int,
    payload: schemas.MedicationUpdate,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    med = db.query(models.Medication).filter(models.Medication.id == med_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    update_data = payload.model_dump(exclude_unset=True)
    audit_model_update(db, "medications", med_id, med, update_data, reason=reason)
    for k, v in update_data.items():
        setattr(med, k, v)
    db.commit()
    db.refresh(med)
    return med


@router.post("/{patient_id}/conditions", response_model=schemas.ConditionOut)
def add_condition(patient_id: int, payload: schemas.ConditionBase, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    cond = models.Condition(patient_id=patient_id, **payload.model_dump())
    db.add(cond)
    db.commit()
    db.refresh(cond)
    log_change(db, "conditions", cond.id, "create", changed_by="user")
    db.commit()
    return cond


@router.patch("/conditions/{cond_id}", response_model=schemas.ConditionOut)
def update_condition(
    cond_id: int,
    payload: schemas.ConditionUpdate,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cond = db.query(models.Condition).filter(models.Condition.id == cond_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail="Condition not found")
    update_data = payload.model_dump(exclude_unset=True)
    audit_model_update(db, "conditions", cond_id, cond, update_data, reason=reason)
    for k, v in update_data.items():
        setattr(cond, k, v)
    db.commit()
    db.refresh(cond)
    return cond


@router.post("/{patient_id}/vitals", response_model=schemas.VitalSignOut)
def add_vitals(patient_id: int, payload: schemas.VitalSignBase, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    data = payload.model_dump()
    # Auto-calculate BMI if possible
    if data.get("weight_kg") and data.get("height_cm") and not data.get("bmi"):
        h_m = data["height_cm"] / 100
        data["bmi"] = round(data["weight_kg"] / (h_m * h_m), 1)
    vital = models.VitalSign(patient_id=patient_id, **data)
    db.add(vital)
    # Also update patient's latest height/weight
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if data.get("weight_kg"):
        patient.weight_kg = data["weight_kg"]
    if data.get("height_cm"):
        patient.height_cm = data["height_cm"]
    db.commit()
    db.refresh(vital)
    log_change(db, "vital_signs", vital.id, "create", changed_by="user")
    db.commit()
    return vital


@router.post("/{patient_id}/labs", response_model=schemas.LabResultOut)
def add_lab(patient_id: int, payload: schemas.LabResultBase, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    lab = models.LabResult(patient_id=patient_id, **payload.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    log_change(db, "lab_results", lab.id, "create", changed_by="user")
    db.commit()
    return lab


@router.post("/{patient_id}/encounters", response_model=schemas.EncounterOut)
def add_encounter(patient_id: int, payload: schemas.EncounterBase, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    enc = models.Encounter(patient_id=patient_id, **payload.model_dump())
    db.add(enc)
    db.commit()
    db.refresh(enc)
    log_change(db, "encounters", enc.id, "create", changed_by="user")
    db.commit()
    return enc


@router.post("/{patient_id}/notes", response_model=schemas.ClinicalNoteOut)
def add_note(patient_id: int, payload: schemas.ClinicalNoteCreate, db: Session = Depends(get_db)):
    if not db.query(models.Patient).filter(models.Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")
    note = models.ClinicalNote(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    log_change(db, "clinical_notes", note.id, "create", changed_by="user")
    db.commit()
    return note


@router.get("/{patient_id}/summary", response_model=schemas.SummaryResponse)
def get_summary(
    patient_id: int,
    focus: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data = build_patient_dict(db, patient_id)
    if not data:
        raise HTTPException(status_code=404, detail="Patient not found")
    summary = generate_patient_summary(data, focus=focus)
    # Store the summary generation as a communication
    comm = models.Communication(
        patient_id=patient_id,
        role="assistant",
        content=f"[SUMMARY generated]\n{summary}",
        modality="text",
    )
    db.add(comm)
    db.commit()
    return schemas.SummaryResponse(summary=summary, generated_at=datetime.utcnow())


@router.get("/{patient_id}/audit", response_model=List[schemas.AuditLogOut])
def get_patient_audit(patient_id: int, limit: int = 100, db: Session = Depends(get_db)):
    # Simple: all audit entries for tables that reference this patient is harder;
    # for demo we return recent global audits + those with matching record if possible.
    logs = (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.changed_at.desc())
        .limit(limit)
        .all()
    )
    return logs
