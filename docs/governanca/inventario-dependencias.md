# Inventário de ativos e dependências

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Fontes | `requirements.txt`, `package-lock.json` (versões de package.json), imagens Docker |

Licenças: conferidas pelos nomes dos pacotes (MIT/BSD/Apache típicos). Não há varredura `pip-licenses` neste repositório.

## Componentes internos

| Ativo | Local |
|---|---|
| API Django | `BACKEND/` |
| SPA | `SISTEMA-FINAL/` |
| Nginx config | `nginx/default.conf` |
| Compose | `compose.yaml` |
| Docs | `docs/` |

## Bibliotecas backend (principais)

| Pacote | Versão pinada |
|---|---|
| Django | 5.2.17 |
| djangorestframework | 3.18.0 |
| djangorestframework_simplejwt | 5.5.1 |
| django-cors-headers | 4.9.0 |
| django-filter | 26.1 |
| django-storages[s3] | 1.14.6 |
| gunicorn | 26.0.0 |
| psycopg2-binary | 2.9.11 |
| pillow | 12.3.0 |
| python-decouple | 3.8 |
| requests | 2.34.2 |
| PyJWT | 2.13.0 |
| boto3 | >=1.35,<2 |
| reportlab | 4.4.3 |
| openpyxl | 3.1.5 |

Python da imagem: 3.12-slim-bookworm.

## Frontend

| Pacote | Faixa em package.json |
|---|---|
| react / react-dom | ^18.3.1 |
| react-router-dom | ^6.26.2 |
| axios | ^1.7.7 |
| vite | ^5.4.8 |
| @vitejs/plugin-react | ^4.3.1 |

Node da imagem de build: 20-alpine. Nginx runtime: 1.27-alpine.

## Serviços externos

| Serviço | Uso | Crítico? |
|---|---|---|
| PyPI / npm | só build | Sim no deploy |
| parallelum.com.br FIPE | consulta marcas/modelos | Não (cadastro manual) |
| fonts.googleapis.com | tipografia SPA | Não |
| SMTP | e-mail operacional | Não (desligado) |
| Supabase | opcional DB/storage | Não no Compose mínimo |

## Imagens Docker

postgres:16-alpine; python:3.12-slim-bookworm; node:20-alpine; nginx:1.27-alpine.

## Riscos de desatualização

Dependências pinadas reduzem surpresa, mas exigem atualização periódica (Django LTS, Pillow, urllib3). Sem Dependabot/CI neste repo.
