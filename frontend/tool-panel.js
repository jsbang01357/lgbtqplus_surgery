function renderToolTemplate(tool) {
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
  return templates[tool] || templates.cleaner;
}

function bindToolPanel(tool, deps) {
  const { showToast, setBusy, postJson, downloadPostBlob } = deps;

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

      const people = peopleText.split(/[,\n]/).map((p) => p.trim()).filter(Boolean);
      const lines = expenseText.split("\n").filter((l) => l.trim());
      const expenses = lines.map((line) => {
        const parts = line.trim().split(/\s+/);
        let amount = 0;
        let payer = "";
        let item = "";
        parts.forEach((p) => {
          const num = parseInt(p.replace(/,/g, ""));
          if (!Number.isNaN(num) && num > 100) amount = num;
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
          .map((r) => `${r.사람}: ${r.잔액 >= 0 ? "+" : ""}${r.잔액.toLocaleString()}원 (${r["낸 금액"]}원 냄)`)
          .join("\n");
        document.querySelector("#tool-settlement-transfers").textContent = data.transfer_rows.length
          ? data.transfer_rows.map((t) => `${t["보내는 사람"]} → ${t["받는 사람"]}: ${t["금액"].toLocaleString()}원`).join("\n")
          : "추가 송금이 필요 없습니다.";
        if (data.errors && data.errors.length) showToast(data.errors[0]);
      } catch (error) {
        showToast(error.message);
      } finally {
        setBusy(runBtn, "계산 중", false);
      }
    });
  }
}

export function renderToolPanel(tool, deps = {}) {
  const toolOutput = document.querySelector("#tool-output");
  if (!toolOutput) return;
  toolOutput.innerHTML = renderToolTemplate(tool);
  bindToolPanel(tool, deps);
  toolOutput.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
