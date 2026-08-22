/* Local Patient Records – frontend with Web Speech API voice control */

const API = "/api";
let currentPatientId = null;
let recognition = null;
let isListening = false;
let synth = window.speechSynthesis;

// ---------- Utils ----------
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  return res.json();
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function speak(text) {
  if (!synth) return;
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.0;
  u.pitch = 1.0;
  synth.speak(u);
}

function addChatMessage(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;
  const box = $("#chat-messages");
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

// ---------- Voice (Web Speech API – fully local in browser) ----------
function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    $("#voice-status").textContent = "Voice: Not supported";
    return;
  }
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isListening = true;
    $("#btn-mic").classList.add("recording");
    $("#voice-status").textContent = "Voice: Listening…";
    $("#voice-status").classList.add("listening");
  };
  recognition.onend = () => {
    isListening = false;
    $("#btn-mic").classList.remove("recording");
    $("#voice-status").textContent = "Voice: Ready";
    $("#voice-status").classList.remove("listening");
  };
  recognition.onerror = (e) => {
    console.warn("Speech error", e);
    $("#voice-status").textContent = "Voice: Error";
  };
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    if (transcript) {
      $("#chat-input").value = transcript;
      handleUserMessage(transcript, "voice");
    }
  };
}

function toggleMic() {
  if (!recognition) {
    alert("Speech recognition not supported in this browser. Use Chrome/Edge.");
    return;
  }
  if (isListening) {
    recognition.stop();
  } else {
    recognition.start();
  }
}

// ---------- Patients ----------
async function loadPatients(search = "") {
  const q = search ? `?search=${encodeURIComponent(search)}` : "";
  const list = await api(`/patients/${q}`);
  const ul = $("#patient-list");
  ul.innerHTML = "";
  list.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = `${p.last_name}, ${p.first_name} (${p.mrn})`;
    li.dataset.id = p.id;
    if (p.id === currentPatientId) li.classList.add("active");
    li.onclick = () => selectPatient(p.id);
    ul.appendChild(li);
  });
}

async function selectPatient(id) {
  currentPatientId = id;
  $$("#patient-list li").forEach((li) => li.classList.toggle("active", +li.dataset.id === id));
  $("#welcome").classList.add("hidden");
  $("#patient-panel").classList.remove("hidden");
  const p = await api(`/patients/${id}`);
  renderPatient(p);
  loadChatHistory(id);
}

function renderPatient(p) {
  $("#patient-name").textContent = `${p.first_name} ${p.last_name}`;
  $("#patient-mrn").textContent = `MRN: ${p.mrn} · DOB: ${p.date_of_birth} · ${p.gender || ""}`;

  $("#demo-info").innerHTML = `
    <p>Phone: ${p.phone_primary || "—"}</p>
    <p>Email: ${p.email || "—"}</p>
    <p>Blood type: ${p.blood_type || "—"}</p>
    <p>Height: ${p.height_cm ? p.height_cm + " cm" : "—"} · Weight: ${p.weight_kg ? p.weight_kg + " kg" : "—"}</p>
    <p>Status: ${p.status}</p>
    <p>PCP: ${p.primary_care_provider || "—"}</p>
  `;

  const renderList = (el, items, fmt) => {
    el.innerHTML = items.length ? items.map(fmt).join("") : "<li class='muted'>None recorded</li>";
  };
  renderList($("#conditions-list"), p.conditions || [], (c) =>
    `<li><strong>${c.name}</strong> ${c.icd_code ? "(" + c.icd_code + ")" : ""} – ${c.status}</li>`
  );
  renderList($("#allergies-list"), p.allergies || [], (a) =>
    `<li><strong>${a.allergen}</strong> – ${a.reaction || ""} (${a.severity || "?"})</li>`
  );
  renderList($("#allergies-list-2"), p.allergies || [], (a) =>
    `<li><strong>${a.allergen}</strong> – ${a.reaction || ""} (${a.severity || "?"})</li>`
  );
  renderList($("#meds-list"), p.medications || [], (m) =>
    `<li><strong>${m.name}</strong> ${m.dosage || ""} ${m.frequency || ""} – ${m.status}</li>`
  );

  // Vitals table
  const vitals = p.recent_vitals || [];
  $("#vitals-table").innerHTML = vitals.length
    ? `<table><thead><tr><th>Time</th><th>BP</th><th>HR</th><th>Temp</th><th>SpO2</th><th>Wt</th></tr></thead>
       <tbody>${vitals.map((v) => `<tr>
         <td>${v.recorded_at?.slice(0, 16) || ""}</td>
         <td>${v.bp_systolic || "—"}/${v.bp_diastolic || "—"}</td>
         <td>${v.heart_rate || "—"}</td>
         <td>${v.temperature_c || "—"}</td>
         <td>${v.spo2 || "—"}</td>
         <td>${v.weight_kg || "—"}</td>
       </tr>`).join("")}</tbody></table>`
    : "<p class='muted'>No vitals recorded</p>";

  // Labs
  const labs = p.recent_labs || [];
  $("#labs-table").innerHTML = labs.length
    ? `<table><thead><tr><th>Test</th><th>Value</th><th>Flag</th><th>Date</th></tr></thead>
       <tbody>${labs.map((l) => `<tr>
         <td>${l.test_name}</td>
         <td>${l.value || l.numeric_value || "—"} ${l.unit || ""}</td>
         <td>${l.flag || ""}</td>
         <td>${(l.resulted_at || "").slice(0, 10)}</td>
       </tr>`).join("")}</tbody></table>`
    : "<p class='muted'>No labs recorded</p>";

  // Documents
  const docs = p.documents || [];
  $("#docs-list").innerHTML = docs.length
    ? docs.map((d) => `
        <li style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;padding:0.5rem 0;">
          <span style="flex:1;min-width:180px;">${d.original_filename || d.filename}
            <span class="muted"> – ${d.processing_status} (${(d.uploaded_at||"").slice(0,16)})</span>
          </span>
          <a href="/api/documents/${d.id}/download" target="_blank" style="color:#3b82f6;text-decoration:none;font-size:0.85rem;">📄 View / Download</a>
          <button onclick="viewExtracted(${d.id})" style="font-size:0.8rem;padding:0.25rem 0.6rem;">View Extracted Data</button>
        </li>`).join("")
    : "<li class='muted'>No documents</li>";
}

async function viewExtracted(docId) {
  try {
    const data = await api(`/documents/${docId}/extracted`);
    const text = data.extracted_text || "(no text extracted)";
    const structured = data.structured_data ? JSON.stringify(data.structured_data, null, 2) : "(none)";
    const win = window.open("", "_blank");
    win.document.write(`<pre style="white-space:pre-wrap;font-family:system-ui;padding:1.5rem;background:#0f172a;color:#f1f5f9;">Status: ${data.processing_status}

=== EXTRACTED TEXT ===
${text}

=== STRUCTURED DATA ===
${structured}</pre>`);
  } catch (e) {
    alert("Could not load extracted data: " + e.message);
  }
}


// ---------- Chat ----------
async function handleUserMessage(text, modality = "text") {
  if (!text.trim()) return;
  addChatMessage("user", text);
  $("#chat-input").value = "";

  try {
    const res = await api("/chat/", {
      method: "POST",
      body: JSON.stringify({
        patient_id: currentPatientId,
        message: text,
        modality,
        include_history: true,
      }),
    });
    addChatMessage("assistant", res.reply);
    if (modality === "voice") speak(res.reply);

    // Refresh patient view after any likely update (voice editing)
    if (currentPatientId && (res.reply.includes("Done.") || res.reply.includes("Updated:") || res.reply.includes("Added") ||
        /add|create|update|record|save|allerg|medic|vital|lab|condition|blood|phone|set|change|remove/i.test(text))) {
      setTimeout(() => selectPatient(currentPatientId), 300);
    }
  } catch (e) {
    addChatMessage("assistant", "Error: " + e.message);
  }
}

function formatIST(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
    return d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }) + " IST";
  } catch (_) {
    return isoStr;
  }
}

async function loadChatHistory(patientId) {
  const box = $("#chat-messages");
  box.innerHTML = "";
  const histBox = $("#comm-history");
  if (histBox) histBox.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const hist = await api(`/chat/history?patient_id=${patientId}&limit=50`);
    // Chat panel stays chronological (oldest first) for natural reading
    hist.forEach((m) => addChatMessage(m.role, m.content));

    // History tab: newest first + India timestamps
    if (histBox) {
      if (!hist.length) {
        histBox.innerHTML = "<p class='muted'>No communication history yet.</p>";
      } else {
        const reversed = [...hist].reverse();
        histBox.innerHTML = reversed.map((m) => `
          <div style="margin-bottom:0.75rem;padding:0.6rem 0.85rem;border-radius:10px;background:${m.role === 'user' ? '#1e3a5f' : '#1e293b'};">
            <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.25rem;">
              ${m.role.toUpperCase()} · ${formatIST(m.created_at)} · ${m.modality || "text"}
            </div>
            <div style="white-space:pre-wrap;font-size:0.9rem;">${m.content}</div>
          </div>`).join("");
      }
    }
  } catch (e) {
    if (histBox) histBox.innerHTML = "<p class='muted'>Could not load history.</p>";
  }
}

// ---------- Summary ----------
async function requestSummary() {
  if (!currentPatientId) return;
  addChatMessage("user", "Generate a full patient summary");
  try {
    const res = await api(`/patients/${currentPatientId}/summary`);
    addChatMessage("assistant", res.summary);
    speak(res.summary.slice(0, 600) + (res.summary.length > 600 ? " …" : ""));
  } catch (e) {
    addChatMessage("assistant", "Error generating summary: " + e.message);
  }
}

// ---------- PDF Upload ----------
async function uploadPdf() {
  if (!currentPatientId) {
    alert("Select a patient first");
    return;
  }
  const fileInput = $("#pdf-upload");
  if (!fileInput.files.length) {
    alert("Choose a PDF file");
    return;
  }
  const fd = new FormData();
  fd.append("patient_id", currentPatientId);
  fd.append("document_type", "lab_report");
  fd.append("file", fileInput.files[0]);

  addChatMessage("assistant", "Uploading and processing PDF… this may take a moment.");
  try {
    const res = await fetch(API + "/documents/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
    const doc = await res.json();
    addChatMessage("assistant", `Document processed successfully (status: ${doc.processing_status}). Data has been added to the record.`);
    speak("Document processed. Data extracted into the patient record.");
    selectPatient(currentPatientId);
  } catch (e) {
    addChatMessage("assistant", "Upload error: " + e.message);
  }
}

// ---------- Simple modal forms ----------
function showModal(title, fields, onSave) {
  $("#modal-title").textContent = title;
  const body = $("#modal-body");
  body.innerHTML = fields
    .map(
      (f) =>
        `<label>${f.label}</label><input type="${f.type || "text"}" id="f-${f.name}" value="${f.value || ""}" ${f.required ? "required" : ""} />`
    )
    .join("");
  $("#modal").classList.remove("hidden");
  $("#modal-cancel").onclick = () => $("#modal").classList.add("hidden");
  $("#modal-save").onclick = async () => {
    const data = {};
    fields.forEach((f) => {
      const el = $(`#f-${f.name}`);
      data[f.name] = el.value || null;
    });
    try {
      await onSave(data);
      $("#modal").classList.add("hidden");
    } catch (e) {
      alert(e.message);
    }
  };
}

function newPatientForm() {
  showModal(
    "New Patient",
    [
      { name: "mrn", label: "MRN *", required: true },
      { name: "first_name", label: "First name *", required: true },
      { name: "last_name", label: "Last name *", required: true },
      { name: "date_of_birth", label: "Date of birth (YYYY-MM-DD) *", type: "date", required: true },
      { name: "gender", label: "Gender" },
      { name: "phone_primary", label: "Phone" },
      { name: "email", label: "Email" },
    ],
    async (data) => {
      const p = await api("/patients/", { method: "POST", body: JSON.stringify(data) });
      await loadPatients();
      selectPatient(p.id);
      speak(`Patient ${p.first_name} ${p.last_name} created.`);
    }
  );
}

async function editPatientForm() {
  if (!currentPatientId) return;
  const p = await api(`/patients/${currentPatientId}`);
  showModal(
    "Edit Patient",
    [
      { name: "first_name", label: "First name *", value: p.first_name || "", required: true },
      { name: "last_name", label: "Last name *", value: p.last_name || "", required: true },
      { name: "date_of_birth", label: "Date of birth", type: "date", value: p.date_of_birth || "" },
      { name: "gender", label: "Gender", value: p.gender || "" },
      { name: "phone_primary", label: "Phone", value: p.phone_primary || "" },
      { name: "email", label: "Email", value: p.email || "" },
      { name: "blood_type", label: "Blood type", value: p.blood_type || "" },
      { name: "height_cm", label: "Height (cm)", type: "number", value: p.height_cm || "" },
      { name: "weight_kg", label: "Weight (kg)", type: "number", value: p.weight_kg || "" },
      { name: "primary_care_provider", label: "Primary Care Provider", value: p.primary_care_provider || "" },
      { name: "notes", label: "Notes", value: p.notes || "" },
    ],
    async (data) => {
      // Convert number fields
      if (data.height_cm) data.height_cm = parseFloat(data.height_cm);
      if (data.weight_kg) data.weight_kg = parseFloat(data.weight_kg);
      await api(`/patients/${currentPatientId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      await loadPatients();
      selectPatient(currentPatientId);
      speak("Patient updated.");
    }
  );
}

// ---------- Tabs ----------
$$(".tab").forEach((tab) => {
  tab.onclick = () => {
    $$(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    $$(".tab-content").forEach((c) => c.classList.add("hidden"));
    $(`#tab-${tab.dataset.tab}`).classList.remove("hidden");
  };
});

// ---------- Event bindings ----------
$("#btn-mic").onclick = toggleMic;
$("#btn-send").onclick = () => handleUserMessage($("#chat-input").value);
$("#btn-stop-voice").onclick = () => synth.cancel();
$("#chat-input").onkeydown = (e) => {
  if (e.key === "Enter") handleUserMessage($("#chat-input").value);
};
$("#btn-search").onclick = () => loadPatients($("#search-input").value);
$("#search-input").onkeydown = (e) => {
  if (e.key === "Enter") loadPatients($("#search-input").value);
};
$("#btn-new-patient").onclick = newPatientForm;
$("#btn-edit-patient").onclick = editPatientForm;
$("#btn-summary").onclick = requestSummary;
$("#btn-upload-pdf").onclick = uploadPdf;

$("#btn-add-vitals").onclick = () => {
  if (!currentPatientId) return;
  showModal(
    "Add Vitals",
    [
      { name: "bp_systolic", label: "Systolic BP", type: "number" },
      { name: "bp_diastolic", label: "Diastolic BP", type: "number" },
      { name: "heart_rate", label: "Heart rate", type: "number" },
      { name: "temperature_c", label: "Temp (°C)", type: "number" },
      { name: "spo2", label: "SpO2 %", type: "number" },
      { name: "weight_kg", label: "Weight (kg)", type: "number" },
      { name: "height_cm", label: "Height (cm)", type: "number" },
    ],
    async (data) => {
      // coerce numbers
      for (const k of Object.keys(data)) if (data[k]) data[k] = +data[k];
      await api(`/patients/${currentPatientId}/vitals`, { method: "POST", body: JSON.stringify(data) });
      selectPatient(currentPatientId);
    }
  );
};

$("#btn-add-med").onclick = () => {
  if (!currentPatientId) return;
  showModal(
    "Add Medication",
    [
      { name: "name", label: "Name *", required: true },
      { name: "dosage", label: "Dosage" },
      { name: "frequency", label: "Frequency" },
      { name: "route", label: "Route" },
    ],
    async (data) => {
      await api(`/patients/${currentPatientId}/medications`, { method: "POST", body: JSON.stringify(data) });
      selectPatient(currentPatientId);
    }
  );
};

$("#btn-add-allergy").onclick = () => {
  if (!currentPatientId) return;
  showModal(
    "Add Allergy",
    [
      { name: "allergen", label: "Allergen *", required: true },
      { name: "reaction", label: "Reaction" },
      { name: "severity", label: "Severity (mild/moderate/severe)" },
    ],
    async (data) => {
      await api(`/patients/${currentPatientId}/allergies`, { method: "POST", body: JSON.stringify(data) });
      selectPatient(currentPatientId);
    }
  );
};

$("#btn-add-lab").onclick = () => {
  if (!currentPatientId) return;
  showModal(
    "Add Lab Result",
    [
      { name: "test_name", label: "Test name *", required: true },
      { name: "value", label: "Value" },
      { name: "unit", label: "Unit" },
      { name: "reference_range", label: "Reference range" },
      { name: "flag", label: "Flag (normal/high/low)" },
      { name: "category", label: "Category (CBC, CMP…)" },
    ],
    async (data) => {
      await api(`/patients/${currentPatientId}/labs`, { method: "POST", body: JSON.stringify(data) });
      selectPatient(currentPatientId);
    }
  );
};

// ---------- Init ----------
initVoice();
loadPatients();
addChatMessage("assistant", "Hello! I am your local patient records assistant. Select or create a patient, or just speak to me. All data stays on this machine except LLM calls.");
