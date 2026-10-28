# Checklist de entrega e operação

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |

Use em cada promoção de versão. Itens “não executados” devem permanecer abertos.

## Build e testes

- [ ] `python manage.py test --settings=config.test_settings`
- [ ] `npm run build` em `SISTEMA-FINAL`
- [ ] Sem segredos no diff

## Segurança

- [ ] `DEBUG=False` no ambiente alvo
- [ ] `.env` não versionado; chaves novas se for instalação nova
- [ ] `is_admin` revisado
- [ ] TLS se o ambiente for público
- [ ] [checklist de segurança](../seguranca/checklist.md)

## Backup

- [ ] Dump PostgreSQL recente
- [ ] Tarball `media`
- [ ] Cópia controlada do `.env` (cofre)

## Deploy Compose

- [ ] Código atualizado sem sobrescrever `.env`
- [ ] `docker compose up -d --build`
- [ ] `docker compose ps` healthy (`db`, `backend`, `rotina`, `web`)
- [ ] `showmigrations` coerente

## Validação funcional

- [ ] Login admin e funcionário
- [ ] SPA em `/` e API em `/api/`
- [ ] Admin Django se utilizado
- [ ] Upload e leitura `/media/`
- [ ] Uma reserva de homologação (não produção real)

## Rollback

- [ ] Imagem/código anterior disponível
- [ ] Dump pré-deploy guardado
- [ ] Procedimento [backup-restauracao.md](../operacao/backup-restauracao.md) conhecido

## Aprovação

| Papel | Nome | Data | Assinatura |
|---|---|---|---|
| Desenvolvimento | | | |
| Operação / TI | | | |
| Gestor da frota | | | |
