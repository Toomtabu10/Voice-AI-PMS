from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import os
from pathlib import Path
from datetime import datetime, date

from app.database import get_db
from app import models, schemas
from app.config import settings
from app.services.pdf_service import process_pdf
from app.services.audit import log_change
from app.services.patient_context import build_patient_context_text

router = APIRouter(prefix="/documents", tags=["documents"])


def _apply_structured_data(db: Session, patient_id: int, structured: dict, source: str = "pdf_report", document_id: int | None = None):
    """Apply extracted structured data into the database tables."""
    # Demographics updates (only if missing)
    dem = structured.get("demographics") or {}
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient and dem:
        for field in ["blood_type", "gender", "phone_primary", "email"]:
            if dem.get(field) and not getattr(patient, field):
                setattr(patient, field, dem[field])

    for a in structured.get("allergies") or []:
        if not a.get("allergen"):
            continue
        exists = (
            db.query(models.Allergy)
            .filter(
                models.Allergy.patient_id == patient_id,
                models.Allergy.allergen.ilike(a["allergen"]),
            )
            .first()
        )
        if not exists:
            db.add(
                models.Allergy(
                    patient_id=patient_id,
                    allergen=a["allergen"],
                    reaction=a.get("reaction"),
                    severity=a.get("severity"),
                    source=source,
                )
            )

    for m in structured.get("medications") or []:
        if not m.get("name"):
            continue
        db.add(
            models.Medication(
                patient_id=patient_id,
                name=m["name"],
                dosage=m.get("dosage"),
                frequency=m.get("frequency"),
                route=m.get("route"),
                status=m.get("status", "active"),
                source=source,
            )
        )

    for c in structured.get("conditions") or []:
        if not c.get("name"):
            continue
        db.add(
            models.Condition(
                patient_id=patient_id,
                name=c["name"],
                icd_code=c.get("icd_code"),
                status=c.get("status", "active"),
                source=source,
            )
        )

    for v in structured.get("vitals") or []:
        db.add(
            models.VitalSign(
                patient_id=patient_id,
                temperature_c=v.get("temperature_c"),
                heart_rate=v.get("heart_rate"),
                bp_systolic=v.get("bp_systolic"),
                bp_diastolic=v.get("bp_diastolic"),
                spo2=v.get("spo2"),
                weight_kg=v.get("weight_kg"),
                height_cm=v.get("height_cm"),
                source=source,
            )
        )

    for lab in structured.get("lab_results") or []:
        if not lab.get("test_name"):
            continue
        # Skip if same test_name already exists for this patient (case-insensitive)
        exists = (
            db.query(models.LabResult)
            .filter(
                models.LabResult.patient_id == patient_id,
                models.LabResult.test_name.ilike(lab["test_name"]),
            )
            .first()
        )
        if exists:
            continue
        numeric = None
        try:
            if lab.get("value") is not None:
                numeric = float(str(lab["value"]).replace(",", ""))
        except (ValueError, TypeError):
            pass
        db.add(
            models.LabResult(
                patient_id=patient_id,
                document_id=document_id,
                test_name=lab["test_name"],
                value=str(lab.get("value")) if lab.get("value") is not None else None,
                numeric_value=numeric,
                unit=lab.get("unit"),
                reference_range=lab.get("reference_range"),
                flag=lab.get("flag"),
                category=lab.get("category"),
                source=source,
            )
        )

    for e in structured.get("encounters") or []:
        db.add(
            models.Encounter(
                patient_id=patient_id,
                encounter_type=e.get("encounter_type"),
                provider=e.get("provider"),
                chief_complaint=e.get("chief_complaint"),
                assessment=e.get("assessment"),
                plan=e.get("plan"),
                source=source,
            )
        )

    if structured.get("notes"):
        db.add(
            models.ClinicalNote(
                patient_id=patient_id,
                note_type="extracted",
                title="Extracted from uploaded report",
                content=structured["notes"],
                author="system",
                source=source,
            )
        )


@router.post("/upload", response_model=schemas.DocumentOut)
async def upload_document(
    patient_id: int = Form(...),
    document_type: Optional[str] = Form("lab_report"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / stored_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = models.Document(
        patient_id=patient_id,
        filename=stored_name,
        original_filename=file.filename,
        file_path=str(file_path),
        mime_type=file.content_type or "application/pdf",
        file_size=len(content),
        document_type=document_type,
        processing_status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process
    try:
        context = build_patient_context_text(db, patient_id)
        raw_text, structured = await process_pdf(str(file_path), context)
        doc.extracted_text = raw_text
        doc.structured_data = structured
        doc.processing_status = "processed"
        _apply_structured_data(db, patient_id, structured, source="pdf_report", document_id=doc.id)
        log_change(db, "documents", doc.id, "create", changed_by="user", reason="PDF upload + extraction")
        db.commit()
    except Exception as e:
        doc.processing_status = "failed"
        doc.notes = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    db.refresh(doc)
    return doc


@router.get("/patient/{patient_id}", response_model=List[schemas.DocumentOut])
def list_documents(patient_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Document)
        .filter(models.Document.patient_id == patient_id)
        .order_by(models.Document.uploaded_at.desc())
        .all()
    )


@router.get("/{doc_id}", response_model=schemas.DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/download")
def download_document(doc_id: int, inline: bool = False, db: Session = Depends(get_db)):
    """Download or inline-view the original PDF.
    Use ?inline=1 for iframe preview; default is attachment download.

    Explicitly disables caching: doc_id is a reused, autoincrementing
    integer, and this filesystem's uploaded file behind a given id can
    change across a fresh DB/uploads reset (e.g. after a wipe-and-restart,
    the new first upload becomes doc_id=1 again, reusing the exact same
    URL an old, deleted doc_id=1 used). Without no-store, browsers can
    silently serve a stale cached response for that URL instead of the
    current file on disk.
    """
    from fastapi.responses import FileResponse
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    filename = doc.original_filename or doc.filename
    media = doc.mime_type or "application/pdf"
    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    if inline:
        return FileResponse(
            path=str(path),
            media_type=media,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                **no_cache_headers,
            },
        )
    return FileResponse(
        path=str(path),
        filename=filename,
        media_type=media,
        headers=no_cache_headers,
    )


@router.get("/{doc_id}/extracted")
def get_extracted_text(doc_id: int, db: Session = Depends(get_db)):
    """Return the extracted text and structured data from a processed PDF."""
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "processing_status": doc.processing_status,
        "extracted_text": doc.extracted_text,
        "structured_data": doc.structured_data,
        "notes": doc.notes,
    }