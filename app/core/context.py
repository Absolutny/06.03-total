"""IP клиента текущего запроса (для журнала аудита). Устанавливается middleware."""
from contextvars import ContextVar

client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)
