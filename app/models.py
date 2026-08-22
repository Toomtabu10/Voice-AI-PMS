from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class PatientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    deceased = "deceased"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    mrn = Column(String(50), unique=True, index=True, nullable=False)  # Medical Record Number
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), default="unknown")
    sex_at_birth = Column(String(20))
    blood_type = Column(String(10))
    phone_primary = Column(String(30))
    phone_secondary = Column(String(30))
    email = Column(String(255))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(50), default="USA")
    race = Column(String(100))
    ethnicity = Column(String(100))
    preferred_language = Column(String(50), default="English")
    marital_status = Column(String(50))
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(30))
    emergency_contact_relation = Column(String(50))
    primary_care_provider = Column(String(200))
    insurance_provider = Column(String(200))
    insurance_id = Column(String(100))
    status = Column(String(20), default="active")
    deceased_date = Column(Date)
    height_cm = Column(Float)  # latest
    weight_kg = Column(Float)  # latest
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("Condition", back_populates="patient", cascade="all, delete-orphan")
    vitals = relationship("VitalSign", back_populates="patient", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")
    notes_list = relationship("ClinicalNote", back_populates="patient", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="patient", cascade="all, delete-orphan")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    allergen = Column(String(200), nullable=False)
    reaction = Column(String(500))
    severity = Column(String(50))  # mild, moderate, severe, life-threatening
    onset_date = Column(Date)
    status = Column(String(20), default="active")  # active, resolved
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))  # e.g. "user", "pdf_report", "ai"

    patient = relationship("Patient", back_populates="allergies")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    name = Column(String(200), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))
    route = Column(String(50))  # oral, IV, topical, etc.
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="active")  # active, discontinued, completed
    prescribed_by = Column(String(200))
    indication = Column(String(300))
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))

    patient = relationship("Patient", back_populates="medications")


class Condition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    name = Column(String(300), nullable=False)
    icd_code = Column(String(20))
    status = Column(String(20), default="active")  # active, resolved, chronic
    onset_date = Column(Date)
    resolved_date = Column(Date)
    severity = Column(String(50))
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))

    patient = relationship("Patient", back_populates="conditions")


class VitalSign(Base):
    __tablename__ = "vital_signs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    temperature_c = Column(Float)
    heart_rate = Column(Integer)  # bpm
    respiratory_rate = Column(Integer)
    bp_systolic = Column(Integer)
    bp_diastolic = Column(Integer)
    spo2 = Column(Float)  # %
    weight_kg = Column(Float)
    height_cm = Column(Float)
    bmi = Column(Float)
    pain_score = Column(Integer)  # 0-10
    blood_glucose = Column(Float)
    notes = Column(Text)
    source = Column(String(100))

    patient = relationship("Patient", back_populates="vitals")
    encounter = relationship("Encounter", back_populates="vitals")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)
    test_name = Column(String(200), nullable=False)
    test_code = Column(String(50))  # LOINC if available
    value = Column(String(100))  # store as string for flexibility (can be numeric or qualitative)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50))
    reference_range = Column(String(100))
    flag = Column(String(20))  # normal, high, low, critical
    collected_at = Column(DateTime)
    resulted_at = Column(DateTime, default=datetime.utcnow)
    lab_name = Column(String(200))
    notes = Column(Text)
    source = Column(String(100))
    category = Column(String(100))  # CBC, CMP, Lipid, HbA1c, etc.

    patient = relationship("Patient", back_populates="lab_results")
    encounter = relationship("Encounter", back_populates="lab_results")


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_type = Column(String(50))  # outpatient, inpatient, emergency, telehealth, etc.
    date = Column(DateTime, default=datetime.utcnow)
    provider = Column(String(200))
    location = Column(String(200))
    chief_complaint = Column(Text)
    assessment = Column(Text)
    plan = Column(Text)
    notes = Column(Text)
    status = Column(String(20), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))

    patient = relationship("Patient", back_populates="encounters")
    vitals = relationship("VitalSign", back_populates="encounter")
    lab_results = relationship("LabResult", back_populates="encounter")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(500))
    mime_type = Column(String(100))
    file_size = Column(Integer)
    document_type = Column(String(100))  # lab_report, imaging, discharge_summary, etc.
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    extracted_text = Column(Text)
    structured_data = Column(JSON)  # LLM-extracted structured fields
    processing_status = Column(String(50), default="pending")  # pending, processed, failed
    notes = Column(Text)
    source = Column(String(100), default="upload")

    patient = relationship("Patient", back_populates="documents")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    note_type = Column(String(50))  # progress, soap, discharge, nursing, etc.
    title = Column(String(300))
    content = Column(Text, nullable=False)
    author = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(100))

    patient = relationship("Patient", back_populates="notes_list")


class Communication(Base):
    """Stores all AI chats / voice interactions / user messages related to a patient."""
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # null for general system chat
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    modality = Column(String(20), default="text")  # text, voice
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON)  # extra info e.g. audio duration, confidence

    patient = relationship("Patient", back_populates="communications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)  # create, update, delete
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(100), default="system")
    changed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String(500))
    ip_address = Column(String(50))
