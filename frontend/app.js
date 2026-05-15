const files = [
  { name: "SOAP 발표 정리.pdf", type: "PDF", size: "3.4 MB", updated: "오늘 22:14" },
  { name: "임상 QnA 메모.docx", type: "DOC", size: "980 KB", updated: "어제 19:02" },
  { name: "검사결과 요약.xlsx", type: "XLS", size: "620 KB", updated: "05/14 08:31" },
];

const memos = [
  {
    title: "교수님께 질문할 내용",
    body: "치료 우선순위, 추적 검사 기준, 설명할 때 놓치기 쉬운 위험 신호를 확인하기.",
  },
  {
    title: "발표 구조",
    body: "주호소, 검사 결과, 판단 근거, 계획 순서로 1분 안에 말할 수 있게 정리.",
  },
];

const presets = [
  "SOAP 1분 발표",
  "예상 QnA",
  "교수님 질문",
  "환자 설명문",
];

const state = {
  files: [...files],
  memos: [...memos],
  session: null,
  usesDemoData: true,
  fileQuery: "",
  memoQuery: "",
  editingMemoFileName: "",
  lastAiResult: "",
};

const fileList = document.querySelector("#file-list");
const memoList = document.querySelector("#memo-list");
const fileCount = document.querySelector("#file-count");
const memoCount = document.querySelector("#memo-count");
const aiMonthCost = document.querySelector("#ai-month-cost");
const aiModelLabel = document.querySelector("#ai-model-label");
const storageStatusLabel = document.querySelector("#storage-status-label");
const toast = document.querySelector("#toast");
const sessionChip = document.querySelector("#session-chip");
const navStatusIndicator = document.querySelector("#nav-status-indicator");
const navStatusText = document.querySelector("#nav-status-text");
const navTime = document.querySelector("#nav-time");
const navIp = document.querySelector("#nav-ip");
const navPasskeyRegister = document.querySelector("#nav-passkey-register");
const navLoginButton = document.querySelector("#nav-login-button");
const navLogoutButton = document.querySelector("#nav-logout-button");
const fileListStatus = document.querySelector("#file-list-status");
const memoListStatus = document.querySelector("#memo-list-status");
const memoSaveButton = document.querySelector("#memo-save-button");
const saveAiMemoButton = document.querySelector("#save-ai-memo");
const downloadAiMdButton = document.querySelector("#download-ai-md");
const downloadAiPdfButton = document.querySelector("#download-ai-pdf");
const downloadCurrentMemoButton = document.querySelector("#download-current-memo");
const toolOutput = document.querySelector("#tool-output");
const heroFileSummary = document.querySelector("#hero-file-summary");
const heroFileList = document.querySelector("#hero-file-list");
const heroMemoPreview = document.querySelector("#hero-memo-preview");
const aiFileSources = document.querySelector("#ai-file-sources");
const aiMemoSources = document.querySelector("#ai-memo-sources");
const aiFileStatus = document.querySelector("#ai-file-status");
const aiMemoStatus = document.querySelector("#ai-memo-status");

const pageIds = ["login", "home", "files", "memos", "ai", "tools", "settings"];
const defaultPage = "home";

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

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatBytes(size = 0) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(size) || 0;
  for (const unit of units) {
    if (value < 1024 || unit === units[units.length - 1]) {
      return unit === "B" ? `${value} ${unit}` : `${value.toFixed(1)} ${unit}`;
    }
    value /= 1024;
  }
  return `${size} B`;
}

function formatUpdated(value) {
  if (!value) return "시간 정보 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function fileTypeLabel(name = "") {
  return (name.split(".").pop() || "FILE").slice(0, 3).toUpperCase();
}

function includesQuery(...values) {
  const query = values.pop().trim().toLowerCase();
  if (!query) return true;
  return values.some((value) => String(value || "").toLowerCase().includes(query));
}

function pageFromLocation() {
  const path = window.location.pathname.replace(/^\/+/, "").split("/")[0];
  if (pageIds.includes(path)) return path;
  const hashPage = window.location.hash.replace("#", "");
  return pageIds.includes(hashPage) ? hashPage : defaultPage;
}

function setActivePage(page = pageFromLocation(), options = {}) {
  let nextPage = pageIds.includes(page) ? page : defaultPage;

  // Force login if not authorized
  if (state.session && !state.session.authorized && nextPage !== "login") {
    nextPage = "login";
  } else if (state.session?.authorized && nextPage === "login") {
    nextPage = defaultPage;
  }

  // Toggle global navigation and footer visibility
  const isLoginPage = nextPage === "login";
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
    const targetPath = nextPage === defaultPage ? "/home" : `/${nextPage}`;
    if (window.location.pathname !== targetPath) {
      window.history.pushState({ page: nextPage }, "", targetPath);
    }
  }
  if (nextPage === "settings") {
    loadSettings();
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

function getFilteredFiles() {
  return state.files.filter((file) =>
    includesQuery(file.name, file.type, file.updated, state.fileQuery),
  );
}

function getFilteredMemos() {
  return state.memos.filter((memo) =>
    includesQuery(memo.title, memo.body, memo.updated, state.memoQuery),
  );
}

function resetMemoForm() {
  document.querySelector("#memo-title").value = "";
  document.querySelector("#memo-body").value = "";
  document.querySelector("#memo-file-name").value = "";
  state.editingMemoFileName = "";
  memoSaveButton.textContent = "메모 저장";
  downloadCurrentMemoButton.disabled = true;
}

function updateHeroPreview() {
  const fileCount = document.querySelector("#file-count");
  const memoCount = document.querySelector("#memo-count");
  if (fileCount) fileCount.textContent = state.files.length;
  if (memoCount) memoCount.textContent = state.memos.length;

  if (heroFileList) {
    heroFileList.innerHTML = state.files
      .slice(0, 2)
      .map(
        (file) => `
          <div class="file-row">
            <span class="file-icon">${escapeHtml(file.type || fileTypeLabel(file.name))}</span>
            <div>
              <strong>${escapeHtml(file.name)}</strong>
              <small>${escapeHtml(file.updated)} · ${escapeHtml(file.size)}</small>
            </div>
          </div>
        `,
      )
      .join("") || `<p class="source-empty">표시할 파일이 없습니다.</p>`;
  }
  
  if (heroMemoPreview) {
    const firstMemo = state.memos[0];
    heroMemoPreview.textContent = firstMemo
      ? `${firstMemo.title}: ${firstMemo.body}`
      : "최근 메모가 없습니다.";
  }
}

function selectedValues(selector) {
  return Array.from(document.querySelectorAll(`${selector}:checked`)).map(
    (input) => input.value,
  );
}

function setBusy(button, busyText, isBusy) {
  if (!button) return;
  if (isBusy) {
    button.dataset.idleText = button.textContent;
    button.innerHTML = `<span class="spinner"></span>${busyText}`;
    button.disabled = true;
    return;
  }
  button.textContent = button.dataset.idleText || button.textContent;
  button.disabled = false;
}

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "요청에 실패했습니다.");
  }
  return data;
}

async function downloadFromApi(url, filename) {
  const response = await fetch(url);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "다운로드에 실패했습니다.");
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

async function downloadPostBlob(url, payload, filename) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "다운로드에 실패했습니다.");
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function downloadTextFile(filename, content, type = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function inlineMarkdown(value = "") {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function markdownToHtml(markdown = "") {
  const lines = markdown.replace(/\r/g, "").split("\n");
  const html = [];
  let listOpen = false;
  const closeList = () => {
    if (listOpen) {
      html.push("</ul>");
      listOpen = false;
    }
  };
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      return;
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      html.push(`<h${heading[1].length}>${inlineMarkdown(heading[2])}</h${heading[1].length}>`);
      return;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${inlineMarkdown(bullet[1])}</li>`);
      return;
    }
    closeList();
    html.push(`<p>${inlineMarkdown(trimmed)}</p>`);
  });
  closeList();
  return html.join("");
}

function setSessionChip(session) {
  state.session = session;
  const authorized = !!session?.authorized;

  // Update top bar status
  if (navStatusIndicator) {
    navStatusIndicator.className = "status-indicator " + (authorized ? "is-authorized" : "is-locked");
  }
  if (navStatusText) {
    if (authorized) {
      const methodLabel = session.auth_method === "passkey" ? "Passkey" : session.auth_method === "account" ? "Account" : "Google";
      navStatusText.textContent = `${methodLabel} 인증됨`;
    } else {
      navStatusText.textContent = "인증 필요";
    }
  }
  if (navIp && session?.client_ip) {
    navIp.textContent = session.client_ip;
  }

  // Handle buttons visibility
  if (navPasskeyRegister) navPasskeyRegister.hidden = !authorized;
  if (navLoginButton) navLoginButton.hidden = authorized;
  if (navLogoutButton) navLogoutButton.hidden = !authorized;

  // Legacy chip update (if exists)
  if (sessionChip) {
    sessionChip.classList.remove("is-authorized", "is-locked");
    if (authorized) {
      sessionChip.textContent = navStatusText.textContent;
      sessionChip.classList.add("is-authorized");
    } else {
      sessionChip.textContent = "인증 필요";
      sessionChip.classList.add("is-locked");
    }
  }

  if (authorized) {
    document.body.classList.add("is-authorized");
  } else {
    document.body.classList.remove("is-authorized");
  }
}

async function logout() {
  if (!confirm("로그아웃 하시겠습니까?")) return;
  try {
    await postJson("/api/auth/logout");
    window.location.reload();
  } catch (error) {
    showToast("로그아웃 실패: " + error.message);
  }
}

async function loadSession() {
  try {
    const session = await apiJson("/api/session");
    setSessionChip(session);
    return session;
  } catch (error) {
    console.error("Session load failed:", error);
    if (navStatusText) navStatusText.textContent = "오프라인";
    if (navStatusIndicator) navStatusIndicator.className = "status-indicator is-locked";
    return null;
  }
}

async function loadFiles() {
  try {
    const data = await apiJson("/api/files");
    state.files = data.files.map((file) => ({
      name: file.name,
      blobName: file.blob_name,
      type: fileTypeLabel(file.name),
      size: formatBytes(file.size),
      updated: formatUpdated(file.updated),
      downloadUrl: file.download_url,
    }));
    state.usesDemoData = false;
  } catch (error) {
    state.files = [...files];
    state.usesDemoData = true;
  }
  renderFiles();
  updateHeroPreview();
  renderAiSources();
}

async function loadMemos() {
  try {
    const data = await apiJson("/api/memos");
    state.memos = data.memos.map((memo) => ({
      title: memo.title,
      body: memo.content || "클릭해서 메모 내용을 불러오세요.",
      fileName: memo.file_name,
      updated: formatUpdated(memo.updated_at || memo.created_at),
    }));
    state.usesDemoData = false;
  } catch {
    state.memos = [...memos];
  }
  renderMemos();
  updateHeroPreview();
  renderAiSources();
}

async function loadUsageSummary() {
  try {
    const usage = await apiJson("/api/usage/summary");
    if (aiMonthCost) aiMonthCost.textContent = usage.month_cost_label || "-";
    if (aiModelLabel) aiModelLabel.textContent = usage.model || "Gemini";
    if (storageStatusLabel) storageStatusLabel.textContent = `${usage.request_count || 0} AI 요청`;
  } catch {
    if (aiMonthCost) aiMonthCost.textContent = "-";
    if (aiModelLabel) aiModelLabel.textContent = "인증 후 표시";
    if (storageStatusLabel) storageStatusLabel.textContent = "Cloud Run";
  }
}

function fromBase64Url(value) {
  const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0)).buffer;
}

function toBase64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function prepareCreationOptions(options) {
  const publicKey = options.publicKey;
  publicKey.challenge = fromBase64Url(publicKey.challenge);
  publicKey.user.id = fromBase64Url(publicKey.user.id);
  publicKey.excludeCredentials = (publicKey.excludeCredentials || []).map((item) => ({
    ...item,
    id: fromBase64Url(item.id),
  }));
  return publicKey;
}

function prepareRequestOptions(options) {
  const publicKey = options.publicKey;
  publicKey.challenge = fromBase64Url(publicKey.challenge);
  publicKey.allowCredentials = (publicKey.allowCredentials || []).map((item) => ({
    ...item,
    id: fromBase64Url(item.id),
  }));
  return publicKey;
}

function serializeCredential(credential) {
  const response = credential.response;
  const payload = {
    id: credential.id,
    rawId: toBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: toBase64Url(response.clientDataJSON),
    },
  };
  if (response.attestationObject) {
    payload.response.attestationObject = toBase64Url(response.attestationObject);
  }
  if (response.authenticatorData) {
    payload.response.authenticatorData = toBase64Url(response.authenticatorData);
  }
  if (response.signature) {
    payload.response.signature = toBase64Url(response.signature);
  }
  if (response.userHandle) {
    payload.response.userHandle = toBase64Url(response.userHandle);
  }
  return payload;
}

async function postJson(url, payload = {}) {
  return apiJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2200);
}

async function registerPasskey() {
  if (!window.PublicKeyCredential) {
    showToast("브라우저가 패스키를 지원하지 않습니다.");
    return;
  }
  try {
    const session = state.session || await loadSession();
    if (!session?.authorized) {
      showToast("먼저 로그인이 필요합니다.");
      return;
    }
    const options = await postJson("/api/auth/passkey/register/options");
    const credential = await navigator.credentials.create({
      publicKey: prepareCreationOptions(options),
    });
    await postJson("/api/auth/passkey/register/verify", serializeCredential(credential));
    await loadSession();
    showToast("패스키가 등록됐습니다.");
  } catch (error) {
    showToast(error.message);
  }
}

async function loginWithPasskey() {
  if (!window.PublicKeyCredential) {
    showToast("브라우저가 패스키를 지원하지 않습니다.");
    return;
  }
  try {
    const options = await postJson("/api/auth/passkey/login/options");
    const credential = await navigator.credentials.get({
      publicKey: prepareRequestOptions(options),
    });
    await postJson("/api/auth/passkey/login/verify", serializeCredential(credential));
    await loadSession();
    if (state.session?.authorized) {
      await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);
      showToast("패스키 로그인 완료");
      setActivePage("home");
    }
  } catch (error) {
    if (error.message.includes("등록된 passkey가 없습니다")) {
      showToast("등록된 패스키가 없습니다. 계정 ID로 먼저 로그인 후 등록하세요.");
    } else {
      showToast(error.message);
    }
  }
}

async function loadSettings() {
  renderSettingsAuth(state.session);
  if (!state.session?.authorized) {
    renderAccessLogSettings({ logs: [] });
    renderGeminiUsageSettings({ daily: [] });
    return;
  }
  try {
    const [accessLogs, geminiUsage] = await Promise.all([
      apiJson("/api/settings/access-logs"),
      apiJson("/api/settings/gemini-usage"),
    ]);
    renderAccessLogSettings(accessLogs);
    renderGeminiUsageSettings(geminiUsage);
  } catch (error) {
    showToast(error.message);
  }
}

function renderSettingsAuth(session = state.session) {
  const authMetrics = document.querySelector("#settings-auth-metrics");
  const accountStatus = document.querySelector("#account-id-status");
  if (!authMetrics) return;
  accountStatus.textContent = session?.authorized ? "인증 완료" : "ID와 비밀번호 필요";
  authMetrics.innerHTML = `
    <article><span>상태</span><strong>${session?.authorized ? "인증됨" : "잠김"}</strong></article>
    <article><span>방식</span><strong>${escapeHtml(session?.auth_method || "-")}</strong></article>
    <article><span>Access</span><strong>${session?.cloudflare_access_required ? "필수" : "선택"}</strong></article>
    <article><span>계정 ID</span><strong>${session?.account_id_fallback_allowed ? "ON" : "OFF"}</strong></article>
  `;
  const accountInput = document.querySelector("#account-id-input");
  if (accountInput && !accountInput.value) {
    accountInput.value = session?.account_login_id || "jsbang01357@gmail.com";
  }
  renderSettingsStorage();
}

function renderSettingsStorage() {
  const metrics = document.querySelector("#settings-storage-metrics");
  if (!metrics) return;
  metrics.innerHTML = `
    <article><span>파일</span><strong>${state.files.length}</strong></article>
    <article><span>메모</span><strong>${state.memos.length}</strong></article>
    <article><span>저장소</span><strong>GCS</strong></article>
    <article><span>런타임</span><strong>Cloud Run</strong></article>
  `;
}

function renderAccessLogSettings(data) {
  const metrics = document.querySelector("#access-log-metrics");
  const list = document.querySelector("#access-log-list");
  const status = document.querySelector("#access-log-status");
  if (!metrics || !list || !status) return;
  status.textContent = data.total ? `최근 ${data.total}건` : "접속 기록 없음";
  metrics.innerHTML = `
    <article><span>기록</span><strong>${data.total || 0}</strong></article>
    <article><span>고유 IP</span><strong>${data.unique_ips || 0}</strong></article>
    <article><span>최근 IP</span><strong>${escapeHtml(data.latest?.ip || "-")}</strong></article>
    <article><span>최근 시간</span><strong>${escapeHtml(data.latest?.time || "-")}</strong></article>
  `;
  list.innerHTML = (data.logs || [])
    .map(
      (entry) => `
        <article class="settings-row">
          <strong>${escapeHtml(entry.time || "시간 없음")}</strong>
          <span>${escapeHtml(entry.ip || "Unknown IP")}</span>
          <small>${escapeHtml(entry.ua || "Unknown Browser")}</small>
        </article>
      `,
    )
    .join("") || `<p class="empty-state">접속 기록이 없습니다.</p>`;
}

function renderGeminiUsageSettings(data) {
  const metrics = document.querySelector("#gemini-usage-metrics");
  const list = document.querySelector("#gemini-usage-list");
  const status = document.querySelector("#gemini-usage-status");
  if (!metrics || !list || !status) return;
  status.textContent = `${data.model || "Gemini"} · ${data.request_count || 0} 요청`;
  metrics.innerHTML = `
    <article><span>이번 달</span><strong>${escapeHtml(data.month_cost_label || "-")}</strong></article>
    <article><span>전체 토큰</span><strong>${Number(data.total_tokens || 0).toLocaleString()}</strong></article>
    <article><span>입력</span><strong>${Number(data.input_tokens || 0).toLocaleString()}</strong></article>
    <article><span>출력</span><strong>${Number(data.output_tokens || 0).toLocaleString()}</strong></article>
  `;
  list.innerHTML = (data.daily || [])
    .map(
      (row) => `
        <article class="settings-row">
          <strong>${escapeHtml(row.date)}</strong>
          <span>${Number(row.tokens || 0).toLocaleString()} tokens · ${row.requests || 0} requests</span>
          <small>${escapeHtml(row.cost_label || "-")}</small>
        </article>
      `,
    )
    .join("") || `<p class="empty-state">Gemini 사용량 로그가 없습니다.</p>`;
}

function renderFiles() {
  const visibleFiles = getFilteredFiles();
  fileList.innerHTML = visibleFiles
    .map(
      (file, index) => `
        <div class="data-row">
          <span class="file-icon">${escapeHtml(file.type)}</span>
          <div>
            <strong>${escapeHtml(file.name)}</strong>
            <small>${escapeHtml(file.updated)} · ${escapeHtml(file.size)}</small>
          </div>
          <div class="row-actions">
            <button class="icon-button" type="button" data-download="${index}" aria-label="${file.name} 다운로드">
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 20h14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <button class="icon-button" type="button" data-delete="${index}" aria-label="${file.name} 삭제">
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path d="M6 7h12M10 7V5h4v2m-6 3 1 9h6l1-9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      `,
    )
    .join("") || `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
          <polyline points="13 2 13 9 20 9"></polyline>
        </svg>
        <p>아직 업로드된 파일이 없습니다.</p>
      </div>
    `;
  fileCount.textContent = String(state.files.length);
  fileListStatus.textContent = state.fileQuery
    ? `${visibleFiles.length}개 표시 · 전체 ${state.files.length}개`
    : `전체 ${state.files.length}개`;
  updateHeroPreview();
}

function renderMemos() {
  const visibleMemos = getFilteredMemos();
  memoList.innerHTML = visibleMemos
    .map(
      (memo, index) => `
        <article class="memo-card ${memo.fileName && memo.fileName === state.editingMemoFileName ? "is-selected" : ""}">
          <h3>${escapeHtml(memo.title)}</h3>
          <p>${escapeHtml(memo.body)}</p>
          <div class="memo-actions">
            ${memo.updated ? `<small>${escapeHtml(memo.updated)}</small>` : "<small>미리보기</small>"}
            ${
              memo.fileName
                ? `<button class="text-button" type="button" data-memo-open="${index}">열기</button>
                   <button class="text-button" type="button" data-memo-delete="${index}">삭제</button>`
                : ""
            }
          </div>
        </article>
      `,
    )
    .join("") || `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
        <p>아직 저장된 메모가 없습니다.</p>
      </div>
    `;
  memoCount.textContent = String(state.memos.length);
  memoListStatus.textContent = state.memoQuery
    ? `${visibleMemos.length}개 표시 · 전체 ${state.memos.length}개`
    : `전체 ${state.memos.length}개`;
  updateHeroPreview();
}

function renderPresets() {
  const row = document.querySelector("#preset-row");
  if (!row) return;
  row.innerHTML = presets
    .map((preset) => `<button type="button" data-preset="${preset}">${preset}</button>`)
    .join("");
}

function renderAiSources() {
  const realFiles = state.files.filter((file) => file.blobName);
  const realMemos = state.memos.filter((memo) => memo.fileName);
  if (aiFileSources) {
    aiFileSources.innerHTML = realFiles.length
      ? realFiles
          .slice(0, 8)
          .map(
            (file, index) => `
              <label class="source-option">
                <input type="checkbox" value="${escapeHtml(file.blobName)}" data-ai-file />
                <span>${escapeHtml(file.name)}</span>
                <small>${escapeHtml(file.size)}</small>
              </label>
            `,
          )
          .join("")
      : `<p class="source-empty">인증 후 파일을 선택할 수 있습니다.</p>`;
  }
  if (aiMemoSources) {
    aiMemoSources.innerHTML = realMemos.length
      ? realMemos
          .slice(0, 8)
          .map(
            (memo) => `
              <label class="source-option">
                <input type="checkbox" value="${escapeHtml(memo.fileName)}" data-ai-memo />
                <span>${escapeHtml(memo.title)}</span>
                <small>${escapeHtml(memo.updated || "메모")}</small>
              </label>
            `,
          )
          .join("")
      : `<p class="source-empty">인증 후 메모를 선택할 수 있습니다.</p>`;
  }
  updateAiSourceStatus();
}

function updateAiSourceStatus() {
  const fCount = selectedValues("[data-ai-file]").length;
  const mCount = selectedValues("[data-ai-memo]").length;
  if (aiFileStatus) aiFileStatus.textContent = fCount ? `${fCount}개 선택` : "선택 없음";
  if (aiMemoStatus) aiMemoStatus.textContent = mCount ? `${mCount}개 선택` : "선택 없음";
}

function renderTool(tool) {
  const templates = {
    cleaner: `
      <div class="tool-panel">
        <h3>텍스트 클리너</h3>
        <textarea id="tool-cleaner-input" rows="7" placeholder="정리할 텍스트를 붙여넣으세요."></textarea>
        <div class="tool-options">
          <label><input type="radio" name="cleaner-mode" value="basic" checked> 기본 정리</label>
          <label><input type="radio" name="cleaner-mode" value="plain"> Markdown → Plain</label>
          <label><input type="radio" name="cleaner-mode" value="word"> Markdown → Word</label>
        </div>
        <div id="cleaner-basic-options" class="tool-sub-options">
          <label><input type="checkbox" id="cleaner-ai-mode" checked> AI 모드 (불릿/구분선)</label>
          <label><input type="checkbox" id="cleaner-ai-dash"> 번호를 '- '로 변환</label>
        </div>
        <div class="form-actions">
          <button class="button button-primary" id="tool-cleaner-run" type="button">정리하기</button>
          <button class="button button-secondary" id="tool-copy-output" type="button">결과 복사</button>
        </div>
        <div id="tool-cleaner-metrics" class="tool-metrics" style="display:none; margin-top:1rem;">
           <article><span>원본</span><strong id="cleaner-orig-len">0</strong></article>
           <article><span>정리 후</span><strong id="cleaner-new-len">0</strong></article>
           <article><span>변화</span><strong id="cleaner-diff-len">0</strong></article>
        </div>
        <pre id="tool-result">결과가 여기에 표시됩니다.</pre>
      </div>
    `,
    "md-pdf": `
      <div class="tool-panel">
        <h3>MD to PDF</h3>
        <textarea id="tool-md-input" rows="8" placeholder="# 제목&#10;&#10;마크다운 내용을 입력하세요."></textarea>
        <button class="button button-primary" id="tool-md-run" type="button">PDF 다운로드</button>
      </div>
    `,
    counter: `
      <div class="tool-panel">
        <h3>글자수 카운터</h3>
        <textarea id="tool-counter-input" rows="7" placeholder="계산할 텍스트를 입력하세요."></textarea>
        <div class="tool-metrics" id="tool-counter-result">
          <article><span>공백 포함</span><strong>0</strong></article>
          <article><span>공백 제외</span><strong>0</strong></article>
          <article><span>단어</span><strong>0</strong></article>
          <article><span>예상 A4</span><strong>0</strong></article>
        </div>
      </div>
    `,
    settlement: `
      <div class="tool-panel">
        <h3>정산 계산기</h3>
        <div class="tool-input-group">
          <label>사람 목록 (쉼표 또는 줄바꿈)</label>
          <input type="text" id="tool-settlement-people" placeholder="지송, 민수, 서연">
        </div>
        <div class="tool-input-group">
          <label>지출 내역 (항목, 돈낸사람, 비용, n빵할사람 순서 무관 - 텍스트 기반 입력)</label>
          <textarea id="tool-settlement-input" rows="5" placeholder="저녁 지송 50000&#10;택시 민수 12000"></textarea>
        </div>
        <button class="button button-primary" id="tool-settlement-run" type="button">정산 계산하기</button>
        <div id="tool-settlement-result-container" style="display:none; margin-top:1rem;">
          <h4>사람별 잔액</h4>
          <pre id="tool-settlement-summary"></pre>
          <h4>최소 송금 목록</h4>
          <pre id="tool-settlement-transfers"></pre>
        </div>
      </div>
    `,
  };
  if (toolOutput) {
    toolOutput.innerHTML = templates[tool] || templates.cleaner;
    bindToolPanel(tool);
    toolOutput.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function bindToolPanel(tool) {
  if (tool === "cleaner") {
    const runBtn = document.querySelector("#tool-cleaner-run");
    const modeInputs = document.querySelectorAll('input[name="cleaner-mode"]');
    const basicOptions = document.querySelector("#cleaner-basic-options");

    modeInputs.forEach((input) => {
      input.addEventListener("change", (e) => {
        basicOptions.style.display = e.target.value === "basic" ? "block" : "none";
      });
    });

    runBtn.addEventListener("click", async () => {
      const text = document.querySelector("#tool-cleaner-input").value;
      if (!text.trim()) {
        showToast("텍스트를 입력하세요.");
        return;
      }
      const mode = document.querySelector('input[name="cleaner-mode"]:checked').value;
      const options = {
        ai_mode: document.querySelector("#cleaner-ai-mode").checked,
        ai_numbered_to_dash: document.querySelector("#cleaner-ai-dash").checked,
      };

      setBusy(runBtn, "정리 중", true);
      try {
        const data = await postJson("/api/tools/text-cleaner", { text, mode, options });
        document.querySelector("#tool-result").textContent = data.cleaned;
        document.querySelector("#tool-cleaner-metrics").style.display = "flex";
        document.querySelector("#cleaner-orig-len").textContent = data.original_len;
        document.querySelector("#cleaner-new-len").textContent = data.cleaned_len;
        const diff = data.cleaned_len - data.original_len;
        document.querySelector("#cleaner-diff-len").textContent = (diff >= 0 ? "+" : "") + diff;
      } catch (error) {
        showToast(error.message);
      } finally {
        setBusy(runBtn, "정리 중", false);
      }
    });

    document.querySelector("#tool-copy-output").addEventListener("click", async () => {
      const result = document.querySelector("#tool-result").textContent;
      if (!result || result === "결과가 여기에 표시됩니다.") return;
      try {
        await navigator.clipboard.writeText(result);
        showToast("결과를 복사했습니다.");
      } catch {
        showToast("복사에 실패했습니다.");
      }
    });
  }
  if (tool === "md-pdf") {
    document.querySelector("#tool-md-run").addEventListener("click", async () => {
      try {
        await downloadPostBlob(
          "/api/tools/markdown-pdf",
          { markdown: document.querySelector("#tool-md-input").value },
          "jisong-markdown.pdf",
        );
        showToast("PDF 다운로드를 시작합니다.");
      } catch (error) {
        showToast(error.message);
      }
    });
  }
  if (tool === "counter") {
    const input = document.querySelector("#tool-counter-input");
    const render = () => {
      const text = input.value;
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      const a4 = (text.length / 1500).toFixed(2);
      document.querySelector("#tool-counter-result").innerHTML = `
        <article><span>공백 포함</span><strong>${text.length}</strong></article>
        <article><span>공백 제외</span><strong>${text.replace(/\s/g, "").length}</strong></article>
        <article><span>단어</span><strong>${words}</strong></article>
        <article><span>예상 A4</span><strong>${a4}쪽</strong></article>
      `;
    };
    input.addEventListener("input", render);
  }
  if (tool === "settlement") {
    const runBtn = document.querySelector("#tool-settlement-run");
    runBtn.addEventListener("click", async () => {
      const peopleText = document.querySelector("#tool-settlement-people").value;
      const expenseText = document.querySelector("#tool-settlement-input").value;
      if (!peopleText.trim()) {
        showToast("사람 목록을 입력하세요.");
        return;
      }
      
      const people = peopleText.split(/[,\n]/).map(p => p.trim()).filter(Boolean);
      const lines = expenseText.split("\n").filter(l => l.trim());
      const expenses = lines.map(line => {
        const parts = line.trim().split(/\s+/);
        let amount = 0;
        let payer = "";
        let item = "";
        parts.forEach(p => {
          const num = parseInt(p.replace(/,/g, ""));
          if (!isNaN(num) && num > 100) amount = num;
          else if (people.includes(p)) payer = p;
          else item = p;
        });
        return { 항목: item, 돈낸사람: payer, 비용: amount };
      });

      setBusy(runBtn, "계산 중", true);
      try {
        const data = await postJson("/api/tools/settlement", { people, expenses });
        const container = document.querySelector("#tool-settlement-result-container");
        container.style.display = "block";
        document.querySelector("#tool-settlement-summary").textContent = data.summary_rows
          .map(r => `${r.사람}: ${r.잔액 >= 0 ? "+" : ""}${r.잔액.toLocaleString()}원 (${r["낸 금액"]}원 냄)`)
          .join("\n");
        document.querySelector("#tool-settlement-transfers").textContent = data.transfer_rows.length 
          ? data.transfer_rows.map(t => `${t["보내는 사람"]} → ${t["받는 사람"]}: ${t["금액"].toLocaleString()}원`).join("\n")
          : "추가 송금이 필요 없습니다.";
        if (data.errors && data.errors.length) showToast(data.errors[0]);
      } catch (error) {
        showToast(error.message);
      } finally {
        setBusy(runBtn, "계산 중", false);
      }
    });
  }
  if (tool === "menu-picker") {
    const runBtn = document.querySelector("#tool-menu-run");
    runBtn.addEventListener("click", async () => {
      setBusy(runBtn, "추천 중", true);
      try {
        const data = await apiJson("/api/tools/menu-picker");
        const box = document.querySelector("#menu-result-box");
        box.style.display = "block";
        document.querySelector("#selected-menu-label").textContent = data.selected_menu;
      } catch (error) {
        showToast(error.message);
      } finally {
        setBusy(runBtn, "추천 중", false);
      }
    });
  }
  if (tool === "storage-status") {
    const refreshBtn = document.querySelector("#tool-storage-refresh");
    const load = async () => {
      setBusy(refreshBtn, "확인 중", true);
      try {
        const data = await apiJson("/api/tools/storage-status");
        document.querySelector("#storage-status-metrics").innerHTML = `
          <article><span>Backend</span><strong>${data.backend}</strong></article>
          <article><span>파일 수</span><strong>${data.file_count}개</strong></article>
        `;
      } catch (error) {
        showToast(error.message);
      } finally {
        setBusy(refreshBtn, "확인 중", false);
      }
    };
    refreshBtn.addEventListener("click", load);
    load();
  }
}

async function bootstrap() {
  bindRoutes();

  // Login page logic
  const loginTabs = document.querySelectorAll(".login-tab");
  loginTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      loginTabs.forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      const mode = tab.dataset.loginTab;
      const pPass = document.querySelector("#login-panel-passkey");
      const pAcc = document.querySelector("#login-panel-account");
      if (pPass) pPass.classList.toggle("active", mode === "passkey");
      if (pAcc) pAcc.classList.toggle("active", mode === "account");
    });
  });

  document.querySelector("#login-button-passkey")?.addEventListener("click", async () => {
    const btn = document.querySelector("#login-button-passkey");
    setBusy(btn, "인증 중", true);
    try {
      await loginWithPasskey();
    } finally {
      setBusy(btn, "인증 중", false);
    }
  });

  document.querySelector("#login-form-account")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.querySelector("#login-button-account");
    const email = document.querySelector("#login-email").value;
    const password = document.querySelector("#login-password").value;
    setBusy(btn, "로그인 중", true);
    try {
      await postJson("/api/auth/account/login", { account_id: email, password });
      const session = await loadSession();
      if (session?.authorized) {
        showToast("로그인 성공");
        await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);
        setActivePage("home");
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(btn, "로그인 중", false);
    }
  });

  const session = await loadSession();
  renderFiles();
  renderMemos();
  updateHeroPreview();
  renderPresets();
  renderAiSources();
  renderTool("cleaner");
  renderSettingsAuth(session);
  
  if (session?.authorized) {
    await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);
  }
  
  // Event listeners that require session
  document.querySelector("#upload-form")?.addEventListener("submit", e => {
    e.preventDefault();
    uploadSelectedFiles(document.querySelector("#file-input"));
  });
  document.querySelector("#file-input")?.addEventListener("change", e => uploadSelectedFiles(e.target));
  document.querySelector("#download-all")?.addEventListener("click", async () => {
    try { await downloadFromApi("/api/files/zip", "jisong-cloud-files.zip"); showToast("ZIP 다운로드 시작"); } 
    catch(err) { showToast(err.message); }
  });
  navPasskeyRegister?.addEventListener("click", registerPasskey);
  navLoginButton?.addEventListener("click", loginWithPasskey);
  navLogoutButton?.addEventListener("click", logout);
  document.querySelector("#global-search-input")?.addEventListener("input", (e) => {
    const query = e.target.value;
    state.fileQuery = query;
    state.memoQuery = query;
    renderFiles();
    renderMemos();
  });

  document.querySelector("#passkey-register")?.addEventListener("click", registerPasskey);
  document.querySelector("#passkey-login")?.addEventListener("click", loginWithPasskey);
  document.querySelector("#account-id-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const email = document.querySelector("#account-id-input").value;
    try { await submitAccountIdLogin(email); showToast("로그인 성공"); } catch(err) { showToast(err.message); }
  });
  document.querySelector("#settings-refresh")?.addEventListener("click", async () => {
    await loadSession(); await loadSettings(); showToast("새로고침 완료");
  });
  document.querySelector("#access-log-clear")?.addEventListener("click", async () => {
    if (!confirm("삭제하시겠습니까?")) return;
    try { await postJson("/api/settings/access-logs/clear"); await loadSettings(); showToast("삭제 완료"); } catch(err) { showToast(err.message); }
  });
  document.querySelector("#file-search")?.addEventListener("input", e => { state.fileQuery = e.target.value; renderFiles(); });
  document.querySelector("#memo-search")?.addEventListener("input", e => { state.memoQuery = e.target.value; renderMemos(); });
  document.querySelector("#download-memos")?.addEventListener("click", async () => {
    try { await downloadFromApi("/api/memos/zip", "jisong-cloud-memos.zip"); showToast("ZIP 다운로드 시작"); } 
    catch(err) { showToast(err.message); }
  });
  // Tools switching
  document.addEventListener("click", (e) => {
    const card = e.target.closest(".tool-card");
    if (card) {
      const tool = card.dataset.tool;
      document.querySelectorAll(".tool-card").forEach(c => c.classList.remove("is-selected"));
      card.classList.add("is-selected");
      renderTool(tool);
    }

    const shortcut = e.target.closest("[data-tool-shortcut]");
    if (shortcut) {
      const tool = shortcut.dataset.toolShortcut;
      setActivePage("tools");
      // Wait for partial to render
      setTimeout(() => {
        const card = document.querySelector(`.tool-card[data-tool="${tool}"]`);
        if (card) {
          card.click();
        }
      }, 50);
    }
  });

  document.querySelector("#memo-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const t = document.querySelector("#memo-title").value;
    const b = document.querySelector("#memo-body").value;
    const f = document.querySelector("#memo-file-name").value;
    try { await postJson("/api/memos", { title: t, content: b, file_name: f || undefined }); resetMemoForm(); await loadMemos(); showToast("저장 완료"); } catch(err) { showToast(err.message); }
  });
  document.querySelector("#memo-reset-button")?.addEventListener("click", () => { resetMemoForm(); renderMemos(); });
  document.querySelector("#run-ai")?.addEventListener("click", async () => {
    const prompt = document.querySelector("#ai-prompt").value;
    const btn = document.querySelector("#run-ai");
    setBusy(btn, "분석 중", true);
    try {
      const data = await postJson("/api/ai/analyze", { prompt, blob_names: selectedValues("[data-ai-file]"), memo_file_names: selectedValues("[data-ai-memo]") });
      document.querySelector("#ai-result").innerHTML = `<span>AI result</span><h3>분석 결과</h3><div>${markdownToHtml(data.result)}</div>`;
      state.lastAiResult = data.result;
      saveAiMemoButton.disabled = false; downloadAiMdButton.disabled = false; downloadAiPdfButton.disabled = false;
      await loadUsageSummary();
    } catch(err) { showToast(err.message); } finally { setBusy(btn, "분석 중", false); }
  });

  setActivePage(pageFromLocation(), { skipHistory: true });
}

bootstrap();
