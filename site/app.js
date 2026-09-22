const language = document.querySelector('#language');
function setLanguage(lang) {
  document.documentElement.lang = lang;
  language.textContent = lang === 'en' ? 'RU' : 'EN';
  language.setAttribute('aria-label', lang === 'en' ? 'Switch to Russian' : 'Switch to English');
  document.querySelector('.guide').href = document.querySelector('.guide').dataset[lang];
  document.querySelector('#close').setAttribute('aria-label', lang === 'en' ? 'Close image' : 'Закрыть изображение');
  try { localStorage.setItem('locus-site-language', lang); } catch {}
}
let saved; try { saved = localStorage.getItem('locus-site-language'); } catch {}
setLanguage(saved === 'ru' ? 'ru' : 'en');
language.addEventListener('click', () => setLanguage(document.documentElement.lang === 'en' ? 'ru' : 'en'));
const dialog = document.querySelector('#lightbox');
document.querySelectorAll('[data-image]').forEach(link => link.addEventListener('click', event => {
  event.preventDefault();
  dialog.querySelector('img').src = link.dataset.image;
  dialog.querySelector('img').alt = link.querySelector('img').alt;
  dialog.showModal();
}));
document.querySelector('#close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
