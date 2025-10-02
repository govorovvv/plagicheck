// === include header/footer на каждой странице ===
async function includeHTML(id, file, onDone) {
   const el = document.getElementById(id);
   if (!el) return;
   try {
    const resp = await fetch(file.startsWith("/") ? file : `/${file}`);
     if (resp.ok) {
       el.innerHTML = await resp.text();
       if (typeof onDone === "function") onDone();
     } else {
       console.error("Include failed:", file, resp.status);
     }
   } catch (e) {
     console.error("Include failed:", file, e);
   }
 }
 

document.addEventListener("DOMContentLoaded", () => {
  includeHTML("site-header", "/header.html");
  includeHTML("site-footer", "/footer.html", () => {
     const y = document.querySelector("#year");
     if (y) y.textContent = new Date().getFullYear();
   });
 });


// =============================
// PlagiCheck frontend script (no drag&drop)
// =============================
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
  try { data = await res.json(); } catch {}
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
  const mimeOk = !file.type || allowed.includes(file.type);
  if (!(extOk && mimeOk)) return "Допустимы только TXT, DOC, DOCX, PDF.";
  const max = 10 * 1024 * 1024; // 10 MB
  if (file.size > max) return "Файл слишком большой (лимит 10 МБ).";
  return null;
}

document.addEventListener("DOMContentLoaded", () => {
  setYear();

  // ---- ТЕКСТ ----
  const textForm = $("#textForm");
  const textBtn = $("#textBtn");
  const textResult = $("#textResult");
  const textReportLink = $("#textReportLink");

  if (textForm) {
    textForm.addEventListener(
      "submit",
      withLoading(textBtn, "Проверяем…", async (e) => {
        e.preventDefault();
        if (textReportLink) textReportLink.style.display = "none";
        if (textResult) textResult.textContent = "";

        const formData = new FormData(textForm);
        const txt = (formData.get("text") || "").toString().trim();
        if (!txt) { textResult.textContent = "Введите текст для проверки."; return; }

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

  // ---- ФАЙЛ ----
  const fileForm = $("#fileForm");
  const fileInput = $("#fileInput");
  const fileBtn = $("#fileBtn");
  const fileResult = $("#fileResult");
  const fileReportLink = $("#fileReportLink");

  if (fileForm && fileInput) {
    fileForm.addEventListener(
      "submit",
      withLoading(fileBtn, "Проверяем…", async (e) => {
        e.preventDefault();
        if (fileReportLink) fileReportLink.style.display = "none";
        if (fileResult) fileResult.textContent = "";

        const file = fileInput.files && fileInput.files[0];
        const err = validateFile(file);
        if (err) { fileResult.textContent = err; return; }

        try {
          const fd = new FormData();
          fd.append("file", file);
          const data = await postForm("/api/check-file", fd);

          fileResult.innerHTML =
            `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · ` +
            `Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
          if (data.report_id && fileReportLink) {
            fileReportLink.href = `/api/report/${data.report_id}`;
            fileReportLink.textContent = "Скачать PDF-отчёт";
            fileReportLink.style.display = "inline";
          }
          if (window.plausible) window.plausible("CheckFile");
        } catch (err) {
          fileResult.textContent = err.message || "Не удалось проверить файл.";
        }
      })
    );
  }
});

