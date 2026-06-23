// Qplus surgery - Core Frontend Logic
const navTime = document.querySelector("#nav-time");
const navIp = document.querySelector("#nav-ip");
const navStatusIndicator = document.querySelector("#nav-status-indicator");
const navStatusText = document.querySelector("#nav-status-text");
const navLoginButton = document.querySelector("#nav-login-button");
const navLogoutButton = document.querySelector("#nav-logout-button");

const pageIds = ["login", "surgery"];
const defaultPage = "surgery";

// Application State
const state = {
  session: null,
  surgeries: [],
  surgeryFilter: "all",
};

// Update Top Bar Clock
function updateClock() {
  const now = new Date();
  if (navTime) {
    navTime.textContent = now.toLocaleTimeString("ko-KR", {
      hour12: true,
      hour: "2-digit",
      minute: "2-digit"
    });
  }
}
setInterval(updateClock, 1000);
updateClock();

// Escape HTML for safety
function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Toast Notifications
function showToast(message) {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.className = "toast show";
  setTimeout(() => {
    toast.className = "toast";
  }, 3000);
}

// Button Busy State Helper
function setBusy(button, text, isBusy) {
  if (!button) return;
  if (isBusy) {
    button.disabled = true;
    button.dataset.originalText = button.textContent;
    button.textContent = text;
  } else {
    button.disabled = false;
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
  }
}

// API Fetch Helpers
async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "요청 처리에 실패했습니다.");
  }
  return data;
}

async function postJson(url, body = {}) {
  return apiJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function downloadFromApi(url, filename) {
  const response = await fetch(url);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "파일 다운로드 실패");
  }
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}

// Load Authentication Session
async function loadSession() {
  try {
    const session = await apiJson("/api/session");
    state.session = session;

    if (navIp) navIp.textContent = session.client_ip || "0.0.0.0";

    if (session.authorized) {
      if (navStatusIndicator) navStatusIndicator.className = "status-indicator status-online";
      if (navStatusText) navStatusText.textContent = session.cloudflare_access?.email || session.account_login_id || "인증됨";
      if (navLoginButton) navLoginButton.hidden = true;
      if (navLogoutButton) navLogoutButton.hidden = false;
    } else {
      if (navStatusIndicator) navStatusIndicator.className = "status-indicator status-offline";
      if (navStatusText) navStatusText.textContent = "인증 대기";
      if (navLoginButton) navLoginButton.hidden = false;
      if (navLogoutButton) navLogoutButton.hidden = true;
    }
    return session;
  } catch (err) {
    console.error("Session load error:", err);
    return null;
  }
}

// Routing Logic
function pageFromLocation() {
  const path = window.location.pathname.replace(/^\/+/, "").split("/")[0];
  if (pageIds.includes(path)) return path;
  const hashPage = window.location.hash.replace("#", "");
  return pageIds.includes(hashPage) ? hashPage : defaultPage;
}

function setActivePage(page = pageFromLocation(), options = {}) {
  let nextPage = pageIds.includes(page) ? page : defaultPage;

  if (state.session && !state.session.authorized && nextPage !== "login") {
    nextPage = "login";
  } else if (state.session?.authorized && nextPage === "login") {
    nextPage = defaultPage;
  }

  const isLoginPage = nextPage === "login";
  document.documentElement.setAttribute("data-active-page", nextPage);
  document.body.setAttribute("data-router-ready", "true");
  document.querySelectorAll(".global-nav, .sub-nav, .footer").forEach((el) => {
    el.hidden = isLoginPage;
  });

  document.querySelectorAll("[data-page]").forEach((section) => {
    if (section.dataset.page === nextPage) {
      section.hidden = false;
      section.classList.remove("fade-in");
      void section.offsetWidth;
      section.classList.add("fade-in");
    } else {
      section.hidden = true;
      section.classList.remove("fade-in");
    }
  });

  document.querySelectorAll("[data-route]").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.route === nextPage);
  });

  if (!options.skipHistory) {
    const targetPath = nextPage === defaultPage ? "/surgery" : `/${nextPage}`;
    if (window.location.pathname !== targetPath) {
      window.history.pushState({ page: nextPage }, "", targetPath);
    }
  }

  if (nextPage === "surgery") {
    loadSurgeries();
  }
}

function bindRoutes() {
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-route]");
    if (!link || link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey) {
      return;
    }
    event.preventDefault();
    setActivePage(link.dataset.route);
  });
  window.addEventListener("popstate", () => {
    setActivePage(pageFromLocation(), { skipHistory: true });
  });
}

// Google Calendar Status Loader
async function loadCalendarStatus() {
  const indicator = document.querySelector("#calendar-sync-indicator");
  const text = document.querySelector("#calendar-sync-text");
  const btnConnect = document.querySelector("#btn-connect-calendar");
  const btnDisconnect = document.querySelector("#btn-disconnect-calendar");

  if (!indicator) return;

  try {
    const data = await apiJson("/api/surgery/calendar/status");
    if (data.connected) {
      indicator.textContent = "연동완료";
      indicator.className = "status-badge status-준비완료";
      if (text) text.textContent = "수술 일정 등록/수정 시 구글 캘린더에 실시간으로 동기화됩니다.";
      if (btnConnect) btnConnect.style.display = "none";
      if (btnDisconnect) btnDisconnect.style.display = "block";
    } else {
      indicator.textContent = "미연동";
      indicator.className = "status-badge status-취소";
      if (text) text.textContent = "수술 일정을 구글 캘린더와 동기화하려면 구글 계정을 연동해주세요.";
      if (btnConnect) btnConnect.style.display = "block";
      if (btnDisconnect) btnDisconnect.style.display = "none";
    }
  } catch (err) {
    console.error("Failed to load calendar status:", err);
    indicator.textContent = "오류";
    indicator.className = "status-badge status-확인필요";
    if (text) text.textContent = "캘린더 상태 조회 실패: " + err.message;
    if (btnConnect) btnConnect.style.display = "block";
    if (btnDisconnect) btnDisconnect.style.display = "none";
  }
}

// Surgery Dashboard Implementation
async function loadSurgeries() {
  await loadCalendarStatus();
  try {
    const data = await apiJson("/api/surgery/cases");
    state.surgeries = data.cases || [];
  } catch (err) {
    state.surgeries = [];
  }
  
  try {
    const summary = await apiJson("/api/surgery/summary");
    const totalEl = document.querySelector("#stat-count-total");
    if (totalEl) totalEl.textContent = summary.total;
    const readyEl = document.querySelector("#stat-count-ready");
    if (readyEl) readyEl.textContent = summary.ready;
    const warningEl = document.querySelector("#stat-count-warning");
    if (warningEl) warningEl.textContent = summary.warning;
    const ongoingEl = document.querySelector("#stat-count-ongoing");
    if (ongoingEl) ongoingEl.textContent = summary.ongoing;
    const cancelledEl = document.querySelector("#stat-count-cancelled");
    if (cancelledEl) cancelledEl.textContent = summary.cancelled;
  } catch (err) {
    console.error("Failed to load surgery summary", err);
  }

  // Update 11 quick views sidebar badges
  try {
    let countAll = 0;
    let countWeeks2 = 0;
    let countLabTodo = 0;
    let countPremedTodo = 0;
    let countCoopTodo = 0;
    let countPendingStatus = 0;
    let countRoom1personTodo = 0;
    let countRoomNeutralTodo = 0;
    let countAnCallTodo = 0;
    let countCoopExpected = 0;
    let countCancelledHistory = 0;

    state.surgeries.forEach(c => {
      countAll++;
      const isCancelled = c.is_cancelled || c.surgery_status === "취소";
      
      if (isCancelled) {
        countCancelledHistory++;
        return;
      }

      if (c.days_until_surgery !== null && c.days_until_surgery >= 0 && c.days_until_surgery <= 14) {
        countWeeks2++;
      }
      
      if (!c.prep || (!c.prep.lab_completed_date && !c.prep.lab_date) || c.is_lab_valid === false) {
        countLabTodo++;
      }
      
      if (c.prep && c.prep.premed_status === "미완료") {
        countPremedTodo++;
      }
      
      if (c.prep && c.prep.cooperation_status === "진행중") {
        countCoopTodo++;
      }
      
      if (c.surgery_status === "가예약") {
        countPendingStatus++;
      }
      
      if (c.room_1person_status === "필요") {
        countRoom1personTodo++;
      }
      
      if (c.room_gender_neutral_status === "확인 중" || (c.room_gender_neutral_required && c.room_gender_neutral_status === "필요")) {
        countRoomNeutralTodo++;
      }
      
      if (c.an_call_required && c.an_call_patient_intent === "미정") {
        countAnCallTodo++;
      }
      
      if (c.coop_status === "예정") {
        countCoopExpected++;
      }
    });

    const setBadge = (id, count) => {
      const el = document.querySelector(id);
      if (el) el.textContent = count;
    };

    setBadge("#badge-all", countAll);
    setBadge("#badge-weeks-2", countWeeks2);
    setBadge("#badge-lab-todo", countLabTodo);
    setBadge("#badge-premed-todo", countPremedTodo);
    setBadge("#badge-coop-todo", countCoopTodo);
    setBadge("#badge-pending-status", countPendingStatus);
    setBadge("#badge-room-1person-todo", countRoom1personTodo);
    setBadge("#badge-room-neutral-todo", countRoomNeutralTodo);
    setBadge("#badge-an-call-todo", countAnCallTodo);
    setBadge("#badge-coop-expected", countCoopExpected);
    setBadge("#badge-cancelled-history", countCancelledHistory);
  } catch (err) {
    console.error("Failed to calculate sidebar badges", err);
  }
  
  try {
    const alertsData = await apiJson("/api/surgery/alerts");
    const alertBanner = document.querySelector("#surgery-alert-banner");
    const alertList = document.querySelector("#surgery-alert-list");
    
    if (alertBanner && alertList) {
      if (alertsData.alerts && alertsData.alerts.length > 0) {
        alertBanner.style.display = "flex";
        alertList.innerHTML = alertsData.alerts.map(c => {
          const missingStr = c.missing_items && c.missing_items.length > 0
            ? c.missing_items.join(", ")
            : "확인 필요";
          return `
            <div class="surgery-alert-item">
              <strong>[${escapeHtml(c.surgery_date)}] ${escapeHtml(c.patient_code)} (${escapeHtml(c.patient_name || 'N/A')})</strong>: 
              <span style="color:#fa5252; font-weight:600;">${escapeHtml(missingStr)}</span> 
              (집도의: ${escapeHtml(c.surgeon)} / ${escapeHtml(c.surgery_name)})
            </div>
          `;
        }).join("");
      } else {
        alertBanner.style.display = "none";
        alertList.innerHTML = "";
      }
    }
  } catch (err) {
    console.error("Failed to load surgery alerts", err);
  }

  try {
    const surgeonsData = await apiJson("/api/surgery/surgeons/summary");
    const list = document.querySelector("#surgeon-summary-list");
    
    if (list) {
      if (surgeonsData.summary && surgeonsData.summary.length > 0) {
        list.innerHTML = surgeonsData.summary.map(s => `
          <div class="surgeon-row">
            <strong>${escapeHtml(s.surgeon)}</strong>
            <div class="surgeon-metrics">
              <span class="s-metric s-total" title="전체 수술">${s.total}</span>
              <span class="s-metric s-ready" title="준비완료">${s.ready}</span>
              <span class="s-metric s-warning" title="확인필요">${s.warning}</span>
            </div>
          </div>
        `).join("");
      } else {
        list.innerHTML = `<p class="source-empty" style="padding:10px 0; text-align:center;">집도의 현황 없음</p>`;
      }
    }
  } catch (err) {
    console.error("Failed to load surgeons summary", err);
  }
  
  renderSurgeries();
}

function renderSurgeries() {
  const tbody = document.querySelector("#surgery-table-body");
  if (!tbody) return;
  
  const filtered = state.surgeries.filter(c => {
    // Card header filters
    if (state.surgeryFilter === "준비완료" || state.surgeryFilter === "확인필요" || state.surgeryFilter === "진행중" || state.surgeryFilter === "취소") {
      return c.status === state.surgeryFilter;
    }
    
    // Sidebar view filter cases
    const isCancelled = c.is_cancelled || c.surgery_status === "취소";
    
    if (state.surgeryFilter === "cancelled_history") {
      return isCancelled;
    }
    
    // If not looking for cancelled history specifically, filter out cancelled ones
    if (isCancelled) return false;
    
    if (state.surgeryFilter === "all") return true;
    
    if (state.surgeryFilter === "weeks_2") {
      return c.days_until_surgery !== null && c.days_until_surgery >= 0 && c.days_until_surgery <= 14;
    }
    if (state.surgeryFilter === "lab_todo") {
      return !c.prep || (!c.prep.lab_completed_date && !c.prep.lab_date) || c.is_lab_valid === false;
    }
    if (state.surgeryFilter === "premed_todo") {
      return c.prep && c.prep.premed_status === "미완료";
    }
    if (state.surgeryFilter === "coop_todo") {
      return c.prep && c.prep.cooperation_status === "진행중";
    }
    if (state.surgeryFilter === "pending_status") {
      return c.surgery_status === "가예약";
    }
    if (state.surgeryFilter === "room_1person_todo") {
      return c.room_1person_status === "필요";
    }
    if (state.surgeryFilter === "room_neutral_todo") {
      return c.room_gender_neutral_status === "확인 중" || (c.room_gender_neutral_required && c.room_gender_neutral_status === "필요");
    }
    if (state.surgeryFilter === "an_call_todo") {
      return c.an_call_required && c.an_call_patient_intent === "미정";
    }
    if (state.surgeryFilter === "coop_expected") {
      return c.coop_status === "예정";
    }
    
    return true;
  });
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align:center; padding: 40px; color: var(--color-muted);">
          표시할 수술 일정이 없습니다.
        </td>
      </tr>
    `;
    return;
  }
  
  // Sort: 확인필요 -> 진행중 -> 준비완료 -> 취소 -> 수술일 오름차순
  const statusOrder = { "확인필요": 1, "진행중": 2, "준비완료": 3, "취소": 4 };
  filtered.sort((a, b) => {
    const orderA = statusOrder[a.status] || 99;
    const orderB = statusOrder[b.status] || 99;
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    const dateA = a.surgery_date || "9999-12-31";
    const dateB = b.surgery_date || "9999-12-31";
    if (dateA !== dateB) {
      return dateA.localeCompare(dateB);
    }
    const timeA = a.surgery_start_time || "00:00";
    const timeB = b.surgery_start_time || "00:00";
    return timeA.localeCompare(timeB);
  });
  
  tbody.innerHTML = filtered.map(c => {
    const isCancelled = c.is_cancelled || c.surgery_status === "취소";
    const badgeClass = `status-${c.status}`;
    const missingStr = c.missing_items && c.missing_items.length > 0
      ? c.missing_items.join(", ")
      : "";
      
    let actionsHtml = "";
    if (isCancelled) {
      actionsHtml = `
        <button class="text-button" type="button" data-surgery-restore="${c.case_id}">복구</button>
      `;
    } else {
      actionsHtml = `
        <button class="text-button" type="button" data-surgery-cancel="${c.case_id}" style="color:#fa5252;">취소</button>
      `;
    }
    
    actionsHtml += `
      <button class="text-button" type="button" data-surgery-edit="${c.case_id}">수정</button>
      <button class="text-button" type="button" data-surgery-delete="${c.case_id}" style="color:#fa5252;">삭제</button>
    `;
    
    // Notes & Cancel reasons
    const displayNotes = isCancelled 
      ? `<span style="color:#fa5252; font-weight:600;">[취소사유] ${escapeHtml(c.cancellation_reason)}</span>`
      : escapeHtml(c.notes);
      
    // Prep status column
    const displayPrep = c.status === "확인필요" && missingStr
      ? `<div style="line-height:1.2;">
          <span class="status-badge ${badgeClass}">${escapeHtml(c.status)}</span>
          <div style="font-size:10px; color:#e64980; margin-top:4px; white-space:normal; max-width:140px;">${escapeHtml(missingStr)}</div>
         </div>`
      : `<span class="status-badge ${badgeClass}">${escapeHtml(c.status)}</span>`;

    // Patient display (Name + Preferred Name)
    let patientInfo = `<code>${escapeHtml(c.patient_code)}</code>`;
    if (c.patient_name) {
      if (c.patient_preferred_name) {
        patientInfo += `<div style="font-weight:600;">${escapeHtml(c.patient_name)} (${escapeHtml(c.patient_preferred_name)})</div>`;
      } else {
        patientInfo += `<div style="font-weight:600;">${escapeHtml(c.patient_name)}</div>`;
      }
    } else {
      patientInfo += `<div style="color:var(--color-muted); font-size:12px;">이름 미정</div>`;
    }

    // Room info display
    const roomInfo = `
      <div style="font-weight:600;">OR ${escapeHtml(c.operating_room || '-')}</div>
      <small style="color:var(--color-muted);">${escapeHtml(c.admission_type)} (${escapeHtml(c.room_type || '다인실')})</small>
    `;

    // Diagnosis & Surgery Name
    let diagnosisInfo = "";
    if (c.diagnosis) {
      diagnosisInfo = `<div style="font-size:11px; color:var(--color-muted); text-overflow:ellipsis; overflow:hidden; max-width:180px;" title="${escapeHtml(c.diagnosis)}">Dx: ${escapeHtml(c.diagnosis)}</div>`;
    }
    let coopInfo = "";
    if (c.coop_status && c.coop_status !== "불필요") {
      coopInfo = `<div style="font-size:11px; color:#7048e8; margin-top:2px;">Co-op: ${escapeHtml(c.coop_status)} (${escapeHtml(c.coop_dept || '')})</div>`;
    }
    const surgeryInfo = `
      <div style="font-weight:600; max-width: 200px; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(c.surgery_name)}">
        ${escapeHtml(c.surgery_name)}
      </div>
      ${diagnosisInfo}
      ${coopInfo}
    `;

    return `
      <tr style="${isCancelled ? 'opacity: 0.6; background: #f8f9fa;' : ''}">
        <td>
          <div style="font-weight:600;">${escapeHtml(c.surgery_date)}</div>
          <small style="color:var(--color-muted);">${escapeHtml(c.surgery_start_time)} ~ ${escapeHtml(c.surgery_end_time)} (${escapeHtml(c.surgery_duration || 0)}분)</small>
        </td>
        <td>${patientInfo}</td>
        <td>${roomInfo}</td>
        <td>${surgeryInfo}</td>
        <td><strong>${escapeHtml(c.surgeon)}</strong></td>
        <td>${escapeHtml(c.anesthesia)}</td>
        <td>${displayPrep}</td>
        <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:normal; font-size:12px;">
          ${displayNotes}
        </td>
        <td style="text-align: center;">
          <div style="display:flex; justify-content:center; gap:8px;">
            ${actionsHtml}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// Coop Template dynamic auto-generation
function updateCoopTemplatePreview() {
  const preview = document.querySelector("#form-coop-template-preview");
  if (!preview) return;
  
  const disease = document.querySelector("#form-history-disease").value || "[내용]";
  const diagnosis = document.querySelector("#form-diagnosis").value || document.querySelector("#form-surgery-name").value || "[진단명]";
  const date = document.querySelector("#form-surgery-date").value || "[날짜]";
  const surgeryName = document.querySelector("#form-surgery-name").value || "[수술명]";
  const duration = document.querySelector("#form-surgery-duration").value || "[OP time]";
  
  const medName = document.querySelector("#form-history-med-name").value || "";
  const medDose = document.querySelector("#form-history-med-dose").value || "";
  const medFreq = document.querySelector("#form-history-med-frequency").value || "";
  const medStop = document.querySelector("#form-history-med-stop-date").value || "";
  
  let medStr = "[성분명 / 용량 / 횟수 / 중단 일시]";
  if (medName) {
    medStr = `${medName} / ${medDose || '용량미상'} / ${medFreq || '횟수미상'} / ${medStop || '중단안함'}`;
  }
  
  const ekg = document.querySelector("#form-exam-ekg").value || "";
  const chest = document.querySelector("#form-exam-chest").value || "";
  const labNotes = document.querySelector("#form-exam-lab-notes").value || "";
  
  let examStr = "[Abnormal EKG / 고령 / 수술 전 검사 수치 이상 / 투석 / 수술 관련 특이사항]";
  const examItems = [];
  if (ekg) examItems.push(`EKG: ${ekg}`);
  if (chest) examItems.push(`Chest: ${chest}`);
  if (labNotes) examItems.push(`Lab: ${labNotes}`);
  if (examItems.length > 0) {
    examStr = examItems.join(", ");
  }

  const text = `안녕하십니까 교수님.
상환 기저질환 ${disease} 있는 환자분으로, ${diagnosis} 진단 하 ${date}에 ${surgeryName} 수술 예정인 분입니다.
예상 수술 시간은 ${duration}분입니다.
복용 중인 약은 다음과 같습니다.
${medStr}
${examStr}으로 수술 전 마취 위험도 평가 및 management 위해 여쭙고자 의뢰드립니다.
감사합니다.
PS Staff / PA 배상`;

  preview.value = text;
}

function openCaseModal(caseData = null) {
  const modal = document.querySelector("#surgery-case-modal-overlay");
  const title = document.querySelector("#surgery-modal-title");
  const form = document.querySelector("#surgery-case-form");
  if (!modal || !title || !form) return;
  
  form.reset();
  document.querySelector("#form-case-id").value = "";
  
  // Reset active tab to 'basic'
  document.querySelectorAll(".modal-tab-btn").forEach(btn => {
    btn.classList.toggle("is-active", btn.dataset.modalTab === "basic");
  });
  document.querySelectorAll(".modal-tab-panel").forEach(panel => {
    panel.classList.toggle("is-active", panel.id === "panel-basic");
  });
  
  // Reset checkboxes
  document.querySelectorAll("#form-insurance-container input[type='checkbox']").forEach(cb => {
    cb.checked = false;
  });
  
  if (caseData) {
    title.textContent = "수술 일정 수정";
    document.querySelector("#form-case-id").value = caseData.case_id || "";
    document.querySelector("#form-calendar-event-id").value = caseData.calendar_event_id || "";
    document.querySelector("#form-patient-code").value = caseData.patient_code || "";
    document.querySelector("#form-patient-name").value = caseData.patient_name || "";
    document.querySelector("#form-patient-preferred-name").value = caseData.patient_preferred_name || "";
    document.querySelector("#form-surgery-date").value = caseData.surgery_date || "";
    document.querySelector("#form-start-time").value = caseData.surgery_start_time || "";
    document.querySelector("#form-end-time").value = caseData.surgery_end_time || "";
    document.querySelector("#form-surgery-name").value = caseData.surgery_name || "";
    document.querySelector("#form-surgeon").value = caseData.surgeon || "";
    document.querySelector("#form-operating-room").value = caseData.operating_room || "";
    document.querySelector("#form-anesthesia").value = caseData.anesthesia || "G/A";
    document.querySelector("#form-admission-type").value = caseData.admission_type || "입원";
    document.querySelector("#form-calendar-status").value = caseData.calendar_status || "미연동";
    
    document.querySelector("#form-diagnosis").value = caseData.diagnosis || "";
    document.querySelector("#form-coop-detail").value = caseData.coop_detail || "";
    document.querySelector("#form-surgery-fee").value = caseData.surgery_fee || "";
    document.querySelector("#form-surgery-duration").value = caseData.surgery_duration || 0;
    document.querySelector("#form-room-type").value = caseData.room_type || "다인실";
    
    // Set insurance checkboxes
    const insTypes = caseData.insurance_types || [];
    document.querySelectorAll("#form-insurance-container input[type='checkbox']").forEach(cb => {
      cb.checked = insTypes.includes(cb.value);
    });
    
    // Status states
    document.querySelector("#form-surgery-status").value = caseData.surgery_status || "예정";
    document.querySelector("#form-pending-requester").value = caseData.pending_requester || "";
    document.querySelector("#form-is-confirmed").checked = !!caseData.is_confirmed;
    document.querySelector("#form-pending-registered-date").value = caseData.pending_registered_date || "";
    document.querySelector("#form-pending-deadline").value = caseData.pending_deadline || "";
    document.querySelector("#form-pending-memo").value = caseData.pending_memo || "";
    
    // AN Phone Call
    document.querySelector("#form-an-call-required").checked = !!caseData.an_call_required;
    document.querySelector("#form-an-call-followup-needed").checked = !!caseData.an_call_followup_needed;
    document.querySelector("#form-an-call-scheduled-date").value = caseData.an_call_scheduled_date || "";
    document.querySelector("#form-an-call-completed-date").value = caseData.an_call_completed_date || "";
    document.querySelector("#form-an-call-checker").value = caseData.an_call_checker || "";
    document.querySelector("#form-an-call-patient-intent").value = caseData.an_call_patient_intent || "미정";
    document.querySelector("#form-an-call-notes").value = caseData.an_call_notes || "";
    
    // Room Reservation
    document.querySelector("#form-room-1person-required").checked = !!caseData.room_1person_required;
    document.querySelector("#form-room-1person-status").value = caseData.room_1person_status || "미정";
    document.querySelector("#form-room-gender-neutral-required").checked = !!caseData.room_gender_neutral_required;
    document.querySelector("#form-room-gender-neutral-consent").checked = !!caseData.room_gender_neutral_consent;
    document.querySelector("#form-room-gender-neutral-status").value = caseData.room_gender_neutral_status || "불필요";
    document.querySelector("#form-room-gender-neutral-checker").value = caseData.room_gender_neutral_checker || "";
    document.querySelector("#form-room-gender-neutral-checked-date").value = caseData.room_gender_neutral_checked_date || "";
    document.querySelector("#form-room-memo").value = caseData.room_memo || "";
    
    // Co-op
    document.querySelector("#form-coop-status").value = caseData.coop_status || "불필요";
    document.querySelector("#form-coop-confirmed").checked = !!caseData.coop_confirmed;
    document.querySelector("#form-coop-dept").value = caseData.coop_dept || "";
    document.querySelector("#form-coop-doctor").value = caseData.coop_doctor || "";
    document.querySelector("#form-coop-notes").value = caseData.coop_notes || "";
    document.querySelector("#form-coop-memo").value = caseData.coop_memo || "";
    
    // Prep
    const prep = caseData.prep || {};
    document.querySelector("#form-lab-scheduled-date").value = prep.lab_scheduled_date || "";
    document.querySelector("#form-lab-completed-date").value = prep.lab_completed_date || "";
    document.querySelector("#form-lab-status").value = prep.lab_status || "";
    document.querySelector("#form-premed-status").value = prep.premed_status || "미완료";
    document.querySelector("#form-cooperation-status").value = prep.cooperation_status || "불필요";
    document.querySelector("#form-admission-guidance-done").checked = !!prep.admission_guidance_done;
    document.querySelector("#form-documents-checked").checked = !!prep.documents_checked;
    document.querySelector("#form-last-checker").value = prep.last_checker || "";
    document.querySelector("#form-last-checked-date").value = prep.last_checked_date || "";
    document.querySelector("#form-prep-memo").value = prep.prep_memo || "";
    
    // Premed detail
    const premed = prep.premed_detail || {};
    document.querySelector("#form-premed-writer").value = premed.writer || "";
    document.querySelector("#form-premed-lab-checker").value = premed.lab_checker || "";
    document.querySelector("#form-premed-coop-checker").value = premed.coop_checker || "";
    document.querySelector("#form-premed-amount").value = premed.amount || "";
    document.querySelector("#form-premed-consent-admission").checked = !!premed.consent_admission;
    document.querySelector("#form-premed-consent-surgery").checked = !!premed.consent_surgery;
    document.querySelector("#form-premed-consent-discharge").checked = !!premed.consent_discharge;
    document.querySelector("#form-premed-notes").value = premed.premed_notes || "";
    
    // Premed History & Meds
    document.querySelector("#form-history-disease").value = premed.history_disease || "";
    document.querySelector("#form-history-disease-year").value = premed.history_disease_year || "";
    document.querySelector("#form-history-med-name").value = premed.history_med_name || "";
    document.querySelector("#form-history-med-dose").value = premed.history_med_dose || "";
    document.querySelector("#form-history-med-frequency").value = premed.history_med_frequency || "";
    document.querySelector("#form-history-med-stop-date").value = premed.history_med_stop_date || "";
    document.querySelector("#form-history-hormone-med").value = premed.history_hormone_med || "";
    document.querySelector("#form-history-hormone-dose").value = premed.history_hormone_dose || "";
    document.querySelector("#form-history-hormone-period").value = premed.history_hormone_period || "";
    document.querySelector("#form-history-surgery-history").value = premed.history_surgery_history || "";
    document.querySelector("#form-history-surgery-year").value = premed.history_surgery_year || "";
    document.querySelector("#form-history-surgery-hospital").value = premed.history_surgery_hospital || "";
    document.querySelector("#form-history-allergy").value = premed.history_allergy || "";
    
    // Premed Exams
    document.querySelector("#form-exam-ekg").value = premed.exam_ekg || "";
    document.querySelector("#form-exam-chest").value = premed.exam_chest || "";
    document.querySelector("#form-exam-lab-notes").value = premed.exam_lab_notes || "";
    
    document.querySelector("#form-notes").value = caseData.notes || "";
  } else {
    title.textContent = "수술 일정 등록";
    document.querySelector("#form-calendar-status").value = "미연동";
    document.querySelector("#form-anesthesia").value = "G/A";
    document.querySelector("#form-admission-type").value = "입원";
    document.querySelector("#form-room-type").value = "다인실";
    document.querySelector("#form-surgery-status").value = "예정";
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];
    document.querySelector("#form-surgery-date").value = tomorrowStr;
  }
  
  // Pre-generate consult template
  updateCoopTemplatePreview();
  modal.classList.add("is-visible");
}

function closeCaseModal() {
  const modal = document.querySelector("#surgery-case-modal-overlay");
  if (modal) modal.classList.remove("is-visible");
}

function openCancelModal(caseId) {
  const idInput = document.querySelector("#cancel-case-id");
  const reasonInput = document.querySelector("#form-cancel-reason");
  const modal = document.querySelector("#surgery-cancel-modal-overlay");
  if (idInput && reasonInput && modal) {
    idInput.value = caseId;
    reasonInput.value = "";
    modal.classList.add("is-visible");
  }
}

function closeCancelModal() {
  const modal = document.querySelector("#surgery-cancel-modal-overlay");
  if (modal) modal.classList.remove("is-visible");
}

// Bootstrap Event Bindings
async function bootstrap() {
  bindRoutes();
  
  // Reparent modals to body to prevent transform containing block clipping
  const caseOverlay = document.querySelector("#surgery-case-modal-overlay");
  if (caseOverlay) {
    document.body.appendChild(caseOverlay);
  }
  const cancelOverlay = document.querySelector("#surgery-cancel-modal-overlay");
  if (cancelOverlay) {
    document.body.appendChild(cancelOverlay);
  }

  // Check Session
  const session = await loadSession();
  setActivePage(pageFromLocation(), { skipHistory: true });

  if (session?.authorized) {
    await loadSurgeries();
    // Auto refresh every 60s
    setInterval(async () => {
      const activePage = document.documentElement.getAttribute("data-active-page");
      if (activePage === "surgery") {
        await loadSurgeries();
      }
    }, 60000);
  }

  // Login page logic
  const loginTabs = document.querySelectorAll(".login-tab");
  loginTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      loginTabs.forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      const mode = tab.dataset.loginTab;
      document.querySelectorAll(".login-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === `login-panel-${mode}`);
      });
    });
  });

  // Login Form Submission
  document.querySelector("#login-form-account")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.querySelector("#login-button-account");
    const email = document.querySelector("#login-email").value.trim().toLowerCase();
    const password = document.querySelector("#login-password").value;
    setBusy(btn, "로그인 중", true);
    try {
      await postJson("/api/auth/account/login", { account_id: email, password });
      const updatedSession = await loadSession();
      if (updatedSession?.authorized) {
        showToast("로그인 성공");
        setActivePage("surgery");
        await loadSurgeries();
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(btn, "로그인 중", false);
    }
  });

  // Register Form Submission
  document.querySelector("#register-form-account")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.querySelector("#register-button-account");
    const email = document.querySelector("#register-email").value.trim().toLowerCase();
    const password = document.querySelector("#register-password").value;
    const confirmPassword = document.querySelector("#register-confirm-password").value;

    if (password !== confirmPassword) {
      showToast("비밀번호가 일치하지 않습니다.");
      return;
    }

    setBusy(btn, "가입 중", true);
    try {
      await postJson("/api/auth/account/register", { account_id: email, password });
      showToast("회원가입이 완료되었습니다. 로그인해 주세요.");
      
      const loginTab = document.querySelector('[data-login-tab="login"]');
      if (loginTab) loginTab.click();
      
      const loginEmailInput = document.querySelector("#login-email");
      if (loginEmailInput) loginEmailInput.value = email;
      
      document.querySelector("#register-password").value = "";
      document.querySelector("#register-confirm-password").value = "";
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(btn, "가입 중", false);
    }
  });

  // Top nav login/logout buttons
  navLoginButton?.addEventListener("click", () => {
    setActivePage("login");
  });

  navLogoutButton?.addEventListener("click", async () => {
    try {
      await postJson("/api/auth/logout");
      showToast("로그아웃 되었습니다.");
      await loadSession();
      setActivePage("login");
    } catch (err) {
      showToast("로그아웃 실패: " + err.message);
    }
  });

  // Surgery Dashboard Event Listeners
  document.querySelector("#surgery-stat-cards")?.addEventListener("click", (e) => {
    const card = e.target.closest(".surgery-stat-card");
    if (card) {
      document.querySelectorAll(".surgery-stat-card").forEach(c => c.classList.remove("is-active"));
      document.querySelectorAll(".sidebar-item").forEach(i => i.classList.remove("is-active"));
      card.classList.add("is-active");
      
      const matchFilter = card.dataset.statusFilter;
      const sidebarItem = document.querySelector(`[data-sidebar-filter="${matchFilter}"]`);
      if (sidebarItem) {
        sidebarItem.classList.add("is-active");
      }
      
      state.surgeryFilter = card.dataset.statusFilter;
      renderSurgeries();
    }
  });

  document.querySelectorAll(".sidebar-item").forEach(item => {
    item.addEventListener("click", (e) => {
      document.querySelectorAll(".sidebar-item").forEach(i => i.classList.remove("is-active"));
      const currentItem = e.currentTarget;
      currentItem.classList.add("is-active");
      
      document.querySelectorAll(".surgery-stat-card").forEach(c => c.classList.remove("is-active"));
      
      state.surgeryFilter = currentItem.dataset.sidebarFilter;
      renderSurgeries();
    });
  });

  // CSV Import Event Handlers
  document.querySelector("#btn-import-surgery")?.addEventListener("click", () => {
    document.querySelector("#csv-import-input")?.click();
  });

  document.querySelector("#csv-import-input")?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const btn = document.querySelector("#btn-import-surgery");
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "가져오는 중...";

    try {
      const response = await fetch("/api/surgery/import.csv", {
        method: "POST",
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "가져오기에 실패했습니다.");
      }
      showToast(`수술 일정 가져오기 완료: ${data.count || 0}건`);
      await loadSurgeries();
    } catch (err) {
      showToast("가져오기 실패: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
      e.target.value = ""; // Reset file input
    }
  });

  document.querySelector("#btn-create-surgery")?.addEventListener("click", () => {
    openCaseModal();
  });

  document.querySelector("#btn-close-case-modal")?.addEventListener("click", closeCaseModal);
  document.querySelector("#btn-cancel-case-modal")?.addEventListener("click", closeCaseModal);

  document.querySelector("#surgery-case-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const caseId = document.querySelector("#form-case-id").value;

    const insTypes = [];
    document.querySelectorAll("#form-insurance-container input[type='checkbox']:checked").forEach(cb => {
      insTypes.push(cb.value);
    });

    const payload = {
      patient_code: document.querySelector("#form-patient-code").value.trim(),
      patient_name: document.querySelector("#form-patient-name").value.trim(),
      patient_preferred_name: document.querySelector("#form-patient-preferred-name").value.trim(),
      surgery_date: document.querySelector("#form-surgery-date").value,
      surgery_start_time: document.querySelector("#form-start-time").value,
      surgery_end_time: document.querySelector("#form-end-time").value,
      surgery_name: document.querySelector("#form-surgery-name").value.trim(),
      surgeon: document.querySelector("#form-surgeon").value.trim(),
      operating_room: document.querySelector("#form-operating-room").value.trim(),
      anesthesia: document.querySelector("#form-anesthesia").value,
      admission_type: document.querySelector("#form-admission-type").value,
      
      diagnosis: document.querySelector("#form-diagnosis").value.trim(),
      coop_detail: document.querySelector("#form-coop-detail").value.trim(),
      insurance_types: insTypes,
      surgery_fee: document.querySelector("#form-surgery-fee").value.trim(),
      surgery_duration: parseInt(document.querySelector("#form-surgery-duration").value) || 0,
      room_type: document.querySelector("#form-room-type").value,
      calendar_event_id: document.querySelector("#form-calendar-event-id").value,
      
      surgery_status: document.querySelector("#form-surgery-status").value,
      pending_requester: document.querySelector("#form-pending-requester").value,
      is_confirmed: document.querySelector("#form-is-confirmed").checked,
      pending_registered_date: document.querySelector("#form-pending-registered-date").value,
      pending_deadline: document.querySelector("#form-pending-deadline").value,
      pending_memo: document.querySelector("#form-pending-memo").value.trim(),
      
      an_call_required: document.querySelector("#form-an-call-required").checked,
      an_call_followup_needed: document.querySelector("#form-an-call-followup-needed").checked,
      an_call_scheduled_date: document.querySelector("#form-an-call-scheduled-date").value,
      an_call_completed_date: document.querySelector("#form-an-call-completed-date").value,
      an_call_checker: document.querySelector("#form-an-call-checker").value.trim(),
      an_call_patient_intent: document.querySelector("#form-an-call-patient-intent").value,
      an_call_notes: document.querySelector("#form-an-call-notes").value.trim(),
      
      room_1person_required: document.querySelector("#form-room-1person-required").checked,
      room_1person_status: document.querySelector("#form-room-1person-status").value,
      room_gender_neutral_required: document.querySelector("#form-room-gender-neutral-required").checked,
      room_gender_neutral_consent: document.querySelector("#form-room-gender-neutral-consent").checked,
      room_gender_neutral_status: document.querySelector("#form-room-gender-neutral-status").value,
      room_gender_neutral_checker: document.querySelector("#form-room-gender-neutral-checker").value.trim(),
      room_gender_neutral_checked_date: document.querySelector("#form-room-gender-neutral-checked-date").value,
      room_memo: document.querySelector("#form-room-memo").value.trim(),
      
      coop_status: document.querySelector("#form-coop-status").value,
      coop_confirmed: document.querySelector("#form-coop-confirmed").checked,
      coop_dept: document.querySelector("#form-coop-dept").value.trim(),
      coop_doctor: document.querySelector("#form-coop-doctor").value.trim(),
      coop_notes: document.querySelector("#form-coop-notes").value.trim(),
      coop_memo: document.querySelector("#form-coop-memo").value.trim(),
      
      notes: document.querySelector("#form-notes").value.trim(),
      prep: {
        lab_date: document.querySelector("#form-lab-completed-date").value || document.querySelector("#form-lab-scheduled-date").value,
        lab_scheduled_date: document.querySelector("#form-lab-scheduled-date").value,
        lab_completed_date: document.querySelector("#form-lab-completed-date").value,
        lab_status: document.querySelector("#form-lab-status").value.trim(),
        premed_status: document.querySelector("#form-premed-status").value,
        cooperation_status: document.querySelector("#form-cooperation-status").value,
        admission_guidance_done: document.querySelector("#form-admission-guidance-done").checked,
        documents_checked: document.querySelector("#form-documents-checked").checked,
        last_checker: document.querySelector("#form-last-checker").value.trim(),
        last_checked_date: document.querySelector("#form-last-checked-date").value,
        prep_memo: document.querySelector("#form-prep-memo").value.trim(),
        
        premed_detail: {
          writer: document.querySelector("#form-premed-writer").value.trim(),
          lab_checker: document.querySelector("#form-premed-lab-checker").value.trim(),
          coop_checker: document.querySelector("#form-premed-coop-checker").value.trim(),
          amount: document.querySelector("#form-premed-amount").value.trim(),
          consent_admission: document.querySelector("#form-premed-consent-admission").checked,
          consent_surgery: document.querySelector("#form-premed-consent-surgery").checked,
          consent_discharge: document.querySelector("#form-premed-consent-discharge").checked,
          premed_notes: document.querySelector("#form-premed-notes").value.trim(),
          
          history_disease: document.querySelector("#form-history-disease").value.trim(),
          history_disease_year: document.querySelector("#form-history-disease-year").value.trim(),
          history_med_name: document.querySelector("#form-history-med-name").value.trim(),
          history_med_dose: document.querySelector("#form-history-med-dose").value.trim(),
          history_med_frequency: document.querySelector("#form-history-med-frequency").value.trim(),
          history_med_stop_date: document.querySelector("#form-history-med-stop-date").value.trim(),
          history_hormone_med: document.querySelector("#form-history-hormone-med").value.trim(),
          history_hormone_dose: document.querySelector("#form-history-hormone-dose").value.trim(),
          history_hormone_period: document.querySelector("#form-history-hormone-period").value.trim(),
          history_surgery_history: document.querySelector("#form-history-surgery-history").value.trim(),
          history_surgery_year: document.querySelector("#form-history-surgery-year").value.trim(),
          history_surgery_hospital: document.querySelector("#form-history-surgery-hospital").value.trim(),
          history_allergy: document.querySelector("#form-history-allergy").value.trim(),
          
          exam_ekg: document.querySelector("#form-exam-ekg").value.trim(),
          exam_chest: document.querySelector("#form-exam-chest").value.trim(),
          exam_lab_notes: document.querySelector("#form-exam-lab-notes").value.trim(),
        }
      }
    };

    const method = caseId ? "PUT" : "POST";
    const url = caseId ? `/api/surgery/cases/${caseId}` : "/api/surgery/cases";

    try {
      await apiJson(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      showToast(caseId ? "수술 일정이 수정되었습니다." : "새로운 수술 일정이 등록되었습니다.");
      closeCaseModal();
      await loadSurgeries();
    } catch (err) {
      showToast("저장 실패: " + err.message);
    }
  });

  // Table actions: edit, delete, cancel, restore
  document.querySelector("#surgery-table-body")?.addEventListener("click", async (e) => {
    const editBtn = e.target.closest("[data-surgery-edit]");
    if (editBtn) {
      const caseId = editBtn.dataset.surgeryEdit;
      const caseData = state.surgeries.find(c => c.case_id === caseId);
      if (caseData) openCaseModal(caseData);
      return;
    }

    const deleteBtn = e.target.closest("[data-surgery-delete]");
    if (deleteBtn) {
      const caseId = deleteBtn.dataset.surgeryDelete;
      const caseData = state.surgeries.find(c => c.case_id === caseId);
      if (caseData && confirm(`'${caseData.patient_code} (${caseData.patient_name || 'N/A'})' 환자의 수술 일정을 삭제하시겠습니까?`)) {
        try {
          await apiJson(`/api/surgery/cases/${caseId}`, { method: "DELETE" });
          showToast("수술 일정이 삭제되었습니다.");
          await loadSurgeries();
        } catch (err) {
          showToast("삭제 실패: " + err.message);
        }
      }
      return;
    }

    const cancelBtn = e.target.closest("[data-surgery-cancel]");
    if (cancelBtn) {
      const caseId = cancelBtn.dataset.surgeryCancel;
      openCancelModal(caseId);
      return;
    }

    const restoreBtn = e.target.closest("[data-surgery-restore]");
    if (restoreBtn) {
      const caseId = restoreBtn.dataset.surgeryRestore;
      try {
        await postJson(`/api/surgery/cases/${caseId}/restore`);
        showToast("수술 일정이 복구되었습니다.");
        await loadSurgeries();
      } catch (err) {
        showToast("복구 실패: " + err.message);
      }
      return;
    }
  });

  document.querySelector("#btn-close-cancel-modal")?.addEventListener("click", closeCancelModal);
  document.querySelector("#btn-abort-cancel-modal")?.addEventListener("click", closeCancelModal);
  
  document.querySelector("#surgery-cancel-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const caseId = document.querySelector("#cancel-case-id").value;
    const reason = document.querySelector("#form-cancel-reason").value.trim();

    try {
      await postJson(`/api/surgery/cases/${caseId}/cancel`, { cancellation_reason: reason });
      showToast("수술 일정이 취소 처리되었습니다.");
      closeCancelModal();
      await loadSurgeries();
    } catch (err) {
      showToast("취소 실패: " + err.message);
    }
  });

  document.querySelector("#btn-export-surgery")?.addEventListener("click", async () => {
    try {
      const nowStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      await downloadFromApi("/api/surgery/export.csv", `surgery_schedules_${nowStr}.csv`);
      showToast("엑셀 파일 다운로드 시작");
    } catch (err) {
      showToast("엑셀 다운로드 실패: " + err.message);
    }
  });

  // Modal tab switching listeners
  document.querySelectorAll(".modal-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-tab-btn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      
      const tabId = btn.dataset.modalTab;
      document.querySelectorAll(".modal-tab-panel").forEach(p => {
        p.classList.toggle("is-active", p.id === `panel-${tabId}`);
      });
    });
  });

  // Real-time update of coop template preview when inputs change
  [
    "#form-history-disease", "#form-diagnosis", "#form-surgery-date",
    "#form-surgery-name", "#form-surgery-duration", "#form-history-med-name",
    "#form-history-med-dose", "#form-history-med-frequency", "#form-history-med-stop-date",
    "#form-exam-ekg", "#form-exam-chest", "#form-exam-lab-notes"
  ].forEach(selector => {
    document.querySelector(selector)?.addEventListener("input", updateCoopTemplatePreview);
  });

  // Clipboard copy for coop template
  document.querySelector("#btn-copy-coop-template")?.addEventListener("click", () => {
    const preview = document.querySelector("#form-coop-template-preview");
    if (preview && preview.value) {
      navigator.clipboard.writeText(preview.value)
        .then(() => showToast("협진 의뢰문이 클립보드에 복사되었습니다."))
        .catch(err => showToast("복사 실패: " + err.message));
    }
  });

  // Google Calendar Connection / Disconnection
  document.querySelector("#btn-connect-calendar")?.addEventListener("click", async () => {
    try {
      const data = await apiJson("/api/auth/gdrive/url");
      if (data.url) {
        const width = 600;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        const popup = window.open(
          data.url,
          "google-calendar-auth",
          `width=${width},height=${height},left=${left},top=${top},status=no,resizable=yes,scrollbars=yes`
        );
        
        const timer = setInterval(async () => {
          if (!popup || popup.closed) {
            clearInterval(timer);
            showToast("캘린더 연동 완료 여부를 확인합니다.");
            await loadCalendarStatus();
            await loadSurgeries();
          }
        }, 1000);
      }
    } catch (err) {
      showToast("인증 URL 로드 실패: " + err.message);
    }
  });

  document.querySelector("#btn-disconnect-calendar")?.addEventListener("click", async () => {
    if (confirm("Google Calendar 연동을 해제하시겠습니까? 더 이상 수술 일정이 동기화되지 않습니다.")) {
      try {
        await postJson("/api/surgery/calendar/disconnect");
        showToast("구글 캘린더 연동이 해제되었습니다.");
        await loadCalendarStatus();
        await loadSurgeries();
      } catch (err) {
        showToast("연동 해제 실패: " + err.message);
      }
    }
  });
}

bootstrap();
