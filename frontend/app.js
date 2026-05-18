import { renderToolPanel } from "./tool-panel.js";



const presets = [
  "SOAP 1분 발표",
  "예상 QnA",
  "교수님 질문",
  "환자 설명문",
];

const state = {
  files: [],
  memos: [],
  session: null,
  usesDemoData: true,
  fileQuery: "",
  memoQuery: "",
  editingMemoFileName: "",
  lastAiResult: "",
  lastParsedData: null,
  editingDocIdx: null,
  selectedDocIndices: [],
};

const DEFAULT_GEMINI_COST_MULTIPLIER = "1.0";

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
const heroFileList = document.querySelector("#hero-file-list");
const heroMemoPreview = document.querySelector("#hero-memo-preview");
const geminiExchangeRateInput = document.querySelector("#gemini-exchange-rate");
const geminiCostMultiplierInput = document.querySelector("#gemini-cost-multiplier");
const geminiSettingsSaveBtn = document.querySelector("#gemini-settings-save");
const folderSyncRescanButton = document.querySelector("#folder-sync-rescan");
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

function getFileIconHtml(name = "") {
  const ext = (name.split(".").pop() || "").toLowerCase();
  let iconName = "generic";

  if (["zip", "tar", "gz", "rar", "7z"].includes(ext)) iconName = "archive";
  else if (["xls", "xlsx", "csv"].includes(ext)) iconName = "excel";
  else if (["jpg", "jpeg", "png", "gif", "svg", "webp"].includes(ext)) iconName = "image";
  else if (["md"].includes(ext)) iconName = "markdown";
  else if (["mp3", "mp4", "wav", "avi", "mov", "mkv"].includes(ext)) iconName = "media";
  else if (["pdf"].includes(ext)) iconName = "pdf";
  else if (["ppt", "pptx"].includes(ext)) iconName = "powerpoint";
  else if (["txt", "log", "json"].includes(ext)) iconName = "text";
  else if (["doc", "docx"].includes(ext)) iconName = "word";

  return `<img src="/assets/icons/filetypes/${iconName}.svg" alt="${ext}" width="24" height="24" style="display:block;">`;
}

function includesQuery(...values) {
  const query = values.pop().trim().toLowerCase();
  if (!query) return true;
  return values.some((value) => String(value || "").toLowerCase().includes(query));
}

function highlightMatch(text, query) {
  if (!query) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
  return escaped.replace(regex, '<mark class="highlight">$1</mark>');
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
    includesQuery(file.name, file.ext, file.updated, state.fileQuery),
  );
}

function getFilteredMemos() {
  return state.memos.filter((memo) =>
    includesQuery(memo.title, memo.body, memo.updated, state.memoQuery),
  );
}

async function uploadSelectedFiles(input) {
  const files = input.files;
  if (!files.length) return;
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append(`file${i}`, files[i]);
  }
  const btn = document.querySelector("#upload-form button") || { textContent: "" };
  setBusy(btn, "업로드 중", true);
  try {
    await fetch("/api/files", {
      method: "POST",
      body: formData,
    });
    showToast("업로드 완료");
    await loadFiles();
  } catch (error) {
    showToast("업로드 실패: " + error.message);
  } finally {
    setBusy(btn, "", false);
    input.value = "";
  }
}

async function deleteFile(index) {
  const file = getFilteredFiles()[index];
  if (!file || !confirm(`'${file.name}' 파일을 삭제하시겠습니까?`)) return;
  try {
    await postJson("/api/files/delete", { blob_name: file.blobName });
    showToast("삭제 완료");
    await loadFiles();
  } catch (error) {
    showToast("삭제 실패: " + error.message);
  }
}

async function downloadFile(index) {
  const file = getFilteredFiles()[index];
  if (!file) return;
  try {
    await downloadFromApi(`/api/files/download?blob_name=${encodeURIComponent(file.blobName)}`, file.name);
  } catch (error) {
    showToast("다운로드 실패: " + error.message);
  }
}

async function saveMemo(silent = false) {
  const t = document.querySelector("#memo-title").value;
  const b = document.querySelector("#memo-body").value;
  const f = document.querySelector("#memo-file-name").value;
  if (!t.trim() || !b.trim()) return;
  try {
    await postJson("/api/memos", { title: t, content: b, file_name: f || undefined });
    if (!silent) {
      resetMemoForm();
      showToast("저장 완료");
    }
    await loadMemos();
  } catch (error) {
    if (!silent) showToast(error.message);
  }
}

async function deleteMemo(index) {
  const memo = getFilteredMemos()[index];
  if (!memo || !confirm(`'${memo.title}' 메모를 삭제하시겠습니까?`)) return;
  try {
    await postJson("/api/memos/delete", { file_name: memo.fileName });
    showToast("삭제 완료");
    await loadMemos();
  } catch (error) {
    showToast("삭제 실패: " + error.message);
  }
}

function resetMemoForm() {
  document.querySelector("#memo-title").value = "";
  document.querySelector("#memo-body").value = "";
  document.querySelector("#memo-file-name").value = "";
  state.editingMemoFileName = "";
  if (memoSaveButton) memoSaveButton.textContent = "메모 저장";
  if (downloadCurrentMemoButton) downloadCurrentMemoButton.disabled = true;
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
            <span class="file-icon" style="padding:0;background:transparent;border:none;">${getFileIconHtml(file.name)}</span>
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
    state.session = null;
    setSessionChip(null);
    renderSettingsAuth(null);
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
      ext: (file.name.split(".").pop() || "").toLowerCase(),
      size: formatBytes(file.size),
      updated: formatUpdated(file.updated),
      downloadUrl: file.download_url,
    }));
    state.usesDemoData = false;
  } catch (error) {
    state.files = [];
    state.usesDemoData = false;
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
    state.memos = [];
  }
  renderMemos();
  updateHeroPreview();
  renderAiSources();
}

async function loadMemoDetail(fileName) {
  if (!fileName) return null;
  const data = await apiJson(`/api/memos/${encodeURIComponent(fileName)}`);
  return data.memo || null;
}

async function loadUsageSummary() {
  try {
    const exchangeRate = localStorage.getItem("geminiExchangeRate") || "";
    const multiplier = localStorage.getItem("geminiCostMultiplier") || "";
    const query = new URLSearchParams();
    if (exchangeRate) query.append("exchange_rate", exchangeRate);
    if (multiplier) query.append("multiplier", multiplier);

    const usage = await apiJson(`/api/usage/summary?${query.toString()}`);
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
    renderSyncSettings({ file_records: [] });
    return;
  }
  try {
    const exchangeRate = localStorage.getItem("geminiExchangeRate") || "";
    const multiplier = localStorage.getItem("geminiCostMultiplier") || "";
    const query = new URLSearchParams();
    if (exchangeRate) query.append("exchange_rate", exchangeRate);
    if (multiplier) query.append("multiplier", multiplier);

    const [accessLogs, geminiUsage] = await Promise.all([
      apiJson("/api/settings/access-logs"),
      apiJson(`/api/settings/gemini-usage?${query.toString()}`),
    ]);
    const syncStatus = await apiJson("/api/sync/status");
    renderAccessLogSettings(accessLogs);
    renderGeminiUsageSettings(geminiUsage);
    renderSyncSettings(syncStatus);
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

function renderSyncSettings(data = {}) {
  const metrics = document.querySelector("#folder-sync-metrics");
  const list = document.querySelector("#folder-sync-list");
  const status = document.querySelector("#sync-status");
  if (!metrics || !list || !status) return;

  const lastResult = data.last_result || {};
  const fileRecords = data.file_records || [];
  status.textContent = data.enabled
    ? `${data.root || "-"} · ${data.running ? "실행 중" : "대기"}`
    : "비활성";

  metrics.innerHTML = `
    <article><span>상태</span><strong>${data.enabled ? (data.running ? "Running" : "Idle") : "Off"}</strong></article>
    <article><span>루트</span><strong>${escapeHtml(data.root || "-")}</strong></article>
    <article><span>업로드</span><strong>${Number(lastResult.uploaded || 0).toLocaleString()}</strong></article>
    <article><span>충돌</span><strong>${Number(lastResult.conflicts || 0).toLocaleString()}</strong></article>
  `;

  const records = fileRecords.slice(-8).reverse();
  list.innerHTML = records.length
    ? records
      .map((row) => {
        const badge = row.status || "skipped";
        const conflict = row.conflict_blob_name
          ? `<small>conflict: ${escapeHtml(row.conflict_blob_name)}</small>`
          : "";
        return `
            <article class="settings-row">
              <strong>${escapeHtml(row.relative_path || row.blob_name || "-")}</strong>
              <span>${escapeHtml(badge)} · ${escapeHtml(row.synced_at || "-")}</span>
              ${conflict}
            </article>
          `;
      })
      .join("")
    : `<p class="empty-state">동기화 기록이 없습니다.</p>`;
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
  const visibleFiles = getFilteredFiles().sort((a, b) => {
    return new Date(b.updated || 0) - new Date(a.updated || 0);
  });
  fileList.innerHTML = visibleFiles
    .map(
      (file, index) => `
        <div class="data-row">
          <span class="file-icon" style="padding:0;background:transparent;border:none;">${getFileIconHtml(file.name)}</span>
          <div>
            <strong>${highlightMatch(file.name, state.fileQuery)}</strong>
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
  const visibleMemos = getFilteredMemos().sort((a, b) => {
    return new Date(b.updated || 0) - new Date(a.updated || 0);
  });
  memoList.innerHTML = visibleMemos
    .map(
      (memo, index) => `
        <article class="memo-card ${memo.fileName && memo.fileName === state.editingMemoFileName ? "is-selected" : ""}">
          <h3>${highlightMatch(memo.title, state.memoQuery)}</h3>
          <p>${highlightMatch(memo.body, state.memoQuery)}</p>
          <div class="memo-actions">
            ${memo.updated ? `<small>${escapeHtml(memo.updated)}</small>` : "<small>미리보기</small>"}
            ${memo.fileName
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

function renderParsedDocuments() {
  const data = state.lastParsedData;
  if (!data || !data.documents) return;

  let html = `<div style="border-bottom: 2px solid var(--neutral-20); padding-bottom: 8px; margin-bottom: 16px; display:flex; justify-content:space-between; align-items:center;">
    <div>
      <span style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; color: var(--neutral-50);">Pipeline Result</span>
      <h3 style="margin: 4px 0 0 0; color: var(--neutral-90);">Extracted Artifacts (${data.documents.length})</h3>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
      <span style="font-size:0.75rem; color:var(--neutral-50);">* 검수 완료 후 동기화하세요</span>
    </div>
  </div>`;

  if (state.selectedDocIndices.length > 0) {
    html += `
    <div style="background: var(--blue-50); color: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,90,158,0.2);">
      <span style="font-weight: 600; font-size: 0.9rem;">${state.selectedDocIndices.length}개 선택됨</span>
      <div style="display: flex; gap: 8px;">
        <button type="button" class="button" id="bulk-add-tag" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 10px; font-size: 0.8rem;">태그 추가</button>
        <button type="button" class="button" id="bulk-delete" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 10px; font-size: 0.8rem;">삭제</button>
        <button type="button" class="button" id="bulk-clear" style="background: transparent; border: none; color: white; padding: 4px 10px; font-size: 0.8rem; text-decoration: underline;">취소</button>
      </div>
    </div>`;
  }

  html += `<div style="display: flex; flex-direction: column; gap: 16px;">`;
  data.documents.forEach((doc, index) => {
    const isEditing = state.editingDocIdx === index;
    const isSelected = state.selectedDocIndices.includes(index);
    const isCsv = doc.kind === "lab" || doc.kind === "medication";
    const icon = isCsv ? "📊" : "📝";

    if (isEditing) {
      html += `
        <div style="background:#fff; border-radius:8px; border:2px solid var(--blue-50); box-shadow: 0 4px 12px rgba(0,90,158,0.15); overflow: hidden;">
          <div style="background:var(--neutral-10); padding:12px 16px; border-bottom:1px solid var(--neutral-20);">
            <div style="display:flex; flex-direction:column; gap:8px;">
              <div>
                <label style="display:block; font-size:0.75rem; font-weight:600; color:var(--neutral-60); margin-bottom:4px;">File Relative Path</label>
                <input type="text" id="edit-doc-path" class="input" value="${escapeHtml(doc.relativePath)}" style="width:100%; font-family:monospace; font-size:0.85rem; padding:6px 10px;">
              </div>
              <div style="display:flex; gap:12px;">
                <div style="flex:1;">
                  <label style="display:block; font-size:0.75rem; font-weight:600; color:var(--neutral-60); margin-bottom:4px;">Title</label>
                  <input type="text" id="edit-doc-title" class="input" value="${escapeHtml(doc.metadata.title)}" style="width:100%; font-size:0.85rem; padding:6px 10px;">
                </div>
                <div style="flex:1;">
                  <label style="display:block; font-size:0.75rem; font-weight:600; color:var(--neutral-60); margin-bottom:4px;">Tags (comma separated)</label>
                  <input type="text" id="edit-doc-tags" class="input" value="${escapeHtml(doc.metadata.tags?.join(", "))}" style="width:100%; font-size:0.85rem; padding:6px 10px;">
                </div>
              </div>
              <div style="display:flex; gap:12px;">
                <div style="flex:1;">
                  <label style="display:block; font-size:0.75rem; font-weight:600; color:var(--neutral-60); margin-bottom:4px;">Modality Kind</label>
                  <select id="edit-doc-kind" class="input" style="width:100%; padding:6px 10px;">
                    <option value="note" ${doc.kind === "note" ? "selected" : ""}>note (MD)</option>
                    <option value="lab" ${doc.kind === "lab" ? "selected" : ""}>lab (CSV)</option>
                    <option value="medication" ${doc.kind === "medication" ? "selected" : ""}>medication (CSV)</option>
                    <option value="imaging" ${doc.kind === "imaging" ? "selected" : ""}>imaging (MD)</option>
                    <option value="pathology" ${doc.kind === "pathology" ? "selected" : ""}>pathology (MD)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          <div style="padding:16px;">
            <label style="display:block; font-size:0.75rem; font-weight:600; color:var(--neutral-60); margin-bottom:6px;">Document Content</label>
            <textarea id="edit-doc-content" class="input" rows="12" style="width:100%; font-family:monospace; font-size:0.85rem; line-height:1.4; padding:12px; white-space:pre-wrap;">${escapeHtml(doc.content)}</textarea>
            <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:12px;">
              <button type="button" class="button button-secondary" data-doc-cancel style="padding:6px 12px; font-size:0.85rem;">취소</button>
              <button type="button" class="button button-primary" data-doc-save="${index}" style="padding:6px 12px; font-size:0.85rem;">적용</button>
            </div>
          </div>
        </div>`;
    } else {
      html += `
       <div style="background:#fff; border-radius:8px; border:1px solid ${isSelected ? "var(--blue-50)" : "var(--neutral-20)"}; box-shadow: ${isSelected ? "0 4px 12px rgba(0,90,158,0.1)" : "0 1px 3px rgba(0,0,0,0.05)"}; overflow: hidden; transition: all 0.2s;">
         <div style="background: ${isSelected ? "rgba(0,90,158,0.03)" : "var(--neutral-10)"}; padding:10px 16px; border-bottom:1px solid var(--neutral-20); display:flex; justify-content:space-between; align-items:center;">
           <div style="display:flex; align-items:center; gap:12px;">
             <input type="checkbox" data-doc-select="${index}" ${isSelected ? "checked" : ""} style="width:16px; height:16px; cursor:pointer;">
             <span style="font-size:1.2rem;">${icon}</span>
             <strong style="color:var(--neutral-90); font-family:monospace; font-size:0.9rem;">${escapeHtml(doc.relativePath)}</strong>
           </div>
           <div style="display:flex; align-items:center; gap:12px;">
             <span style="font-size:0.75rem; font-weight:600; text-transform:uppercase; background:var(--blue-10); color:var(--blue-70); padding:2px 8px; border-radius:12px;">${escapeHtml(doc.kind)}</span>
             <button type="button" class="text-button" data-doc-edit="${index}" style="font-size:0.8rem; font-weight:600;">수정</button>
           </div>
         </div>
         <div style="padding:0; margin:0;">
           <pre style="margin:0; padding:16px; background:#fcfcfc; max-height:250px; overflow-y:auto; font-size:0.85rem; border:none; white-space:pre-wrap; color:var(--neutral-80);">${escapeHtml(doc.content)}</pre>
         </div>
       </div>`;
    }
  });
  html += `</div>`;
  const resultEl = document.querySelector("#ai-result");
  if (resultEl) {
    resultEl.style.display = "block";
    resultEl.innerHTML = html;
  }
}

async function sha256(message) {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function rebuildManifests() {
  const data = state.lastParsedData;
  if (!data || !data.documents) return [];

  const manifests = [];
  for (let i = 0; i < data.documents.length; i++) {
    const doc = data.documents[i];
    const originalManifest = data.manifest && data.manifest[i] ? data.manifest[i] : {};

    const checksum = await sha256(doc.content);
    const sourceArtId = doc.metadata?.sourceArtifactId || originalManifest.sourceArtifactId || "api-upload";
    const patientId = doc.metadata?.patientId || originalManifest.patientId || "unknown";

    manifests.push({
      documentId: `${sourceArtId}:${doc.relativePath}`,
      patientId: patientId,
      type: doc.kind,
      relativePath: doc.relativePath,
      checksum: checksum,
      generatedAt: new Date().toISOString(),
      sourceArtifactId: sourceArtId,
      reviewRequired: doc.metadata?.reviewRequired ?? originalManifest.reviewRequired ?? false,
      tags: doc.metadata?.tags || originalManifest.tags || [],
    });
  }
  return manifests;
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

async function bootstrap() {
  bindRoutes();
  setActivePage("login", { skipHistory: true });

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
    const email = document.querySelector("#login-email").value.trim().toLowerCase();
    const password = document.querySelector("#login-password").value;
    setBusy(btn, "로그인 중", true);
    try {
      await postJson("/api/auth/account/login", { account_id: email, password });
      const session = await loadSession();
      if (session?.authorized) {
        showToast("로그인 성공");
        setActivePage("home");
        await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(btn, "로그인 중", false);
    }
  });

  const session = await loadSession();
  const loginEmailInput = document.querySelector("#login-email");
  if (loginEmailInput && !loginEmailInput.value && session?.account_login_id) {
    loginEmailInput.value = session.account_login_id;
  }
  renderFiles();
  renderMemos();
  updateHeroPreview();
  renderPresets();
  renderAiSources();
  renderToolPanel("cleaner", { showToast, setBusy, postJson, downloadPostBlob, selectedValues });
  renderSettingsAuth(session);

  if (session?.authorized) {
    await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);

    // Auto polling for stale data
    setInterval(async () => {
      await Promise.all([loadFiles(), loadMemos(), loadUsageSummary(), loadSettings()]);
    }, 60000);
  }

  // Event listeners that require session
  document.querySelector("#upload-form")?.addEventListener("submit", e => {
    e.preventDefault();
    uploadSelectedFiles(document.querySelector("#file-input"));
  });
  document.querySelector("#file-input")?.addEventListener("change", e => uploadSelectedFiles(e.target));
  document.querySelector("#download-all")?.addEventListener("click", async () => {
    try { await downloadFromApi("/api/files/zip", "jisong-cloud-files.zip"); showToast("ZIP 다운로드 시작"); }
    catch (err) { showToast(err.message); }
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

    // Auto-navigate to files if searching from dashboard
    const current = document.documentElement.getAttribute("data-active-page");
    if (query && !["files", "memos"].includes(current)) {
      setActivePage("files");
    }
  });
  document.addEventListener("change", (e) => {
    if (e.target.matches("[data-ai-file], [data-ai-memo]")) {
      updateAiSourceStatus();
    }
  });

  document.querySelector("#account-id-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const email = document.querySelector("#account-id-input").value;
    const password = document.querySelector("#account-password-input").value;
    const btn = e.target.querySelector("button");
    setBusy(btn, "로그인 중", true);
    try {
      await postJson("/api/auth/account/login", { account_id: email, password });
      const session = await loadSession();
      if (session?.authorized) {
        setActivePage("settings");
        showToast("로그인 성공");
      }
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(btn, "로그인 중", false);
    }
  });
  document.querySelector("#password-update-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const newPassword = document.querySelector("#new-password-input").value;
    const btn = e.target.querySelector("button");
    setBusy(btn, "저장 중", true);
    try {
      await postJson("/api/settings/password", { new_password: newPassword });
      showToast("비밀번호가 변경되었습니다.");
      document.querySelector("#new-password-input").value = "";
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(btn, "저장 중", false);
    }
  });
  document.querySelector("#settings-refresh")?.addEventListener("click", async () => {
    await loadSession(); await loadSettings(); showToast("새로고침 완료");
  });
  folderSyncRescanButton?.addEventListener("click", async () => {
    try {
      setBusy(folderSyncRescanButton, "동기화 중", true);
      await postJson("/api/sync/rescan");
      await loadSettings();
      showToast("동기화 완료");
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(folderSyncRescanButton, "지금 동기화", false);
    }
  });
  document.querySelector("#access-log-clear")?.addEventListener("click", async () => {
    if (!confirm("삭제하시겠습니까?")) return;
    try { await postJson("/api/settings/access-logs/clear"); await loadSettings(); showToast("삭제 완료"); } catch (err) { showToast(err.message); }
  });
  document.querySelector("#file-search")?.addEventListener("input", e => { state.fileQuery = e.target.value; renderFiles(); });
  document.querySelector("#memo-search")?.addEventListener("input", e => { state.memoQuery = e.target.value; renderMemos(); });
  document.querySelector("#download-memos")?.addEventListener("click", async () => {
    try { await downloadFromApi("/api/memos/zip", "jisong-cloud-memos.zip"); showToast("ZIP 다운로드 시작"); }
    catch (err) { showToast(err.message); }
  });
  // Tools switching
  document.addEventListener("click", async (e) => {
    const card = e.target.closest(".tool-card");
    if (card) {
      const tool = card.dataset.tool;
      document.querySelectorAll(".tool-card").forEach(c => c.classList.remove("is-selected"));
      card.classList.add("is-selected");
      renderToolPanel(tool, { showToast, setBusy, postJson, downloadPostBlob, selectedValues });
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
      return;
    }

    const dlBtn = e.target.closest("[data-download]");
    if (dlBtn) {
      downloadFile(parseInt(dlBtn.dataset.download));
      return;
    }

    const delBtn = e.target.closest("[data-delete]");
    if (delBtn) {
      deleteFile(parseInt(delBtn.dataset.delete));
      return;
    }

    const memoOpen = e.target.closest("[data-memo-open]");
    if (memoOpen) {
      const memo = getFilteredMemos()[parseInt(memoOpen.dataset.memoOpen)];
      if (memo) {
        try {
          const fullMemo = await loadMemoDetail(memo.fileName);
          const nextMemo = fullMemo
            ? {
              ...memo,
              title: fullMemo.title || memo.title,
              body: fullMemo.content || memo.body,
            }
            : memo;
          state.memos = state.memos.map((item) =>
            item.fileName === memo.fileName ? nextMemo : item,
          );
          document.querySelector("#memo-title").value = nextMemo.title;
          document.querySelector("#memo-body").value = nextMemo.body;
          document.querySelector("#memo-file-name").value = memo.fileName;
          state.editingMemoFileName = memo.fileName;
          if (memoSaveButton) memoSaveButton.textContent = "메모 수정";
          if (downloadCurrentMemoButton) downloadCurrentMemoButton.disabled = false;
          renderMemos();
        } catch (err) {
          showToast(err.message);
        }
      }
      return;
    }

    const memoDelete = e.target.closest("[data-memo-delete]");
    if (memoDelete) {
      deleteMemo(parseInt(memoDelete.dataset.memoDelete));
      return;
    }

    const docEdit = e.target.closest("[data-doc-edit]");
    if (docEdit) {
      state.editingDocIdx = parseInt(docEdit.getAttribute("data-doc-edit"));
      renderParsedDocuments();
      return;
    }

    const docCancel = e.target.closest("[data-doc-cancel]");
    if (docCancel) {
      state.editingDocIdx = null;
      renderParsedDocuments();
      return;
    }

    const docSave = e.target.closest("[data-doc-save]");
    if (docSave) {
      const idx = parseInt(docSave.getAttribute("data-doc-save"));
      const pathVal = document.querySelector("#edit-doc-path")?.value.trim();
      const kindVal = document.querySelector("#edit-doc-kind")?.value;
      const contentVal = document.querySelector("#edit-doc-content")?.value;
      const titleVal = document.querySelector("#edit-doc-title")?.value.trim();
      const tagsVal = document.querySelector("#edit-doc-tags")?.value.split(",").map(t => t.trim()).filter(Boolean);

      if (pathVal && kindVal && contentVal !== undefined) {
        state.lastParsedData.documents[idx].relativePath = pathVal;
        state.lastParsedData.documents[idx].kind = kindVal;
        state.lastParsedData.documents[idx].content = contentVal;
        if (titleVal) state.lastParsedData.documents[idx].metadata.title = titleVal;
        if (tagsVal) state.lastParsedData.documents[idx].metadata.tags = tagsVal;
        showToast("임시 수정사항이 반영되었습니다.");
      }

      state.editingDocIdx = null;
      renderParsedDocuments();
      return;
    }

    const docSelect = e.target.closest("[data-doc-select]");
    if (docSelect) {
      const idx = parseInt(docSelect.getAttribute("data-doc-select"));
      if (state.selectedDocIndices.includes(idx)) {
        state.selectedDocIndices = state.selectedDocIndices.filter(i => i !== idx);
      } else {
        state.selectedDocIndices.push(idx);
      }
      renderParsedDocuments();
      return;
    }

    if (e.target.id === "bulk-clear") {
      state.selectedDocIndices = [];
      renderParsedDocuments();
      return;
    }

    if (e.target.id === "bulk-delete") {
      if (confirm(`${state.selectedDocIndices.length}개의 항목을 삭제하시겠습니까?`)) {
        state.lastParsedData.documents = state.lastParsedData.documents.filter((_, i) => !state.selectedDocIndices.includes(i));
        state.selectedDocIndices = [];
        renderParsedDocuments();
        showToast("선택한 항목이 삭제되었습니다.");
      }
      return;
    }

    if (e.target.id === "bulk-add-tag") {
      const tag = prompt("추가할 태그를 입력하세요:");
      if (tag) {
        state.selectedDocIndices.forEach(idx => {
          const doc = state.lastParsedData.documents[idx];
          if (!doc.metadata.tags) doc.metadata.tags = [];
          if (!doc.metadata.tags.includes(tag)) {
            doc.metadata.tags.push(tag);
          }
        });
        renderParsedDocuments();
        showToast("태그가 추가되었습니다.");
      }
      return;
    }
  });

  document.querySelector("#memo-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    await saveMemo();
  });
  document.querySelector("#memo-reset-button")?.addEventListener("click", () => { resetMemoForm(); renderMemos(); });

  const themeToggle = document.querySelector("#theme-toggle");
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);
  if (themeToggle) {
    themeToggle.textContent = currentTheme === "dark" ? "라이트 모드 전환" : "다크 모드 전환";
    themeToggle.addEventListener("click", () => {
      const newTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      themeToggle.textContent = newTheme === "dark" ? "라이트 모드 전환" : "다크 모드 전환";
    });
  }

  document.querySelector("#preset-row")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-preset]");
    if (!btn) return;
    const promptInput = document.querySelector("#ai-prompt");
    if (promptInput) {
      const presetText = btn.getAttribute("data-preset");
      const baseText = promptInput.value.trim();
      promptInput.value = baseText ? `${baseText}\n\n${presetText}` : presetText;
    }
  });

  // Drag & Drop for EMR Intake
  const intakeDropzone = document.querySelector("#intake-dropzone");
  const promptInput = document.querySelector("#ai-prompt");
  if (intakeDropzone && promptInput) {
    intakeDropzone.addEventListener("dragover", e => {
      e.preventDefault();
      intakeDropzone.classList.add("drag-over");
    });
    intakeDropzone.addEventListener("dragleave", e => {
      e.preventDefault();
      intakeDropzone.classList.remove("drag-over");
    });
    intakeDropzone.addEventListener("drop", async e => {
      e.preventDefault();
      intakeDropzone.classList.remove("drag-over");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (!file.name.toLowerCase().endsWith(".txt")) {
          showToast("텍스트 파일(.txt)만 처리할 수 있습니다.");
          return;
        }
        try {
          const text = await file.text();
          promptInput.value = text;
          showToast(`${file.name} 파일을 불러왔습니다.`);
        } catch (err) {
          showToast("파일을 읽는 중 오류가 발생했습니다.");
        }
      }
    });
  }

  const modeV6Btn = document.querySelector("#mode-v6");
  const modeV5Btn = document.querySelector("#mode-v5");
  const v6Inputs = document.querySelector("#v6-inputs");
  const v5SourcePicker = document.querySelector("#v5-source-picker");
  const runAiV6Btn = document.querySelector("#run-ai");
  const runAiV5Btn = document.querySelector("#run-ai-v5");
  const syncContainer = document.querySelector("#sync-container");
  const v5Actions = document.querySelector("#v5-actions");
  const v5Presets = document.querySelector("#v5-prompt-presets");
  const aiVersionBadge = document.querySelector("#ai-version-badge");
  const aiTitle = document.querySelector("#ai-title");

  let currentAiMode = "v6";

  const updateAiModeUI = () => {
    if (currentAiMode === "v6") {
      modeV6Btn.classList.add("is-active", "button-primary");
      modeV6Btn.classList.remove("button-secondary");
      modeV6Btn.style.border = "none";
      modeV6Btn.style.background = "";

      modeV5Btn.classList.remove("is-active", "button-primary");
      modeV5Btn.classList.add("button-secondary");
      modeV5Btn.style.border = "none";
      modeV5Btn.style.background = "transparent";

      v6Inputs.style.display = "flex";
      runAiV6Btn.style.display = "block";
      runAiV5Btn.style.display = "none";
      v5Actions.style.display = "none";
      v5Presets.style.display = "none";
      if (v5SourcePicker) v5SourcePicker.style.display = "none";

      aiTitle.textContent = "EMR Intake";
      aiVersionBadge.textContent = "v6 Pipeline";

      if (state.lastParsedData) syncContainer.style.display = "flex";
    } else {
      modeV5Btn.classList.add("is-active", "button-primary");
      modeV5Btn.classList.remove("button-secondary");
      modeV5Btn.style.border = "none";
      modeV5Btn.style.background = "";

      modeV6Btn.classList.remove("is-active", "button-primary");
      modeV6Btn.classList.add("button-secondary");
      modeV6Btn.style.border = "none";
      modeV6Btn.style.background = "transparent";

      v6Inputs.style.display = "none";
      runAiV6Btn.style.display = "none";
      runAiV5Btn.style.display = "block";
      syncContainer.style.display = "none";
      v5Presets.style.display = "flex";
      if (v5SourcePicker) v5SourcePicker.style.display = "block";

      aiTitle.textContent = "AI Workbench";
      aiVersionBadge.textContent = "v5 Legacy";

      if (state.lastAiResult) v5Actions.style.display = "flex";
    }
    const aiResult = document.querySelector("#ai-result");
    aiResult.style.display = "none";
    aiResult.innerHTML = "";
  };

  modeV6Btn?.addEventListener("click", () => { currentAiMode = "v6"; updateAiModeUI(); });
  modeV5Btn?.addEventListener("click", () => { currentAiMode = "v5"; updateAiModeUI(); });

  document.querySelectorAll(".preset-badge").forEach(badge => {
    badge.addEventListener("click", () => {
      badge.classList.toggle("is-active");
      const presetText = badge.dataset.preset;
      const promptEl = document.querySelector("#ai-prompt");
      let currentVal = promptEl.value;

      if (badge.classList.contains("is-active")) {
        promptEl.value = currentVal ? `${currentVal}\n\n${presetText}` : presetText;
      } else {
        promptEl.value = currentVal.replace(`\n\n${presetText}`, "").replace(presetText, "").trim();
      }
    });
  });

  document.querySelector("#run-ai")?.addEventListener("click", async () => {
    const rawText = document.querySelector("#ai-prompt").value;
    const patientId = document.querySelector("#intake-patient-id")?.value || "patient_001";
    const btn = document.querySelector("#run-ai");
    setBusy(btn, "파이프라인 실행 중", true);
    try {
      const data = await postJson("/api/v6/parse", { patient_id: patientId, raw_text: rawText });
      state.lastParsedData = data;
      state.editingDocIdx = null;

      renderParsedDocuments();

      const syncContainer = document.querySelector("#sync-container");
      if (syncContainer) syncContainer.style.display = "flex";

      showToast("정규화 완료");
    } catch (err) { showToast(err.message); } finally { setBusy(btn, "Run Normalization Pipeline", false); }
  });

  document.querySelector("#run-ai-v5")?.addEventListener("click", async () => {
    const rawText = document.querySelector("#ai-prompt").value;
    const selectedBlobNames = selectedValues("[data-ai-file]");
    const selectedMemoFileNames = selectedValues("[data-ai-memo]");
    if (!rawText.trim() && !selectedBlobNames.length && !selectedMemoFileNames.length) {
      return showToast("질문을 입력하거나 파일/메모를 하나 이상 선택해주세요.");
    }

    const btn = document.querySelector("#run-ai-v5");
    setBusy(btn, "Gemini 분석 중", true);
    try {
      const data = await postJson("/api/ai/analyze", {
        prompt: rawText,
        blob_names: selectedBlobNames,
        memo_file_names: selectedMemoFileNames,
      });
      state.lastAiResult = data.result || "결과가 없습니다.";
      const aiResult = document.querySelector("#ai-result");
      aiResult.innerHTML = markdownToHtml(state.lastAiResult);
      aiResult.style.display = "block";
      document.querySelector("#v5-actions").style.display = "flex";
      showToast("분석 완료");
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(btn, "Run Gemini Analysis", false);
    }
  });

  document.querySelector("#sync-local")?.addEventListener("click", async () => {
    if (!state.lastParsedData || !state.lastParsedData.documents) return;
    const btn = document.querySelector("#sync-local");
    setBusy(btn, "Syncing", true);
    try {
      const newManifests = await rebuildManifests();
      const payload = {
        documents: state.lastParsedData.documents,
        manifest: newManifests,
      };
      const data = await postJson("/api/v6/publish", payload);
      showToast(`${data.synced_count}개의 파일이 동기화 큐(GCS)에 발행되었습니다.`);
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(btn, "Sync to Local Workspace (Phase 3)", false);
    }
  });

  saveAiMemoButton?.addEventListener("click", async () => {
    if (!state.lastAiResult) return;
    try { await postJson("/api/memos", { title: "AI 분석 결과", content: state.lastAiResult }); await loadMemos(); showToast("메모로 저장되었습니다."); }
    catch (err) { showToast(err.message); }
  });
  downloadAiMdButton?.addEventListener("click", () => {
    const blob = new Blob([state.lastAiResult], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "ai-result.md"; a.click();
  });
  downloadAiPdfButton?.addEventListener("click", async () => {
    try { await downloadPostBlob("/api/tools/markdown-pdf", { markdown: state.lastAiResult }, "ai-result.pdf"); showToast("PDF 다운로드 시작"); }
    catch (err) { showToast(err.message); }
  });
  downloadCurrentMemoButton?.addEventListener("click", async () => {
    const fileName = document.querySelector("#memo-file-name").value;
    if (!fileName) return;
    try { await downloadFromApi(`/api/memos/${fileName}/download`, "memo.txt"); }
    catch (err) { showToast(err.message); }
  });

  setActivePage(session?.authorized ? pageFromLocation() : "login", { skipHistory: true });

  // Drag & Drop
  const filesSection = document.querySelector("#files");
  if (filesSection) {
    filesSection.addEventListener("dragover", e => {
      e.preventDefault();
      filesSection.classList.add("drag-over");
    });
    filesSection.addEventListener("dragleave", () => {
      filesSection.classList.remove("drag-over");
    });
    filesSection.addEventListener("drop", e => {
      e.preventDefault();
      filesSection.classList.remove("drag-over");
      if (e.dataTransfer.files.length) {
        uploadSelectedFiles({ files: e.dataTransfer.files });
      }
    });
  }

  // Memo Auto-save (Debounced)
  let autoSaveTimeout;
  document.querySelector("#memo-body")?.addEventListener("input", () => {
    if (!state.editingMemoFileName) return;
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
      saveMemo(true); // silent save
    }, 2000);
  });

  if (geminiSettingsSaveBtn) {
    if (geminiExchangeRateInput) geminiExchangeRateInput.value = localStorage.getItem("geminiExchangeRate") || "1400";
    if (geminiCostMultiplierInput) geminiCostMultiplierInput.value = localStorage.getItem("geminiCostMultiplier") || DEFAULT_GEMINI_COST_MULTIPLIER;

    geminiSettingsSaveBtn.addEventListener("click", async () => {
      if (geminiExchangeRateInput && geminiExchangeRateInput.value) {
        localStorage.setItem("geminiExchangeRate", geminiExchangeRateInput.value);
      }
      const multiplierValue = geminiCostMultiplierInput?.value || DEFAULT_GEMINI_COST_MULTIPLIER;
      localStorage.setItem("geminiCostMultiplier", multiplierValue);
      showToast("Gemini 요금 설정이 저장되었습니다.");
      await Promise.all([loadUsageSummary(), loadSettings()]);
    });
  }
}
bootstrap();
