function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
    return v.toString(16);
  });
}

const textForm = document.getElementById('textForm');
const textResult = document.getElementById('textResult');
const textReportLink = document.getElementById('textReportLink');

textForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  textResult.textContent = 'Проверяем...';
  textReportLink.style.display = 'none';

  const formData = new FormData(textForm);
  try {
    const res = await fetch('/api/check-text', { method: 'POST', body: formData });
    const data = await res.json();
    textResult.innerHTML = `Оригинальность: <b>${data.originality}%</b> · Заимствования: <b>${data.plagiarism}%</b>`;
    // Генерируем UUID на клиенте и скачиваем PDF (бек генерит "на лету")
    const id = uuidv4();
    textReportLink.href = `/api/report/${id}`;
    textReportLink.style.display = 'inline';
    textReportLink.textContent = 'Скачать PDF-отчёт';
  } catch (err) {
    textResult.textContent = 'Ошибка при проверке. Попробуйте ещё раз.';
  }
});

const fileForm = document.getElementById('fileForm');
const fileResult = document.getElementById('fileResult');
const fileReportLink = document.getElementById('fileReportLink');

fileForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  fileResult.textContent = 'Проверяем...';
  fileReportLink.style.display = 'none';

  const formData = new FormData(fileForm);
  try {
    const res = await fetch('/api/check-file', { method: 'POST', body: formData });
    const data = await res.json();
    fileResult.innerHTML = `Оригинальность: <b>${data.originality}%</b> · Заимствования: <b>${data.plagiarism}%</b>`;
    const id = uuidv4();
    fileReportLink.href = `/api/report/${id}`;
    fileReportLink.style.display = 'inline';
    fileReportLink.textContent = 'Скачать PDF-отчёт';
  } catch (err) {
    fileResult.textContent = 'Ошибка при проверке файла. Попробуйте ещё раз.';
  }
});
