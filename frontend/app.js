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
};

const fileList = document.querySelector("#file-list");
const memoList = document.querySelector("#memo-list");
const fileCount = document.querySelector("#file-count");
const memoCount = document.querySelector("#memo-count");
const toast = document.querySelector("#toast");
const sessionChip = document.querySelector("#session-chip");

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

function setSessionChip(session) {
  state.session = session;
  sessionChip.classList.remove("is-authorized", "is-locked");
  if (session?.authorized) {
    sessionChip.textContent =
      session.auth_method === "passkey" ? "Passkey 인증됨" : "Google 인증됨";
    sessionChip.classList.add("is-authorized");
    return;
  }
  sessionChip.textContent = "인증 필요";
  sessionChip.classList.add("is-locked");
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
  fileList.innerHTML = state.files
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
}

function renderMemos() {
  memoList.innerHTML = state.memos
    .map(
      (memo, index) => `
        <article class="memo-card">
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
}

function renderPresets() {
  const row = document.querySelector("#preset-row");
  row.innerHTML = presets
    .map((preset) => `<button type="button" data-preset="${preset}">${preset}</button>`)
    .join("");
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
    const removed = state.files[index];
    if (!removed?.blobName) {
      state.files.splice(index, 1);
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
    const file = state.files[index];
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
    const memo = state.memos[Number(openButton.dataset.memoOpen)];
    try {
      const data = await apiJson(`/api/memos/${encodeURIComponent(memo.fileName)}`);
      memo.title = data.memo.title;
      memo.body = data.memo.content || "내용이 비어 있습니다.";
      renderMemos();
      showToast("메모를 불러왔습니다.");
    } catch (error) {
      showToast(error.message);
    }
  }

  if (deleteButton) {
    const memo = state.memos[Number(deleteButton.dataset.memoDelete)];
    try {
      await postJson("/api/memos/delete", { file_name: memo.fileName });
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
  const title = titleInput.value.trim();
  const body = bodyInput.value.trim();

  if (!title || !body) {
    showToast("제목과 내용을 모두 입력하세요.");
    return;
  }

  try {
    await postJson("/api/memos", { title, content: body });
    titleInput.value = "";
    bodyInput.value = "";
    await loadMemos();
    showToast("메모가 저장됐습니다.");
  } catch (error) {
    showToast(error.message);
  }
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

  button.disabled = true;
  button.textContent = "분석 중";
  result.innerHTML = `
    <span>AI result</span>
    <h3>분석 중</h3>
    <p>Gemini가 요청을 정리하고 있습니다.</p>
  `;
  try {
    const data = await postJson("/api/ai/analyze", { prompt });
    result.innerHTML = `
      <span>AI result</span>
      <h3>분석 결과</h3>
      <p>${escapeHtml(data.result)}</p>
    `;
    showToast("AI 분석이 완료됐습니다.");
  } catch (error) {
    result.innerHTML = `
      <span>AI result</span>
      <h3>분석 대기</h3>
      <p>${escapeHtml(error.message)}</p>
    `;
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "분석 시작";
  }
});

async function bootstrap() {
  renderFiles();
  renderMemos();
  renderPresets();
  const session = await loadSession();
  if (session?.authorized) {
    await Promise.all([loadFiles(), loadMemos()]);
  }
}

bootstrap();
