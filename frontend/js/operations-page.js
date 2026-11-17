import { createOperation, deleteOperation, listCategories, listOperations, updateOperation } from "./api.js";
import { showError } from "./auth-page.js";
import { currentMonth, escapeHtml, formatDate, formatMoney, todayIso } from "./format.js";

export async function operationsPage(root) {
  root.innerHTML = `
    <section class="page">
      <div class="row"><h1>Операции</h1><button class="btn primary" id="add-operation">Добавить операцию</button></div>
      <form class="filters">
        <label>С <input name="date_from" type="date"></label>
        <label>По <input name="date_to" type="date"></label>
        <label>Тип <select name="type"><option value="">Все</option><option value="income">Доход</option><option value="expense">Расход</option></select></label>
        <label>Категория <select name="category_id"><option value="">Все</option></select></label>
        <button class="btn">Применить</button>
        <button class="btn" type="button" id="reset-filters">Текущий месяц</button>
      </form>
      <p class="alert" role="alert" hidden></p>
      <div id="totals" class="row" aria-live="polite"></div>
      <div class="table-scroll"><table class="table"><thead><tr>
        <th>Дата</th><th>Тип</th><th>Категория</th><th>Сумма</th><th>Комментарий</th><th>Действия</th>
      </tr></thead><tbody></tbody></table></div>
      <p id="list-status" role="status">Загрузка…</p>
      <div class="row" id="pagination" hidden>
        <button class="btn" id="prev-page">Назад</button><span></span><button class="btn" id="next-page">Далее</button>
      </div>
      <dialog><h2></h2>
        <form class="form">
          <label>Тип <select name="type"><option value="expense">Расход</option><option value="income">Доход</option></select></label>
          <label>Сумма, ₽ <input name="amount" type="number" min="0.01" max="9999999999.99" step="0.01" required></label>
          <label>Категория <select name="category_id"><option value="">Без категории</option></select></label>
          <label>Дата <input name="date" type="date" required max="${todayIso()}"></label>
          <label>Комментарий <textarea name="comment" maxlength="500"></textarea></label>
          <p class="alert" role="alert" hidden></p>
          <div class="row"><button class="btn primary">Сохранить</button><button class="btn" type="button" id="cancel-editor">Отмена</button></div>
        </form>
      </dialog>
    </section>`;
  const section = root.firstElementChild;
  const find = (selector) => section.querySelector(selector);
  const filters = find(".filters");
  const dialog = find("dialog");
  const editor = dialog.querySelector("form");
  const alert = find(".alert");
  const listStatus = find("#list-status");
  const pagination = find("#pagination");
  const tableBody = find("tbody");
  let criteria = currentMonth();
  let page = 1;
  let requestNumber = 0;
  let editing = null;
  let categories = new Map();
  let operations = new Map();
  let rowActionPending = false;
  let saving = false;

  function setMonth() {
    filters.reset();
    for (const [key, value] of Object.entries(currentMonth())) filters.elements[key].value = value;
  }

  async function refresh() {
    const request = ++requestNumber;
    alert.hidden = true;
    listStatus.textContent = "Загрузка…";
    try {
      const result = await listOperations({ ...criteria, page, per_page: 10 });
      if (request !== requestNumber || !section.isConnected) return;
      const lastPage = Math.max(1, Math.ceil(result.total / result.per_page));
      if (page > lastPage) {
        page = lastPage;
        return refresh();
      }
      operations = new Map(result.items.map((operation) => [operation.id, operation]));
      tableBody.innerHTML = result.items.map((operation) => {
        const expense = operation.type === "expense";
        const category = categories.get(operation.category_id) ?? "Без категории";
        return `<tr><td>${escapeHtml(formatDate(operation.date))}</td><td>${expense ? "Расход" : "Доход"}</td>
          <td>${escapeHtml(category)}</td><td class="${expense ? "expense" : "income"}">${formatMoney(operation.amount, operation.type)}</td>
          <td>${escapeHtml(operation.comment || "—")}</td><td><div class="row actions">
          <button class="btn" data-edit="${operation.id}">Изменить</button>
          <button class="btn" data-delete="${operation.id}">Удалить</button></div></td></tr>`;
      }).join("");
      const { income, expense, balance } = result.totals;
      find("#totals").innerHTML = `<span>Доходы <strong>${formatMoney(income)}</strong></span>
        <span>Расходы <strong>${formatMoney(expense)}</strong></span>
        <span>Баланс <strong>${formatMoney(balance)}</strong></span>`;
      listStatus.textContent = result.total ? `Всего операций: ${result.total}` : "За выбранный период операций нет.";
      pagination.hidden = lastPage === 1;
      pagination.querySelector("span").textContent = `Страница ${page} из ${lastPage}`;
      find("#prev-page").disabled = page === 1;
      find("#next-page").disabled = page === lastPage;
    } catch (error) {
      if (request !== requestNumber) return;
      showError(alert, error);
      listStatus.textContent = "";
    }
  }

  function openEditor(operation = null) {
    editing = operation?.id ?? null;
    editor.reset();
    editor.querySelector(".alert").hidden = true;
    dialog.querySelector("h2").textContent = operation ? "Изменить операцию" : "Добавить операцию";
    editor.elements.date.value = operation?.date ?? todayIso();
    if (operation) {
      for (const name of ["type", "amount", "category_id", "comment"]) {
        editor.elements[name].value = operation[name] ?? "";
      }
    }
    dialog.showModal();
  }

  filters.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(filters));
    if (values.date_from && values.date_to && values.date_from > values.date_to) {
      showError(alert, new Error("Начало периода должно быть не позже окончания."));
      return;
    }
    criteria = values;
    page = 1;
    refresh();
  });
  find("#reset-filters").addEventListener("click", () => { setMonth(); filters.requestSubmit(); });
  find("#prev-page").addEventListener("click", () => { page -= 1; refresh(); });
  find("#next-page").addEventListener("click", () => { page += 1; refresh(); });
  find("#add-operation").addEventListener("click", () => openEditor());
  find("#cancel-editor").addEventListener("click", () => {
    if (!saving) dialog.close();
  });
  dialog.addEventListener("cancel", (event) => {
    if (saving) event.preventDefault();
  });
  tableBody.addEventListener("click", async (event) => {
    const { edit, delete: remove } = event.target.dataset;
    if (rowActionPending) return;
    if (edit) openEditor(operations.get(Number(edit)));
    if (!remove || !confirm("Удалить операцию?")) return;
    rowActionPending = true;
    try {
      await deleteOperation(remove);
      await refresh();
    } catch (error) {
      showError(alert, error);
    } finally {
      rowActionPending = false;
    }
  });
  editor.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    const submit = editor.querySelector('button:not([type="button"])');
    editor.querySelector(".alert").hidden = true;
    submit.disabled = true;
    const values = Object.fromEntries(new FormData(editor));
    values.category_id = values.category_id ? Number(values.category_id) : null;
    values.comment = values.comment.trim() || null;
    try {
      if (editing === null) await createOperation(values);
      else await updateOperation(editing, values);
      dialog.close();
      await refresh();
    } catch (error) {
      showError(editor.querySelector(".alert"), error);
    } finally {
      saving = false;
      submit.disabled = false;
    }
  });
  setMonth();
  try {
    const values = await listCategories();
    categories = new Map(values.map(({ id, name }) => [id, name]));
    for (const { id, name } of values) {
      filters.elements.category_id.add(new Option(name, id));
      editor.elements.category_id.add(new Option(name, id));
    }
  } catch (error) {
    find("#add-operation").disabled = true;
    showError(alert, error);
    listStatus.textContent = "";
    return;
  }
  await refresh();
}
