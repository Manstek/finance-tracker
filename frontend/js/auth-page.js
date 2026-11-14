import { login, register } from "./api.js";
import { navigate } from "./router.js";

export function showError(target, error) {
  target.textContent = Array.isArray(error.detail)
    ? error.detail.map(({ msg }) => msg).join(". ")
    : error.message;
  target.hidden = false;
}

export function authPage(root, registration = false) {
  const title = registration ? "Регистрация" : "Вход";
  root.innerHTML = `
    <section class="page">
      <h1>${title}</h1>
      <form class="form">
        <label>Имя пользователя <input name="username" required maxlength="50" autocomplete="username"
          ${registration ? 'minlength="3" pattern="[A-Za-z0-9_\\-]+"' : ""}></label>
        ${registration ? '<label>Email (необязательно) <input name="email" type="email" maxlength="255" autocomplete="email"></label>' : ""}
        <label>Пароль <input name="password" required type="password" maxlength="128"
          ${registration ? 'minlength="8" autocomplete="new-password"' : 'autocomplete="current-password"'}></label>
        <p class="alert" role="alert" hidden></p>
        <button class="btn primary">${registration ? "Создать аккаунт" : "Войти"}</button>
      </form>
      <p>${registration ? '<a href="#/login">Уже есть аккаунт</a>' : '<a href="#/register">Зарегистрироваться</a>'}</p>
    </section>`;
  const form = root.querySelector("form");
  const message = form.querySelector(".alert");
  const submit = form.querySelector("button");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.hidden = true;
    submit.disabled = true;
    const { username, password, email } = Object.fromEntries(new FormData(form));
    try {
      if (registration) await register(username, password, email);
      if (!form.isConnected) return;
      await login(username, password);
      navigate("/operations");
    } catch (error) {
      showError(message, error);
    } finally {
      submit.disabled = false;
    }
  });
}
