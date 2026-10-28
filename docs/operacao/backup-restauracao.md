# Backup e restauração

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |
| Status dos procedimentos | Documentados; restauração **não ensaiada** neste repositório |

## O que proteger

| Ativo | Onde | Criticidade |
|---|---|---|
| Banco PostgreSQL | volume `pgdata` | máxima |
| Uploads | volume `media` | máxima (CNH, termos, fotos) |
| `.env` | host | máxima (segredos) — backup **offline** controlado, nunca no Git |
| Código | repositório | alta |
| `staticfiles` | regenerável via collectstatic | baixa |
| Cadeia de auditoria | tabela no banco | máxima; depende da chave HMAC |

## PostgreSQL (Compose)

Substitua `frota` se `DB_USER`/`DB_NAME` forem outros.

```bash
docker compose exec -T db pg_dump -U frota -d frota -Fc > "frota-$(date +%Y%m%d).dump"
```

Restauração (destrutiva para o **conteúdo atual do banco**, não para o volume Docker):

```bash
docker compose exec -T db pg_restore -U frota -d frota --clean --if-exists < frota-AAAAMMDD.dump
```

A opção `--clean --if-exists` recria os objetos **dentro** do banco. Não use `docker compose down -v`: a flag `-v` apaga os volumes `pgdata` e `media`.

**Não execute restauração em produção sem janela e backup imediatamente anterior.** Este procedimento **não foi ensaiado**. Integridade do dump só é válida após restore de teste em ambiente isolado.

## Mídia

```bash
docker compose exec -T backend tar czf - -C /app/media . > "media-$(date +%Y%m%d).tar.gz"
docker compose exec -T backend tar xzf - -C /app/media < media-AAAAMMDD.tar.gz
```

A extração sobrescreve arquivos no volume `media`; não remove o volume. Ensaio apenas em clone, nunca nos volumes de produção.

## Frequência, retenção, local (propostos)

Não há job de backup no Compose. Metas **recomendadas** (não contratadas no código):

| Item | Proposta |
|---|---|
| Frequência | diário do banco; mídia diária ou contínua se o volume permitir |
| Retenção | 14–30 dias de dumps; 1 cópia offsite |
| Local | armazenamento institucional criptografado, fora do mesmo disco do servidor |
| RPO proposto | 24 h (se backup diário) |
| RTO proposto | a definir pela TI após ensaio |

## Verificação

1. Restore em clone Docker **sem** volumes de produção.
2. `manage.py check`, login, abrir um arquivo `/media/` conhecido.
3. `GET /api/auditoria/integridade/` (admin) — deve permanecer íntegra se a chave HMAC for a mesma.

## Storage Supabase

Se `USE_SUPABASE_STORAGE=True`, o tarball de `/app/media` **não** cobre os objetos do bucket. Backup do bucket é responsabilidade da plataforma — **não documentado como procedimento testado aqui**.
