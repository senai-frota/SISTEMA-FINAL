# Frota SENAI — implantação com Docker (Debian)

Guia completo: [docs/operacao/implantacao.md](docs/operacao/implantacao.md). Índice da documentação: [docs/README.md](docs/README.md).

Instalação completa: **PostgreSQL + Django/Gunicorn + Nginx (SPA) + rotina operacional**.

- Schema do banco criado automaticamente (`migrate`).
- O boot **não** popula o banco: só aplica migrações, coleta estáticos e sobe o Gunicorn.
- Volumes persistentes: banco (`pgdata`) e uploads (`media`).
- PostgreSQL **não** é publicado na rede do host.

## O que transferir para o servidor

Transfira o **diretório completo** do repositório (não apenas `BACKEND/` ou `SISTEMA-FINAL/`). Os arquivos Docker ficam na **raiz** e precisam ir junto:

| Incluir | Não incluir |
|---------|-------------|
| `compose.yaml`, `.env.example`, `.dockerignore`, `.gitignore` | `.env` do PC intermediário (segredos) |
| `README-DOCKER.md`, `nginx/` | `SISTEMA-FINAL/node_modules/`, `SISTEMA-FINAL/dist/` |
| `BACKEND/` (código + `Dockerfile` + `docker-entrypoint.sh` + `requirements.txt`) | `BACKEND/.venv/`, `__pycache__/`, `media/`, `staticfiles/` |
| `SISTEMA-FINAL/` (código + `Dockerfile` + `package-lock.json` + `public/`) | backups locais |

Exemplo:

```bash
# No computador intermediário (sem .env):
rsync -a --exclude '.env' --exclude 'SISTEMA-FINAL/node_modules' \
  --exclude 'SISTEMA-FINAL/dist' --exclude '**/__pycache__' \
  ./FROTA/ usuario@servidor:/opt/frota/
```

No servidor, crie o `.env` a partir do exemplo — **não** reutilize o `.env` do PC intermediário.

## Pré-requisitos no servidor

- Debian com Docker Engine 24+ e plugin Compose (`docker compose version`)
- Acesso root ou usuário no grupo `docker`
- Porta HTTP livre (`HTTP_PORT`, padrão 80)
- Rede de saída **no build** das imagens (PyPI + npm registries). Em runtime: FIPE e Google Fonts são opcionais.

## 1. Preparar o `.env` (não sobrescrever)

```bash
cd /opt/frota

# Cria .env somente se ainda não existir
[ -f .env ] || cp .env.example .env
```

Edite o `.env` e defina no mínimo:

| Variável | Observação |
|----------|------------|
| `SECRET_KEY` | Chave Django (comando abaixo) |
| `AUDITORIA_CHAVE_INTEGRIDADE` | Estável; não alterar depois dos primeiros dados |
| `DB_PASSWORD` | Senha forte do PostgreSQL |
| `ALLOWED_HOSTS` | Hostname/IP de acesso **sem** esquema; **mantenha** `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Origem do navegador **com** `http://` ou `https://` |
| `CORS_ALLOWED_ORIGINS` | Em geral igual a `CSRF_TRUSTED_ORIGINS` |
| `HTTP_PORT` | `80` ou outra porta livre |

Gerar chaves:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

O Compose força `DB_HOST=db`, `DEBUG` padrão `False` e `USE_SUPABASE_STORAGE` padrão `False`.

**Nunca** versione o `.env`.

## 2. Construir e iniciar

```bash
cd /opt/frota
docker compose up -d --build
```

Ordem garantida:

1. `db` fica healthy (`pg_isready`)
2. `backend` espera o banco → `migrate` → `collectstatic` → Gunicorn
3. `web` (Nginx) sobe só após o backend healthy

**Não use** `docker compose down -v` — a flag `-v` remove os volumes e apaga banco e mídia.

## 3. Criar o superusuário

```bash
docker compose exec backend python manage.py createsuperuser
```

Informe matrícula, nome e senha (modelo `usuarios.Usuario`).

## 4. Verificar a aplicação

```bash
docker compose ps
curl -sI "http://127.0.0.1:${HTTP_PORT:-80}/" | head -5
curl -sI "http://127.0.0.1:${HTTP_PORT:-80}/admin/login/" | head -5
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  "http://127.0.0.1:${HTTP_PORT:-80}/api/usuarios/login/"
# Login é POST. Esperado com {}: 400. GET no mesmo URL: 405. 502/000 = falha de proxy.
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations | tail -20
```

Acessos no navegador (ajuste host/porta):

| Recurso | URL |
|---------|-----|
| Frontend | `http://SERVIDOR/` |
| API | `http://SERVIDOR/api/` |
| Admin | `http://SERVIDOR/admin/` |
| Mídia | `http://SERVIDOR/media/...` |

O frontend é compilado com `VITE_API_URL=/api` (mesmo origin). Não depende da porta 8000 no browser.

## 5. Logs

```bash
docker compose logs -f --tail=100
docker compose logs -f backend
docker compose logs -f rotina
docker compose logs -f web
docker compose logs -f db
```

## 6. Parar / reiniciar sem perder dados

```bash
docker compose stop
docker compose start
# ou
docker compose up -d
```

## 7. Backup e restauração

Use `DB_USER` / `DB_NAME` do `.env` (padrão: `frota`).

### PostgreSQL

```bash
docker compose exec -T db pg_dump -U frota -d frota -Fc > "frota-$(date +%Y%m%d).dump"
docker compose exec -T db pg_restore -U frota -d frota --clean --if-exists < frota-YYYYMMDD.dump
```

### Mídia (uploads)

```bash
docker compose exec -T backend tar czf - -C /app/media . > "media-$(date +%Y%m%d).tar.gz"
docker compose exec -T backend tar xzf - -C /app/media < media-YYYYMMDD.tar.gz
```

## 8. Atualizar sem perder dados

```bash
cd /opt/frota
# atualize o código; preserve o arquivo .env
docker compose up -d --build
```

## Estrutura

| Serviço | Função | Persistência |
|---------|--------|--------------|
| `db` | PostgreSQL 16 | volume `pgdata` |
| `backend` | Django + Gunicorn | volumes `media`, `staticfiles` |
| `rotina` | `rotina_operacional --loop` (60 s) | usa o mesmo banco; `SKIP_MIGRATE=1` |
| `web` | Nginx + SPA Vite | porta `HTTP_PORT` |

Sem Redis, Celery ou MinIO. Storage: disco local (`USE_SUPABASE_STORAGE=False`).

## Dependências externas (runtime)

| Recurso | Papel |
|---------|--------|
| PyPI / npm | Só no **build** das imagens |
| API FIPE (Parallelum) | Opcional (cadastro de veículo) |
| Google Fonts (CDN) | Opcional (tipografia no browser) |
| Supabase / S3 / Render | **Não** usados no Compose mínimo |

## Problemas comuns

| Sintoma | Ação |
|---------|------|
| `permission denied` no Docker socket | `usermod -aG docker USUARIO` e nova sessão, ou use root |
| 502 Bad Gateway | `docker compose logs backend` — aguarde migrate/Gunicorn |
| DisallowedHost | Inclua o host em `ALLOWED_HOSTS` (sem remover localhost) |
| CSRF no Admin | Inclua a origem com esquema em `CSRF_TRUSTED_ORIGINS` |
| `/media/` 404 | Confirme volumes e upload após o volume montado |
| Build sem internet | PyPI/npm precisam de rede no `docker compose build` |
| Healthcheck do backend falha | Mantenha `localhost` em `ALLOWED_HOSTS` |
