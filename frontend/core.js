// ====== Core (общий) ======
const $ = (sel) => document.querySelector(sel);

async function includeHTML(id, file, onDone) {
  const el = document.getElementById(id);
  if (!el) return;
  try {
    const url = file.startsWith("/") ? file : `/${file}`;
    const resp = await fetch(url, { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    el.innerHTML = await resp.text();
    if (typeof onDone === "function") onDone();
  } catch (e) {
    console.error(`[includeHTML] ${file}:`, e);
  }
}

function setYear() {
  const y = document.querySelector("#year");
  if (y) y.textContent = new Date().getFullYear();
}

// Небольшие утилиты можно держать тут,
// чтобы ими мог пользоваться checker.js
function withLoading(btn, label, fn) {
  return async (...args) => {
    let original;
    if (btn) {
      original = btn.textContent;
      btn.disabled = true;
      btn.textContent = label || "Проверяем…";
    }
    try { return await fn(...args); }
    finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = original ?? "Готово";
      }
    }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  includeHTML("site-header", "/header.html");
  includeHTML("site-footer", "/footer.html", setYear);
});
