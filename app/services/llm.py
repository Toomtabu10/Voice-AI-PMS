"""
LLM service – fully configurable via .env.
Uses LiteLLM so switching providers/models requires only .env changes.
Now supports structured actions for voice editing.
"""
from litellm import completion
from app.config import settings
from typing import List, Dict, Any, Optional, Tuple
import json
import os
import re


def _ensure_env_keys():
    """Push settings into os.environ so LiteLLM can pick them up."""
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
    if settings.XAI_API_KEY:
        os.environ["XAI_API_KEY"] = settings.XAI_API_KEY
    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    if settings.OLLAMA_API_BASE:
        os.environ["OLLAMA_API_BASE"] = settings.OLLAMA_API_BASE


def _recover_from_tool_use_error(error_text: str) -> Optional[str]:
    """Some Groq-hosted models (notably the openai/gpt-oss-* family) are
    natively trained with a "Harmony" tool-calling format and can emit a
    native tool call on their own initiative -- even though this app never
    declares any `tools` in the request. Groq then rejects the response
    server-side with a tool_use_failed error (tool_choice defaults to
    "none" when no tools were registered, and the model ignored that).

    The model's actual intended reply is still present in the error body
    as `failed_generation`, shaped like {"name": "action", "arguments": {...}}
    -- "arguments" is exactly the JSON payload our own prompt asks the model
    to put inside a ```action fenced block. Recover it and reformat it as
    that same fenced block, so answer_with_context's existing parser
    handles it completely unchanged. Returns None if nothing recoverable
    is found (e.g. a genuinely different error), so callers can fall back
    to raising/surfacing the original error untouched.
    """
    if "tool_use_failed" not in error_text and "failed_generation" not in error_text:
        return None
    match = re.search(r'"failed_generation"\s*:\s*"((?:[^"\\]|\\.)*)"', error_text)
    if not match:
        return None
    try:
        # The captured group is itself a JSON-escaped string; un-escape it
        # by re-parsing it as a JSON string literal, then parse THAT as JSON.
        inner = json.loads('"' + match.group(1) + '"')
        payload = json.loads(inner)
    except (json.JSONDecodeError, ValueError):
        return None
    arguments = payload.get("arguments")
    if not isinstance(arguments, dict):
        return None
    return "I'll make that change.\n\n```action\n" + json.dumps(arguments) + "\n```"


def chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 2000,
    response_format: Optional[Dict] = None,
) -> str:
    """Call the configured LLM and return the assistant message content."""
    _ensure_env_keys()
    kwargs: Dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = completion(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        recovered = _recover_from_tool_use_error(str(e))
        if recovered is not None:
            return recovered
        raise


def extract_structured_from_text(text: str, patient_context: str = "") -> Dict[str, Any]:
    """
    Use LLM to extract structured medical data from free-text (e.g. PDF content).
    """
    system = """You are a medical data extraction assistant. Extract structured patient information from the provided medical report text.
Return ONLY valid JSON with the following top-level keys (use empty lists/objects if nothing found):
{
  "demographics": {"first_name": null, "last_name": null, "date_of_birth": null, "gender": null, "mrn": null, ...},
  "allergies": [{"allergen": "", "reaction": "", "severity": "", "start_date": null, "end_date": null, "status": "active"}],
  "medications": [{"name": "", "dosage": "", "frequency": "", "route": "", "start_date": null, "end_date": null, "status": "active"}],
  "conditions": [{"name": "", "icd_code": null, "status": "active", "start_date": null, "end_date": null}],
  "vitals": [{"temperature_c": null, "heart_rate": null, "bp_systolic": null, "bp_diastolic": null, "spo2": null, "weight_kg": null, "height_cm": null, "recorded_at": null}],
  "lab_results": [{"test_name": "", "value": "", "unit": "", "reference_range": "", "flag": null, "category": "", "resulted_at": null}],
  "encounters": [{"encounter_type": "", "date": null, "provider": "", "chief_complaint": "", "assessment": "", "plan": ""}],
  "notes": ""
}
Use ISO dates (YYYY-MM-DD) or ISO datetimes where possible. Be conservative – only extract clearly stated facts.
Do not invent data."""

    user = f"Patient context (if any):\n{patient_context}\n\nMedical report text:\n{text[:15000]}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    raw = chat(messages, temperature=0.1, max_tokens=4000)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_extraction": raw, "error": "Failed to parse JSON"}


def generate_patient_summary(patient_data: Dict[str, Any], focus: Optional[str] = None) -> str:
    """Generate a concise clinical summary of the patient."""
    system = """You are an experienced clinician. Produce a clear, professional patient summary suitable for a quick hand-over or chart review.
Structure the summary with sections: Demographics, Active Problems, Medications, Allergies, Recent Vitals, Key Lab Trends, Recent Encounters / Notes, and Overall Impression / Recommendations if appropriate.
Be factual and concise. Highlight abnormal or critical values. Do not invent information."""

    focus_note = f"\nFocus especially on: {focus}" if focus else ""
    user = f"Patient data (JSON):\n{json.dumps(patient_data, default=str, indent=2)[:12000]}{focus_note}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat(messages, temperature=0.2, max_tokens=2500)


def answer_with_context(
    user_message: str,
    patient_context: str,
    conversation_history: List[Dict[str, str]],
    patient_id: Optional[int] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Answer a user question. If the user wants to change data, return a structured action.
    Returns: (reply_text, action_dict or None)
    """
    system = f"""You are a helpful medical AI assistant embedded in a local patient records system.
You can both answer questions AND update the patient record when the user asks you to change something.

Current patient data:
{patient_context}

=== RULES ===
1. If the user is only asking a question → reply normally in plain text.
2. If the user wants to CHANGE or ADD data (blood type, phone, allergy, medication, condition, vitals, etc.) you MUST output a special JSON action block.

When you need to make a change, end your reply with exactly this format (nothing after it):

```action
{{"action": "ACTION_NAME", ...fields...}}
```

Supported actions:

A) Update patient demographics:
```action
{{"action": "update_patient", "fields": {{"blood_type": "O+", "phone_primary": "9972455188", "email": "...", "height_cm": 172, "weight_kg": 77, "gender": "male", "primary_care_provider": "..."}}}}
```
Only include the fields that should be changed.

B) Add allergy:
```action
{{"action": "add_allergy", "allergen": "NSAID", "reaction": "vomiting", "severity": "moderate", "start_date": "2024-01-15", "status": "active"}}
```

C) Add medication:
```action
{{"action": "add_medication", "name": "Metformin", "dosage": "500mg", "frequency": "twice daily", "route": "oral", "start_date": "2024-03-01", "status": "active"}}
```

D) Update medication (ANY field can be changed):
```action
{{"action": "update_medication", "medication_name": "Metformin", "status": "inactive", "end_date": "2026-08-22"}}
```
You can update any of these fields: name, dosage, frequency, route, start_date, end_date, status, prescribed_by, indication, notes.
Match by medication_name (case-insensitive). If multiple match, the most recent one is updated.
Examples:
- Mark inactive: {{"action": "update_medication", "medication_name": "Metformin", "status": "inactive", "end_date": "2026-08-22"}}
- Change dose: {{"action": "update_medication", "medication_name": "Metformin", "dosage": "1000mg", "frequency": "once daily"}}
- Change multiple: {{"action": "update_medication", "medication_name": "Atorvastatin", "dosage": "20mg", "status": "active", "start_date": "2026-01-01"}}

E) Add condition:
```action
{{"action": "add_condition", "name": "Type 2 Diabetes", "status": "active", "start_date": "2023-06-01"}}
```

F) Add vitals:
```action
{{"action": "add_vitals", "bp_systolic": 120, "bp_diastolic": 80, "heart_rate": 72, "temperature_c": 36.6, "spo2": 98, "weight_kg": 77, "height_cm": 172}}
```

Before the action block, write a short friendly confirmation of what you are changing.
If the request is unclear, ask for clarification instead of inventing values.
Never invent medical facts that were not provided by the user.
"""

    messages = [{"role": "system", "content": system}]
    for msg in conversation_history[-16:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    raw = chat(messages, temperature=0.2, max_tokens=1200)

    # Try to extract action block
    action = None
    reply = raw

    # Look for ```action ... ```
    match = re.search(r"```action\s*\n?(.*?)\n?```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            action = json.loads(match.group(1).strip())
            # Remove the action block from the visible reply
            reply = raw[: match.start()].strip()
            if not reply:
                reply = "Done. I have updated the record."
        except json.JSONDecodeError:
            action = None

    return reply, action