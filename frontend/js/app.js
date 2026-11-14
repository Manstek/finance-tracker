import { auth, getCurrentUser, setUnauthorizedHandler, logout } from "./api.js";
import { adminPage } from "./admin-page.js";
import { authPage } from "./auth-page.js";
import { operationsPage } from "./operations-page.js";
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

route("/login", authPage);
route("/register", (root) => authPage(root, true));
route("/operations", operationsPage);
route("/categories", page("Категории", 40, "Справочник категорий — /categories."));
route("/statistics", page("Статистика", 39, "Круговая диаграмма — GET /statistics/categories."));
route("/admin", adminPage);
route("/404", (root) => { root.innerHTML = `<section class="page"><h1>Страница не найдена</h1><a href="#/operations">К операциям</a></section>`; });

// Шапка: меню видно только после входа
let headerRequest = 0;
let accountToken;
let account;

async function renderHeader() {
  const request = ++headerRequest;
  const nav = document.getElementById("nav");
  const admin = document.getElementById("nav-admin");
  const token = auth.getToken();
  nav.hidden = !token;
  const path = location.hash.replace(/^#/, "");
  nav.querySelectorAll("a[data-path]").forEach((a) => a.classList.toggle("active", a.dataset.path === path));
  if (token !== accountToken) {
    accountToken = token;
    account = token ? getCurrentUser().catch(() => null) : null;
    admin.hidden = true;
  }
  const user = await account;
  if (request === headerRequest && token === auth.getToken()) admin.hidden = !user?.is_admin;
}

document.addEventListener("route:changed", renderHeader);
document.getElementById("logout").addEventListener("click", (e) => {
  e.preventDefault();
  logout();
  navigate("/login");
});

start();
