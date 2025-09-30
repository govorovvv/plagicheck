// утилиты
const $ = (sel) => document.querySelector(sel);
const yearEl = $("#year");
if (yearEl) yearEl.textContent = new Date().getFullYear();

// генерация UUID для отчёта (беку всё равно — он генерит PDF "на лету")
function uuidv4() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// общее: блокировка кнопки + индикатор
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

// ТЕКСТ
textForm.addEventListener(
  "submit",
  withLoading(textBtn, async (e) => {
    e.preventDefault();
    textResult.textContent = "";
    textReportLink.style.display = "none";
    const data = await postForm("/api/check-text", formData);
    const formData = new FormData(textForm);
    const txt = (formData.get("text") || "").toString().trim();
    if (!txt) {
      textResult.textContent = "Введите текст для проверки.";
      return;
    }

    try {
      const res = await fetch("/api/check-text", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Ошибка API");
      const data = await res.json();

      textResult.innerHTML = `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
      const id = data.report_id;
      if (id) {
        textReportLink.href = `/api/report/${id}`;
        textReportLink.style.display = "inline";
        textReportLink.textContent = "Скачать PDF-отчёт";
      }
    } catch (err) {
	textResult.textContent = err.message || "Не удалось выполнить проверку.";
    }
  })
);

// ФАЙЛ
fileForm.addEventListener(
  "submit",
  withLoading(fileBtn, async (e) => {
    e.preventDefault();
    fileResult.textContent = "";
    fileReportLink.style.display = "none";
    const data = await postForm("/api/check-file", formData);
    const file = fileInput.files[0];
    const err = validateFile(file);
    if (err) { fileResult.textContent = err; return; }

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/check-file", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Ошибка API");
      const data = await res.json();

      fileResult.innerHTML = `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
      const id = data.report_id;
      if (id) {
        fileReportLink.href = `/api/report/${id}`;
        fileReportLink.style.display = "inline";
        fileReportLink.textContent = "Скачать PDF-отчёт";
      }
   } catch (err) {
	fileResult.textContent = err.message || "Не удалось проверить файл.";
   }
  })
);


// === Drag & Drop ===
const dropzone = $("#dropzone");
if (dropzone && fileInput) {
  ;["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("drag");
    })
  );
  ;["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("drag");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (!files || !files.length) return;
    fileInput.files = files;
    const err = validateFile(files[0]);
    dropzone.querySelector("p").textContent = err ? err : `Выбран файл: ${files[0].name}`;
  });
}
