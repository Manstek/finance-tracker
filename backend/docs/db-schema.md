# Схема базы данных

Три таблицы (FR-11). Все записи пользователя изолированы через `user_id` (FR-3): любой запрос API фильтруется по владельцу.

## users — пользователи

| Поле | Тип | Описание |
|---|---|---|
| id | serial PK | |
| username | varchar(50), UNIQUE, indexed | логин для регистрации/входа (FR-1) |
| email | varchar(255), UNIQUE, nullable | опционален, для восстановления доступа |
| password_hash | varchar(255) | только хеш, пароль не хранится (FR-1, NFR-1) |
| is_admin | boolean, default false | роль администратора (FR-13) |
| created_at | timestamptz, default now() | |

## categories — категории пользователя (FR-10)

| Поле | Тип | Описание |
|---|---|---|
| id | serial PK | |
| user_id | int FK → users.id ON DELETE CASCADE, indexed | владелец |
| name | varchar(100) | название |

Уникальность `user_id + name` — одинаковые названия допустимы у разных пользователей, но не у одного.

## transactions — финансовые операции (FR-4..FR-7)

| Поле | Тип | Описание |
|---|---|---|
| id | serial PK | |
| user_id | int FK → users.id ON DELETE CASCADE, indexed | владелец |
| category_id | int FK → categories.id ON DELETE SET NULL, indexed | при удалении категории операции сохраняются |
| type | varchar(10) | `income` / `expense` (CHECK-констрейнт) |
| amount | numeric(12,2), CHECK > 0 | сумма |
| date | date | день операции (не в будущем — валидируется на уровне API) |
| comment | varchar(500), nullable | комментарий |

Составной индекс `ix_transactions_user_date (user_id, date)` — под сортировку по дате (FR-5) и выборки за период с итогами (FR-6, FR-7).

## Миграции

Alembic, каталог `backend/alembic`. Применение: `alembic upgrade head`.
