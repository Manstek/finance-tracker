"""Единые обработчики ошибок API (FR-12).

Требования api.md: ошибки — JSON вида {"detail": "понятное сообщение"},
валидация Pydantic — 422. Здесь:
- 422 для тела запроса переводятся на русский и группируются по полям;
- IntegrityError (нарушение уникальности/ограничений БД) → 409, а не 500.
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

# Понятные названия полей для сообщений валидации
FIELD_NAMES = {
    "username": "Имя пользователя",
    "password": "Пароль",
    "email": "Email",
    "new_password": "Новый пароль",
    "type": "Тип операции",
    "amount": "Сумма",
    "category_id": "Категория",
    "date": "Дата",
    "comment": "Комментарий",
    "name": "Название категории",
    "date_from": "Начало периода",
    "date_to": "Окончание периода",
}

# Словарь типовых ошибок Pydantic → понятный текст (FR-12)
ERROR_TEMPLATES = {
    "missing": "Обязательное поле не заполнено",
    "string_too_short": "Значение слишком короткое",
    "string_too_long": "Значение слишком длинное",
    "greater_than": "Значение должно быть больше {gt}",
    "less_than": "Значение должно быть меньше {lt}",
    "string_pattern_mismatch": "Недопустимые символы",
    "literal_error": "Недопустимое значение",
    "int_parsing": "Ожидается целое число",
    "decimal_parsing": "Ожидается число",
    "date_from_datetime_parsing": "Ожидается дата в формате ГГГГ-ММ-ДД",
    "value_error": "",  # текст уже задан валидатором
}


def _human_message(error: dict) -> str:
    """Перевести одну ошибку Pydantic в понятное сообщение."""
    template = ERROR_TEMPLATES.get(error.get("type"), "")
    if not template:  # value_error: сообщение из валидатора
        return str(error.get("msg", "Некорректное значение")).removeprefix("Value error, ")
    ctx = error.get("ctx") or {}
    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return template


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 с сообщениями на русском, сгруппированными по полям."""
    fields: dict[str, list[str]] = {}
    other: list[str] = []
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")]
        message = _human_message(error)
        if loc:
            field = loc[-1]
            label = FIELD_NAMES.get(field, field)
            fields.setdefault(label, []).append(message)
        else:
            other.append(message)

    details: list[str] = []
    for label, messages in fields.items():
        details.append(f"{label}: {'; '.join(dict.fromkeys(messages))}")
    details.extend(dict.fromkeys(other))

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": ". ".join(details) if details else "Некорректные данные"},
    )


def integrity_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Нарушение ограничений БД → 409 вместо 500 (FR-12)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Действие нарушает ограничения данных (возможно, дубликат)"},
    )


def register_error_handlers(app) -> None:
    """Подключить обработчики к приложению."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_exception_handler)
