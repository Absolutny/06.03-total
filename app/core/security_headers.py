from starlette.middleware.base import BaseHTTPMiddleware

_DOCS_PREFIXES = ("/swagger-ui", "/redoc", "/v3/api-docs")

# Строгий CSP для API: ничего не исполняется и не подгружается
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        h["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.url.scheme == "https":
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if not request.url.path.startswith(_DOCS_PREFIXES):  # Swagger UI грузит скрипты с CDN
            h["Content-Security-Policy"] = _API_CSP
            h["Cache-Control"] = "no-store"
        return response
