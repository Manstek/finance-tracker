// Точка входа: маршруты, защита страниц, шапка. Экраны — заглушки, наполняются в задачах этапа 2.
import { auth, setUnauthorizedHandler, logout } from "./api.js";
import { route, setGuard, navigate, start } from "./router.js";

const PUBLIC = new Set(["/login", "/register"]);

setGuard((path) => {
  if (!auth.isLoggedIn() && !PUBLIC.has(path)) return "/login";
  if (auth.isLoggedIn() && PUBLIC.has(path)) return "/operations";
  return null;
});

setUnauthorizedHandler(() => navigate("/login")); // 401 → на вход

function page(title, issue, text) {
  return (root) => {
    root.innerHTML = `
      <section class="page">
        <h1>${title}</h1>
        <p class="muted">${text}</p>
        <p class="todo">Экран будет реализован в задаче #${issue}.</p>
      </section>`;
  };
}

route("/login", page("Вход", 17, "Имя пользователя и пароль → POST /auth/login."));
route("/register", page("Регистрация", 17, "Имя пользователя, email (необязательно), пароль ≥ 8 символов → POST /auth/register."));
route("/operations", page("Операции", 18, "Список за текущий месяц, фильтры, итоги — GET /operations."));
route("/categories", page("Категории", 40, "Справочник категорий — /categories."));
route("/statistics", page("Статистика", 39, "Круговая диаграмма — GET /statistics/categories."));
route("/admin", page("Администрирование", 21, "Пользователи — GET /admin/users (только is_admin)."));
route("/404", (root) => { root.innerHTML = `<section class="page"><h1>Страница не найдена</h1><a href="#/operations">К операциям</a></section>`; });

// Шапка: меню видно только после входа
function renderHeader() {
  const nav = document.getElementById("nav");
  nav.hidden = !auth.isLoggedIn();
  const path = location.hash.replace(/^#/, "");
  nav.querySelectorAll("a[data-path]").forEach((a) => a.classList.toggle("active", a.dataset.path === path));
}

document.addEventListener("route:changed", renderHeader);
document.getElementById("logout").addEventListener("click", (e) => {
  e.preventDefault();
  logout();
  navigate("/login");
});

start();
