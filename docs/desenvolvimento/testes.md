# Testes e qualidade — FROTA-SENAI

| Campo | Valor |
|---|---|
| Versão | 1.0 |
| Data | 26 de outubro de 2026 |
| Classificação | Uso interno |

## Como executar

```bash
cd BACKEND
.venv/bin/python manage.py test --settings=config.test_settings
```

Frontend: não há Jest/Vitest. Qualidade de entrega: `npm run build` em `SISTEMA-FINAL`.

Lint: não há ESLint/Ruff configurados no repositório.

## Inventário (`def test_` no código)

Total: **190**.

| Módulo | Arquivo | Qtd | Foco |
|---|---|---|---|
| usuarios | `tests.py` | 23 | listagem, CNH, 1º acesso, inativação |
| veiculos | `tests.py` | 21 | permissões, imagens, FIPE 503 |
| reservas | `tests.py` | 42 | 14 dias, CNH, turno, pernoite, fluxo |
| reservas | `tests_operacoes.py` | 13 | antecipado, auto-cancel, checkout atrasado |
| vistorias | `tests.py` | 29 | mobile, fotos, janela, unidade, km |
| termos | `tests.py` | 9 | validade, reserva |
| relatorios | `tests.py` | 16 | 403, xlsx, filtros |
| auditoria | `tests.py` | 8 | permissão, arquivos |
| auditoria | `test_integridade.py` | 15 | HMAC, imutabilidade |
| auditoria | `test_recusas.py` | 14 | justificativas |

## Última execução local

| Comando | Resultado | Data |
|---|---|---|
| `manage.py test --settings=config.test_settings` | 190 OK em ~228 s | 26/10/2026 |
| `npm run build` (SISTEMA-FINAL) | OK (Vite 5.4.21) | 26/10/2026 |

## Lacunas

- Sem testes E2E da SPA.
- Sem teste de isolamento de alerta por terceiro usuário (o filtro `usuario=usuario` permanece no backend).
- Sem cobertura percentual (`coverage` não está em `requirements.txt`).

## Regressão recomendada (homologação)

1. Login funcionário e admin; primeiro acesso.
2. Upload CNH e termo; aprovação.
3. Reserva turno e horário; conflito; 14 dias.
4. Check-in mobile com 5 fotos; check-out na mesma unidade.
5. Check-in antecipado.
6. Recusa com e sem justificativa.
7. Relatório Excel (admin) e 403 (funcionário).
8. Integridade da auditoria.
9. `rotina_operacional` em reserva vencida sem check-in.
