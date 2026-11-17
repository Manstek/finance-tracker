import { adminDeleteUser, adminListUsers, adminResetPassword, getCurrentUser } from "./api.js";
import { showError } from "./auth-page.js";
import { escapeHtml } from "./format.js";

export async function adminPage(root) {
  root.innerHTML = `<section class="page"><h1>Администрирование</h1>
    <p class="alert" role="alert" hidden></p><p class="status" role="status">Загрузка…</p>
    <div class="table-scroll"><table class="table"><thead><tr>
    <th>Имя</th><th>Email</th><th>Роль</th><th>Действия</th></tr></thead><tbody></tbody></table></div>
    <dialog><h2>Сброс пароля</h2><form class="form">
      <label>Новый пароль <input name="password" type="password" minlength="8" required autocomplete="new-password"></label>
      <p class="alert" role="alert" hidden></p>
      <div class="row"><button class="btn primary">Сохранить</button><button class="btn" type="button">Отмена</button></div>
    </form></dialog></section>`;
  const section = root.firstElementChild;
  const status = section.querySelector(".status");
  const alert = section.querySelector(".alert");
  const tableBody = section.querySelector("tbody");
  const dialog = section.querySelector("dialog");
  const form = dialog.querySelector("form");
  let selectedUser;
  let currentUser;
  let deleting = false;
  let saving = false;

  async function loadUsers() {
    const users = await adminListUsers();
    tableBody.innerHTML = users.map((user) => `<tr>
      <td>${escapeHtml(user.username)}</td><td>${escapeHtml(user.email || "—")}</td>
      <td>${user.is_admin ? "Администратор" : "Пользователь"}</td>
      <td><div class="row actions"><button class="btn" data-reset="${user.id}">Сбросить пароль</button>
      ${user.id === currentUser.id ? "" : `<button class="btn" data-delete="${user.id}">Удалить</button>`}</div></td></tr>`).join("");
  }

  tableBody.addEventListener("click", async (event) => {
    const { reset, delete: remove } = event.target.dataset;
    if (deleting) return;
    if (reset) {
      selectedUser = reset;
      form.reset();
      form.querySelector(".alert").hidden = true;
      dialog.showModal();
    }
    if (!remove || !confirm("Удалить пользователя и его операции?")) return;
    deleting = true;
    try {
      alert.hidden = true;
      await adminDeleteUser(remove);
      await loadUsers();
      status.textContent = "Пользователь удалён.";
    } catch (error) {
      showError(alert, error);
    } finally {
      deleting = false;
    }
  });
  form.querySelector('button[type="button"]').addEventListener("click", () => {
    if (!saving) dialog.close();
  });
  dialog.addEventListener("cancel", (event) => {
    if (saving) event.preventDefault();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    const submit = form.querySelector(".primary");
    form.querySelector(".alert").hidden = true;
    submit.disabled = true;
    try {
      await adminResetPassword(selectedUser, form.elements.password.value);
      dialog.close();
      status.textContent = "Пароль обновлён.";
    } catch (error) {
      showError(form.querySelector(".alert"), error);
    } finally {
      saving = false;
      submit.disabled = false;
    }
  });

  try {
    currentUser = await getCurrentUser();
    if (!currentUser.is_admin) throw new Error("Требуются права администратора.");
    await loadUsers();
    status.textContent = "";
  } catch (error) {
    showError(alert, error);
    status.textContent = "";
  }
}
