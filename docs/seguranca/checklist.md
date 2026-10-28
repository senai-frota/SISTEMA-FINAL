# Segurança

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |
| Conformidade LGPD/OWASP | **Não afirmada.** Há tratamento de dados pessoais no sistema; faltam DPO, RIPD e pentest neste repositório. |

## Autenticação e autorização

- JWT Bearer; access 8 h; refresh 7 dias com rotação e blacklist.
- Login por matrícula; primeiro acesso sem senha usável.
- Autorização: `is_admin` + dono do objeto. Frontend apenas esconde rotas.
- Conta inativa ainda autentica; reserva bloqueada.

## Segredos

- `.env` no gitignore.
- `SECRET_KEY` e `AUDITORIA_CHAVE_INTEGRIDADE` distintas e estáveis.
- Senhas SMTP nunca na documentação nem no Git.
- `auditoria/services` registra detalhes **sem** senha/token/arquivo (há teste de limpeza).

## Endpoints

- Padrão: autenticado + senha definida.
- Admin: relatórios, auditoria, pendências, decisões.
- Uploads: tipos e tamanhos nas views de veículo/CNH/termo/vistoria; Nginx `client_max_body_size 25m`.
- `/media/` com `Cache-Control: private` no Nginx — **não** substitui autenticação: o Nginx serve o arquivo se a URL for conhecida (**lacuna**: URLs enumeráveis se o nome for previsível).

## CORS / CSRF / HTTPS

- CORS explícito; LAN só com `CORS_ALLOW_LAN`.
- CSRF no Admin Django.
- Compose escuta HTTP. HTTPS: **recomendado** no proxy; `SECURE_PROXY_SSL_HEADER` só com TLS real.
- Sem HSTS/configuração Django de cookies secure no `settings.py` analisado (**lacuna** em HTTP puro).

## Validação

- Serializers DRF, maiúsculas em campos de texto de reserva.
- CNH numérica validada no termo.
- Check-in mobile: cabeçalhos podem ser forjados por cliente HTTP; é **sinal**, não atestado de hardware.

## Dados pessoais

Presentes: nome, matrícula, e-mail, telefone, CPF, número de CNH, fotos do veículo e eventualmente do interior (painel). Base legal e retenção: **pendente de política institucional**.

## Backup

Ver [backup-restauracao.md](../operacao/backup-restauracao.md). Sem job automático no Compose.

## Checklist de produção (recomendado)

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` e HMAC fortes e únicos
- [ ] `ALLOWED_HOSTS` mínimo + localhost para healthcheck
- [ ] CORS/CSRF alinhados à origem pública
- [ ] TLS na frente do Nginx
- [ ] `FROTA_EMAIL_ENABLED` só com SMTP oficial
- [ ] `USE_SUPABASE_STORAGE` coerente com a topologia
- [ ] Backup ensaiado
- [ ] Superusuário criado; senhas iniciais trocadas
- [ ] Volumes sem `down -v`
- [ ] Integridade da auditoria após o go-live
- [ ] Revisão de quem possui `is_admin=True`

## Lacunas priorizadas

| Prioridade | Item | Evidência |
|---|---|---|
| Alta | HTTPS não vem no Compose | `nginx/default.conf` listen 80 |
| Alta | `/media/` sem auth no Nginx | `alias /var/www/media` |
| Alta | Backup não agendado | ausência de cron no repo |
| Média | FIPE depende de rede externa | HTTP 503 + cadastro manual |
| Média | Client mobile forjável | `dispositivo.py` |
| Média | Sem CI | ausência de workflows |
| Baixa | E-mail desligado | intencional |
