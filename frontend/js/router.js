// Простой hash-роутер: #/login, #/operations, ...
const routes = new Map();
let guard = () => null;

export function route(path, render) { routes.set(path, render); }

// guard(path) возвращает путь для редиректа или null
export function setGuard(fn) { guard = fn; }

export function navigate(path) { location.hash = `#${path}`; }

export function currentPath() { return location.hash.replace(/^#/, "") || "/operations"; }

async function resolve() {
  const path = currentPath();
  const redirect = guard(path);
  if (redirect && redirect !== path) return navigate(redirect);
  const render = routes.get(path) || routes.get("/404");
  const root = document.getElementById("app");
  root.innerHTML = "";
  await render(root);
  document.dispatchEvent(new CustomEvent("route:changed", { detail: path }));
}

export function start() {
  window.addEventListener("hashchange", resolve);
  resolve();
}
