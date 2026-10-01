# 🏋️ АИС «СпортКомплекс» — REST API

Система управления спортивным комплексом: клиенты, тренеры, залы, расписание, записи, абонементы, оплаты, журнал аудита.

**Стек:** Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic v2 · PostgreSQL 16 · JWT (PyJWT) · BCrypt · Docker · pytest

## 🚀 Запуск

```bash
docker compose up -d --build
```

| Что | Адрес |
| --- | --- |
| Swagger UI | http://localhost:8080/swagger-ui.html |
| OpenAPI (JSON) | http://localhost:8080/v3/api-docs |
| Проверка работоспособности | http://localhost:8080/health |

По умолчанию (`SEED_DEMO_DATA=true`) создаются тестовые данные: 2 зала, 2 занятия на завтра, клиенту выдан месячный абонемент.

### Тестовые учётные данные (только для разработки)

| Роль | Email | Пароль |
| --- | --- | --- |
| ADMIN | `admin@complex.com` | `Admin123!` |
| MANAGER | `manager@complex.com` | `Manager123!` |
| TRAINER | `trainer@complex.com` | `Trainer123!` |
| CLIENT | `client@complex.com` | `Client123!` |

> ⚠️ Пароли публичны. Для боевого запуска задайте `SEED_DEMO_DATA=false`, `ENVIRONMENT=production`, свой `JWT_SECRET` и `ADMIN_PASSWORD` (см. `.env.example`). В `production` запуск с секретом по умолчанию запрещён.

### Как пользоваться в Swagger
1. `POST /api/v1/auth/login` → скопировать `access_token`.
2. Кнопка **Authorize** → вставить токен.
3. Когда access истечёт (15 мин) — `POST /api/v1/auth/refresh`.

### Локальный запуск без Docker (SQLite)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export SEED_DEMO_DATA=true
uvicorn app.main:app --reload --port 8080       # БД: ./sport.db
```

## 🧪 Тесты

```bash
pip install -r requirements-dev.txt
pytest                                           # все тесты
pytest --cov=app --cov-report=term-missing       # с покрытием (цель ≥ 70 %)
python scripts/check_imports.py                  # статическая проверка внутренних импортов
```

* `tests/test_booking_service_unit.py`, `tests/test_security_unit.py` — unit-тесты (моки, без БД).
* `tests/test_api_auth.py`, `tests/test_api_business.py` — интеграционные тесты API на временной SQLite.

## 🏗 Архитектура (Controller → Service → Repository)

```text
app/
├── main.py              # сборка приложения, middleware, роутеры
├── config.py            # настройки из переменных окружения
├── database.py          # engine, сессии
├── seed.py              # первичное наполнение
├── api/v1/              # контроллеры (только HTTP: разбор запроса → вызов сервиса)
├── schemas/             # DTO: запросы и ответы, валидация (Pydantic)
├── services/            # бизнес-логика, транзакции, аудит
├── repositories/        # доступ к данным (SQLAlchemy)
├── models/              # ORM-сущности
├── security/            # JWT, BCrypt, зависимости RBAC
└── core/                # исключения, глобальный обработчик ошибок, rate limit, заголовки, логирование
```

Внедрение зависимостей — через `Depends` (`app/api/deps.py`); сервисы принимают репозитории в конструкторе, поэтому unit-тестируются на моках.

ERD: [`docs/ERD.md`](docs/ERD.md).

## 🔌 Эндпоинты

| Метод | Путь | Доступ |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | все (создаёт CLIENT) |
| POST | `/api/v1/auth/login` | все, лимит 5/мин на IP |
| POST | `/api/v1/auth/refresh` | refresh-токен |
| POST | `/api/v1/auth/logout` · `/change-password` | любой авторизованный |
| GET | `/api/v1/auth/me` | любой авторизованный |
| GET / POST | `/api/v1/halls` | GET — все авторизованные; POST — ADMIN, MANAGER |
| GET | `/api/v1/schedule` (фильтры: `date_from`, `date_to`, `trainer_id`, `hall_id`), `/schedule/{id}` | все авторизованные |
| POST | `/api/v1/schedule` | ADMIN, MANAGER |
| POST | `/api/v1/bookings` | CLIENT |
| GET | `/api/v1/bookings/my` | любой авторизованный |
| DELETE | `/api/v1/bookings/{id}` | владелец, ADMIN, MANAGER |
| GET | `/api/v1/subscriptions/my` | CLIENT |
| POST | `/api/v1/subscriptions/issue` | ADMIN, MANAGER (создаёт оплату) |
| GET | `/api/v1/trainer/schedule`, `/trainer/slots/{id}/bookings` | TRAINER, ADMIN |
| POST | `/api/v1/trainer/bookings/{id}/attendance` | TRAINER (свои занятия), ADMIN |
| POST | `/api/v1/admin/staff` | ADMIN |
| GET | `/api/v1/admin/audit-logs`, `/admin/reports/revenue` | ADMIN |

### Бизнес-правила бронирования
* Записаться можно только на будущее занятие, при наличии свободных мест и **действующего абонемента** на дату занятия.
* Визит списывается с абонемента (если он ограничен по визитам); при отмене — возвращается.
* Дубль записи на одно занятие запрещён; зал и тренер не могут быть заняты двумя занятиями одновременно; `max_clients` не больше вместимости зала.
* Чужую запись клиент отменить не может — в ответ `404` (существование записи не раскрывается).

## 🔒 Безопасность (OWASP)

| Мера | Реализация |
| --- | --- |
| Пароли | BCrypt (12 раундов, случайная соль), политика: ≥8 символов, заглавная, строчная, цифра |
| Токены | access 15 мин + refresh 7 дней; refresh одноразовый (ротация), хранится только SHA-256 от `jti`; повторное использование отзывает все сессии пользователя; после смены пароля все refresh отзываются |
| RBAC | роли ADMIN / MANAGER / TRAINER / CLIENT, зависимости `require_roles`; роль и активность проверяются **по БД**, а не по токену |
| SQL-инъекции | только ORM / параметризованные запросы |
| Валидация | Pydantic-DTO на всех входах; `<`/`>` в именах запрещены; время — без часового пояса |
| Rate limiting | 100 запросов/мин на IP + 5 попыток входа/мин на IP (`429` + `Retry-After`); `X-Forwarded-For` не принимается на веру |
| CORS | явный список `CORS_ORIGINS`, без `*` |
| Заголовки | `nosniff`, `X-Frame-Options`, CSP, `Referrer-Policy`, HSTS (при HTTPS), `Cache-Control: no-store` |
| Перебор логинов | одинаковое время и текст ответа для существующего и несуществующего email |
| Аудит | входы, неудачи, регистрации, смена пароля, создание сотрудников/занятий/абонементов, записи, повторное использование refresh; защита от подделки записей переводами строк |
| Ошибки | единый формат `{status, code, message, timestamp, details}`; трассировки наружу не уходят |
| Docker | запуск не от root; PostgreSQL слушает только `127.0.0.1` |

## ⚙️ Переменные окружения

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./sport.db` | в Docker — PostgreSQL |
| `JWT_SECRET` | dev-значение | **≥ 32 символов**, обязателен в production |
| `ENVIRONMENT` | `development` | `production` включает защитные проверки |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | `15` / `7` | время жизни токенов |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8080` | через запятую |
| `RATE_LIMIT_PER_MINUTE` / `LOGIN_RATE_LIMIT_PER_MINUTE` | `100` / `5` | лимиты |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@complex.com` / случайный | первый администратор |
| `SEED_DEMO_DATA` | `false` (в compose — `true`) | тестовые данные |
| `BCRYPT_ROUNDS` | `12` | стоимость хеширования |

## 💾 Резервное копирование

Требование ТЗ о ежечасовом бэкапе: `docker compose --profile backup up -d` — раз в час делается `pg_dump` в `./backups`, хранится 48 копий.

## ⚠️ Известные ограничения

* Схема БД создаётся через `create_all` при старте. Для эволюции схемы в продакшене подключите Alembic.
* Rate limiter хранит счётчики в памяти процесса; при нескольких репликах нужен Redis.
* Это только API; веб-интерфейс прежней версии (Flask + Jinja) не переносился.
