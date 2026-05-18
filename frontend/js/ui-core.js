import { loadSession } from "./auth.js";
import { loadFiles, renderFiles } from "./files.js";
import { loadMemos, renderMemos } from "./memos.js";
import { loadUsageSummary } from "./ai.js";

// DOM Elements
const toast = document.querySelector("#toast");
const navTime = document.querySelector("#nav-time");

export function showToast(message) {
  if (toast) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    setTimeout(() => {
      toast.classList.remove("is-visible");
    }, 3000);
  }
}

export function setBusy(button, originalText, isBusy) {
  if (!button) return;
  if (isBusy) {
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>${originalText}`;
  } else {
    button.disabled = false;
    button.innerHTML = originalText;
  }
}

export function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function formatBytes(size = 0) {
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

export function formatUpdated(value) {
  if (!value) return "시간 정보 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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

const pageIds = ["login", "home", "files", "memos", "ai", "tools", "settings"];
const defaultPage = "home";

export function setActivePage(pageId) {
  if (!pageIds.includes(pageId)) pageId = defaultPage;

  pageIds.forEach((id) => {
    const section = document.querySelector(`[data-page="${id}"]`);
    if (section) {
      if (id === pageId) {
        section.removeAttribute("hidden");
        section.classList.add("fade-in");
        setTimeout(() => section.classList.remove("fade-in"), 300);
      } else {
        section.setAttribute("hidden", "true");
      }
    }
  });

  document.querySelectorAll("[data-route]").forEach((link) => {
    if (link.dataset.route === pageId) {
      link.classList.add("is-active");
    } else {
      link.classList.remove("is-active");
    }
  });

  document.documentElement.setAttribute("data-active-page", pageId);

  if (pageId === "login") {
    document.body.classList.remove("is-authorized");
  } else {
    document.body.classList.add("is-authorized");
    if (pageId === "files") renderFiles();
    if (pageId === "memos") renderMemos();
  }
}

export function initRouter() {
  document.addEventListener("click", (e) => {
    const link = e.target.closest("[data-route]");
    if (link) {
      e.preventDefault();
      const route = link.dataset.route;
      setActivePage(route);
      window.history.pushState({ page: route }, "", `/${route}`);
    }
  });

  window.addEventListener("popstate", (e) => {
    const route = e.state?.page || defaultPage;
    setActivePage(route);
  });
}
