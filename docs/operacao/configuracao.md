# Configuração e variáveis de ambiente

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |
| Fontes | `.env.example` (raiz), `BACKEND/.env.example`, `SISTEMA-FINAL/.env.example`, `config/settings.py`, `compose.yaml` |

**Não** reproduza valores de `.env` reais. Placeholders abaixo são fictícios.

## Arquivos

| Arquivo | Uso |
|---|---|
| `FROTA/.env` | Compose (não versionado) |
| `FROTA/.env.example` | Modelo Docker Debian |
| `BACKEND/.env` | `runserver` local / outros hosts |
| `BACKEND/.env.example` | Modelo dev com comentários Supabase/Render |
| `SISTEMA-FINAL/.env` | opcional `VITE_API_URL` no Vite |

O Compose define `DB_HOST=db`, `DB_PORT=5432` e, por padrão, `DEBUG=False`, `USE_SUPABASE_STORAGE=False`.

## Variáveis (Django / Compose)

| Nome | Obrigatória em produção | Padrão no código | Quem usa | Exemplo seguro |
|---|---|---|---|---|
| `SECRET_KEY` | Sim | `django-insecure-change-me` | Django | `troque-por-token-urlsafe-50` |
| `AUDITORIA_CHAVE_INTEGRIDADE` | Fortemente recomendada | igual a `SECRET_KEY` | HMAC auditoria | chave **estável** distinta |
| `DEBUG` | `False` | `True` no settings se omitido | Django | `False` |
| `ALLOWED_HOSTS` | Sim | localhost | Django; healthcheck precisa de localhost | `localhost,127.0.0.1,frota.exemplo.local` |
| `CSRF_TRUSTED_ORIGINS` | Admin Django | vazio | CSRF | `http://frota.exemplo.local` |
| `CORS_ALLOWED_ORIGINS` | Sim se SPA em outra origem | localhost:3000/5173 | corsheaders | mesma origem pública |
| `CORS_ALLOW_LAN` | Não | igual a DEBUG | regex RFC1918 :3000/:5173 | `False` em produção |
| `USE_X_FORWARDED_HOST` | Compose: True | False | URLs atrás do proxy | `True` |
| `SECURE_PROXY_SSL_HEADER` | Se TLS no proxy | False | `X-Forwarded-Proto` | `True` só com HTTPS |
| `DB_ENGINE` | Sim | postgresql | Django | `django.db.backends.postgresql` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Sim | name `postgres`, user vazio | Django, entrypoint | `frota` / senha forte |
| `DB_HOST` / `DB_PORT` | Sim | host vazio, porta `6543` | Django | Compose: `db` / `5432` |
| `DB_SSLMODE` | Conforme rede | `require` | psycopg | Compose interno: `disable` |
| `DB_DISABLE_SERVER_SIDE_CURSORS` | Pooler | `True` | Django | Compose: `False` |
| `USE_SUPABASE_STORAGE` | Não | False | STORAGES | `False` no Compose mínimo |
| `SUPABASE_S3_*` | Se storage True | — | django-storages | não usar no Compose mínimo |
| `MEDIA_ROOT` / `STATIC_ROOT` | Compose | `BACKEND/media`, `staticfiles` | Django | `/app/media`, `/app/staticfiles` |
| `FROTA_EMAIL_ENABLED` | Não | False | `notificacoes.py` | `False` até a TI autorizar |
| `EMAIL_BACKEND` | Se e-mail | dummy | Django | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` `EMAIL_PORT` `EMAIL_HOST_USER` `EMAIL_HOST_PASSWORD` `EMAIL_USE_TLS` `EMAIL_USE_SSL` `DEFAULT_FROM_EMAIL` | Se e-mail | ver settings | Django | placeholders; **nunca** senha real na documentação |
| `VEICULO_IMAGEM_TAMANHO_MAXIMO_MB` | Não | 5 | veículos | `5` |
| `VEICULO_IMAGEM_MAXIMO_FOTOS` | Não | 8 | veículos | `8` |
| `SKIP_MIGRATE` / `SKIP_COLLECTSTATIC` | Só rotina | unset | entrypoint | `1` no serviço `rotina` |
| `HTTP_PORT` | Não | 80 | Compose | `80` ou `8080` |
| `VITE_API_URL` | Build frontend | detecção automática | Vite | Compose: `/api` |

## JWT (código, não env)

`ACCESS_TOKEN_LIFETIME`: 8 h. `REFRESH_TOKEN_LIFETIME`: 7 dias. Rotação e blacklist: True.

## Cuidados

- Trocar `AUDITORIA_CHAVE_INTEGRIDADE` após dados existentes faz a tela de integridade falhar.
- `DEBUG=True` força `ALLOWED_HOSTS=['*']`.
- Não commitar `.env`. O `.gitignore` da raiz já ignora.
