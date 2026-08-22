# Local Patient Records System (Voice AI + PMS)

A **FastAPI + SQLite** patient records application that runs entirely on your local machine.

All clinical data is stored locally. The only network traffic is to the configured LLM provider.

---

## Key Features

- **Voice-first interface** – Full system control via browser Web Speech API (speech-to-text + text-to-speech). No extra local models required for voice.
- **LLM switchable via `.env` only** – Powered by [LiteLLM](https://docs.litellm.ai/). Change model / provider / API key without touching code.
- **Rich patient schema** covering demographics, allergies, medications, conditions, vitals, lab results, encounters, clinical notes, and uploaded documents.
- **Start / end dates + active/inactive status** on allergies, medications, and conditions.
- **Full medication editing by voice** – Change any field (dosage, frequency, route, status, dates, etc.).
- **PDF medical report upload** – Text is extracted and structured into the database by the LLM.
- **Editable records with full audit trail** – Every create/update is logged (table, record, field, old/new value, who, when).
- **AI patient summary** – Generate a clinical hand-over style summary on demand from the complete history.
- **Conversation history** – All chat / voice interactions are persisted and available for context.

---

## Quick Start

```bash
# 1. Clone / enter directory
cd patient_records_system

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env – set LLM_MODEL and the corresponding API key

# 5. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in **Chrome or Edge** (best Web Speech API support).

---

## Switching the LLM

Edit only `.env`:

```env
# Examples
LLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...

# or
LLM_MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# or
LLM_MODEL=xai/grok-beta
XAI_API_KEY=xai-...

# or
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk-...

# or local Ollama
LLM_MODEL=ollama/llama3.2
OLLAMA_API_BASE=http://localhost:11434
```

No code changes required.

---

## Voice Usage

- Click the **microphone** button or type in the chat box.
- The browser performs speech recognition locally.
- Replies can be spoken back via the browser’s TTS.
- Example utterances:

  - “Create a new patient named Jane Smith, date of birth 1975-03-22, female”
  - “Show me a summary of the current patient”
  - “What are the latest lab results?”
  - “Add allergy to penicillin with reaction of rash, severity moderate”
  - “Add medication Metformin 500 mg twice daily starting 2024-03-01”
  - “Mark Metformin as inactive with end date today”
  - “Change the dosage of Atorvastatin to 20 mg once daily”
  - “Stop fabrics medication, set status inactive, end date 2026-08-22”

The AI can both **answer questions** and **update the record** (add / edit allergies, medications, conditions, vitals, demographics).

---

## Data Model (main tables)

| Table            | Purpose                                              |
|------------------|------------------------------------------------------|
| patients         | Demographics, identifiers, contacts, height/weight   |
| allergies        | Allergen, reaction, severity, start_date, end_date, status (active/inactive) |
| medications      | Name, dose, frequency, route, start_date, end_date, status (active/inactive) |
| conditions       | Diagnoses / problems, ICD codes, start_date, end_date, status (active/inactive) |
| vital_signs      | BP, HR, temp, SpO2, weight, BMI, etc.                |
| lab_results      | Test name, value, unit, flag, category               |
| encounters       | Visits, chief complaint, assessment, plan            |
| documents        | Uploaded PDFs + extracted structured data            |
| clinical_notes   | Free-text notes                                      |
| communications   | Full chat / voice history                            |
| audit_logs       | Field-level change history                           |

---

## API Overview

| Method | Endpoint                                      | Description                    |
|--------|-----------------------------------------------|--------------------------------|
| POST   | `/api/patients/`                              | Create patient                 |
| GET    | `/api/patients/`                              | List / search patients         |
| GET    | `/api/patients/{id}`                          | Full patient detail            |
| PATCH  | `/api/patients/{id}`                          | Update (audited)               |
| POST   | `/api/patients/{id}/allergies`                | Add allergy                    |
| PATCH  | `/api/allergies/{id}`                         | Update allergy                 |
| POST   | `/api/patients/{id}/medications`              | Add medication                 |
| PATCH  | `/api/medications/{id}`                       | Update medication              |
| POST   | `/api/patients/{id}/conditions`               | Add condition                  |
| POST   | `/api/patients/{id}/vitals`                   | Add vitals                     |
| POST   | `/api/patients/{id}/labs`                     | Add lab result                 |
| POST   | `/api/patients/{id}/encounters`               | Add encounter                  |
| POST   | `/api/patients/{id}/notes`                    | Add clinical note              |
| GET    | `/api/patients/{id}/summary`                  | AI-generated summary           |
| POST   | `/api/documents/upload`                       | PDF upload + extraction        |
| POST   | `/api/chat/`                                  | Conversational AI + actions    |
| GET    | `/api/chat/history`                           | Communication log              |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Security Notes

- Designed for **local single-user / trusted network** use.
- No authentication layer is included (add one for multi-user deployments).
- PHI stays on disk in the SQLite file (`data/patient_records.db`) and the `uploads/` folder.
- Only the text sent to the LLM leaves the machine.

---

## Extending

- Add more structured fields to the models / schemas.
- Replace browser voice with a local STT/TTS stack (e.g. faster-whisper + Piper) if desired.
- Hook the audit log into a compliance dashboard.
- Add authentication for multi-user deployments.

---

Built for privacy-preserving, AI-augmented clinical record keeping on a local machine.
