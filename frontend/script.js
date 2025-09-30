// ==== утилиты ====
const $ = (sel) => document.querySelector(sel);
const yearEl = $("#year");
if (yearEl) yearEl.textContent = new Date().getFullYear();

function withLoading(btn, fn) {
  return async (...args) => {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Проверяем…";
    try {
      return await fn(...args);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  };
}

async function postForm(url, formData) {
  const res = await fetch(url, { method: "POST", body: formData });
  let data = null;
  try { data = await res.json(); } catch {}
  if (!res.ok) {
    const msg = (data && data.detail) ? data.detail : "Ошибка API";
    throw new Error(msg);
  }
  return data;
}

// ==== селекторы ====
// Текст
const textForm = $("#textForm");
const textBtn = $("#textBtn");
const textResult = $("#textResult");
const textReportLink = $("#textReportLink");

// Файл
const fileForm = $("#fileForm");
const fileInput = $("#fileInput");
const fileBtn = $("#fileBtn");
const fileResult = $("#fileResult");
const fileReportLink = $("#fileReportLink");

// Валидация файла (тип/размер)
function validateFile(file) {
  if (!file) return "Выберите файл.";
  const allowed = [
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ];
  // MIME может быть пустым — тогда проверяем имя
  const extOk = /\.(txt|pdf|docx?)$/i.test(file.name);
  const mimeOk = !file.type || allowed.includes(file.type);
  if (!(extOk && mimeOk)) return "Допустимы только TXT, DOC, DOCX, PDF.";
  const max = 10 * 1024 * 1024; // 10 МБ
  if (file.size > max) return "Файл слишком большой (лимит 10 МБ).";
  return null;
}

// ==== обработчик формы текста ====
if (textForm) {
  textForm.addEventListener("submit", withLoading(textBtn, async (e) => {
    e.preventDefault();
    textResult.textContent = "";
    textReportLink.style.display = "none";

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
      const id = data.report_id;
      if (id) {
        textReportLink.href = `/api/report/${id}`;
        textReportLink.textContent = "Скачать PDF-отчёт";
        textReportLink.style.display = "inline";
      }
    } catch (err) {
      textResult.textContent = err.message || "Не удалось выполнить проверку.";
    }
  }));
}

// ==== обработчик формы файла ====
if (fileForm) {
  fileForm.addEventListener("submit", withLoading(fileBtn, async (e) => {
    e.preventDefault();
    fileResult.textContent = "";
    fileReportLink.style.display = "none";

    const file = fileInput && fileInput.files && fileInput.files[0];
    const err = validateFile(file);
    if (err) { fileResult.textContent = err; return; }

    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await postForm("/api/check-file", formData);
      fileResult.innerHTML =
        `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · ` +
        `Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
      const id = data.report_id;
      if (id) {
        fileReportLink.href = `/api/report/${id}`;
        fileReportLink.textContent = "Скачать PDF-отчёт";
        fileReportLink.style.display = "inline";
      }
    } catch (err) {
      fileResult.textContent = err.message || "Не удалось проверить файл.";
    }
  }));
}

// ==== drag & drop ====
const dropzone = $("#dropzone");
if (dropzone && fileInput) {
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
  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (!files || !files.length) return;
    fileInput.files = files;
    const msg = validateFile(files[0]);
    const p = dropzone.querySelector("p");
    if (p) p.textContent = msg ? msg : `Выбран файл: ${files[0].name}`;
  });
}
