# Checklist de entrega e operação

| Campo | Valor |
|---|---|
| Versão | 1.1 |
| Data | 28 de outubro de 2026 |

Use em cada promoção de versão. Itens “não executados” devem permanecer abertos.

## Build

- [ ] `npm run build` em `SISTEMA-FINAL`
- [ ] `python manage.py check` no backend
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

- [ ] Login admin e funcionário; primeiro acesso
- [ ] SPA em `/` e API em `/api/`
- [ ] Admin Django se utilizado
- [ ] Upload e leitura `/media/`
- [ ] Upload CNH e termo; aprovação
- [ ] Reserva turno e horário; conflito; 14 dias
- [ ] Check-in mobile com 5 fotos; check-out na mesma unidade
- [ ] Check-in antecipado
- [ ] Recusa com e sem justificativa
- [ ] Relatório Excel (admin) e 403 (funcionário)
- [ ] Integridade da auditoria
- [ ] `rotina_operacional` em reserva vencida sem check-in
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
