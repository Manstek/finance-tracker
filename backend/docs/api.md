# Спецификация REST API (v1)

База: `http://localhost:8000/api/v1`. Формат данных — JSON, кодировка UTF-8.
Авторизация: `Authorization: Bearer <access_token>` (JWT, HS256, срок жизни 30 минут — NFR-1).

Коды ошибок:
- `400` — некорректные данные ввода (FR-12)
- `401` — не авторизован / токен истёк
- `403` — нет прав (чужие данные / не администратор, NFR-2)
- `404` — объект не найден или чужой (чужие объекты не отличаются от несуществующих)
- `409` — конфликт (например, занятый username)
- `422` — ошибка валидации Pydantic (автоматически)

Формат ошибки: `{"detail": "понятное сообщение"}`.

---

## Auth

### POST /auth/register — регистрация (FR-1)
```json
// request
{"username": "ivan", "password": "12345678", "email": "ivan@example.com"} // email опционален
// 201 response
{"id": 1, "username": "ivan", "email": "ivan@example.com", "is_admin": false}
```
- пароль ≥ 8 символов; username уникален → иначе `409`.

### POST /auth/login — вход, выдача JWT (FR-2)
```json
// request
{"username": "ivan", "password": "12345678"}
// 200 response
{"access_token": "…", "token_type": "bearer", "expires_in": 1800}
```
- неверные учётные данные → `401`.

### POST /auth/logout — выход (UC-3)
Клиент удаляет токен; токены stateless, серверный blacklist не входит в MVP.

---

## Операции (все — только свои данные, FR-3)

### POST /operations — добавить операцию (FR-4)
```json
// request
{"type": "expense", "amount": 1500.00, "category_id": 3, "date": "2026-11-02", "comment": "продукты"}
// 201 response
{"id": 10, "type": "expense", "amount": "1500.00", "category_id": 3, "date": "2026-11-02", "comment": "продукты"}
```
- дата не в будущем → `400`; категория чужая → `404`; amount > 0.

### GET /operations — список, сортировка по дате по убыванию (FR-5)
Параметры фильтрации (FR-6): `date_from`, `date_to`, `type` (`income`|`expense`), `category_id`.
```
GET /operations?date_from=2026-11-01&date_to=2026-11-30&type=expense&category_id=3&page=1&per_page=50
// 200 response
{
  "items": [ {"id": 10, …} ],
  "totals": {"income": "45000.00", "expense": "12300.50", "balance": "32699.50"}, // итог за период, FR-7
  "page": 1, "per_page": 50, "total": 12
}
```
- по умолчанию (без фильтров) — текущий месяц.

### PATCH /operations/{id} — редактировать (FR-8)
Любое подмножество полей из POST. Чужая операция → `404`.

### DELETE /operations/{id} — удалить (FR-8)
`204`. Чужая операция → `404`.

### GET /operations/summary — итоги за период (FR-7)
```
GET /operations/summary?date_from=…&date_to=…
// 200
{"income": "45000.00", "expense": "12300.50", "balance": "32699.50"}
```

---

## Категории (FR-10)

### GET /categories — список своих категорий → `200 [{"id": 1, "name": "Продукты"}]`
### POST /categories — `{"name": "Транспорт"}` → `201`; дубликат имени → `409`
### PATCH /categories/{id} — переименование → `200`
### DELETE /categories/{id} — `204`; операции категории не удаляются (category_id → NULL)

---

## Статистика (FR-9)

### GET /statistics/categories?date_from=…&date_to=…&type=expense
Распределение по категориям за период, для круговой диаграммы.
```json
// 200
{"type": "expense", "total": "12300.50", "items": [
  {"category_id": 3, "name": "Продукты", "amount": "8200.00", "percent": 66.7},
  {"category_id": null, "name": "Без категории", "amount": "4100.50", "percent": 33.3}
]}
```

---

## Администратор (FR-13, NFR-2 — только `is_admin=true`, иначе `403`)

### GET /admin/users — список пользователей
```
// 200 {"items": [{"id": 1, "username": "ivan", "email": "…", "is_admin": false, "created_at": "…"}]}
```
### GET /admin/users/{id} — профиль пользователя
### DELETE /admin/users/{id} — удалить пользователя → `204` (каскадно удаляет его данные)
### POST /admin/users/{id}/reset-password — помощь в восстановлении доступа (UC-11)
```json
// request
{"new_password": "87654321"} → 200 {"detail": "Пароль обновлён"}
```
Администратор не меняет свой `is_admin` и не удаляет себя.

---

## Схема OpenAPI

Автогенерируется FastAPI: `/docs` (Swagger UI), `/openapi.json`. Спецификация в этом документе — контракт для фронтенда (Александр) и основа автотестов (#16).
