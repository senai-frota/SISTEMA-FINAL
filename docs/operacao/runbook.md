# Runbook operacional — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |
| Risco | Não usar `docker compose down -v` nem `flush` |

Pré-condição: diretório do Compose e permissão Docker.

## 1. Estado dos serviços

```bash
docker compose ps
docker compose exec backend python manage.py check
```

Esperado: `db`, `backend`, `rotina`, `web` Up (backend/web healthy).

## 2. Logs

```bash
docker compose logs -f --tail=100
docker compose logs -f backend
docker compose logs -f rotina
docker compose logs -f web
docker compose logs -f db
```

Loggers de aplicação: `reservas.operacoes`, `vistorias.desempenho` (stdout).

## 3. Frontend não carrega

1. `curl -sI http://127.0.0.1:${HTTP_PORT:-80}/`
2. Logs `web`.
3. Confirmar build da imagem (SPA está na imagem, não em volume de código).

## 4. API 502 / 401 inesperado

1. Logs `backend`.
2. Healthcheck: `docker compose exec backend python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/admin/login/', headers={'Host':'localhost'}), timeout=5)"`
3. 401 em rotas autenticadas é normal sem Bearer.

## 5. Banco

```bash
docker compose exec db pg_isready -U frota -d frota
```

Ajuste usuário/banco ao `.env` (`DB_USER`, `DB_NAME`).

Não publique a porta 5432 no host (Compose atual não publica).

## 6. Reinício seguro

```bash
docker compose stop
docker compose start
# ou
docker compose up -d
```

Reinício do `backend` dispara migrate de novo (idempotente se já aplicado).

## 7. Disco

```bash
df -h
docker system df
```

Volumes críticos: `pgdata`, `media`. Limpeza `docker system prune` **não** é rotina (risco de apagar imagens ainda úteis; não remove volumes nomeados sem `-a --volumes`).

## 8. Rotina operacional parada

Sintoma: reservas aprovadas sem check-in não cancelam após a meia-noite do dia seguinte.

```bash
docker compose logs rotina --tail=50
docker compose exec backend python manage.py rotina_operacional
```

O comando avulso no backend executa **uma** passagem. O serviço `rotina` é o loop.

## 9. Escalação

1. Reproduzir horário (fuso America/Sao_Paulo).
2. Guardar `docker compose logs` (sem colar `.env`).
3. Verificar auditoria (`/auditoria`) se a ação deveria ter gerado registro.
4. Envolver TI para SMTP, DNS, TLS e disco.

## 10. Confirmar recuperação

- `docker compose ps` healthy
- Login na SPA
- `POST /api/usuarios/login/` com `{}` responde 400 (GET nesse URL responde 405)
- Uma reserva de teste em homologação, nunca dados de produção improvisados
