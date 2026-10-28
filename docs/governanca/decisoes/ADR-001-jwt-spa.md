# ADR-001 — JWT para a SPA

| Campo | Valor |
|---|---|
| Status | Aceito (código atual) |
| Data documental | 26 de outubro de 2026 |

## Contexto

A interface é uma SPA React em origem que pode ser distinta da API em desenvolvimento (Vite :5173, Django :8000).

## Decisão

`rest_framework_simplejwt` com Bearer. Tokens no `localStorage` (`AuthContext.jsx`). CSRF da sessão Django permanece para `/admin/`.

## Consequências

- CORS necessário em origens cruzadas.
- XSS no SPA pode roubar tokens (risco clássico de localStorage).
- Refresh com blacklist exige tabela SimpleJWT.
