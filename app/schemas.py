from datetime import datetime, date
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# ---------- Patient ----------
class PatientBase(BaseModel):
    mrn: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    date_of_birth: date
    gender: Optional[str] = "unknown"
    sex_at_birth: Optional[str] = None
    blood_type: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "USA"
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: Optional[str] = "English"
    marital_status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    primary_care_provider: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_id: Optional[str] = None
    status: Optional[str] = "active"
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    sex_at_birth: Optional[str] = None
    blood_type: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: Optional[str] = None
    marital_status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    primary_care_provider: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_id: Optional[str] = None
    status: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class PatientOut(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Allergy ----------
class AllergyBase(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = "active"
    notes: Optional[str] = None
    source: Optional[str] = "user"


class AllergyCreate(AllergyBase):
    patient_id: int


class AllergyUpdate(BaseModel):
    allergen: Optional[str] = None
    reaction: Optional[str] = None
    severity: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AllergyOut(AllergyBase):
    id: int
    patient_id: int
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Medication ----------
class MedicationBase(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = "active"
    prescribed_by: Optional[str] = None
    indication: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = "user"


class MedicationCreate(MedicationBase):
    patient_id: int


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    prescribed_by: Optional[str] = None
    indication: Optional[str] = None
    notes: Optional[str] = None


class MedicationOut(MedicationBase):
    id: int
    patient_id: int
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Condition ----------
class ConditionBase(BaseModel):
    name: str
    icd_code: Optional[str] = None
    status: Optional[str] = "active"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = "user"


class ConditionCreate(ConditionBase):
    patient_id: int


class ConditionUpdate(BaseModel):
    name: Optional[str] = None
    icd_code: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    severity: Optional[str] = None
    notes: Optional[str] = None


class ConditionOut(ConditionBase):
    id: int
    patient_id: int
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- VitalSign ----------
class VitalSignBase(BaseModel):
    temperature_c: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    spo2: Optional[float] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    bmi: Optional[float] = None
    pain_score: Optional[int] = None
    blood_glucose: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[str] = "user"
    recorded_at: Optional[datetime] = None
    encounter_id: Optional[int] = None


class VitalSignCreate(VitalSignBase):
    patient_id: int


class VitalSignOut(VitalSignBase):
    id: int
    patient_id: int
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- LabResult ----------
class LabResultBase(BaseModel):
    test_name: str
    test_code: Optional[str] = None
    value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: Optional[str] = None
    collected_at: Optional[datetime] = None
    resulted_at: Optional[datetime] = None
    lab_name: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = "user"
    category: Optional[str] = None
    encounter_id: Optional[int] = None


class LabResultCreate(LabResultBase):
    patient_id: int


class LabResultOut(LabResultBase):
    id: int
    patient_id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- Encounter ----------
class EncounterBase(BaseModel):
    encounter_type: Optional[str] = None
    date: Optional[datetime] = None
    provider: Optional[str] = None
    location: Optional[str] = None
    chief_complaint: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "completed"
    source: Optional[str] = "user"


class EncounterCreate(EncounterBase):
    patient_id: int


class EncounterOut(EncounterBase):
    id: int
    patient_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------- Document ----------
class DocumentOut(BaseModel):
    id: int
    patient_id: int
    filename: str
    original_filename: Optional[str]
    document_type: Optional[str]
    uploaded_at: datetime
    processing_status: str
    structured_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- ClinicalNote ----------
class ClinicalNoteCreate(BaseModel):
    patient_id: int
    note_type: Optional[str] = "progress"
    title: Optional[str] = None
    content: str
    author: Optional[str] = "user"
    source: Optional[str] = "user"


class ClinicalNoteOut(BaseModel):
    id: int
    patient_id: int
    note_type: Optional[str]
    title: Optional[str]
    content: str
    author: Optional[str]
    created_at: datetime
    updated_at: datetime
    source: Optional[str]
    model_config = ConfigDict(from_attributes=True)


# ---------- Communication ----------
class CommunicationCreate(BaseModel):
    patient_id: Optional[int] = None
    role: str
    content: str
    modality: Optional[str] = "text"
    metadata_json: Optional[Dict[str, Any]] = None


class CommunicationOut(BaseModel):
    id: int
    patient_id: Optional[int]
    role: str
    content: str
    modality: str
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


# ---------- Chat / AI ----------
class ChatRequest(BaseModel):
    patient_id: Optional[int] = None
    message: str
    modality: Optional[str] = "text"
    include_history: bool = True


class ChatResponse(BaseModel):
    reply: str
    communication_id: Optional[int] = None


class SummaryRequest(BaseModel):
    patient_id: int
    focus: Optional[str] = None  # e.g. "recent labs", "medications", "full"


class SummaryResponse(BaseModel):
    summary: str
    generated_at: datetime


# ---------- Audit ----------
class AuditLogOut(BaseModel):
    id: int
    table_name: str
    record_id: int
    action: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: str
    changed_at: datetime
    reason: Optional[str]
    model_config = ConfigDict(from_attributes=True)


# ---------- Full Patient Detail ----------
class PatientDetail(PatientOut):
    allergies: List[AllergyOut] = []
    medications: List[MedicationOut] = []
    conditions: List[ConditionOut] = []
    recent_vitals: List[VitalSignOut] = []
    recent_labs: List[LabResultOut] = []
    encounters: List[EncounterOut] = []
    documents: List[DocumentOut] = []
