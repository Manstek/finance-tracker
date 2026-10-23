// API-клиент по контракту backend/docs/api.md (v1).
import { API_BASE } from "./config.js";

const TOKEN_KEY = "ft_access_token";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
  isLoggedIn: () => Boolean(localStorage.getItem(TOKEN_KEY)),
};

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Ошибка запроса");
    this.status = status;
    this.detail = detail; // строка или массив ошибок валидации (422)
  }
}

// Колбэк на 401 (токен истёк) — устанавливается в app.js
let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

function query(params = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") q.append(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

async function request(method, path, { body, params } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = auth.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(API_BASE + path + query(params), {
      method, headers, body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Сервер недоступен. Проверьте, что бэкенд запущен.");
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) { auth.clear(); onUnauthorized(); }
    throw new ApiError(res.status, data?.detail ?? `Ошибка ${res.status}`);
  }
  return data;
}

// --- Auth (FR-1, FR-2) ---
export const register = (username, password, email) =>
  request("POST", "/auth/register", { body: { username, password, ...(email ? { email } : {}) } });

export async function login(username, password) {
  const data = await request("POST", "/auth/login", { body: { username, password } });
  auth.setToken(data.access_token);
  return data;
}

export function logout() { auth.clear(); } // токены stateless (api.md, UC-3)

// --- Операции (FR-4…FR-8) ---
export const listOperations = (filters = {}) => request("GET", "/operations", { params: filters });
export const createOperation = (op) => request("POST", "/operations", { body: op });
export const updateOperation = (id, patch) => request("PATCH", `/operations/${id}`, { body: patch });
export const deleteOperation = (id) => request("DELETE", `/operations/${id}`);
export const getSummary = (period = {}) => request("GET", "/operations/summary", { params: period });

// --- Категории (FR-10) ---
export const listCategories = () => request("GET", "/categories");
export const createCategory = (name) => request("POST", "/categories", { body: { name } });
export const renameCategory = (id, name) => request("PATCH", `/categories/${id}`, { body: { name } });
export const deleteCategory = (id) => request("DELETE", `/categories/${id}`);

// --- Статистика (FR-9) ---
export const categoryStats = (params) => request("GET", "/statistics/categories", { params });

// --- Администратор (FR-13) ---
export const adminListUsers = () => request("GET", "/admin/users");
export const adminDeleteUser = (id) => request("DELETE", `/admin/users/${id}`);
export const adminResetPassword = (id, newPassword) =>
  request("POST", `/admin/users/${id}/reset-password`, { body: { new_password: newPassword } });
