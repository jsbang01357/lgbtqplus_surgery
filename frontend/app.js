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
};

const fileList = document.querySelector("#file-list");
const memoList = document.querySelector("#memo-list");
const fileCount = document.querySelector("#file-count");
const memoCount = document.querySelector("#memo-count");
const toast = document.querySelector("#toast");

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
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "요청에 실패했습니다.");
  }
  return data;
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
    showToast("패스키 로그인 완료");
  } catch (error) {
    showToast(error.message);
  }
}

async function continueWithGoogleAuth() {
  try {
    const response = await fetch("/api/session");
    const data = await response.json();
    if (data.authorized && data.auth_method === "google") {
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
          <span class="file-icon">${file.type}</span>
          <div>
            <strong>${file.name}</strong>
            <small>${file.updated} · ${file.size}</small>
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
    .join("");
  fileCount.textContent = String(state.files.length);
}

function renderMemos() {
  memoList.innerHTML = state.memos
    .map(
      (memo) => `
        <article class="memo-card">
          <h3>${memo.title}</h3>
          <p>${memo.body}</p>
        </article>
      `,
    )
    .join("");
  memoCount.textContent = String(state.memos.length);
}

function renderPresets() {
  const row = document.querySelector("#preset-row");
  row.innerHTML = presets
    .map((preset) => `<button type="button" data-preset="${preset}">${preset}</button>`)
    .join("");
}

document.querySelector("#upload-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#file-input");
  const selected = Array.from(input.files || []);
  if (!selected.length) {
    showToast("추가할 파일을 먼저 선택하세요.");
    return;
  }

  const now = new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());

  selected.forEach((file) => {
    const extension = file.name.split(".").pop()?.toUpperCase() || "FILE";
    state.files.unshift({
      name: file.name,
      type: extension.slice(0, 3),
      size: `${Math.max(file.size / 1024 / 1024, 0.1).toFixed(1)} MB`,
      updated: `오늘 ${now}`,
    });
  });
  input.value = "";
  renderFiles();
  showToast(`${selected.length}개 파일이 목록에 추가됐습니다.`);
});

fileList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete]");
  const downloadButton = event.target.closest("[data-download]");

  if (deleteButton) {
    const index = Number(deleteButton.dataset.delete);
    const [removed] = state.files.splice(index, 1);
    renderFiles();
    showToast(`${removed.name} 삭제됨`);
  }

  if (downloadButton) {
    const index = Number(downloadButton.dataset.download);
    showToast(`${state.files[index].name} 다운로드 준비`);
  }
});

document.querySelector("#download-all").addEventListener("click", () => {
  showToast("전체 ZIP 다운로드 준비");
});

document.querySelector("#passkey-register").addEventListener("click", registerPasskey);
document.querySelector("#passkey-login").addEventListener("click", loginWithPasskey);
document.querySelector("#google-auth-fallback").addEventListener("click", continueWithGoogleAuth);

document.querySelector("#memo-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const titleInput = document.querySelector("#memo-title");
  const bodyInput = document.querySelector("#memo-body");
  const title = titleInput.value.trim();
  const body = bodyInput.value.trim();

  if (!title || !body) {
    showToast("제목과 내용을 모두 입력하세요.");
    return;
  }

  state.memos.unshift({ title, body });
  titleInput.value = "";
  bodyInput.value = "";
  renderMemos();
  showToast("메모가 저장됐습니다.");
});

document.querySelector("#preset-row").addEventListener("click", (event) => {
  const button = event.target.closest("[data-preset]");
  if (!button) return;
  const prompt = document.querySelector("#ai-prompt");
  prompt.value = `${prompt.value.trim()}\n\n${button.dataset.preset} 형식으로 정리해줘.`;
  prompt.focus();
});

document.querySelector("#run-ai").addEventListener("click", () => {
  const prompt = document.querySelector("#ai-prompt").value.trim();
  const result = document.querySelector("#ai-result");
  if (!prompt) {
    showToast("분석할 요청을 입력하세요.");
    return;
  }

  result.innerHTML = `
    <span>AI result</span>
    <h3>분석 초안</h3>
    <p>요청을 바탕으로 핵심 요약, 발표 순서, 예상 질문을 분리해 정리했습니다. 실제 연결 시 Gemini와 비용 제한을 그대로 사용합니다.</p>
  `;
  showToast("AI 분석 초안이 생성됐습니다.");
});

renderFiles();
renderMemos();
renderPresets();
