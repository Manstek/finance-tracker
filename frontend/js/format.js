// Форматирование: API отдаёт даты YYYY-MM-DD и суммы строками ("1500.00").
const money = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatMoney(value, type) {
  const n = Number(value);
  const sign = type === "income" ? "+" : type === "expense" ? "−" : "";
  return `${sign}${money.format(Math.abs(n))} ₽`;
}

export function formatDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

export function todayIso() {
  const t = new Date();
  return new Date(t.getTime() - t.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

// Период по умолчанию — текущий месяц (как в api.md)
export function currentMonth() {
  const t = new Date();
  const first = new Date(t.getFullYear(), t.getMonth(), 1);
  const last = new Date(t.getFullYear(), t.getMonth() + 1, 0);
  const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  return { date_from: iso(first), date_to: iso(last) };
}

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
