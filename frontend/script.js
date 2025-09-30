// =============================
// PlagiCheck frontend script
// - text check
// - file check
// - drag & drop autostart
// =============================

// small helpers
const $ = (sel) => document.querySelector(sel);
function setYear() {
  const y = $("#year");
  if (y) y.textContent = new Date().getFullYear();
}
function withLoading(btn, label, fn) {
  return async (...args) => {
    let original;
    if (btn) {
      original = btn.textContent;
      btn.disabled = true;
      btn.textContent = label || "Проверяем…";
    }
    try {
      return await fn(...args);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = original ?? "Проверить";
      }
    }
  };
}
async function postForm(url, formData) {
  const res = await fetch(url, { method: "POST", body: formData });
  let data = null;
  try { data = await res.json(); } catch { /* ignore */ }
  if (!res.ok) {
    const msg = (data && data.detail) ? data.detail : "Ошибка API";
    throw new Error(msg);
  }
  return data;
}
function validateFile(file) {
  if (!(file instanceof File)) return "Выберите файл.";
  const allowed = [
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ];
  const extOk  = /\.(txt|pdf|docx?)$/i.test(file.name);
  const mimeOk = !file.type || allowed.includes(file.type); // у некоторых браузеров MIME пустой
  if (!(extOk && mimeOk)) return "Допустимы только TXT, DOC, DOCX, PDF.";
  const max = 10 * 1024 * 1024; // 10 MB
  if (file.size > max) return "Файл слишком большой (лимит 10 МБ).";
  return null;
}

// core UI refs (keep IDs in index.html in sync!)
let textForm, textBtn, textResult, textReportLink;
let fileForm, fileInput, fileBtn, fileResult, fileReportLink, dropzone;

document.addEventListener("DOMContentLoaded", () => {
  setYear();

  // grab elements
  textForm = $("#textForm");
  textBtn = $("#textBtn");
  textResult = $("#textResult");
  textReportLink = $("#textReportLink");

  fileForm = $("#fileForm");
  fileInput = $("#fileInput");
  fileBtn = $("#fileBtn");
  fileResult = $("#fileResult");
  fileReportLink = $("#fileReportLink");
  dropzone = $("#dropzone");

  // === TEXT FORM ===
  if (textForm) {
    textForm.addEventListener(
      "submit",
      withLoading(textBtn, "Проверяем…", async (e) => {
        e.preventDefault();
        textResult.textContent = "";
        if (textReportLink) textReportLink.style.display = "none";

        const formData = new FormData(textForm);
        const txt = (formData.get("text") || "").toString().trim();
        if (!txt) {
          textResult.textContent = "Введите текст для проверки.";
          return;
        }

        try {
          const data = await postForm("/api/check-text", formData);
          textResult.innerHTML =
            `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · ` +
            `Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;

          if (data.report_id && textReportLink) {
            textReportLink.href = `/api/report/${data.report_id}`;
            textReportLink.textContent = "Скачать PDF-отчёт";
            textReportLink.style.display = "inline";
          }

          if (window.plausible) window.plausible("CheckText");
        } catch (err) {
          textResult.textContent = err.message || "Не удалось выполнить проверку.";
        }
      })
    );
  }

  // helper to run file check (used by submit & drop)
  const runFileCheck = withLoading(fileBtn, "Проверяем…", async (file, announceEl) => {
    if (!file) {
      if (fileResult) fileResult.textContent = "Выберите файл.";
      return;
    }
    const err = validateFile(file);
    if (err) {
      if (announceEl) announceEl.textContent = err;
      if (fileResult) fileResult.textContent = err;
      return;
    }

    try {
      const fd = new FormData();
      fd.append("file", file);
      const data = await postForm("/api/check-file", fd);

      if (fileResult) {
        fileResult.innerHTML =
          `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · ` +
          `Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
      }
      if (data.report_id && fileReportLink) {
        fileReportLink.href = `/api/report/${data.report_id}`;
        fileReportLink.textContent = "Скачать PDF-отчёт";
        fileReportLink.style.display = "inline";
      }

      if (announceEl) announceEl.textContent = `Готово: ${file.name}`;
      if (window.plausible) window.plausible("CheckFile");
    } catch (err) {
      if (fileResult) fileResult.textContent = err.message || "Не удалось проверить файл.";
      if (announceEl) announceEl.textContent = err.message || "Ошибка при проверке.";
    }
  });

  // === FILE FORM (click "Проверить файл") ===
  if (fileForm && fileInput) {
    fileForm.addEventListener(
      "submit",
      async (e) => {
        e.preventDefault();
        if (fileReportLink) fileReportLink.style.display = "none";
        if (fileResult) fileResult.textContent = "";

        const file = fileInput.files && fileInput.files[0];
        await runFileCheck(file, null);
      }
    );
  }

  // === DRAG & DROP (autostart) ===
  if (dropzone && fileInput) {
    // prevent browser from opening file on drop outside the zone
    ["dragover", "drop"].forEach((ev) =>
      document.addEventListener(ev, (e) => { e.preventDefault(); })
    );

    ["dragenter", "dragover"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault(); e.stopPropagation();
        dropzone.classList.add("drag");
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault(); e.stopPropagation();
        dropzone.classList.remove("drag");
      })
    );

    dropzone.addEventListener("drop", async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;

      const file = files[0];
      // sync to hidden file input so the state matches UI
      try { fileInput.files = files; } catch { /* Safari may ignore */ }

      const p = dropzone.querySelector("p");
      if (p) p.textContent = `Выбран файл: ${file.name}, проверяем…`;
      if (fileReportLink) fileReportLink.style.display = "none";
      if (fileResult) fileResult.textContent = "";

      await runFileCheck(file, p);
    });
  }

});
