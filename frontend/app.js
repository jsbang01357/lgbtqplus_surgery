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
const fileListStatus = document.querySelector("#file-list-status");
const memoListStatus = document.querySelector("#memo-list-status");
const memoSaveButton = document.querySelector("#memo-save-button");
const saveAiMemoButton = document.querySelector("#save-ai-memo");
const toolOutput = document.querySelector("#tool-output");
const heroFileSummary = document.querySelector("#hero-file-summary");
const heroFileList = document.querySelector("#hero-file-list");
const heroMemoPreview = document.querySelector("#hero-memo-preview");
const aiFileSources = document.querySelector("#ai-file-sources");
const aiMemoSources = document.querySelector("#ai-memo-sources");
const aiFileStatus = document.querySelector("#ai-file-status");
const aiMemoStatus = document.querySelector("#ai-memo-status");

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
}

function updateHeroPreview() {
  heroFileSummary.textContent = `${state.files.length} files`;
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
  const firstMemo = state.memos[0];
  heroMemoPreview.textContent = firstMemo
    ? `${firstMemo.title}: ${firstMemo.body}`
    : "최근 메모가 없습니다.";
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
    button.textContent = busyText;
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

function setSessionChip(session) {
  state.session = session;
  sessionChip.classList.remove("is-authorized", "is-locked");
  if (session?.authorized) {
    sessionChip.textContent =
      session.auth_method === "passkey" ? "Passkey 인증됨" : "Google 인증됨";
    sessionChip.classList.add("is-authorized");
    document.body.classList.add("is-authorized");
    return;
  }
  sessionChip.textContent = "인증 필요";
  sessionChip.classList.add("is-locked");
  document.body.classList.remove("is-authorized");
}

async function loadSession() {
  try {
    const session = await apiJson("/api/session");
    setSessionChip(session);
    return session;
  } catch {
    sessionChip.textContent = "오프라인 미리보기";
    sessionChip.classList.add("is-locked");
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
    showToast(error.message);
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
    aiMonthCost.textContent = usage.month_cost_label || "-";
    aiModelLabel.textContent = usage.model || "Gemini";
    storageStatusLabel.textContent = `${usage.request_count || 0} AI 요청`;
  } catch {
    aiMonthCost.textContent = "-";
    aiModelLabel.textContent = "인증 후 표시";
    storageStatusLabel.textContent = "Cloud Run";
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
    await continueWithGoogleAuth();
    return;
  }
  try {
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
    await continueWithGoogleAuth();
    return;
  }
  try {
    const options = await postJson("/api/auth/passkey/login/options");
    const credential = await navigator.credentials.get({
      publicKey: prepareRequestOptions(options),
    });
    await postJson("/api/auth/passkey/login/verify", serializeCredential(credential));
    await loadSession();
    await Promise.all([loadFiles(), loadMemos()]);
    showToast("패스키 로그인 완료");
  } catch (error) {
    showToast(error.message);
  }
}

async function continueWithGoogleAuth() {
  try {
    const response = await fetch("/api/session");
    const data = await response.json();
    setSessionChip(data);
    if (data.authorized && data.auth_method === "google") {
      await Promise.all([loadFiles(), loadMemos()]);
      showToast("Google 인증으로 계속합니다.");
      return;
    }
    if (data.cloudflare_access?.allowed && data.google_auth_fallback_allowed) {
      showToast("허용된 Google 계정으로 인증되었습니다.");
      return;
    }
    showToast("jsbang01357@gmail.com Google 인증이 필요합니다.");
  } catch (error) {
    showToast(error.message || "Google 인증 상태를 확인하지 못했습니다.");
  }
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
    .join("") || `<p class="empty-state">아직 업로드된 파일이 없습니다.</p>`;
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
    .join("") || `<p class="empty-state">아직 저장된 메모가 없습니다.</p>`;
  memoCount.textContent = String(state.memos.length);
  memoListStatus.textContent = state.memoQuery
    ? `${visibleMemos.length}개 표시 · 전체 ${state.memos.length}개`
    : `전체 ${state.memos.length}개`;
  updateHeroPreview();
}

function renderPresets() {
  const row = document.querySelector("#preset-row");
  row.innerHTML = presets
    .map((preset) => `<button type="button" data-preset="${preset}">${preset}</button>`)
    .join("");
}

function renderAiSources() {
  const realFiles = state.files.filter((file) => file.blobName);
  const realMemos = state.memos.filter((memo) => memo.fileName);
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
  updateAiSourceStatus();
}

function updateAiSourceStatus() {
  const fileCount = selectedValues("[data-ai-file]").length;
  const memoCount = selectedValues("[data-ai-memo]").length;
  aiFileStatus.textContent = fileCount ? `${fileCount}개 선택` : "선택 없음";
  aiMemoStatus.textContent = memoCount ? `${memoCount}개 선택` : "선택 없음";
}

function renderTool(tool) {
  const templates = {
    cleaner: `
      <div class="tool-panel">
        <h3>텍스트 클리너</h3>
        <textarea id="tool-cleaner-input" rows="7" placeholder="정리할 텍스트를 붙여넣으세요."></textarea>
        <div class="form-actions">
          <button class="button button-primary" id="tool-cleaner-run" type="button">정리</button>
          <button class="button button-secondary" id="tool-copy-output" type="button">결과 복사</button>
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
          <article><span>줄</span><strong>0</strong></article>
        </div>
      </div>
    `,
    settlement: `
      <div class="tool-panel">
        <h3>정산 계산기</h3>
        <textarea id="tool-settlement-input" rows="7">지송 32000&#10;민수 18000&#10;서연 0</textarea>
        <button class="button button-primary" id="tool-settlement-run" type="button">계산</button>
        <pre id="tool-settlement-result">이름과 금액을 줄마다 입력하세요.</pre>
      </div>
    `,
    storage: `
      <div class="tool-panel">
        <h3>저장소 상태</h3>
        <div class="tool-metrics">
          <article><span>파일</span><strong>${state.files.length}</strong></article>
          <article><span>메모</span><strong>${state.memos.length}</strong></article>
          <article><span>저장소</span><strong>GCS</strong></article>
          <article><span>런타임</span><strong>Cloud Run</strong></article>
        </div>
      </div>
    `,
    access: `
      <div class="tool-panel">
        <h3>접속 상태</h3>
        <pre>${escapeHtml(JSON.stringify(state.session || {}, null, 2))}</pre>
      </div>
    `,
  };
  toolOutput.innerHTML = templates[tool] || templates.cleaner;
  bindToolPanel(tool);
  toolOutput.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function bindToolPanel(tool) {
  if (tool === "cleaner") {
    document.querySelector("#tool-cleaner-run").addEventListener("click", () => {
      const raw = document.querySelector("#tool-cleaner-input").value;
      const cleaned = raw
        .replace(/\r/g, "")
        .split("\n")
        .map((line) => line.replace(/\s+/g, " ").trim())
        .filter(Boolean)
        .join("\n");
      document.querySelector("#tool-result").textContent = cleaned || "정리할 텍스트가 없습니다.";
    });
    document.querySelector("#tool-copy-output").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(document.querySelector("#tool-result").textContent);
        showToast("결과를 복사했습니다.");
      } catch {
        showToast("브라우저가 클립보드 복사를 허용하지 않았습니다.");
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
      document.querySelector("#tool-counter-result").innerHTML = `
        <article><span>공백 포함</span><strong>${text.length}</strong></article>
        <article><span>공백 제외</span><strong>${text.replace(/\s/g, "").length}</strong></article>
        <article><span>단어</span><strong>${words}</strong></article>
        <article><span>줄</span><strong>${text ? text.split(/\n/).length : 0}</strong></article>
      `;
    };
    input.addEventListener("input", render);
  }
  if (tool === "settlement") {
    document.querySelector("#tool-settlement-run").addEventListener("click", () => {
      const rows = document.querySelector("#tool-settlement-input").value
        .split("\n")
        .map((line) => line.trim().split(/\s+/))
        .filter((parts) => parts.length >= 2)
        .map(([name, amount]) => ({ name, amount: Number(amount.replace(/,/g, "")) || 0 }));
      if (!rows.length) {
        document.querySelector("#tool-settlement-result").textContent = "정산할 항목이 없습니다.";
        return;
      }
      const total = rows.reduce((sum, row) => sum + row.amount, 0);
      const share = Math.round(total / rows.length);
      const result = rows
        .map((row) => `${row.name}: ${row.amount - share >= 0 ? "+" : ""}${(row.amount - share).toLocaleString()}원`)
        .join("\n");
      document.querySelector("#tool-settlement-result").textContent =
        `총액 ${total.toLocaleString()}원 · 1인 ${share.toLocaleString()}원\n\n${result}`;
    });
  }
}

document.querySelector("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#file-input");
  const selected = Array.from(input.files || []);
  if (!selected.length) {
    showToast("추가할 파일을 먼저 선택하세요.");
    return;
  }

  try {
    const formData = new FormData();
    selected.forEach((file) => formData.append("files", file));
    await apiJson("/api/files", { method: "POST", body: formData });
    input.value = "";
    await loadFiles();
    showToast(`${selected.length}개 파일이 업로드됐습니다.`);
  } catch (error) {
    showToast(error.message);
  }
});

fileList.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest("[data-delete]");
  const downloadButton = event.target.closest("[data-download]");

  if (deleteButton) {
    const index = Number(deleteButton.dataset.delete);
    const removed = getFilteredFiles()[index];
    if (!removed?.blobName) {
      const originalIndex = state.files.indexOf(removed);
      if (originalIndex >= 0) {
        state.files.splice(originalIndex, 1);
      }
      renderFiles();
      showToast(`${removed?.name || "파일"} 삭제됨`);
      return;
    }
    try {
      await postJson("/api/files/delete", { blob_name: removed.blobName });
      await loadFiles();
      showToast(`${removed.name} 삭제됨`);
    } catch (error) {
      showToast(error.message);
    }
  }

  if (downloadButton) {
    const index = Number(downloadButton.dataset.download);
    const file = getFilteredFiles()[index];
    if (file.downloadUrl) {
      window.location.assign(file.downloadUrl);
      return;
    }
    showToast(`${file.name} 다운로드 준비`);
  }
});

document.querySelector("#download-all").addEventListener("click", async () => {
  try {
    await downloadFromApi("/api/files/zip", "jisong-cloud-files.zip");
    showToast("전체 파일 ZIP 다운로드를 시작합니다.");
  } catch (error) {
    showToast(error.message);
  }
});

document.querySelector("#passkey-register").addEventListener("click", registerPasskey);
document.querySelector("#passkey-login").addEventListener("click", loginWithPasskey);
document.querySelector("#google-auth-fallback").addEventListener("click", continueWithGoogleAuth);
document.querySelector("#file-search").addEventListener("input", (event) => {
  state.fileQuery = event.target.value;
  renderFiles();
});
document.querySelector("#memo-search").addEventListener("input", (event) => {
  state.memoQuery = event.target.value;
  renderMemos();
});
document.querySelector("#download-memos").addEventListener("click", async () => {
  try {
    await downloadFromApi("/api/memos/zip", "jisong-cloud-memos.zip");
    showToast("메모 ZIP 다운로드를 시작합니다.");
  } catch (error) {
    showToast(error.message);
  }
});

memoList.addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-memo-open]");
  const deleteButton = event.target.closest("[data-memo-delete]");

  if (openButton) {
    const memo = getFilteredMemos()[Number(openButton.dataset.memoOpen)];
    try {
      const data = await apiJson(`/api/memos/${encodeURIComponent(memo.fileName)}`);
      memo.title = data.memo.title;
      memo.body = data.memo.content || "내용이 비어 있습니다.";
      document.querySelector("#memo-title").value = memo.title;
      document.querySelector("#memo-body").value = data.memo.content || "";
      document.querySelector("#memo-file-name").value = memo.fileName;
      state.editingMemoFileName = memo.fileName;
      memoSaveButton.textContent = "메모 수정";
      renderMemos();
      showToast("메모를 불러왔습니다.");
    } catch (error) {
      showToast(error.message);
    }
  }

  if (deleteButton) {
    const memo = getFilteredMemos()[Number(deleteButton.dataset.memoDelete)];
    try {
      await postJson("/api/memos/delete", { file_name: memo.fileName });
      if (state.editingMemoFileName === memo.fileName) {
        resetMemoForm();
      }
      await loadMemos();
      showToast("메모가 삭제됐습니다.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

document.querySelector("#memo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const titleInput = document.querySelector("#memo-title");
  const bodyInput = document.querySelector("#memo-body");
  const fileNameInput = document.querySelector("#memo-file-name");
  const title = titleInput.value.trim();
  const body = bodyInput.value.trim();

  if (!title || !body) {
    showToast("제목과 내용을 모두 입력하세요.");
    return;
  }

  try {
    const isEdit = Boolean(fileNameInput.value);
    await postJson("/api/memos", {
      title,
      content: body,
      file_name: fileNameInput.value || undefined,
    });
    resetMemoForm();
    await loadMemos();
    showToast(isEdit ? "메모가 수정됐습니다." : "메모가 저장됐습니다.");
  } catch (error) {
    showToast(error.message);
  }
});

document.querySelector("#memo-reset-button").addEventListener("click", () => {
  resetMemoForm();
  renderMemos();
});

document.querySelector("#preset-row").addEventListener("click", (event) => {
  const button = event.target.closest("[data-preset]");
  if (!button) return;
  const prompt = document.querySelector("#ai-prompt");
  prompt.value = `${prompt.value.trim()}\n\n${button.dataset.preset} 형식으로 정리해줘.`;
  prompt.focus();
});

document.querySelector("#run-ai").addEventListener("click", async () => {
  const prompt = document.querySelector("#ai-prompt").value.trim();
  const result = document.querySelector("#ai-result");
  const button = document.querySelector("#run-ai");
  if (!prompt) {
    showToast("분석할 요청을 입력하세요.");
    return;
  }

  setBusy(button, "분석 중", true);
  saveAiMemoButton.disabled = true;
  result.innerHTML = `
    <span>AI result</span>
    <h3>분석 중</h3>
    <p>Gemini가 요청을 정리하고 있습니다.</p>
  `;
  try {
    const data = await postJson("/api/ai/analyze", {
      prompt,
      blob_names: selectedValues("[data-ai-file]"),
      memo_file_names: selectedValues("[data-ai-memo]"),
    });
    result.innerHTML = `
      <span>AI result</span>
      <h3>분석 결과</h3>
      <p>${escapeHtml(data.result)}</p>
    `;
    state.lastAiResult = data.result;
    saveAiMemoButton.disabled = false;
    await loadUsageSummary();
    showToast("AI 분석이 완료됐습니다.");
  } catch (error) {
    state.lastAiResult = "";
    saveAiMemoButton.disabled = true;
    result.innerHTML = `
      <span>AI result</span>
      <h3>분석 대기</h3>
      <p>${escapeHtml(error.message)}</p>
    `;
    showToast(error.message);
  } finally {
    setBusy(button, "분석 중", false);
  }
});

saveAiMemoButton.addEventListener("click", async () => {
  if (!state.lastAiResult) {
    showToast("저장할 AI 결과가 없습니다.");
    return;
  }
  setBusy(saveAiMemoButton, "저장 중", true);
  try {
    await postJson("/api/memos", {
      title: `AI 분석 ${new Intl.DateTimeFormat("ko-KR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date())}`,
      content: state.lastAiResult,
    });
    await loadMemos();
    showToast("AI 결과를 메모로 저장했습니다.");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(saveAiMemoButton, "저장 중", false);
    saveAiMemoButton.disabled = !state.lastAiResult;
  }
});

document.querySelector(".tool-grid").addEventListener("click", (event) => {
  const card = event.target.closest("[data-tool]");
  if (!card) return;
  document.querySelectorAll(".tool-card").forEach((item) => item.classList.remove("is-selected"));
  card.classList.add("is-selected");
  renderTool(card.dataset.tool);
});

document.querySelector(".ai-source-grid").addEventListener("change", updateAiSourceStatus);

async function bootstrap() {
  renderFiles();
  renderMemos();
  updateHeroPreview();
  renderPresets();
  renderAiSources();
  renderTool("cleaner");
  const session = await loadSession();
  if (session?.authorized) {
    await Promise.all([loadFiles(), loadMemos(), loadUsageSummary()]);
  }
}

bootstrap();
