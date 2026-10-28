# Troubleshooting

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |

| Sintoma | Causas possíveis | Diagnóstico | Solução | Validação |
|---|---|---|---|---|
| 502 Bad Gateway | backend fora, migrate em andamento | `docker compose logs backend` | aguardar healthy; `docker compose up -d` | `curl -X POST /api/usuarios/login/` com `{}` → 400 |
| DisallowedHost | host ausente | log Django | incluir host em `ALLOWED_HOSTS` **sem** remover localhost | healthcheck + acesso pelo hostname |
| CSRF 403 no Admin | origem não listada | console da aba Admin | `CSRF_TRUSTED_ORIGINS` com `http(s)://` | salvar um objeto no Admin |
| SPA chama :8000 em produção | imagem web buildada sem `VITE_API_URL=/api` | rede do browser | rebuild com ARG do Compose | requests em `/api/` same-origin |
| Check-in recusado no PC | `exigir_cliente_mobile` | mensagem da API | usar celular | POST registrar 201 |
| Check-in fora de horário | 06:00–22:00 ou ±30 min | horário do servidor `America/Sao_Paulo` | esperar janela ou antecipação | 201 na janela |
| Check-out unidade errada | `unidade_checkin` diferente | reserva na API | mesma unidade do check-in | 201 |
| Reserva não cancela sozinha | `rotina` parada | `docker compose logs rotina` | subir serviço; comando avulso | status `cancelada` após meia-noite aplicável |
| FIPE 503 | Parallelum indisponível | log `Consulta FIPE falhou` | cadastrar veículo manualmente | POST veículo 201 |
| Integridade auditoria falha | chave HMAC alterada ou DB adulterado | `GET /auditoria/integridade/` | **não** “consertar” hashes; restaurar backup e chave correta | `integra: true` |
| `/media/` 404 | volume vazio ou upload antes do mount | `docker compose exec backend ls /app/media` | conferir volume; reenviar arquivo | URL 200 |
| Login 400 sempre | senha ou modo 1º acesso invertidos | corpo da resposta | seguir fluxo de `precisa_definir_senha` | 200 + tokens |
| Funcionário vê tela admin | `is_admin=True` no cadastro | perfil JSON | corrigir flag (procedimento de RH/TI, não automático) | rotas adminOnly redirecionam |
| E-mail não chega | `FROTA_EMAIL_ENABLED=false` | log `reservas.operacoes` “desligado” | não ligar sem SMTP institucional | log “enviado” só se habilitado |
| permission denied Docker | usuário fora do grupo | `groups` | `usermod -aG docker` + nova sessão | `docker compose ps` |
| Disco cheio | dumps, logs, media | `df -h` | arquivar dumps; **não** apagar `pgdata` | serviços healthy |

Comandos destrutivos (`down -v`, `pg_restore --clean` em produção, `flush`) **não** são solução rotineira.
