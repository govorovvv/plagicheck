// ===== Проверка текста и файлов (страница app.html) =====


// Универсальный POST
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

// Проверка файла (тип, размер)
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
  const max = 10 * 1024 * 1024; // 10 МБ
  if (file.size > max) return "Файл слишком большой (лимит 10 МБ).";
  return null;
}

// Рендер совпадений
function renderSources(containerEl, sources) {
  const wrap = document.createElement("div");
  wrap.style.marginTop = "8px";

  if (!Array.isArray(sources) || sources.length === 0) {
    wrap.innerHTML = `<div class="muted">Совпадения не найдены.</div>`;
    containerEl.appendChild(wrap);
    return;
  }

  const items = sources
    .map(s => `<li><a class="link" target="_blank" rel="noopener" href="${s.url}">${s.title || s.url}</a></li>`)
    .join("");

  wrap.innerHTML = `
    <div class="muted"><b>Найденные совпадения:</b></div>
    <ul class="sources-list">${items}</ul>
  `;
  containerEl.appendChild(wrap);
}

// Хелпер для индикации загрузки
function withLoading(btn, text, fn) {
  return async function (e) {
    e.preventDefault();
    if (!btn) return await fn(e);
    const orig = btn.textContent;
    btn.disabled = true;
    btn.textContent = text;
    try { await fn(e); }
    finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  };
}

document.addEventListener("DOMContentLoaded", () => {
  // ===== ТЕКСТ =====
  const textForm = $("#textForm");
  const textBtn = $("#textBtn");
  const textResult = $("#textResult");
  const textReportOpen = $("#textReportOpen");
  const textReportDownload = $("#textReportDownload");

  if (textForm) {
    textForm.addEventListener("submit", withLoading(textBtn, "Проверяем…", async (e) => {
      e.preventDefault();
      if (textResult) textResult.innerHTML = "";
      if (textReportOpen) textReportOpen.style.display = "none";
      if (textReportDownload) textReportDownload.style.display = "none";

      const formData = new FormData(textForm);
      const txt = (formData.get("text") || "").toString().trim();
      if (!txt) { textResult.textContent = "Введите текст для проверки."; return; }

      try {
        const data = await postForm("/api/check-text", formData);

        textResult.innerHTML =
          `Оригинальность: <b>${(+data.originality).toFixed(1)}%</b> · ` +
          `Заимствования: <b>${(+data.plagiarism).toFixed(1)}%</b>`;
        renderSources(textResult, data.sources || []);

        if (data.report_id) {
          const openUrl = `/api/report/${data.report_id}`;
          const dlUrl = `/api/report/${data.report_id}?dl=1`;

          if (textReportOpen) {
            textReportOpen.href = openUrl;
            textReportOpen.style.display = "inline-flex";
          }
          if (textReportDownload) {
            textReportDownload.href = dlUrl;
            textReportDownload.setAttribute("download", `plagicheck_${data.report_id}.pdf`);
            textReportDownload.style.display = "inline-flex";
          }
        }

        if (window.plausible) window.plausible("CheckText");
      } catch (err) {
        textResult.textContent = err.message || "Не удалось выполнить проверку.";
      }
    }));
  }

  // ===== ФАЙЛ =====
  const fileForm = $("#fileForm");
  const fileInput = $("#fileInput");
  const fileBtn = $("#fileBtn");
  const fileResult = $("#fileResult");
  const fileReportOpen = $("#fileReportOpen");
  const fileReportDownload = $("#fileReportDownload");

  if (fileForm && fileInput) {
    fileForm.addEventListener("submit", withLoading(fileBtn, "Проверяем…", async (e) => {
      e.preventDefault();
      if (fileResult) fileResult.innerHTML = "";
      if (fileReportOpen) fileReportOpen.style.display = "none";
      if (fileReportDownload) fileReportDownload.style.display = "none";

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
        renderSources(fileResult, data.sources || []);

        if (data.report_id) {
          const openUrl = `/api/report/${data.report_id}`;
          const dlUrl = `/api/report/${data.report_id}?dl=1`;

          if (fileReportOpen) {
            fileReportOpen.href = openUrl;
            fileReportOpen.style.display = "inline-flex";
          }
          if (fileReportDownload) {
            fileReportDownload.href = dlUrl;
            fileReportDownload.setAttribute("download", `plagicheck_${data.report_id}.pdf`);
            fileReportDownload.style.display = "inline-flex";
          }
        }

        if (window.plausible) window.plausible("CheckFile");
      } catch (err) {
        fileResult.textContent = err.message || "Не удалось проверить файл.";
      }
    }));
  }
});
