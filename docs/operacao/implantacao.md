# Guia de implantação — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |
| Procedimento Docker | Extraído de `compose.yaml`, Dockerfiles, `README-DOCKER.md` e `docker-entrypoint.sh` |
| TLS no Compose | **Não implementado** (recomendado à frente do Nginx) |

Complementa [README-DOCKER.md](../../README-DOCKER.md).

## Requisitos (produção Compose)

- Debian com Docker Engine 24+ e `docker compose`.
- Porta `HTTP_PORT` livre (padrão 80).
- Rede de saída no **build** (PyPI, npm). Em runtime, FIPE e Google Fonts são opcionais.
- Disco para volumes `pgdata`, `media`, `staticfiles`.

## Preparar o servidor (recomendado, não automatizado neste repo)

1. Usuário no grupo `docker`.
2. Diretório da aplicação (exemplo genérico: `/opt/frota` — ajuste à política local).
3. Copiar o projeto **sem** `.env` de outro ambiente.
4. `[ -f .env ] || cp .env.example .env` e preencher chaves.

## Subir

```bash
docker compose up -d --build
docker compose ps
docker compose exec backend python manage.py createsuperuser
```

Ordem: `db` healthy → `backend` (espera PG, `migrate`, `collectstatic`, Gunicorn) → `web`. `rotina` sobe com `SKIP_MIGRATE=1` após db e backend healthy.

Este fluxo está no Compose e no entrypoint. A execução em servidor de produção **não** foi ensaiada neste repositório.

Há units em `deploy/systemd/` como alternativa **sem** o container `rotina`. Não os habilite se o serviço Compose `rotina` já estiver no ar (duplicaria a rotina). Ajuste o caminho `/opt/frota` à instalação real.

## Pós-implantação

```bash
curl -sI "http://127.0.0.1:${HTTP_PORT:-80}/" | head -5
curl -sI "http://127.0.0.1:${HTTP_PORT:-80}/admin/login/" | head -5
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  "http://127.0.0.1:${HTTP_PORT:-80}/api/usuarios/login/"
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations | tail -20
```

O login JWT é **POST** (`CustomTokenObtainPairView`). Esperado com corpo vazio: **400**. GET no mesmo URL: **405**. Credenciais inválidas em POST: **401**. 502 = proxy/backend. Esta checagem **não** valida TLS.

Acessos: `/` SPA, `/api/`, `/admin/`, `/media/`.

## Atualização

```bash
# preserve .env
docker compose up -d --build
```

O backend reaplica migrate. Backup antes: [backup-restauracao.md](backup-restauracao.md).

## Rollback (recomendado)

Não há ferramenta de rollback no repositório. Procedimento proposto (pendente de ensaio):

1. Manter artefato/código da versão anterior.
2. Restaurar dump PostgreSQL e tarball de mídia **testados**.
3. `docker compose up -d --build` na versão anterior.
4. Não usar `down -v`.

## Desenvolvimento versus produção

| | Dev | Compose (prod documentado) |
|---|---|---|
| DEBUG | True (default settings) | False |
| API | :8000 direto | Nginx `/api` |
| SPA | Vite :5173 | estáticos no Nginx |
| DB | settings ou Supabase no example do BACKEND | `db:5432`, SSL disable |
| Rotina | comando manual | serviço `rotina` |
| CORS LAN | ligado se DEBUG | `CORS_ALLOW_LAN=False` |

## Falhas no boot

| Sintoma | Causa provável |
|---|---|
| backend unhealthy | migrate lento, `ALLOWED_HOSTS` sem localhost, Gunicorn não sobe |
| 502 | backend ainda não escuta |
| DisallowedHost | host público ausente em `ALLOWED_HOSTS` |
| CSRF Admin | origem sem esquema em `CSRF_TRUSTED_ORIGINS` |
