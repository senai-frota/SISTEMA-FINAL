# ADR-003 — Auditoria append-only com HMAC

Registros imutáveis, sequência e HMAC-SHA256 (`AUDITORIA_CHAVE_INTEGRIDADE`). Endpoint de verificação somente leitura para admin.

Consequência: chave deve ser estável; restore de banco precisa da mesma chave. Não substitui WORM externo.
