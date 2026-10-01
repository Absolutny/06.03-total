# ERD — схема базы данных

```mermaid
erDiagram
    users ||--o{ schedule_slots : "ведёт (тренер)"
    users ||--o{ bookings : "записывается (клиент)"
    users ||--o{ subscriptions : "владеет (клиент)"
    users ||--o{ payments : "платит (клиент)"
    users ||--o{ refresh_tokens : "имеет"
    halls ||--o{ schedule_slots : "проводятся в"
    schedule_slots ||--o{ bookings : "содержит записи"
    subscriptions ||--o{ bookings : "списывает визит"
    subscriptions ||--o{ payments : "оплачен"

    users {
        bigint id PK
        varchar email UK
        varchar password_hash "BCrypt"
        varchar full_name
        varchar phone
        varchar role "ADMIN|MANAGER|TRAINER|CLIENT"
        boolean is_active
        timestamp created_at
    }
    halls {
        bigint id PK
        varchar name UK
        int capacity
    }
    schedule_slots {
        bigint id PK
        varchar title
        bigint trainer_id FK
        bigint hall_id FK
        timestamp start_time
        timestamp end_time "CHECK end > start"
        int max_clients "CHECK > 0"
        numeric price
    }
    bookings {
        bigint id PK
        bigint client_id FK
        bigint schedule_slot_id FK
        bigint subscription_id FK
        varchar status "BOOKED|CANCELLED|ATTENDED"
        timestamp created_at
    }
    subscriptions {
        bigint id PK
        bigint client_id FK
        varchar type "MONTHLY|UNLIMITED|SINGLE"
        int visits_left "NULL = без лимита визитов"
        date start_date
        date end_date
        boolean is_active
    }
    payments {
        bigint id PK
        bigint client_id FK
        bigint subscription_id FK
        numeric amount
        varchar status "PAID|REFUNDED"
        bigint created_by FK
        timestamp created_at
    }
    refresh_tokens {
        bigint id PK
        bigint user_id FK
        varchar jti_hash UK "SHA-256 от jti"
        timestamp expires_at
        boolean revoked
    }
    audit_logs {
        bigint id PK
        bigint user_id
        varchar event_type
        varchar description
        varchar ip_address
        timestamp timestamp
    }
```

`audit_logs.user_id` намеренно без внешнего ключа: журнал должен пережить удаление пользователя.

Время занятий хранится как **местное время комплекса без часового пояса** (`TIMESTAMP`).
