const filters = document.querySelector('.filters');
const search = document.querySelector('#search');
const selections = [...filters.querySelectorAll('select')];
const books = [...document.querySelectorAll('.book')];
filters.hidden = false;
function applyFilters() {
  const query = search?.value.trim().toLocaleLowerCase('en-GB');
  let count = 0;
  for (const book of books) {
    const matchesSearch = !query || book.dataset.search.includes(query);
    const matchesSelections = selections.every(select => !select.value || book.dataset[select.id] === select.value);
    book.hidden = !matchesSearch || !matchesSelections;
    if (!book.hidden) count++;
  }
  for (const heading of document.querySelectorAll('.month')) {
    let next = heading.nextElementSibling, any = false;
    while (next && !next.classList.contains('month')) { if (!next.hidden) any = true; next = next.nextElementSibling; }
    heading.hidden = !any;
  }
  document.querySelector('#filter-count').textContent = `${count} ${count === 1 ? 'title' : 'titles'}`;
  document.querySelector('#no-results').hidden = count !== 0;
}
search?.addEventListener('input', applyFilters);
for (const select of selections) select.addEventListener('change', applyFilters);
applyFilters();
const asOf = document.querySelector('#as-of');
if (asOf) {
  const now = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  if (now > asOf.dateTime) { asOf.insertAdjacentText('afterend', ' · rebuild overdue'); }
}
